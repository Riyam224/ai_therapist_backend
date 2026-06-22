# Feature Specification: Migrate Authentication from SimpleJWT to Firebase Auth

**Feature Branch**: `002-migrate-authentication-simplejwt`

**Created**: 2026-06-22

**Status**: Draft

**Input**: User description: "Migrate from SimpleJWT authentication to Firebase Authentication while preserving the existing architecture and minimizing unnecessary changes. Firebase owns registration, login, logout, password reset, email verification, token refresh, Google/Apple sign-in. Django owns user data, mood history, weekly letters, Luna responses, admin panel. Identity must always come from request.user, derived from a verified Firebase ID token. Remove all SimpleJWT, password-reset, and email-verification code. Keep only GET/PATCH /api/accounts/me/ and DELETE /api/accounts/delete-account/. Preserve therapist app business logic unchanged, scoped to request.user."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Authenticate via Firebase ID token (Priority: P1)

A Flutter client signs a user in through Firebase Auth (email/password, Google, or Apple), obtains a Firebase ID token, and sends it as a `Bearer` token to the Django API. The API verifies the token and resolves it to a Django user without the client ever calling a Django login/register endpoint.

**Why this priority**: This is the foundation of the entire migration — no other endpoint works without it.

**Independent Test**: Send a request with a valid Firebase ID token to `GET /api/accounts/me/` and confirm it returns 200 with the corresponding user's profile, auto-creating the `accounts.User` row on first sight of a new `firebase_uid`.

**Acceptance Scenarios**:

1. **Given** a valid, unexpired Firebase ID token for a UID never seen before, **When** the client calls any authenticated endpoint, **Then** Django creates a new `accounts.User` linked to that `firebase_uid` and returns the normal authenticated response.
2. **Given** a valid Firebase ID token for a UID that already has an `accounts.User`, **When** the client calls any authenticated endpoint, **Then** Django resolves `request.user` to the existing record (no duplicate created).
3. **Given** a missing, malformed, invalid, or expired token, **When** the client calls any authenticated endpoint, **Then** the API returns 401 Unauthorized and no `accounts.User` is created or modified.

---

### User Story 2 - Manage own profile (Priority: P2)

An authenticated user views and edits their own profile fields (`full_name`, `phone_number`, `bio`, `date_of_birth`, `gender`) without being able to alter identity-bearing fields.

**Why this priority**: Profile self-service is the only Django-owned account capability left after Firebase takes over credentials.

**Independent Test**: `PATCH /api/accounts/me/` with `{"full_name": "New Name"}` returns 200 and reflects the change on a subsequent `GET /api/accounts/me/`; a PATCH attempting to set `firebase_uid` or `email` is silently ignored or rejected without error, and the original values are unchanged.

**Acceptance Scenarios**:

1. **Given** an authenticated user, **When** they `GET /api/accounts/me/`, **Then** they receive their own profile data only (never another user's).
2. **Given** an authenticated user, **When** they `PATCH /api/accounts/me/` with an allowed field, **Then** the field updates and the response reflects the new value.
3. **Given** an authenticated user, **When** they attempt to `PATCH` `firebase_uid`, `email`, `username`, or staff/admin flags, **Then** those fields remain unchanged regardless of the payload.

---

### User Story 3 - Delete own account (Priority: P2)

An authenticated user permanently deletes their account, which removes both their Firebase identity and their Django user record.

**Why this priority**: Account deletion is a required data-control capability and the riskiest operation in the migration (touches an external system).

**Independent Test**: `DELETE /api/accounts/delete-account/` with a valid token returns success, the Django user row is gone, and a subsequent request with the same (now-revoked) token returns 401.

**Acceptance Scenarios**:

1. **Given** an authenticated user, **When** they call `DELETE /api/accounts/delete-account/`, **Then** their Firebase user is deleted, their Django `accounts.User` row is deleted, and a success response is returned.
2. **Given** the Firebase deletion call fails (e.g., network error, already deleted on Firebase side), **When** the endpoint handles the failure, **Then** the failure is logged and surfaced as an error response rather than silently proceeding to delete the local record and report success.

---

### User Story 4 - Therapist endpoints gain auth + user isolation (Priority: P1)

Luna mood-tracking endpoints (`generate`, `history`, `weekly-letter`) currently accept a free-text, client-supplied `user_id` with no authentication at all (confirmed by inspecting `therapist/views.py`/`therapist/models.py` — contrary to the initial assumption that this was already in place). As part of this migration they become gated the same way as `accounts/`: identity comes exclusively from the verified Firebase-derived `request.user`, and the client-supplied `user_id` is removed from every request contract.

**Why this priority**: This is the existing core product value and the app's largest remaining data-isolation gap (`CLAUDE.md` Known Limitations #1); the migration is the natural point to close it since `accounts/` is gaining the same authentication mechanism anyway.

**Independent Test**: Two different Firebase-authenticated users each create mood entries; each can only retrieve their own entries via `history`/`weekly-letter`, and no request body or query parameter containing a user identifier has any effect.

**Acceptance Scenarios**:

1. **Given** an authenticated user A, **When** they call `generate`, `history`, or `weekly-letter`, **Then** all data read/written is scoped to user A's `request.user`, regardless of any user-identifier-like value present in the request body or query string.
2. **Given** an authenticated user A and a different authenticated user B, **When** each queries `history`, **Then** neither sees the other's entries.
3. **Given** an unauthenticated request, **When** any therapist endpoint is called, **Then** the API returns 401 Unauthorized.
4. **Given** `MoodEntry` rows created before this migration under the old free-text `user_id` scheme, **When** any authenticated user queries `history`/`weekly-letter` after the migration, **Then** those legacy rows are not returned to anyone (not linked to any `accounts.User`) — an accepted, documented data-continuity tradeoff, not a bug.

---

### Edge Cases

- What happens when a Firebase ID token is valid but the associated Firebase user has no email (anonymous/phone-only sign-in)? → User is still created/resolved by `firebase_uid`; `email` may be blank.
- How does the system handle a token signed for a different Firebase project (wrong audience)? → Verification fails → 401.
- What happens if Firebase deletion succeeds but the local DB delete fails (e.g., DB error mid-transaction)? → Must not leave an orphaned Firebase identity silently swallowed; failure must be logged and reported as an error.
- What happens to existing `accounts.User` rows created under the old SimpleJWT system that have no `firebase_uid`? → Out of scope for automated linking; `firebase_uid` is nullable, and a one-time manual/administrative data migration to associate legacy accounts with Firebase UIDs is a follow-up concern, not part of this feature.
- What happens when an authenticated request omits the `Authorization` header entirely vs. sends `Authorization: Bearer` with an empty token? → Both are treated as "missing token" → 401.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST authenticate every protected request by verifying a Firebase ID token supplied in the `Authorization: Bearer <token>` header.
- **FR-002**: System MUST reject requests with missing, malformed, invalid, or expired Firebase ID tokens with 401 Unauthorized.
- **FR-003**: System MUST resolve a verified token's Firebase UID to an `accounts.User`, auto-creating one on first sight of a previously unseen `firebase_uid`.
- **FR-004**: System MUST NOT accept any user identifier from the request body or query parameters for the purpose of establishing identity on any endpoint — identity comes only from `request.user`, set by the authentication backend.
- **FR-005**: System MUST remove SimpleJWT-based registration, login, logout, token-refresh, password-reset, email-verification, and change-password capabilities entirely.
- **FR-006**: System MUST expose exactly three `accounts/` endpoints: `GET /api/accounts/me/`, `PATCH /api/accounts/me/`, `DELETE /api/accounts/delete-account/`.
- **FR-007**: `PATCH /api/accounts/me/` MUST permit updates only to `full_name`, `phone_number`, `bio`, `date_of_birth`, `gender`, and MUST NOT permit updates to `firebase_uid`, `email`, `username`, or any staff/admin field.
- **FR-008**: `DELETE /api/accounts/delete-account/` MUST delete the user's Firebase identity and local Django record, log any Firebase-side failure, and MUST NOT report success if the Firebase deletion call raises an unhandled/unlogged error.
- **FR-009**: Therapist endpoints (`generate`, `history`, `weekly-letter`) MUST require authentication, MUST remove `user_id` from their request body/query-parameter contracts, MUST scope all reads/writes to `request.user`, and MUST remain functionally unchanged otherwise (response shapes, AI behavior, fallback handling, `[SESSION_END]` semantics).
- **FR-010**: System MUST preserve existing throttling, pagination, and drf-spectacular schema configuration unchanged by this migration.
- **FR-011**: System MUST preserve the existing `{"success", "message", "data"/"errors"}` response envelope helpers for the retained `accounts/` endpoints.
- **FR-012**: System MUST remove the `PasswordResetToken` and `EmailVerificationToken` models and all associated serializers, views, services, URLs, and tests.
- **FR-013**: System MUST add a nullable, unique, indexed `firebase_uid` field to `accounts.User` without removing other existing profile fields (`full_name`, `phone_number`, `bio`, `date_of_birth`, `gender`).
- **FR-014**: System MAY remove the `profile_image` field, its upload logic, serializers, and endpoint, since profile photo storage moves to Firebase Storage from the client.

### Key Entities

- **accounts.User**: Existing custom user model (extends `AbstractUser`); gains a nullable unique `firebase_uid` field as the link to Firebase Auth identity; retains `full_name`, `phone_number`, `bio`, `date_of_birth`, `gender`; `profile_image` removed if no longer used.
- **Firebase ID Token**: Bearer credential issued by Firebase Auth on the client, verified server-side per request; not persisted by Django.
- **MoodEntry**: Existing `user_id` `CharField` column is reused (no schema change) but its value is now populated from `str(request.user.id)` rather than accepted from the client, becoming the de facto user-isolation key once `therapist/` requires authentication.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of previously SimpleJWT-protected endpoints now authenticate exclusively via verified Firebase ID tokens, with zero remaining SimpleJWT code paths in the repository.
- **SC-002**: Requests with invalid/expired/missing tokens are rejected with 401 on every protected endpoint, with no exceptions.
- **SC-003**: No endpoint accepts a client-supplied user identifier (body or query param) that has any effect on which user's data is read or written.
- **SC-004**: All existing therapist-app automated tests (adapted to Firebase-token auth) and new accounts-app tests pass; `python manage.py check`, `makemigrations`, `migrate`, `test`, and `check --deploy` all complete without errors.
- **SC-005**: Account deletion removes both the Firebase identity and the Django record in the same logical operation, with no orphaned record left in either system on the success path.

## Assumptions

- The Flutter client is responsible for all Firebase sign-in flows (email/password, Google, Apple) and for refreshing/obtaining the ID token; Django never issues or refreshes tokens itself.
- A Firebase project and service-account credentials (`FIREBASE_CREDENTIALS_PATH`) are available in every environment that needs to verify tokens (dev, CI, production); this feature does not cover provisioning that project.
- Legacy `accounts.User` rows created before this migration (under SimpleJWT) are out of scope for automatic backfilling of `firebase_uid` — they simply have `firebase_uid = NULL` until/unless a separate data-migration effort links them.
- Email delivery (password reset, verification) is fully Firebase's responsibility going forward; Django's stub email-sending code for these flows is deleted rather than kept dormant.
- `django-anymail`/Resend configuration existed only to support the now-removed password-reset/verification emails and has no other consumer in the codebase.
