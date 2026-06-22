---

description: "Task list for migrating authentication from SimpleJWT to Firebase Auth"
---

# Tasks: Migrate Authentication from SimpleJWT to Firebase Auth

**Input**: Design documents from `/specs/002-migrate-authentication-simplejwt/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-contracts.md, quickstart.md

**Tests**: Included — spec.md and CLAUDE.md's testing conventions require Firebase-mocked tests for every changed/surviving endpoint (Constitution Principle IV).

**Organization**: Tasks are grouped by user story per spec.md priorities (US1 > US4 > US2 > US3, since US1 and US4 are both P1 and US4 has no dependency on US2/US3).

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Existing Django project, two apps (`accounts/`, `therapist/`) plus `core/`. No new apps. Paths are exact, taken from the current repository layout.

---

## Phase 1: Setup

**Purpose**: Dependency and settings groundwork shared by every story.

- [X] T001 Add `firebase-admin>=6.5,<7` and remove `djangorestframework-simplejwt` in `requirements.txt`; run `pip install -r requirements.txt` in `.venv`
- [X] T002 Add `FIREBASE_CREDENTIALS_PATH = os.environ.get("FIREBASE_CREDENTIALS_PATH", "")` to `core/settings.py`; remove `rest_framework_simplejwt` from `INSTALLED_APPS` and the entire `SIMPLE_JWT = {...}` settings block

**Checkpoint**: Dependencies installed, settings reference the new env var; nothing wired up yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The Firebase authentication backend and `User.firebase_uid` field that every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Add `firebase_uid = models.CharField(max_length=128, unique=True, db_index=True, null=True, blank=True)` to the `User` model in `accounts/models.py`; remove the `profile_image` field and the entire `PasswordResetToken` and `EmailVerificationToken` model classes
- [X] T004 Run `python manage.py makemigrations accounts` to generate the migration covering T003 (AddField `firebase_uid`, RemoveField `profile_image`, DeleteModel `PasswordResetToken`, DeleteModel `EmailVerificationToken`); run `python manage.py migrate`
- [X] T005 Create `core/firebase_auth.py`: module-level `if not firebase_admin._apps: firebase_admin.initialize_app(credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH))` guarded so import doesn't crash when the env var is unset; `FirebaseAuthentication(BaseAuthentication)` class whose `authenticate(request)` reads `Authorization: Bearer <token>` (missing/empty → return `None` so DRF reports `401`), calls `auth.verify_id_token(token)` (invalid/expired → raise `AuthenticationFailed`), then `get_or_create`s an `accounts.User` by `firebase_uid` (using a synthetic `f"{uid}@firebase.local"` email per research.md when Firebase provides none, and `username=uid`), returning `(user, None)`
- [X] T006 In `core/settings.py`, set `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = ["core.firebase_auth.FirebaseAuthentication"]`, removing any SimpleJWT authentication class entry

**Checkpoint**: `python manage.py check` passes; `FirebaseAuthentication` is wired into DRF and ready for views to use via `request.user`.

---

## Phase 3: User Story 1 - Authenticate via Firebase ID token (Priority: P1) 🎯 MVP

**Goal**: Any authenticated endpoint resolves `request.user` from a verified Firebase ID token, auto-creating/reusing `accounts.User` by `firebase_uid`.

**Independent Test**: `GET /api/accounts/me/` with a mocked valid token creates/returns the matching user; missing/invalid/expired token returns 401.

### Tests for User Story 1

- [X] T007 [P] [US1] In `accounts/tests.py`, replace JWT-flow tests with: `test_new_firebase_uid_creates_user`, `test_existing_firebase_uid_reuses_user`, `test_missing_token_returns_401`, `test_malformed_token_returns_401`, `test_invalid_token_returns_401`, `test_expired_token_returns_401` — all via `@patch("core.firebase_auth.auth.verify_id_token")` against `GET /api/accounts/me/`, per quickstart.md US1 shape

### Implementation for User Story 1

- [X] T008 [US1] Verify `core/firebase_auth.py` (T005) satisfies every T007 case: malformed/missing header → `None`/401 via DRF; `verify_id_token` raising any `firebase_admin.auth` exception → caught and re-raised as `rest_framework.exceptions.AuthenticationFailed`

**Checkpoint**: User Story 1 fully functional — any view with `permission_classes = [IsAuthenticated]` is now protected by real Firebase verification.

---

## Phase 4: User Story 4 - Therapist endpoints gain auth + user isolation (Priority: P1)

**Goal**: `generate/`, `history/`, `weekly-letter/` require authentication and scope all reads/writes to `request.user`, with `user_id` removed from every request contract.

**Independent Test**: Two different authenticated users each create mood entries; each only sees their own via `history`/`weekly-letter`; unauthenticated calls return 401; no `user_id` body/query value has any effect.

### Tests for User Story 4

- [X] T009 [P] [US4] In `therapist/tests.py`, add Firebase-mocked auth (`@patch("core.firebase_auth.auth.verify_id_token")`) to all existing tests, add `test_generate_requires_auth_returns_401_without_token`, `test_history_requires_auth_returns_401_without_token`, `test_weekly_letter_requires_auth_returns_401_without_token`, and `test_history_isolates_between_two_users` (two different mocked `uid`s, confirm no cross-user entries), per quickstart.md US4 shape

### Implementation for User Story 4

- [X] T010 [US4] In `therapist/serializers.py`, remove the `user_id` field and its `USER_ID_VALIDATOR` usage from `MoodEntryCreateSerializer.Meta.fields`; remove `USER_ID_VALIDATOR` entirely if `MoodEntrySerializer` doesn't also need it (check before deleting)
- [X] T011 [US4] In `therapist/views.py`, add `permission_classes = [IsAuthenticated]` to `GenerateResponseAPIView`, `AllHistoryAPIView`, `WeeklyLetterAPIView`; remove `user_id` from the `@extend_schema` request body/query-param docs; replace `input_serializer.validated_data["user_id"]` (line ~100) with `str(request.user.id)`; replace `request.query_params.get("user_id")` + its `400 user_id is required` branch (lines ~175-181, ~205-207) with `str(request.user.id)` directly (no `400` branch needed — identity is guaranteed by `IsAuthenticated`)

**Checkpoint**: Therapist endpoints are authenticated and isolated; legacy free-text `user_id` is no longer accepted from clients anywhere.

---

## Phase 5: User Story 2 - Manage own profile (Priority: P2)

**Goal**: `GET`/`PATCH /api/accounts/me/` expose and update only the five allowed profile fields, never identity-bearing fields.

**Independent Test**: `PATCH` with an allowed field updates it; `PATCH` attempting `firebase_uid`/`email`/`username`/staff fields leaves them unchanged with no error.

### Tests for User Story 2

- [X] T012 [P] [US2] In `accounts/tests.py`, add/keep `test_get_me_returns_own_profile_only`, `test_patch_me_updates_allowed_field`, `test_patch_me_ignores_identity_fields` (asserts `firebase_uid`/`email`/`username` unchanged after a payload attempting to set them), all authenticated via mocked `verify_id_token`

### Implementation for User Story 2

- [X] T013 [P] [US2] In `accounts/serializers.py`, remove `profile_image` from `UserSerializer.Meta.fields`; confirm `UserProfileUpdateSerializer.Meta.fields` already only lists `full_name`, `phone_number`, `bio`, `date_of_birth`, `gender` (no code change needed if already correct — verify, don't assume); delete `RegisterSerializer`, `LoginSerializer`, `LogoutSerializer`, `ChangePasswordSerializer`, `ForgotPasswordSerializer`, `VerifyResetTokenSerializer`, `ResetPasswordSerializer`, `VerifyEmailSerializer`, `ProfileImageSerializer`
- [X] T014 [US2] In `accounts/views.py`, keep only `MeView` (GET/PATCH); delete `RegisterView`, `LoginView`, `LogoutView`, `CustomTokenRefreshView`, `ProfileImageView`, `ChangePasswordView`, `ForgotPasswordView`, `VerifyResetTokenView`, `ResetPasswordView`, `SendVerificationEmailView`, `VerifyEmailView`; update `MeView`'s `@extend_schema` docs to drop `profile_image`
- [X] T015 [US2] In `accounts/urls.py`, remove all routes except `me/` and `delete-account/`
- [X] T016 [P] [US2] In `accounts/services.py`, remove `send_password_reset_email`, `send_verification_email`, and the password-reset/email-verification token issue/lookup/consume helpers; keep `success_response`/`error_response`
- [X] T017 [P] [US2] Delete `accounts/throttling.py` (no surviving endpoint is throttled)
- [X] T018 [P] [US2] In `accounts/validators.py`, remove password-strength and profile-image validators; keep `validate_phone_number`

**Checkpoint**: `accounts/` profile self-service works end-to-end with no SimpleJWT/email-flow code remaining in serializers/views/urls.

---

## Phase 6: User Story 3 - Delete own account (Priority: P2)

**Goal**: `DELETE /api/accounts/delete-account/` removes both the Firebase identity and the Django row, failing loudly (not silently) if the Firebase-side call errors.

**Independent Test**: Valid token → 200, Firebase `delete_user` called with the right UID, local row gone; Firebase deletion failure → error response, local row NOT deleted.

### Tests for User Story 3

- [X] T019 [P] [US3] In `accounts/tests.py`, add `test_delete_account_removes_firebase_and_local_user` (mocks both `verify_id_token` and `delete_user`, asserts `delete_user` called with `firebase_uid`, row gone) and `test_delete_account_firebase_failure_returns_error_and_keeps_local_row` (mocks `delete_user` to raise, asserts non-200 response and the local row still exists), per quickstart.md US3 shape

### Implementation for User Story 3

- [X] T020 [US3] In `accounts/views.py`, implement `DeleteAccountView.delete`: call `firebase_admin.auth.delete_user(request.user.firebase_uid)` if `firebase_uid` is set, wrapped so any exception is logged and returns a `502` error response via `error_response` (per contracts/api-contracts.md) instead of proceeding; only delete the local `User` row after the Firebase call succeeds (or was skipped because `firebase_uid` is `None`); return `{"success": true, "message": "Account deleted permanently."}` on success

**Checkpoint**: All four user stories complete and independently testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Remove remaining dead code and validate the whole migration end-to-end.

- [X] T021 [P] Delete any now-unused imports of `rest_framework_simplejwt` across the repo; confirm `grep -rn "simplejwt\|SimpleJWT" --include=*.py .` (excluding `.venv`) returns nothing
- [X] T022 [P] Update `CLAUDE.md` to reflect the new auth architecture (Firebase instead of SimpleJWT), updated endpoint list, updated Known Limitations/Deployment Checklist entries
- [X] T023 Run `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py migrate`, `python manage.py test accounts`, `python manage.py test therapist`, `python manage.py check --deploy`; fix any failures before considering the migration done

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories (no view can require `IsAuthenticated` against a real backend until `FirebaseAuthentication` + `firebase_uid` exist).
- **User Story 1 (Phase 3)**: Depends on Foundational only.
- **User Story 4 (Phase 4)**: Depends on Foundational only — independent of US1's test additions, can run in parallel with Phase 3.
- **User Story 2 (Phase 5)**: Depends on Foundational; independent of US1/US4 (touches different files).
- **User Story 3 (Phase 6)**: Depends on Foundational; benefits from US2's `MeView`/urls cleanup landing first (same files) but is logically independent.
- **Polish (Phase 7)**: Depends on all four user stories being complete.

### Parallel Opportunities

- T001/T002 in parallel.
- Phase 3 and Phase 4 can be implemented in parallel (different apps/files).
- Within Phase 5: T013/T016/T017/T018 touch different files and can run in parallel; T014 (views) should follow T013 (serializers) since views import serializers; T015 (urls) follows T014.
- T021/T022 in parallel.

---

## Implementation Strategy

### MVP First

1. Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1) → **STOP and VALIDATE**: `GET /api/accounts/me/` works against a mocked Firebase token end-to-end.
2. Phase 4 (US4) next, since it's the other P1 and closes the therapist data-isolation gap.
3. Phase 5 (US2) and Phase 6 (US3) complete the `accounts/` endpoint surface.
4. Phase 7 (Polish) validates the whole migration per quickstart.md.

### Incremental Delivery

Each user story phase ends with its own checkpoint above — validate independently before moving to the next phase.
