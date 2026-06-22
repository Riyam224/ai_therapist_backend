# Data Model: Migrate Authentication from SimpleJWT to Firebase Auth

## `accounts.User` (modified)

Extends `django.contrib.auth.models.AbstractUser`. `USERNAME_FIELD = "email"`, `REQUIRED_FIELDS = []`, custom `UserManager`.

| Field | Type | Change | Notes |
|---|---|---|---|
| `id` | AutoField (PK) | unchanged | |
| `email` | `EmailField(unique=True)` | unchanged | Identity-bearing — never client-writable via `PATCH /me/` |
| `username` | `CharField(max_length=150, unique=True, blank=True, null=True)` | unchanged | No longer used for login; kept only because `get_or_create` needs *some* value and removing it is a larger, unrequested model change |
| `firebase_uid` | `CharField(max_length=128, unique=True, db_index=True, null=True, blank=True)` | **NEW** | Lookup key for `FirebaseAuthentication`; `NULL` for any pre-migration legacy account |
| `full_name` | `CharField(max_length=150, blank=True)` | unchanged | Editable via `PATCH /me/` |
| `phone_number` | `CharField(max_length=32, blank=True)` | unchanged | Editable via `PATCH /me/`; validated by `validate_phone_number` |
| `bio` | `TextField(max_length=500, blank=True)` | unchanged | Editable via `PATCH /me/` |
| `date_of_birth` | `DateField(null=True, blank=True)` | unchanged | Editable via `PATCH /me/` |
| `gender` | `CharField(choices=GenderChoices)` | unchanged | Editable via `PATCH /me/` |
| `profile_image` | `ImageField` | **REMOVED** | Client uploads photos to Firebase Storage directly; removing avoids unused `Pillow`-backed validation/storage code |
| `is_verified` | `BooleanField(default=False)` | unchanged, unused | Not part of the requested removal list; Firebase's own `email_verified` claim could sync into this in a future feature, out of scope here |
| `created_at` / `updated_at` | `DateTimeField` | unchanged | |

**Validation rules** (unchanged from current `UserProfileUpdateSerializer`):
- `phone_number` validated via `validate_phone_number` (format check) when present.
- No other field-level validation needed — `full_name`, `bio`, `date_of_birth`, `gender` use plain Django field constraints (max length / choices).

**Identity rule** (new, enforced at the authentication-backend level, not the serializer level): `firebase_uid`, `email`, `username`, and any `is_staff`/`is_superuser` field are never included in `UserProfileUpdateSerializer.Meta.fields`, so they cannot be set via `PATCH /me/` regardless of payload — DRF `ModelSerializer` silently ignores extra keys not declared as fields.

## `accounts.PasswordResetToken` — **REMOVED**

Entire model deleted (table dropped via migration). No replacement; Firebase owns password reset.

## `accounts.EmailVerificationToken` — **REMOVED**

Entire model deleted (table dropped via migration). No replacement; Firebase owns email verification.

## `therapist.MoodEntry` (unchanged schema, changed semantics)

| Field | Type | Change | Notes |
|---|---|---|---|
| `id` | AutoField (PK) | unchanged | |
| `user_id` | `CharField(max_length=128, db_index=True)` | **no schema change** | Previously: arbitrary client-supplied string. Now: always `str(request.user.id)`, set server-side, never read from request body/query params |
| `emoji` | `CharField(max_length=10)` | unchanged | |
| `thoughts` | `TextField` | unchanged | |
| `ai_response` | `TextField` | unchanged | |
| `created_at` | `DateTimeField(auto_now_add=True)` | unchanged | |

**State/lifecycle**: No state machine; each row is an immutable log entry once created, exactly as today.

**Isolation rule** (new): `GenerateResponseAPIView.post`, `AllHistoryAPIView.get`, `WeeklyLetterAPIView.get` all filter/create using `str(request.user.id)`; `permission_classes = [IsAuthenticated]` added to all three (inherited from `DEFAULT_AUTHENTICATION_CLASSES = [FirebaseAuthentication]` for the auth check itself, since `IsAuthenticated` only checks that *some* authenticated user is present).

## Migration plan (Django migrations, `accounts` app)

One new migration:
1. `AddField`: `accounts.User.firebase_uid` (nullable, unique, indexed).
2. `RemoveField`: `accounts.User.profile_image`.
3. `DeleteModel`: `accounts.PasswordResetToken`.
4. `DeleteModel`: `accounts.EmailVerificationToken`.

No `therapist` migration (no schema change, only application-code change in how `user_id` is populated).
