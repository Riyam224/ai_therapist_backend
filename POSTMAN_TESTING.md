# Postman Testing Guide — AI Therapist Backend

Base URL (local dev): `http://127.0.0.1:8000`

Before testing, start the server:
```bash
export GROQ_API_KEY="your-api-key-here"
python manage.py runserver
```

## 0. Postman Setup

1. Create a new Collection: **AI Therapist Backend**
2. Create a Collection Variable:
   - `base_url` = `http://127.0.0.1:8000`
   - `access_token` = (leave empty, filled after login)
   - `refresh_token` = (leave empty, filled after login)
3. Optional: in the Collection's **Authorization** tab, set type to **Bearer Token** with value `{{access_token}}`, so every request inherits it automatically.
4. Tip: in the **Tests** tab of Register/Login requests, auto-save tokens:
   ```javascript
   const data = pm.response.json().data;
   pm.collectionVariables.set("access_token", data.access);
   pm.collectionVariables.set("refresh_token", data.refresh);
   ```

### Response envelope

Every `accounts/` endpoint returns:
```json
{ "success": true, "message": "...", "data": { ... } }
```
or on failure:
```json
{ "success": false, "message": "...", "errors": { ... } }
```

---

## 1. Accounts App — `/api/accounts/`

### 1.1 Register
- **POST** `{{base_url}}/api/accounts/register/`
- Auth: none
- Body (JSON):
```json
{
  "email": "testuser1@example.com",
  "username": "testuser1",
  "password": "Passw0rd123",
  "password_confirm": "Passw0rd123"
}
```
- `username` is optional.
- Password rules: ≥8 chars, ≥1 uppercase, ≥1 lowercase, ≥1 number.
- **201** on success → `data.user`, `data.access`, `data.refresh`
- **400** duplicate email/username, weak password, mismatched confirm
- **429** rate limited (5 requests / 5 min per IP, and per account/email)

### 1.2 Login
- **POST** `{{base_url}}/api/accounts/login/`
- Auth: none
- Body:
```json
{ "email": "testuser1@example.com", "password": "Passw0rd123" }
```
- **200** → `data.user`, `data.access`, `data.refresh`
- **401** invalid credentials
- **429** rate limited (5/5min)

### 1.3 Logout
- **POST** `{{base_url}}/api/accounts/logout/`
- Auth: Bearer `{{access_token}}` (required)
- Body:
```json
{ "refresh": "{{refresh_token}}" }
```
- **200** success → token is blacklisted
- **400** invalid/expired refresh token
- **401** missing/invalid access token

### 1.4 Refresh Access Token
- **POST** `{{base_url}}/api/accounts/token/refresh/`
- Auth: none
- Body:
```json
{ "refresh": "{{refresh_token}}" }
```
- **200** → `data.access` (new access token; access tokens expire in 15 min, refresh in 7 days)
- **401** refresh token invalid/expired/blacklisted

### 1.5 Get Profile (Me)
- **GET** `{{base_url}}/api/accounts/me/`
- Auth: Bearer required
- **200** → `data` = full `UserSerializer` (id, email, username, full_name, phone_number, bio, date_of_birth, gender, profile_image, is_verified, created_at, updated_at)

### 1.6 Update Profile (Me)
- **PATCH** `{{base_url}}/api/accounts/me/`
- Auth: Bearer required
- Body (any subset, all optional — partial update):
```json
{
  "full_name": "Test User",
  "phone_number": "+1234567890",
  "bio": "Just testing the API",
  "date_of_birth": "1995-05-20",
  "gender": "male"
}
```
- Note: `email`/`username` are NOT editable here.
- Phone format: `^\+?[0-9\s\-()]{7,20}$`
- **200** → updated `UserSerializer`
- **400** invalid phone format etc.

### 1.7 Upload Profile Image
- **POST** `{{base_url}}/api/accounts/profile-image/`
- Auth: Bearer required
- Body type: **form-data** (NOT raw JSON)
  - key: `image`, type: File, select a `.jpg`/`.jpeg`/`.png`/`.webp` file (≤5 MB)
- **200** → `data.profile_image` (URL)
- **400** unsupported format or file too large

### 1.8 Delete Profile Image
- **DELETE** `{{base_url}}/api/accounts/profile-image/`
- Auth: Bearer required
- No body
- **200** → `data.profile_image: null`

### 1.9 Change Password
- **POST** `{{base_url}}/api/accounts/change-password/`
- Auth: Bearer required
- Body:
```json
{
  "old_password": "Passw0rd123",
  "new_password": "NewPassw0rd456",
  "new_password_confirm": "NewPassw0rd456"
}
```
- **200** success
- **400** wrong old password / weak new password / mismatch

### 1.10 Delete Account
- **DELETE** `{{base_url}}/api/accounts/delete-account/`
- Auth: Bearer required
- No body — permanently deletes the authenticated user
- **200** success (do this LAST in your test run, on a throwaway test account)

### 1.11 Forgot Password
- **POST** `{{base_url}}/api/accounts/forgot-password/`
- Auth: none
- Body:
```json
{ "email": "testuser1@example.com" }
```
- **200** always (no account-existence disclosure — same response whether email exists or not)
- **429** rate limited (3/15min)
- Note: email sending is a **log-only stub** — check the Django server console/logs for the reset token (no real email is sent). Search for the token in `accounts/services.py` log output.

### 1.12 Verify Reset Token
- **POST** `{{base_url}}/api/accounts/verify-reset-token/`
- Auth: none
- Body:
```json
{ "token": "<token-from-server-logs>" }
```
- **200** → `data.valid: true`
- **400** invalid/expired token
- **429** rate limited (5/15min)

### 1.13 Reset Password
- **POST** `{{base_url}}/api/accounts/reset-password/`
- Auth: none
- Body:
```json
{
  "token": "<token-from-server-logs>",
  "new_password": "ResetPass789",
  "new_password_confirm": "ResetPass789"
}
```
- **200** success — token is consumed (single-use)
- **400** invalid/expired token or weak password

### 1.14 Send Verification Email
- **POST** `{{base_url}}/api/accounts/send-verification-email/`
- Auth: Bearer required
- No body
- **200** success, or "Account is already verified." if already verified
- **429** rate limited (3/hour)
- Note: again log-only stub — grab the token from server console logs.

### 1.15 Verify Email
- **POST** `{{base_url}}/api/accounts/verify-email/`
- Auth: Bearer required
- Body:
```json
{ "token": "<token-from-server-logs>" }
```
- **200** success → user `is_verified` becomes true
- **400** invalid/expired token, or token belongs to a different user

---

## 2. Therapist App — `/api/therapist/`

These endpoints are **unauthenticated** (no Bearer token needed) and identify the user via a client-supplied `user_id` string.

### 2.1 Generate AI Response
- **POST** `{{base_url}}/api/therapist/generate/`
- Body:
```json
{
  "user_id": "test_user_001",
  "emoji": "😊",
  "thoughts": "Had a great day at work today!",
  "history": [
    { "role": "user", "content": "I felt anxious this morning" },
    { "role": "assistant", "content": "That sounds tough — what helped?" }
  ]
}
```
- `user_id` must match `^[A-Za-z0-9_-]{3,128}$`
- `history` is optional, defaults to `[]`, only last 10 items are used
- **200** → mood entry with `ai_response` (may contain `[SESSION_END]` tag at the end if Luna senses resolution)
- **400** missing/invalid `user_id`, `emoji`, or `thoughts`

### 2.2 Get History
- **GET** `{{base_url}}/api/therapist/history/?user_id=test_user_001`
- **200** → array of mood entries for that user, newest first
- **400** missing `user_id` query param

### 2.3 Weekly Letter
- **GET** `{{base_url}}/api/therapist/weekly-letter/?user_id=test_user_001`
- **200** → `{ "letter": null, "reason": "not_enough_entries" }` if fewer than 2 entries in the last 7 days
- **200** → `{ "letter": "...", "stats": { entry_count, dominant_emoji, streak, week_start, week_end } }` otherwise
- **400** missing `user_id` query param

---

## 3. Suggested Test Order

1. Register → save tokens
2. Get Profile (Me) → verify fields match registration
3. Update Profile → verify PATCH applies partial changes
4. Generate (therapist) x2-3 times with same `user_id` → builds history
5. Get History → confirm entries appear, newest first
6. Weekly Letter → confirm stats once ≥2 entries exist
7. Change Password → then Logout → then Login with new password to confirm it took effect
8. Refresh Token → confirm new access token works on Get Profile
9. Forgot Password → check server logs for token → Verify Reset Token → Reset Password → Login with new password
10. Send Verification Email → check logs for token → Verify Email → confirm `is_verified: true` on Get Profile
11. Upload Profile Image → Get Profile (confirm URL) → Delete Profile Image
12. Logout (blacklist refresh token) → try Refresh Token again → expect 401
13. Delete Account (only on the disposable test account, last)

## 4. Common Gotchas

- 401 on any `accounts/` authenticated endpoint after ~15 min → access token expired, use `token/refresh/`
- 429 → you hit a throttle limit; wait out the window or use a different email/IP, or run `cache.clear()` if testing against a dev shell
- Profile image upload must be **form-data**, not raw JSON — raw JSON will fail serializer validation
- Password reset/verification "emails" are not real emails — read them from the Django server's console output
- `therapist/` endpoints are NOT auth-gated yet — any `user_id` string works, they're independent of `accounts/` login
