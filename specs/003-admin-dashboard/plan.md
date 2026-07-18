# Implementation Plan: Admin Dashboard

**Branch**: `003-admin-dashboard` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-admin-dashboard/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add a staff-only operational dashboard by theming and extending the existing Django Admin (via `django-unfold`) rather than building a separate app: richer `MoodEntryAdmin`/`UserAdmin` list/filter/detail views, a per-user journal-entry count and link, a small analytics summary view of aggregate counts (reusing `calculate_streak()`), and a confirmation-gated admin action that calls the existing `accounts.services.delete_user_account()` — the same deletion function already used by the API and the `delete_user_by_email` management command. No new deletion logic, no new public API surface, no charting library.

## Decisions Requiring Sign-Off Before Implementation

These were explicitly called out in the originating request as needing approval before proceeding — `research.md` documents the recommended answer for each, but none should be implemented until confirmed:

1. ~~**Persisting `crisis_flagged` as a real `MoodEntry` column**~~ — **APPROVED 2026-07-17.** Add a migration + one-time backfill of existing rows via re-running `contains_crisis_language()` over stored `thoughts`, per `research.md` §2. Proceed with this in `/speckit-tasks`.
2. **Any dependency beyond `django-unfold`** — research found none needed (six aggregate numbers don't warrant a charting library). No ask needed unless that changes during implementation.
3. **IP-restricting `/admin/`** at the Railway/proxy level — recommended as a defense-in-depth follow-up, explicitly **not** part of this feature's implementation; `is_staff` gating is the enforced control here (FR-001).

## Technical Context

**Language/Version**: Python 3.11.9 (pinned, `runtime.txt`), Django 5.1.4

**Primary Dependencies**: `django-unfold` (new — approved by the requester by name), Django's built-in `django.contrib.admin`, existing `rest_framework`/`drf-spectacular` (unaffected)

**Storage**: Same PostgreSQL (prod, via `dj-database-url`) / SQLite (dev) as the rest of the project — no new datastore. One possible new column (`MoodEntry.crisis_flagged`) pending sign-off above.

**Testing**: `python manage.py test` (Django's `TestCase` + DRF `APIClient`), same mocking conventions as `accounts/tests.py` / `therapist/tests.py` (mock `firebase_admin.auth.delete_user` for the deletion-action test)

**Target Platform**: Same as existing project — Railway (Gunicorn + WhiteNoise), Linux server

**Project Type**: Web service (Django monolith) — this feature adds no new project/app, only new `ModelAdmin` configuration, one custom admin view, and settings changes within the existing `core`/`therapist`/`accounts` apps

**Performance Goals**: No specific target beyond "the analytics view stays fast with plain COUNT queries at this project's scale" (research.md §3) — not a high-traffic surface (internal staff tool)

**Constraints**: Must not introduce a second account-deletion implementation (Constitution Principle V / spec FR-007); must not expose full journal text outside dedicated entry views, including in `LogEntry` (spec FR-012, research.md §7); must render correctly under WhiteNoise on Railway, not just `runserver` (spec FR-013, SC-006)

**Scale/Scope**: Single Django project, two existing apps (`therapist`, `accounts`) gain admin-layer changes only; no new app is created

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Data Isolation & Privacy, NON-NEGOTIABLE)** — This principle governs *API endpoints* (`therapist/`, `accounts/` views) reachable by end users: no client-supplied identifier, no cross-user aggregation. This feature adds no new API endpoint and touches no API view. Django Admin is a separate, `is_staff`-gated internal surface, and cross-user visibility is the entire point of an admin/support tool — a staff operator looking up a specific user by design sees data across users. **Not a violation**: the principle's rationale (closing an IDOR-shaped risk on the public API) doesn't extend to an authenticated internal tool restricted to staff, and no public endpoint's isolation behavior changes. Documented here rather than silently assumed, since the letter of "no endpoint may aggregate data across users" could be misread to include this. ✅ PASS (with this note on record).
- **Principle II (Input & Contract Validation)** — No new client-facing request/response contract is introduced (Django Admin forms are server-rendered, not part of the DRF/drf-spectacular API surface); N/A to this feature. ✅ PASS.
- **Principle III (Resilient External AI Integration)** — Not touched; no AI call added or modified. ✅ PASS.
- **Principle IV (Test Coverage for Critical Flows)** — The new admin delete action is a new critical flow (irreversible deletion) and MUST have a test mocking `firebase_admin.auth.delete_user` and asserting real DB state, per spec item 7 / FR-007–FR-009. Planned in tasks. ✅ PASS (pending task execution).
- **Principle V (Simplicity & Statelessness)** — `django-unfold` is one new dependency; justified because (a) it was explicitly requested by name, (b) it replaces no existing working code, it only themes the existing `ModelAdmin` registry, and (c) research (§1, §4) found it reuses the project's existing static-file pipeline with no extra config. The analytics view deliberately avoids caching and a charting library per research §3, in line with this principle. The `crisis_flagged` field (pending sign-off) is the smallest schema change that satisfies FR-003/FR-010 without duplicating classification logic — see research §2 for why the zero-migration alternative is rejected as *more* complex, not less (duplicated logic + unindexed scans). ✅ PASS.
- **Security & Deployment Requirements** — No new secret introduced. No new deployed domain (dashboard rides the existing `/admin/` path on the existing Railway domain — `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` unchanged, confirmed in research). The new deletion path reuses `delete_user_account()`, which already fails closed on Firebase errors (existing guarantee, not reimplemented). Static files continue through WhiteNoise (research §4). ✅ PASS.

No violations requiring the Complexity Tracking table below to carry an entry beyond what's already justified inline above.

## Project Structure

### Documentation (this feature)

```text
specs/003-admin-dashboard/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No `contracts/` directory: this feature adds no new external API surface (no new DRF endpoint, no new OpenAPI schema entry). Django Admin views are server-rendered internal tooling, not a versioned contract consumed by another system — consistent with the Phase 1 instruction to skip contracts for purely internal work.

### Source Code (repository root)

```text
core/
├── settings.py            # + INSTALLED_APPS "unfold" entry, UNFOLD dict, (pending) no other change
└── urls.py                # unchanged — /admin/ already routed

therapist/
├── models.py               # (pending sign-off) + crisis_flagged BooleanField
├── migrations/
│   └── 0005_...             # (pending sign-off) new field + backfill data migration
├── admin.py                # MoodEntryAdmin: list_filter, date_hierarchy, list_display truncation,
│                            #   readonly_fields, unfold.admin.ModelAdmin base
├── views.py                # generate() sets crisis_flagged at creation time (pending sign-off);
│                            #   calculate_streak() reused as-is, not modified
└── tests.py                 # + any coverage needed for the new field's admin filter (if approved)

accounts/
├── admin.py                 # UserAdmin: list_filter, ordering, entry-count/link display method,
│                             #   "Delete account and journal entries" admin action + confirm template
├── services.py               # unchanged — delete_user_account() reused as-is
└── tests.py                  # + test: admin delete action calls delete_user_account(), real DB deletion

templates/
└── admin/
    └── accounts/
        └── user/
            └── delete_selected_confirmation.md  # intermediate confirm page for the custom action
                                                   # (exact path/name finalized in tasks.md; Django's
                                                   # convention for action-specific confirm templates)

<dashboard summary view — exact location (custom admin URL vs. Unfold dashboard_callback)
 to be finalized in tasks.md based on the installed django-unfold version's documented
 extension point>
```

**Structure Decision**: No new Django app. All changes live inside the existing `core`, `therapist`, and `accounts` apps, consistent with "don't build a separate admin app" from the request and Constitution Principle V. The one new template lives under the existing `templates/` directory following Django Admin's template-override convention.

## Complexity Tracking

> No unjustified Constitution violations were found (see Constitution Check above — each potential concern was evaluated and passed with an inline rationale rather than requiring a tracked exception here).

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none)* | | |
