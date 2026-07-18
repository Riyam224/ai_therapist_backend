# Quickstart: Validating the Admin Dashboard

Prerequisites: local dev environment set up per `README.md` Quick Start (venv, `GROQ_API_KEY`, `FIREBASE_CREDENTIALS_PATH`, migrations applied), plus a superuser account:

```bash
python manage.py createsuperuser
```

## 1. Admin renders locally

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/admin/` in a browser, log in with the superuser account. **Expected**: stock Django Admin (no third-party theme — `django-unfold` was evaluated and dropped, see tasks.md Phase 1 amendment: it requires Python >=3.12, incompatible with Railway's pinned 3.11.9), page title/header reads "Lueur Admin" (not "Django administration" or anything clinical-sounding), and the index page shows an "Overview" module with the six analytics figures above the app list.

## 2. Journal entry browsing (User Story 1, SC-001)

- Open the `MoodEntry` list. **Expected**: `thoughts`/`ai_response` show truncated text, not raw full paragraphs breaking the table layout.
- Apply the crisis-flagged filter and the date-hierarchy filter. **Expected**: list narrows correctly.
- Open a single entry. **Expected**: full untruncated `thoughts`/`ai_response` visible; `created_at` is displayed but not editable.
- Time the round trip search → open detail for a known test entry. **Expected**: under 1 minute (SC-001).

## 3. User browsing (User Story 1)

- Open the `User` list. **Expected**: ordered newest-first by default; filters for `is_active`, `is_verified`, `is_staff` are present and work.
- Open a single user with at least one `MoodEntry`. **Expected**: entry count is shown and links to that user's filtered `MoodEntry` list.

## 4. Manual deletion (User Story 2, SC-002, SC-003)

- Create a disposable test user with 1–2 `MoodEntry` rows (via the API or `manage.py shell`).
- In the dashboard, select that user and run "Delete account and journal entries." **Expected**: a confirmation step is shown before anything happens (FR-008).
- Confirm. **Expected**: with Firebase's `delete_user` mocked/succeeding, the user row and all their `MoodEntry` rows are gone (verify directly: `User.objects.filter(...).exists()` is `False`, `MoodEntry.objects.filter(user_id=...).exists()` is `False`).
- Repeat against a user whose Firebase deletion is forced to fail (e.g. temporarily point at an invalid `firebase_uid`, or exercise this via the automated test instead — see Task 7 in tasks.md). **Expected**: local `User` row and `MoodEntry` rows still exist; a clear error is shown (FR-009).

## 5. Analytics summary (User Story 3, SC-004)

- Open the dashboard summary/overview screen. **Expected**: all six figures render in one view — total active users, 7/30-day entry counts, 7/30-day crisis-flagged counts, average streak.
- Create a new `MoodEntry` for an existing user, reload. **Expected**: the relevant counts change immediately (FR-011 — no stale caching).

## 6. Access control (SC-005)

- Log in as a non-staff user (`is_staff=False`). **Expected**: `/admin/` login is rejected or redirects away — dashboard is unreachable.

## 7. Production static assets (SC-006)

```bash
python manage.py collectstatic --noinput
```

**Expected**: succeeds with no errors (stock `django.contrib.admin` static assets — no Unfold assets to check for, since that dependency was dropped). After deploying, load `https://<railway-domain>/admin/` and confirm it renders correctly, not a 500 or broken page (this final live check cannot be automated from this environment — see plan.md Task 8 notes).

## 8. Automated tests

```bash
python manage.py test accounts
python manage.py test therapist
python manage.py test    # full suite — must stay green
```
