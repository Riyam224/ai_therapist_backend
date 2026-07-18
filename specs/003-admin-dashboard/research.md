# Research: Admin Dashboard

## 1. Admin theme package: django-unfold

**Decision**: Use `django-unfold` as a drop-in Django Admin theme (`INSTALLED_APPS` entry placed before `django.contrib.admin`), configured via a `UNFOLD` settings dict in `core/settings.py`. No custom admin site subclass, no separate app.

**Rationale**: This was specified directly by the requester as the tool to use, and it satisfies Constitution Principle V (Simplicity) because it's a theme layer over the existing `django.contrib.admin` registry — `UserAdmin` and `MoodEntryAdmin` keep their current `ModelAdmin` structure and gain Unfold's styling/behavior by inheriting from Unfold's `ModelAdmin` base class (or by Unfold's app-level styling hook, depending on version) rather than being rewritten.

**Alternatives considered**: `django-grappelli`, `django-jazzmin` — both viable, but the requester named `django-unfold` explicitly and it has native support for a dashboard callback (needed for item 4) and Tailwind-based modern styling out of the box, avoiding a second package for custom dashboard widgets.

**Setup requirements found**:
- `INSTALLED_APPS`: `"unfold"` (and `"unfold.contrib.filters"` only if using Unfold's enhanced filter widgets — not required for the filters this feature needs, since `list_filter` entries here are plain field names/date hierarchy) must precede `"django.contrib.admin"`.
- Minimum `UNFOLD` dict: `{"SITE_TITLE": "Lueur Admin", "SITE_HEADER": "Lueper Admin"}` plus optional `SITE_SYMBOL` — exact keys to confirm against the installed version's docs at implementation time, since Unfold's settings surface changes between minor versions.
- `ModelAdmin` classes that want Unfold's styled forms/lists inherit from `unfold.admin.ModelAdmin` instead of `django.contrib.admin.ModelAdmin` (drop-in replacement, same API).

## 2. Persisting `crisis_flagged` on `MoodEntry`

**Decision (recommended, pending requester sign-off per their explicit "ask before adding a migration" instruction)**: Add a real `crisis_flagged = models.BooleanField(default=False, db_index=True)` column to `therapist.MoodEntry`, set once at creation time in `GenerateResponseAPIView.post()` (the value is already computed there via `contains_crisis_language(thoughts)` — this only persists a value already being calculated, it does not change the crisis-detection logic itself).

**Rationale**: `list_filter` in Django Admin requires either a real field or a `SimpleListFilter` that runs a query. Recomputing `contains_crisis_language(entry.thoughts)` per-row at filter time (the no-migration alternative) means every filtered admin page load does an unindexed full-table regex scan in Python, and the same classification logic ends up duplicated between `therapist/crisis.py` (source of truth) and a second admin-only code path — both of which conflict with Simplicity/Principle V's single-source-of-truth spirit and won't scale as entries grow. A stored, indexed boolean also directly serves FR-010's "crisis-flagged entries in the last 7/30 days" analytics counts (`MoodEntry.objects.filter(crisis_flagged=True, created_at__gte=...)` — one indexed query, no per-row Python evaluation at read time).

**Alternatives considered**: `SimpleListFilter` recomputing the flag live — rejected as above (no index, duplicated logic, gets slower as the table grows, and analytics queries in item 4 would need the same expensive recomputation). A denormalized flag with periodic backfill job — rejected as unnecessary complexity for a value that's already computed once at write time.

**Backfill note**: Existing rows created before this migration have no reliable way to know their original flagged status was ever computed with today's `CRISIS_KEYWORDS`, but `thoughts` text is still stored, so a one-time data migration can backfill `crisis_flagged` for existing rows by re-running today's `contains_crisis_language()` over stored `thoughts` — this is a deliberate one-time reclassification of history, not a live dual-write, and should be called out explicitly when asking for sign-off.

**Status**: NOT yet implemented — requires explicit requester approval before the migration is written, per their instruction. See plan.md "Decisions Requiring Sign-Off."

## 3. Analytics aggregates (item 4)

**Decision**: A single dashboard-callback function computes all six FR-010 figures with plain Django ORM aggregation (`Count`, `Q` filters on `created_at__gte`) run at request time — no caching layer, no new model, no scheduled job.

**Rationale**: Constitution Principle V forbids adding a caching layer without a demonstrated performance problem, and FR-011 requires figures to reflect current data, which rules out a stale precomputed snapshot anyway. The user/entry volumes implied by this project (a single-developer wellness app) make a handful of `COUNT(*)` queries trivially fast; no charting library is needed for six numbers, matching the requester's explicit "ask before adding a dependency for this" — the answer is: no new dependency needed.

**Average streak**: Reuses `therapist.views.calculate_streak(user_id)` unchanged — iterate over `User.objects.filter(moodentry__isnull=False).distinct()` (or equivalent — exact query to be finalized in data-model.md) and average the per-user streak. `calculate_streak` is a pure function taking a `user_id`, so this is a straight reuse, not a reimplementation.

**Alternatives considered**: A `django-unfold` "chart" widget — explicitly out of scope per the requester (no charting library unless justified, and 6 aggregate numbers don't justify one).

## 4. Static assets in production (WhiteNoise)

**Decision**: No new static-file configuration is needed beyond what already exists. `django-unfold` ships its static assets inside its own app package (`unfold/static/`); because `"unfold"` is a normal `INSTALLED_APPS` entry, Django's `collectstatic` (already run via `STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"`) discovers and copies them into `staticfiles/` automatically via the standard `AppDirectoriesFinder`, the same mechanism that already picks up `rest_framework`'s and `drf_spectacular`'s static assets today (both already render styled in production, per the existing Swagger/ReDoc screenshots in `README.md`).

**Verification step (to run during implementation, not research)**: after adding `"unfold"` to `INSTALLED_APPS`, run `python manage.py collectstatic` locally and grep `staticfiles/` for an `unfold/` directory to confirm assets landed, exactly as the requester asked — this is a build-time check, not a design decision, so it's tracked as a task rather than resolved here.

**Rationale for confidence**: `rest_framework` and `drf_spectacular` are existing proof that this project's static pipeline already correctly picks up third-party app static assets in production (README's Swagger UI / ReDoc screenshots show fully styled output on the real deployment target's static pipeline). `django-unfold` uses the same Django static-file app-discovery convention.

## 5. Destructive admin action confirmation pattern

**Decision**: Implement the "Delete account and journal entries" action as a standard Django Admin `@admin.action` that, instead of deleting immediately, redirects to a small intermediate confirmation template (Django's documented pattern for actions that need an "are you sure?" step — the built-in delete action already does this, and custom actions replicate it via `TemplateResponse` when no `POST["post"]` confirmation key is present yet).

**Rationale**: Django Admin actions do not get a confirmation step for free unless implemented this way — only the built-in "Delete selected" action has one built in. Requiring confirmation was an explicit functional requirement (FR-008) tied to the action being irreversible, so skipping this would violate that requirement.

**Alternatives considered**: JavaScript `confirm()` dialog on the frontend only — rejected as a UX-only guard with no server-side enforcement (a resubmitted/replayed request would bypass it); the intermediate-page pattern enforces confirmation server-side.

## 6. Reuse of `delete_user_account()`

**Decision**: The admin action calls `accounts.services.delete_user_account(user)` directly — the exact function already used by `DeleteAccountView` (API) and `delete_user_by_email` (management command). No new deletion code path.

**Rationale**: Directly satisfies FR-007/FR-009 and Constitution Principle V (no duplicated logic) and matches the existing pattern already documented in `README.md`'s "Account Deletion" section ("Both paths share one implementation").

## 7. `LogEntry` / audit-log content check (FR-012)

**Finding**: Django's built-in `django.contrib.admin.models.LogEntry` stores a `change_message` (a short JSON-encoded summary of which fields changed, e.g. `[{"changed": {"fields": ["full_name"]}}]`) — it does **not** store full field values by default, only field *names* for changes and the object's `__str__()` repr as `object_repr`. Since `MoodEntry.__str__` already truncates to `thoughts[:20]` (existing code, `therapist/models.py`), `LogEntry.object_repr` for a `MoodEntry` change/delete is already bounded to 20 characters of journal text plus the emoji — this is a pre-existing, minor exposure (20 chars, not full content) that predates this feature. No admin edit path for `thoughts`/`ai_response` is being added by this feature (MoodEntry admin stays read-mostly: `readonly_fields` covers `created_at`, and no requirement asks for editable journal text), so `LogEntry` will only ever log the custom delete action against `User` objects (whose `__str__` is just an email address) and any read-only view of `MoodEntry` doesn't create `LogEntry` rows at all (Django only logs add/change/delete, not views). **Conclusion**: no additional scrubbing needed; FR-012 is satisfied by the existing `__str__` truncation plus this feature not introducing any new edit path for journal text.
