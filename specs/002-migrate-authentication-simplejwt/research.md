# Research: Migrate Authentication from SimpleJWT to Firebase Auth

## Decision: Firebase verification via `firebase-admin` SDK, custom DRF `BaseAuthentication`

**Decision**: Implement `core/firebase_auth.py` with a `FirebaseAuthentication(BaseAuthentication)` class that reads the `Authorization: Bearer <token>` header, calls `firebase_admin.auth.verify_id_token(token)`, and resolves/creates an `accounts.User` by `firebase_uid`.

**Rationale**: `firebase-admin` is Google's officially maintained server SDK, handles JWKS fetching/caching and signature/expiry/audience verification internally, and is the same pattern Step 3 of the request specifies. A custom `BaseAuthentication` plugs directly into DRF's `DEFAULT_AUTHENTICATION_CLASSES` with zero changes to how views consume `request.user`, which is what `GenerateResponseAPIView`/`AllHistoryAPIView`/`WeeklyLetterAPIView`/accounts views already expect after Step 9's switch from a free-text `user_id` to `request.user`.

**Alternatives considered**:
- Verifying the JWT manually against Google's public JWKS (no `firebase-admin` dependency) — rejected: reimplements key rotation/caching and audience/issuer checks that `firebase-admin` already solves; higher security risk for no benefit.
- `django-firebase-auth` / similar third-party packages — rejected: adds a dependency wrapping the same `firebase-admin` call with less control over the get-or-create logic this project needs (mapping to an existing custom `User` model with `email` as `USERNAME_FIELD`, not Firebase's default `username` model).

## Decision: `accounts.User` lookup key is `firebase_uid`, with `username` set to `uid` only as a required-but-unused field

**Decision**: `get_or_create(firebase_uid=uid, defaults={"email": email or "", "username": uid})`. `username` stays populated only because it's currently a unique nullable `CharField` on the model (legacy from the SimpleJWT-era registration flow) and is not otherwise used for lookup or login since `USERNAME_FIELD = "email"`.

**Rationale**: `accounts/models.py` already declares `email = models.EmailField(unique=True)`. Firebase users without an email (phone/anonymous sign-in) would violate that uniqueness constraint if multiple such users got `email=""` — Django's `unique=True` treats multiple empty strings as a collision on databases that don't special-case empty unique values consistently (SQLite does **not** treat `""` as `NULL`, so two empty-email creates would conflict on the *second* one). This is flagged as a real risk; see Edge Cases below for the chosen mitigation.

**Alternatives considered**:
- Drop `email` uniqueness — rejected: out of scope per "Do not redesign the data layer," and email uniqueness is a reasonable invariant for any user that *does* have a Firebase email.
- Generate a synthetic placeholder email (`f"{uid}@firebase.local"`) when Firebase provides none — **chosen mitigation**, documented inline in `firebase_auth.py` with a comment explaining why, since it satisfies uniqueness without schema changes and is invisible to normal email/password or Google/Apple sign-in users (who always have a real email from Firebase).

## Decision: `firebase_uid` field is nullable+unique, not a `OneToOneField`

**Decision**: Plain `models.CharField(max_length=128, unique=True, db_index=True, null=True, blank=True)` per the request's Step 1 spec, added via a normal additive migration.

**Rationale**: Matches the exact field spec given, keeps existing rows (created pre-migration under SimpleJWT) valid with `firebase_uid=NULL` (SQLite/Postgres both allow multiple `NULL`s under a unique constraint), and avoids a data backfill being a hard blocker for shipping this migration.

**Alternatives considered**: Making it `null=False` with a backfill migration — rejected: there is no Firebase UID to backfill existing legacy users with; would require an out-of-band identity-linking flow that's explicitly out of scope (see spec Assumptions).

## Decision: Delete `django-anymail`/Resend references — none exist

**Decision**: No removal work needed for Step 4/5's `django-anymail`/Resend/ANYMAIL items.

**Rationale**: Repository inspection (`grep -rn "anymail|ANYMAIL|Resend"`) found zero references anywhere in `requirements.txt`, `core/settings.py`, or any app code. The only real email-related code to remove is `accounts/services.py`'s `send_password_reset_email`/`send_verification_email` *stub* functions (log-only, per `CLAUDE.md`), which are removed as part of deleting the password-reset/email-verification feature entirely (Step 2).

## Decision: `accounts/throttling.py` custom throttle classes are removed entirely, not "kept unchanged"

**Decision**: The custom per-IP/per-account throttle classes in `accounts/throttling.py` exist solely to rate-limit `register`/`login`/`forgot-password`/`verify-reset-token`/`send-verification-email` — all endpoints being deleted in this migration. Since none of the three retained endpoints (`me/` GET+PATCH, `delete-account/`) were throttled in the current codebase, `accounts/throttling.py` becomes dead code and is deleted.

**Rationale**: The request says "Keep throttling unchanged," which this research interprets as: *don't touch DRF's global throttling configuration or any throttle still in use* (there is none left in `accounts/` after this migration, and `therapist/` was never throttled). Removing now-unused throttle classes is required by Step 11 ("Remove ... Dead code") and doesn't contradict "keep throttling unchanged" because no surviving endpoint's throttling behavior changes.

**Alternatives considered**: Leave `throttling.py` in place unused — rejected: explicitly contradicts Step 11's "Remove ... dead code" and Step 2's "Delete all related: serializers, views, services, URLs, and tests" for every deleted endpoint, which includes their throttle wiring.

## Decision: `accounts/validators.py` password/phone/image validators — partially removed

**Decision**: Remove password-strength validators (no password fields remain anywhere). Remove profile-image validators (Step 1 removes `profile_image`). Keep the phone-number validator since `phone_number` remains a `PATCH /me/` field.

**Rationale**: Directly follows from which fields/flows survive the migration.

## Decision: `is_verified` field on `User` — keep as-is (unused by new flows, not explicitly listed for removal)

**Decision**: Leave `is_verified` on the model untouched.

**Rationale**: The request's removal list is explicit (`PasswordResetToken`, `EmailVerificationToken` models, and named endpoints/serializers/views). `is_verified` is a plain boolean column, not part of the email-verification *token* flow's data, and removing it isn't requested. Firebase exposes its own `email_verified` claim on the decoded token if a future feature wants to sync it — left as a documented follow-up, not done now, per "make only the changes described."

## Decision: `therapist/` gains auth + isolation now; `MoodEntry.user_id` keeps its existing `CharField` (no schema change), populated from `request.user.id` instead of client input

**Decision**: Contrary to the initial assumption that `therapist/` "already" enforces authentication and user isolation, inspection of `therapist/views.py`/`therapist/models.py` shows the opposite: no `permission_classes`, and `user_id` taken as a free-text field from the request body (`generate/`) or query string (`history/`, `weekly-letter/`). Per user decision, this migration also closes that gap: all three views get `permission_classes = [IsAuthenticated]` (via the global `DEFAULT_AUTHENTICATION_CLASSES` already switching to `FirebaseAuthentication`), `user_id` is removed from `MoodEntryCreateSerializer`'s client-writable fields and from the `history`/`weekly-letter` query-param contract, and every view derives the value to filter/create by from `str(request.user.id)` instead.

**Rationale**: `CLAUDE.md`'s own "Extension Points → Easy Additions #1" already documents this exact change ("switch `therapist` views to `IsAuthenticated` and derive `user_id` from `request.user` instead of a client-supplied field") as the intended low-risk way to close this gap — reusing the existing `CharField` column (rather than adding a new FK to `accounts.User`) avoids a schema change/data migration for `MoodEntry` while still achieving real per-user isolation, since `str(request.user.id)` is a stable, non-client-controlled value once auth is in place. This keeps the change additive instead of "redesigning the data layer."

**Alternatives considered**: Add a new `MoodEntry.user = models.ForeignKey(accounts.User, ...)` column — rejected for this migration: heavier (new migration, nullable-for-legacy-rows question, query/serializer changes beyond auth) for no behavioral gain over reusing `user_id` as `str(request.user.id)`; can be proposed as a separate, later cleanup if a real FK/join is ever needed.

**Consequence (documented, not silently absorbed)**: `MoodEntry` rows created before this migration (under the old client-supplied `user_id` scheme) become permanently inaccessible through the authenticated endpoints unless their `user_id` string happens to equal some future user's `str(id)` (practically never, since old values were arbitrary client strings like `"user_123"`). This is acceptable per the spec's Assumptions (legacy data linkage is explicitly out of scope) but should be called out in the PR description as a behavior change, not just an implementation detail.

## Decision: Test strategy — mock `firebase_admin.auth.verify_id_token` / `delete_user` at the module level used by `core/firebase_auth.py`

**Decision**: Tests `@patch("core.firebase_auth.auth.verify_id_token")` (and `delete_user` similarly in the delete-account test), constructing requests with `HTTP_AUTHORIZATION="Bearer faketoken"` via DRF's `APIClient`.

**Rationale**: Matches the project's existing test convention (`CLAUDE.md`: mock the external call at its call site, e.g. `@patch('therapist.ai_model.generate_ai_response')`) — Firebase verification is exactly this kind of external dependency and must never make a real network call in tests.

## Decision: `firebase_admin.initialize_app` guarded by `if not firebase_admin._apps`, credentials from `FIREBASE_CREDENTIALS_PATH`

**Decision**: Module-level guarded init in `core/firebase_auth.py`, using `firebase_admin.credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)`. If the env var is unset, defer the error to first use (raise `AuthenticationFailed`/log clearly) rather than crashing Django startup — `manage.py check`/`makemigrations` must still work without Firebase credentials present (e.g., CI without secrets).

**Rationale**: Per Step 3's explicit `if not firebase_admin._apps:` requirement, and per `python manage.py check --deploy` being a completion gate — that command must not hard-require a real Firebase credentials file to exist on disk just to run static checks.

**Alternatives considered**: Initialize Firebase eagerly in `AppConfig.ready()` — rejected: would make `manage.py check`/test runs fail in any environment without real Firebase credentials configured, which is worse for CI/local dev than lazy initialization on first authenticated request.
