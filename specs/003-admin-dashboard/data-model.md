# Data Model: Admin Dashboard


This feature is primarily a read/moderate/delete surface over two **existing** models. It introduces at most one new field (pending sign-off — see plan.md), and no new models.

## Existing: `therapist.MoodEntry`

Unchanged fields (from `therapist/models.py`):

| Field | Type | Notes |
|---|---|---|
| `id` | AutoField (PK) | |
| `user_id` | CharField(128), indexed | `str(request.user.id)`, never client-supplied |
| `emoji` | CharField(10) | |
| `thoughts` | TextField | Full journal text — truncated in admin list view, full on detail view |
| `ai_response` | TextField | Full AI reply — truncated in admin list view, full on detail view |
| `created_at` | DateTimeField, `auto_now_add=True` | Read-only in admin (FR-004) |

**Proposed new field (pending sign-off, see plan.md "Decisions Requiring Sign-Off")**:

| Field | Type | Notes |
|---|---|---|
| `crisis_flagged` | BooleanField, `default=False`, `db_index=True` | Set once at creation time in `GenerateResponseAPIView.post()` from the already-computed `contains_crisis_language(thoughts)` result. Powers FR-003 (admin filter) and FR-010 (analytics counts). Requires a migration + one-time backfill for existing rows (re-run `contains_crisis_language()` over stored `thoughts`). |

No relationships change — `MoodEntry.user_id` remains a loosely-typed string reference to `accounts.User.id`, not a ForeignKey (existing design, unchanged by this feature; see `README.md`'s note that account deletion is "an explicit query-and-delete, not a database-level cascade").

## Existing: `accounts.User`

Unchanged — no new fields. Fields relevant to this feature's admin views: `email`, `username`, `is_active`, `is_verified`, `is_staff`, `firebase_uid`, `created_at`.

**Derived (not stored) per-user values shown in the dashboard**:
- **Journal entry count**: `MoodEntry.objects.filter(user_id=str(user.id)).count()`, computed at render time for the user list/detail — not stored on `User`.
- **Streak**: `therapist.views.calculate_streak(user_id)`, computed at render time — not stored.

## New (not a model): Dashboard summary aggregates

Computed at request time by the analytics view/callback (FR-010, FR-011), not persisted anywhere:

| Metric | Source query (conceptual) |
|---|---|
| Total active users | `User.objects.filter(is_active=True).count()` |
| New entries, last 7 days | `MoodEntry.objects.filter(created_at__gte=now-7d).count()` |
| New entries, last 30 days | `MoodEntry.objects.filter(created_at__gte=now-30d).count()` |
| Crisis-flagged entries, last 7 days | `MoodEntry.objects.filter(crisis_flagged=True, created_at__gte=now-7d).count()` (depends on the new field above) |
| Crisis-flagged entries, last 30 days | `MoodEntry.objects.filter(crisis_flagged=True, created_at__gte=now-30d).count()` (depends on the new field above) |
| Average streak | `mean(calculate_streak(u.id) for u in users with >=1 entry)` |

## State transitions

None introduced. `MoodEntry` rows are still create-once/read-many (no admin edit path for content); `User` rows gain one new terminal transition already documented elsewhere (delete), now reachable via one more entry point (admin action) that calls the same existing `delete_user_account()` — no new state machine.
