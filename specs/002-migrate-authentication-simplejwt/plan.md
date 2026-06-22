# Implementation Plan: Migrate Authentication from SimpleJWT to Firebase Auth

**Branch**: `002-migrate-authentication-simplejwt` | **Date**: 2026-06-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-migrate-authentication-simplejwt/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Replace `accounts/`'s SimpleJWT-based registration/login/logout/refresh/password-reset/email-verification stack with a single custom DRF authentication backend (`core/firebase_auth.py`) that verifies a Firebase ID token via `firebase-admin` and resolves it to an `accounts.User` by a new nullable `firebase_uid` field. `accounts/` shrinks to `GET/PATCH /me/` and `DELETE /delete-account/`. As an in-scope correction (confirmed by reading the code, not assumed), `therapist/`'s three views currently have no authentication and accept a client-supplied `user_id` — they are gated behind the same `FirebaseAuthentication` backend and switched to deriving their isolation key from `request.user.id` instead, reusing the existing `MoodEntry.user_id` column with no schema change.

## Technical Context

**Language/Version**: Python 3.11.9 (pinned, `runtime.txt`)

**Primary Dependencies**: Django 5.1.4, djangorestframework 3.17.1, drf-spectacular 0.27.2, `firebase-admin>=6.5,<7` (new), Pillow 12.2.0 (dropped if `profile_image` removed — see Step 1 decision below), requests 2.33.0 (unchanged, used by `therapist/ai_model.py`)

**Storage**: SQLite (dev, `db.sqlite3`), no storage-layer change in this feature

**Testing**: Django `TestCase` + DRF `APIClient`, run via `python manage.py test accounts` / `python manage.py test therapist`; Firebase calls mocked via `@patch("core.firebase_auth.auth.verify_id_token")` / `@patch("core.firebase_auth.auth.delete_user")` — no real network calls to Firebase or Groq in tests (per Constitution Principle IV)

**Target Platform**: Linux server (Railway deployment, Gunicorn + WhiteNoise, unchanged)

**Project Type**: Web service (Django REST API backend; Flutter client out of repo scope)

**Performance Goals**: No explicit target changes — Firebase token verification adds one JWKS-cached signature check per request (sub-millisecond after first fetch), comparable to or faster than SimpleJWT's local signature check; not a regression risk

**Constraints**: Must not require live Firebase credentials for `manage.py check`/`makemigrations`/`migrate`/non-auth tests to run (CI without secrets); must not change `therapist/ai_model.py` Groq integration behavior

**Scale/Scope**: Two Django apps touched (`accounts/`, `therapist/`), one new module (`core/firebase_auth.py`), one additive `accounts` migration (+`firebase_uid`, -`profile_image`/`PasswordResetToken`/`EmailVerificationToken`), no `therapist` schema change

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Data Isolation & Privacy)** — ✅ Strengthened, not weakened: `accounts/` already scopes to `request.user`; `therapist/` moves from a client-supplied free-text `user_id` (a known gap, `CLAUDE.md` Known Limitations #1) to authenticated `request.user`-derived scoping. No endpoint accepts a client-supplied identifier for lookup after this change.
- **Principle II (Input & Contract Validation)** — ✅ Preserved: `UserProfileUpdateSerializer` already restricts `PATCH /me/` to the five allowed fields (`full_name`, `phone_number`, `bio`, `date_of_birth`, `gender`) via `ModelSerializer.Meta.fields`, satisfying FR-007 with no new code. `MoodEntryCreateSerializer` loses its `user_id` field. drf-spectacular schema annotations on surviving views (`@extend_schema`) are updated to match new request/response shapes, not removed.
- **Principle III (Resilient External AI Integration)** — ✅ Unaffected: `ai_model.py`/Groq error handling in `GenerateResponseAPIView`/`WeeklyLetterAPIView` is untouched by this migration.
- **Principle IV (Test Coverage for Critical Flows)** — ✅ Plan replaces JWT-flow tests with Firebase-mock tests covering success/failure for every surviving/changed endpoint (see Phase 1 quickstart.md and the eventual tasks.md); no test hits real Firebase or Groq.
- **Principle V (Simplicity & Statelessness)** — ✅ No new abstraction layers; one new authentication class, reusing the existing `user_id` column for `therapist/` isolation instead of introducing a new FK (see research.md "Decision: `therapist/` gains auth...").
- **Security & Deployment — "Token-based authentication MUST use explicit, bounded access/refresh token lifetimes plus refresh-token rotation and blacklisting on logout (see `SIMPLE_JWT`...)"** — ⚠️ **GATE FLAG, justified in Complexity Tracking below.** This bullet is written against Django-issued tokens, which cease to exist after this migration — Firebase ID tokens are issued/refreshed/revoked entirely by Firebase (1-hour fixed lifetime, client-side silent refresh, `firebase_admin.auth.revoke_refresh_tokens()` available server-side if a future "log out everywhere" feature is needed). The underlying security property (bounded-lifetime tokens, revocability) is preserved by Firebase's own token lifecycle, not by Django code, so this is a constitution-wording gap to flag for a follow-up amendment rather than a violation to fix in this PR.
- **Security & Deployment — "Authentication-sensitive endpoints ... MUST be rate-limited"** — ✅ N/A after this migration: no Django-side login/register/password-reset endpoints remain to rate-limit; Firebase enforces its own abuse protection on those flows.
- **Security & Deployment — "Any endpoint that accepts or sets a password MUST enforce a minimum server-side strength policy"** — ✅ N/A: no endpoint accepts a password after this migration.

## Project Structure

### Documentation (this feature)

```text
specs/002-migrate-authentication-simplejwt/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
core/
├── settings.py          # MODIFY: drop SIMPLE_JWT/rest_framework_simplejwt app+auth class,
│                         #   add FIREBASE_CREDENTIALS_PATH, switch DEFAULT_AUTHENTICATION_CLASSES
├── firebase_auth.py      # NEW: FirebaseAuthentication(BaseAuthentication)
└── urls.py               # unchanged

accounts/
├── models.py             # MODIFY: User gains firebase_uid; drop profile_image; DELETE
│                         #   PasswordResetToken, EmailVerificationToken
├── migrations/           # NEW migration: add firebase_uid, drop profile_image, drop the two token models
├── serializers.py        # MODIFY: keep UserSerializer (drop profile_image field) and
│                         #   UserProfileUpdateSerializer as-is; DELETE Register/Login/Logout/
│                         #   ChangePassword/ForgotPassword/VerifyResetToken/ResetPassword/
│                         #   VerifyEmail/ProfileImage serializers
├── views.py              # MODIFY: keep MeView, DeleteAccountView (add Firebase delete call);
│                         #   DELETE Register/Login/Logout/CustomTokenRefresh/ProfileImage/
│                         #   ChangePassword/ForgotPassword/VerifyResetToken/ResetPassword/
│                         #   SendVerificationEmail/VerifyEmail views
├── urls.py               # MODIFY: only me/, delete-account/ remain
├── services.py           # MODIFY: drop email-send stubs + token issue/lookup/consume helpers;
│                         #   keep success_response/error_response envelope
├── throttling.py         # DELETE: all throttle classes were for endpoints being removed
├── validators.py         # MODIFY: drop password-strength + profile-image validators; keep phone
└── tests.py              # MODIFY: replace JWT-flow tests with Firebase-mock tests for the
                          #   3 surviving endpoints

therapist/
├── views.py              # MODIFY: add permission_classes = [IsAuthenticated] to all 3 views;
│                         #   derive user_id from str(request.user.id) instead of request data/query
├── serializers.py        # MODIFY: drop user_id from MoodEntryCreateSerializer
├── models.py             # unchanged (MoodEntry.user_id column reused, no migration)
└── tests.py              # MODIFY: add Firebase-token auth to existing test requests,
                          #   add 401-when-unauthenticated cases

requirements.txt           # MODIFY: + firebase-admin>=6.5,<7 ; - djangorestframework-simplejwt
```

**Structure Decision**: Single Django project, no new apps. All changes are modifications to the two existing apps (`accounts/`, `therapist/`) plus one new module (`core/firebase_auth.py`) — matches the existing flat `core/` + per-feature-app layout documented in `CLAUDE.md`'s File Organization section. No `contracts/` subdirectory content beyond a plain-text endpoint contract doc, since this is a Django REST service with no separate schema/IDL beyond drf-spectacular's auto-generated OpenAPI (already covered by `@extend_schema` decorators in `views.py`).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| Constitution's "Token-based authentication MUST use ... refresh-token rotation and blacklisting on logout (see `SIMPLE_JWT`...)" no longer has a literal Django-side implementation to point to | Firebase Auth, per explicit user requirement, now owns the entire token lifecycle (issuance, refresh, revocation) — Django never issues a token to rotate or blacklist | Keeping a Django-side SimpleJWT layer "just to satisfy the constitution's wording" while Firebase also issues tokens would mean two competing, redundant auth systems — directly contradicting Principle V (Simplicity) and the user's explicit "Remove all SimpleJWT code" requirement. The correct fix is a follow-up constitution amendment (separate from this PR) to reword this bullet in terms of "the active token-issuing system" generically, not to keep dead SimpleJWT code around. |
