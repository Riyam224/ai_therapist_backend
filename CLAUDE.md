# CLAUDE.md - AI Therapist Backend

Technical documentation for Claude Code to understand and work with this Django project.

## Project Overview

This is a Django REST Framework application that provides an AI-powered mental health support API. It uses the **Groq API with Llama 3.1 8B Instant model** to generate empathetic responses to user mood inputs. The AI companion is named **Luna**.

## Architecture

### Application Structure

- **Django Project**: `core/` - Main project configuration
- **Django App**: `therapist/` - Main application handling mood entries and AI responses
- **Django App**: `accounts/` - Custom user model, JWT authentication, and account/profile management
- **Database**: SQLite (default), easily swappable for PostgreSQL/MySQL
- **AI Service**: Groq API (external REST API) accessed via [therapist/ai_model.py](therapist/ai_model.py)
- **Auth**: SimpleJWT access/refresh tokens with blacklist-on-logout, via [accounts/](accounts/)
- **API Docs**: drf-spectacular (Swagger UI at `/api/docs/`, ReDoc at `/api/redoc/`)
- **Deployment**: Railway-ready with WhiteNoise for static files

### Key Components

1. **Model Layer** ([therapist/models.py](therapist/models.py))
   - `MoodEntry`: Stores user mood data
     - Fields: `user_id` (CharField, db_index), `emoji`, `thoughts`, `ai_response`, `created_at`
     - `user_id` scopes all entries to a specific user — all queries must filter by it
     - Uses auto-generated timestamps (`auto_now_add=True`)
     - String representation: `"{user_id} | {emoji} - {thoughts[:20]}"`
     - Meta: `verbose_name` and `verbose_name_plural` configured

2. **View Layer** ([therapist/views.py](therapist/views.py))
   - Uses **class-based APIView** (DRF)
   - `GenerateResponseAPIView`: POST-only endpoint
     - Validates input with `MoodEntryCreateSerializer` (user_id, emoji, thoughts required; history optional)
     - Extracts last 10 items from `history` to cap context window
     - Calls `generate_ai_response(emoji, thoughts, history)` from ai_model
     - On AI error: catches exception, saves fallback message, still returns 200
     - Creates `MoodEntry` and returns serialized data (200)
     - Luna may include `[SESSION_END]` tag in `ai_response` when the user feels resolved
   - `AllHistoryAPIView`: GET-only endpoint
     - Requires `user_id` query param — returns 400 if missing
     - Returns entries filtered by `user_id`, ordered by `created_at` DESC
   - `WeeklyLetterAPIView`: GET-only endpoint
     - Requires `user_id` query param
     - Fetches last 7 days of entries for that user
     - Returns `{"letter": null, "reason": "not_enough_entries"}` if fewer than 2 entries
     - Calls Groq API directly to generate a personal weekly letter from Luna
     - Returns letter text + stats (entry_count, dominant_emoji, streak, week_start, week_end)

3. **AI Service** ([therapist/ai_model.py](therapist/ai_model.py))
   - Function: `generate_ai_response(emoji, thoughts, history=None) -> str`
   - `history`: optional list of `{"role": "user"|"assistant", "content": "..."}` dicts — injected between system prompt and current user message for multi-turn context
   - Uses **Groq API** (external cloud service), model: `llama-3.1-8b-instant`
   - Requires `GROQ_API_KEY` environment variable
   - Makes REST POST to `https://api.groq.com/openai/v1/chat/completions`
   - System prompt (`LUNA_SYSTEM_PROMPT`): defines Luna's personality (gentle, non-robotic, friend-like), response rules (2-3 sentences max, one follow-up question, no lists/headers, never repeats herself), and explicit `[SESSION_END]` trigger examples (only on clear resolution/gratitude/goodbye, never on vague requests like "help me")
   - Generation params tuned for natural variation: `temperature=0.85`, `max_tokens=180`, `top_p=0.9`, `frequency_penalty=0.6`, `presence_penalty=0.5`
   - **No local model loading** — stateless, synchronous API calls
   - Does not handle exceptions — caller is responsible

4. **Serializers** ([therapist/serializers.py](therapist/serializers.py))
   - `USER_ID_VALIDATOR`: regex `^[A-Za-z0-9_-]{3,128}$` — used on both serializers
   - `MoodEntrySerializer`: full read serializer — `fields = "__all__"`, `ai_response`/`created_at`/`id` read-only
   - `MoodEntryCreateSerializer`: write serializer — exposes `user_id`, `emoji`, `thoughts`, and optional `history`
     - `history`: write-only ListField of DictFields (`{"role", "content"}`), defaults to `[]`

5. **Accounts App** ([accounts/](accounts/)) — custom auth and account management, fully independent of `therapist/`
   - **Model** ([accounts/models.py](accounts/models.py)): `User` (`AUTH_USER_MODEL = "accounts.User"`, extends `AbstractUser`, email is `USERNAME_FIELD`, optional unique `username`, `full_name`, `phone_number`, `bio`, `date_of_birth`, `gender`, `profile_image`, `is_verified`); `PasswordResetToken` and `EmailVerificationToken` (single-use, expiring, FK to `User`)
   - **Manager** ([accounts/managers.py](accounts/managers.py)): `UserManager.create_user`/`create_superuser`, email-based
   - **Views** ([accounts/views.py](accounts/views.py)): one `APIView` per endpoint (see Full API Endpoints below); every authenticated view operates on `request.user` only — no endpoint accepts another user's identifier
   - **Serializers** ([accounts/serializers.py](accounts/serializers.py)): distinct read (`UserSerializer`) vs. write serializers per action (Register/Login/Logout/ChangePassword/ForgotPassword/VerifyResetToken/ResetPassword/VerifyEmail/ProfileUpdate/ProfileImage)
   - **Validators** ([accounts/validators.py](accounts/validators.py)): password strength (min 8 chars, ≥1 uppercase, ≥1 lowercase, ≥1 number), phone format, profile-image type/size
   - **Services** ([accounts/services.py](accounts/services.py)): `success_response`/`error_response` envelope helpers; `send_password_reset_email`/`send_verification_email` stubs (log-only — real email delivery is out of scope, see `specs/001-accounts-auth-module/spec.md` Assumptions); password-reset/email-verification token issue/lookup/consume helpers
   - **Throttling** ([accounts/throttling.py](accounts/throttling.py)): custom per-IP and per-account throttle classes supporting "N per M minutes/hours" windows (DRF's built-in `parse_rate` only supports single-unit rates)
   - **Response envelope**: every `accounts/` endpoint returns `{"success": bool, "message": str, "data": {...}}` or `{"success": false, "message": str, "errors": {...}}`

### URL Routing

- **Main URLs** ([core/urls.py](core/urls.py)):
  - `/` → Home page (`templates/index.html`)
  - `/admin/` → Django admin interface
  - `/api/therapist/` → Includes therapist app URLs
  - `/api/accounts/` → Includes accounts app URLs
  - `/api/schema/` → OpenAPI schema
  - `/api/docs/` → Swagger UI
  - `/api/redoc/` → ReDoc UI
  - Media files (`MEDIA_URL`/`MEDIA_ROOT`, profile images) served via `static()` when `DEBUG=True`

- **Therapist URLs** ([therapist/urls.py](therapist/urls.py)):
  - `generate/` → `GenerateResponseAPIView` (POST only)
  - `history/` → `AllHistoryAPIView` (GET only)
  - `weekly-letter/` → `WeeklyLetterAPIView` (GET only)

- **Accounts URLs** ([accounts/urls.py](accounts/urls.py)): see Full API Endpoints below

### Full API Endpoints

- `POST /api/therapist/generate/` — Create mood entry with AI response
- `GET /api/therapist/history/?user_id=<id>` — Retrieve entries for a user
- `GET /api/therapist/weekly-letter/?user_id=<id>` — Get Luna's weekly letter
- `POST /api/accounts/register/` — Register a new account, returns JWT access/refresh tokens
- `POST /api/accounts/login/` — Sign in with email + password, returns JWT access/refresh tokens
- `POST /api/accounts/logout/` — Blacklist a refresh token (auth required)
- `POST /api/accounts/token/refresh/` — Exchange a refresh token for a new access token
- `GET /api/accounts/me/` — Get the authenticated user's profile (auth required)
- `PATCH /api/accounts/me/` — Update editable profile fields (auth required)
- `POST /api/accounts/profile-image/` — Upload profile photo, multipart/form-data (auth required)
- `DELETE /api/accounts/profile-image/` — Remove profile photo (auth required)
- `POST /api/accounts/change-password/` — Change password (auth required)
- `DELETE /api/accounts/delete-account/` — Permanently delete own account (auth required)
- `POST /api/accounts/forgot-password/` — Request a password-reset token by email
- `POST /api/accounts/verify-reset-token/` — Check whether a reset token is valid
- `POST /api/accounts/reset-password/` — Set a new password using a valid reset token
- `POST /api/accounts/send-verification-email/` — Issue an email-verification token (auth required)
- `POST /api/accounts/verify-email/` — Confirm email verification with a token (auth required)

## Development Conventions

### Code Style

- Arabic comments present in codebase — maintain when editing existing comments
- PEP 8 compliant
- Django naming conventions followed
- DRF best practices applied (class-based views, serializers)

### Database

- SQLite for development (file: `db.sqlite3`)
- Migrations managed in standard Django way
- Model uses auto-timestamps (`auto_now_add=True`)

### Dependencies

**Core** ([requirements.txt](requirements.txt)):
- `Django==5.1.4` — Web framework
- `djangorestframework==3.17.1` — REST API
- `drf-spectacular==0.27.2` — OpenAPI schema + Swagger/ReDoc (branded "MindEase AI Therapist API" in [core/settings.py](core/settings.py) `SPECTACULAR_SETTINGS`)
- `requests==2.33.0` — HTTP client for Groq API calls
- `gunicorn==25.3.0` — Production WSGI server
- `whitenoise==6.5.0` — Static file serving for production
- `certifi==2026.2.25` — SSL certificate bundle
- `djangorestframework-simplejwt==5.5.1` — JWT issuance/refresh/blacklist for `accounts/`
- `Pillow==12.2.0` — Required by `ImageField` (profile photo validation/storage)

**Note**: No `torch` or `transformers` — uses external API instead of local model. No `python-decouple`/`dotenv` — settings use the existing `os.environ.get(..., default)` pattern.

### Testing

- Therapist test file: [therapist/tests.py](therapist/tests.py) — run with `python manage.py test therapist`; always mock `generate_ai_response()` to avoid real API calls
- Accounts test file: [accounts/tests.py](accounts/tests.py) — run with `python manage.py test accounts`; always mock `send_password_reset_email`/`send_verification_email` (in `accounts.views`) to avoid implying real email delivery; throttled-endpoint tests must call `cache.clear()` in `setUp()` since Django's default `LocMemCache` persists across test classes within a run; profile-image tests should use `@override_settings(MEDIA_ROOT=tempfile.mkdtemp())` to avoid writing test uploads into the real `media/` directory

Example:
```python
from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import patch

class TherapistAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch('therapist.ai_model.generate_ai_response')
    def test_create_mood_entry(self, mock_generate):
        mock_generate.return_value = "Mocked AI response"
        response = self.client.post(
            '/api/therapist/generate/',
            {'user_id': 'user_test', 'emoji': '😊', 'thoughts': 'Great day!'},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('ai_response', response.data)
```

## Common Tasks

### Adding New Features

1. **Database Changes**: Modify [therapist/models.py](therapist/models.py), then run:

   ```bash
   python manage.py makemigrations && python manage.py migrate
   ```

2. **API Changes**: Update [therapist/serializers.py](therapist/serializers.py) if needed, add/modify views in [therapist/views.py](therapist/views.py), add routes in [therapist/urls.py](therapist/urls.py).

3. **AI Service Changes**: Modify [therapist/ai_model.py](therapist/ai_model.py). No server restart needed (stateless calls).

### Working with the AI Service

**Important Notes**:
- Uses **Groq API** — requires `GROQ_API_KEY` environment variable
- No local model loading — each request makes an API call
- API calls are synchronous — blocks request until complete
- Typical response time: 1–2 seconds
- Requires internet connection

**Generation Function**:
```python
generate_ai_response(emoji: str, thoughts: str, history: list = None) -> str
```

- `history`: list of `{"role": "user"|"assistant", "content": "..."}` message dicts (optional)
- Makes POST request to Groq API
- Uses `llama-3.1-8b-instant` model
- Returns AI-generated response text; may include `[SESSION_END]` tag at the end
- Raises exceptions on failure — caller must handle

### Security Considerations

**Current State** ([core/settings.py](core/settings.py)):
- ✅ `SECRET_KEY` uses environment variable with fallback
- ✅ `DEBUG` uses environment variable (defaults to False)
- ✅ `ALLOWED_HOSTS` configured for Railway (`["*", ".railway.app"]`)
- ✅ `CSRF_TRUSTED_ORIGINS` includes the deployed Railway domain (`https://web-production-f8628.up.railway.app`) — **update this if the Railway app domain changes**
- ✅ WhiteNoise configured for secure static file serving
- ✅ `user_id` validated with strict regex on all endpoints (`therapist/`)
- ✅ `accounts/` provides JWT authentication (SimpleJWT access=15min/refresh=7days, rotation + blacklist-on-logout) and rate limiting (5/5min register+login, 3/15min forgot-password, 5/15min verify-reset-token, 3/hour send-verification-email)
- ⚠️ `ALLOWED_HOSTS = ["*"]` allows all hosts — restrict in production
- ⚠️ No CORS headers — add `django-cors-headers` if frontend on a different domain
- ⚠️ `therapist/` endpoints remain unauthenticated — `accounts/` does not (yet) gate `therapist/` endpoints behind login; `therapist.MoodEntry.user_id` is still a free-text client-supplied string with no link to `accounts.User` (see `specs/001-accounts-auth-module/research.md` §8 for why a cascade-on-delete was deliberately not implemented)

**Environment Variables Required**:
- `GROQ_API_KEY` — **Required** for AI functionality
- `SECRET_KEY` — Optional (has fallback for dev; also used to sign JWTs — set a strong value in production)
- `DEBUG` — Optional (defaults to False)

### Running Commands

**Development**:
```bash
export GROQ_API_KEY="your-api-key-here"
python manage.py runserver
python manage.py migrate
python manage.py makemigrations
python manage.py createsuperuser
python manage.py shell
python manage.py collectstatic
```

**Production** (uses Gunicorn per [Procfile](Procfile), launched automatically by Railway):
```bash
gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
```

## API Behaviour

### POST Request Flow (Generate Endpoint)

1. Request received at `POST /api/therapist/generate/`
2. Input validated by `MoodEntryCreateSerializer` — 400 if invalid
3. `history` extracted from validated data (last 10 items kept to cap context)
4. `generate_ai_response(emoji, thoughts, history)` called; exception caught → fallback message used
5. `ai_response` may contain `[SESSION_END]` tag — clients should detect this and close the session
6. `MoodEntry` created with user_id, emoji, thoughts, ai_response
7. Serialized response returned (200)

### GET Request Flow (History Endpoint)

1. Request received at `GET /api/therapist/history/?user_id=...`
2. `user_id` extracted from query params — 400 if missing
3. `MoodEntry.objects.filter(user_id=user_id).order_by("-created_at")`
4. All matching entries serialized and returned

### GET Request Flow (Weekly Letter Endpoint)

1. Request received at `GET /api/therapist/weekly-letter/?user_id=...`
2. `user_id` extracted — 400 if missing
3. Entries from last 7 days fetched for that user
4. If < 2 entries: `{"letter": null, "reason": "not_enough_entries"}` (200)
5. Entries formatted, dominant emoji found
6. Groq API called to generate personal letter from Luna (timeout: 10s)
7. Returns `{"letter": "...", "stats": {...}}` (200)

### Error Handling

- **400**: Invalid/missing required fields
- **200 with fallback**: Groq API error in generate/ (entry still saved)
- **200 with letter: null**: Groq API error in weekly-letter/
- No rate limiting currently implemented

## Data Isolation

All `MoodEntry` queries are scoped to `user_id`. Users cannot see each other's entries. The `user_id` field is indexed (`db_index=True`) for query performance.

## File Organization

```
ai_therapist_backend/
├── core/
│   ├── settings.py       # All Django settings (env-var driven, Railway-ready)
│   ├── urls.py           # Root URL configuration
│   ├── wsgi.py           # WSGI entry point (Gunicorn)
│   └── asgi.py           # ASGI entry point
├── therapist/
│   ├── models.py         # MoodEntry model
│   ├── views.py          # GenerateResponseAPIView, AllHistoryAPIView, WeeklyLetterAPIView
│   ├── serializers.py    # MoodEntrySerializer, MoodEntryCreateSerializer
│   ├── ai_model.py       # Groq API integration
│   ├── urls.py           # App URL patterns
│   ├── admin.py          # Admin site config
│   ├── apps.py           # App configuration
│   ├── tests.py          # Test cases
│   └── migrations/       # Database migrations
├── accounts/
│   ├── models.py         # User (AUTH_USER_MODEL), PasswordResetToken, EmailVerificationToken
│   ├── managers.py       # UserManager (email-based create_user/create_superuser)
│   ├── views.py          # One APIView per endpoint (see Full API Endpoints)
│   ├── serializers.py    # Register/Login/Logout/Profile/Password/Verification serializers
│   ├── validators.py     # Password strength, phone format, image type/size
│   ├── services.py       # Response envelope, email-send stubs, token helpers
│   ├── throttling.py     # Custom per-IP/per-account throttles ("N/Mmin" rate syntax)
│   ├── urls.py           # App URL patterns
│   ├── admin.py          # Admin site config
│   ├── apps.py           # App configuration
│   ├── tests.py          # Test cases
│   └── migrations/       # Database migrations
├── templates/
│   └── index.html        # Home page
├── staticfiles/          # Collected static files (generated)
├── media/                # Profile image uploads (gitignored, dev-only local storage)
├── .venv/                # Virtual environment
├── manage.py
├── requirements.txt
├── Procfile              # Gunicorn start command (Railway/Heroku)
├── runtime.txt           # Pins Python 3.11.9 for Railway
├── README.md             # Setup/usage docs
├── db.sqlite3            # SQLite database
└── .gitignore
```

## Performance Characteristics

- **Cold Start**: < 1 second (no model loading)
- **API Request**: 1–2 seconds (network + Groq API processing)
- **Memory**: ~50–100MB (no ML models in memory)
- **No GPU Required**: All processing happens on Groq's servers

## Extension Points

### Easy Additions

1. **Gate `therapist/` behind `accounts/` auth**: switch `therapist` views to `IsAuthenticated` and derive `user_id` from `request.user` instead of a client-supplied field
2. **Filtering**: Query parameters for date ranges, emoji filters
3. **Pagination**: DRF pagination classes on history endpoint
4. **CORS**: `django-cors-headers` for cross-origin frontend
5. **Social auth**: `accounts.User`/registration flow were designed not to preclude adding Google/Apple sign-in later (see `specs/001-accounts-auth-module/spec.md` Assumptions)

### API Service Improvements

1. **Async Calls**: Use async/await for non-blocking Groq requests
2. **Streaming**: Streaming responses for real-time generation
3. **Retry Logic**: Exponential backoff for failed API calls
4. **Context**: Pass conversation history for context-aware responses

## Known Limitations

1. `therapist/` endpoints remain unauthenticated — `accounts/` exists alongside it but doesn't (yet) gate mood-journal access
2. Synchronous Groq API calls — blocks request during generation
3. SQLite — not suitable for concurrent production writes
4. No rate limiting on `therapist/` endpoints (only `accounts/` auth-sensitive endpoints are throttled)
5. No input sanitization beyond field presence + regex (`therapist/`) / serializer validation (`accounts/`)
6. `ALLOWED_HOSTS = ["*"]` — too permissive for production
7. `accounts/` email delivery is a no-op stub (`send_password_reset_email`/`send_verification_email` only log) — wire up a real provider before relying on these flows in production
8. Account deletion does not cascade into `therapist.MoodEntry` — there's no link between the two today (see `specs/001-accounts-auth-module/research.md` §8)

## Deployment Checklist

- [x] `DEBUG = False` in production (via env var)
- [x] `SECRET_KEY` via environment variable
- [x] Static files configured with WhiteNoise
- [x] `user_id` data isolation implemented
- [x] JWT authentication implemented (`accounts/`, SimpleJWT)
- [x] Rate limiting on auth-sensitive endpoints (`accounts/`)
- [ ] **Set `GROQ_API_KEY`** (CRITICAL)
- [ ] Wire up real email delivery for `accounts/` password-reset and verification flows (currently log-only stubs)
- [ ] Restrict `ALLOWED_HOSTS` to specific domain
- [ ] Use PostgreSQL
- [ ] Add CORS headers if needed
- [ ] Add error logging (Sentry)
- [ ] Set up monitoring

## Debugging Tips

1. **AI not working**: Check `GROQ_API_KEY` is set
2. **Slow responses**: Normal — Groq API takes 1–2 seconds
3. **401 Unauthorized from Groq**: Invalid or missing API key
4. **Database locked**: SQLite concurrency issue — use PostgreSQL
5. **Import errors**: Activate virtual environment first
6. **Static files 404**: Run `python manage.py collectstatic`
7. **401 on `accounts/` endpoints**: access tokens expire after 15 minutes — call `token/refresh/` with the refresh token (valid 7 days) rather than re-logging in
8. **429 on `accounts/` endpoints**: rate limit hit — see Full API Endpoints' throttle thresholds; `cache.clear()` in tests if writing new throttled-endpoint test cases
9. **Profile image upload rejected**: must be JPG/JPEG/PNG/WEBP and ≤5 MB (`accounts/validators.py`)

---

**Last Updated**: 2026-06-19
**Django Version**: 5.1.4
**Python Version**: 3.11.9 (pinned via [runtime.txt](runtime.txt))
**AI Provider**: Groq API (Llama 3.1 8B Instant)
**Deployed**: Railway (no `railway.json`/`railway.toml` — platform auto-detects via [Procfile](Procfile) + [runtime.txt](runtime.txt))

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
`specs/001-accounts-auth-module/plan.md`
<!-- SPECKIT END -->
