<!--
Sync Impact Report
- Version change: 1.1.0 → 2.0.0
- Modified principles:
  - I. Data Isolation & Privacy — redefined: isolation is no longer enforced
    via a regex-validated, client-supplied `user_id`/identifier on any
    endpoint. Every endpoint (across `therapist/` and `accounts/`) MUST now
    derive identity exclusively from `request.user`, set by verified
    Firebase ID token authentication. Accepting a client-supplied identifier
    for lookup/isolation purposes is now itself a violation, not an
    allowed-but-discouraged pattern.
  - IV. Test Coverage for Critical Flows — mocking targets updated: the
    `accounts/` email-send stubs no longer exist; tests MUST instead mock
    `core.firebase_auth.auth.verify_id_token` / `firebase_admin.auth.delete_user`
    for any authenticated-flow test, alongside `generate_ai_response()`.
- Security & Deployment Requirements — substantially redefined (backward
  incompatible, hence MAJOR bump):
  - Removed: SimpleJWT-specific bullet (access/refresh token lifetimes,
    rotation, blacklist-on-logout) — Django no longer issues tokens.
  - Removed: password-strength-policy bullet — Django no longer accepts or
    sets passwords; Firebase owns credential policy.
  - Removed: per-account/per-IP rate-limiting-on-auth-endpoints bullet —
    those endpoints no longer exist in Django; Firebase enforces its own
    abuse protection.
  - Removed: "validate client-supplied identifiers with regex" bullet —
    superseded by Principle I's redefinition (no client-supplied identifiers
    are accepted at all).
  - Added: identity MUST come exclusively from a verified Firebase ID token
    via `core/firebase_auth.py`; `FIREBASE_CREDENTIALS_PATH` handling and
    fail-closed behavior requirements.
- Added sections: none structurally (Security & Deployment Requirements
  rewritten in place)
- Removed sections: none structurally
- Templates requiring updates:
  - ✅ .specify/templates/plan-template.md (generic "[Gates determined based on constitution file]" — no change needed, gate check reads this file directly)
  - ✅ .specify/templates/spec-template.md (no constitution references found)
  - ✅ .specify/templates/tasks-template.md (no constitution references found)
  - ✅ .specify/templates/checklist-template.md (no constitution references found)
  - ✅ CLAUDE.md (already updated for the Firebase migration — documents `core/firebase_auth.py`, removed SimpleJWT/password/throttling sections, consistent with this amendment)
- Follow-up TODOs: none
-->

# AI Therapist Backend Constitution

## Core Principles

### I. Data Isolation & Privacy (NON-NEGOTIABLE)

Every endpoint that reads or writes mood/conversation or account data MUST
scope that operation to `request.user`, where `request.user` is set
exclusively by a verified Firebase ID token (`core/firebase_auth.py`). No
endpoint may accept a client-supplied identifier (request body field or
query parameter) for the purpose of looking up, filtering, or modifying
data — `therapist.MoodEntry.user_id` MUST always be populated from
`str(request.user.id)` server-side, never from client input. No endpoint may
return or aggregate data across users.
**Rationale**: This is a mental health application handling sensitive
personal disclosures. A single cross-user data leak is a trust-ending and
potentially harmful incident, not a recoverable bug. Accepting any
client-supplied identifier as a lookup key reintroduces exactly the
IDOR-shaped risk this principle exists to close — isolation MUST rest
entirely on verified authentication identity, not on input validation of a
free-text field.

### II. Input & Contract Validation

All request input MUST be validated through a DRF serializer before touching
business logic or the database — no raw `request.data` access in views.
Read and write concerns MUST use distinct serializers (e.g.
`MoodEntrySerializer`/`MoodEntryCreateSerializer` in `therapist`,
`UserSerializer`/`UserProfileUpdateSerializer` in `accounts`) so
that read-only and identity-bearing fields (`id`, `ai_response`,
`created_at`, `firebase_uid`, `email`, `username`, `is_staff`, etc.) can
never be client-supplied. API surface changes MUST stay reflected in
drf-spectacular schema output (`/api/docs/`, `/api/redoc/`).
**Rationale**: Class-based views plus serializer validation is the existing
convention; mixing concerns invites unvalidated input reaching the AI
service, the database, or identity-bearing fields.

### III. Resilient External AI Integration

`generate_ai_response()` and any other external AI call MUST be treated as
fallible: it may raise on network failure, timeout, or API error.
View-layer callers MUST catch these exceptions, persist a safe fallback
response, and still return HTTP 200 to the client — a third-party AI outage
MUST NOT surface as a 5xx to the end user. `ai_model.py` itself MUST remain a
stateless, synchronous wrapper around the Groq API and MUST NOT swallow
exceptions itself; handling happens at the call site, where context
(fallback copy, persistence) is known.
**Rationale**: Users in a vulnerable emotional state hitting a generic
500 error is a worse outcome than receiving a gentle fallback message while
the entry is still saved for later context.

### IV. Test Coverage for Critical Flows

Every new or modified endpoint MUST have a corresponding test in that app's
`tests.py` covering at least the success path and the primary failure mode
(missing required field, unauthenticated/invalid-token request, or
external-call failure). Tests MUST mock `generate_ai_response()`,
`core.firebase_auth.auth.verify_id_token` (for any authenticated-flow test),
`firebase_admin.auth.delete_user` (for account-deletion tests), or any other
external or stubbed call — no test may perform a real network call to Groq,
Firebase, or any other third-party service. `python manage.py test <app>`
MUST pass for every touched app before a change is considered complete.
**Rationale**: Network-dependent tests are slow, flaky, and burn real API
quota or hit live identity infrastructure; mocking is the only way to keep
the suite fast, deterministic, and free of accidental side effects on a real
Firebase project.

### V. Simplicity & Statelessness

The AI service layer MUST remain a stateless wrapper over a remote API —
no local model loading, no in-process ML inference, no caching layer unless
a specific, demonstrated performance problem requires one. Authentication
MUST likewise remain stateless on the Django side: Django verifies Firebase
ID tokens per request and MUST NOT issue, store, or refresh its own
credentials. Features MUST be implemented with the smallest change that
satisfies the requirement; new abstractions (base classes, generic helpers,
config layers) require a concrete second use case before being introduced.
**Rationale**: The project's stated value (`CLAUDE.md`) is a lightweight,
fast-cold-start backend with no GPU/local-model dependency and no
credential-lifecycle code to maintain — added complexity directly undermines
that property.

## Security & Deployment Requirements

- Secrets (`GROQ_API_KEY`, `SECRET_KEY`, `FIREBASE_CREDENTIALS_PATH`) MUST be
  supplied via environment variables; no secret may be hardcoded or
  committed, including in tests or fixtures.
- `DEBUG` MUST default to `False` and only be enabled via environment
  variable in non-production environments.
- Any new deployed domain MUST be added to both `ALLOWED_HOSTS` and
  `CSRF_TRUSTED_ORIGINS` in `core/settings.py`.
- Identity MUST come exclusively from a Firebase ID token verified by
  `core.firebase_auth.FirebaseAuthentication` (`Authorization: Bearer
  <token>`). No endpoint may accept a user identifier from the request body
  or query parameters for authentication or authorization purposes.
  Missing, malformed, invalid, or expired tokens MUST result in 401 on every
  protected endpoint, with no exceptions.
- `firebase_admin.initialize_app(...)` MUST remain guarded (e.g. `if not
  firebase_admin._apps`) and conditioned on `FIREBASE_CREDENTIALS_PATH` being
  set, so that `manage.py check`/`makemigrations`/non-auth tests continue to
  run in environments without real Firebase credentials (e.g. CI).
- Operations that delete or mutate a user's Firebase identity (e.g. account
  deletion) MUST fail closed: if the Firebase-side call errors, the
  operation MUST log the failure and return an error response rather than
  silently proceeding to mutate or delete the local Django record.
- Static files MUST continue to be served via WhiteNoise in production; no
  endpoint may bypass `collectstatic` asset handling.

## Development Workflow

- Model changes MUST be followed by `makemigrations` and `migrate` in the
  same change set — migrations MUST be committed alongside the model edit
  that produced them.
- Existing Arabic-language comments MUST be preserved when editing
  surrounding code; new comments may be written in English or Arabic to
  match the surrounding context, not replace it.
- AI service changes (prompt text, generation parameters, model name) MUST
  be documented in `CLAUDE.md` if they change observable behavior (response
  length, tone rules, `[SESSION_END]` triggering conditions).
- Before marking work complete, run the relevant app's test suite
  (`python manage.py test <app>`) and confirm the relevant endpoint manually
  (or via a mocked test) against the documented request/response flow in
  `CLAUDE.md`.

## Governance

This constitution supersedes ad-hoc conventions when the two conflict. Any
change to a Core Principle (I–V) is an amendment and MUST update the version
number, the Sync Impact Report at the top of this file, and the "Last
Amended" date below. Pull requests and reviews MUST verify compliance with
the principles above; a deviation MUST be called out explicitly in the
change description with a justification, not silently introduced. Added
complexity (new dependency, new abstraction layer, new persistent service)
MUST be justified against Principle V before being accepted.

Versioning policy: MAJOR for removal/redefinition of a Core Principle,
MINOR for a new principle or materially expanded section, PATCH for
wording/clarification fixes with no rule change.

**Version**: 2.0.0 | **Ratified**: 2026-06-19 | **Last Amended**: 2026-06-22
