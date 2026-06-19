<!--
Sync Impact Report
- Version change: 1.0.0 → 1.1.0
- Modified principles:
  - I. Data Isolation & Privacy — generalized beyond `MoodEntry`/`user_id` to
    require `request.user`-scoping for any authenticated app (e.g. `accounts/`)
  - II. Input & Contract Validation — examples generalized to reference both
    `therapist` and `accounts` serializers, not just `therapist`'s
  - IV. Test Coverage for Critical Flows — generalized from
    "`therapist/tests.py`"/"`python manage.py test therapist`" to apply to
    any app's test suite, and from mocking only `generate_ai_response()` to
    mocking any external/stubbed call (e.g. `accounts`'s email-send stubs)
- Added sections: none (Security & Deployment Requirements expanded in place)
- Removed sections: none
- Templates requiring updates:
  - ✅ .specify/templates/plan-template.md (generic "[Gates determined based on constitution file]" — no change needed, gate check reads this file directly)
  - ✅ .specify/templates/spec-template.md (no constitution references found)
  - ✅ .specify/templates/tasks-template.md (no constitution references found)
  - ✅ .specify/templates/checklist-template.md (no constitution references found)
  - ✅ CLAUDE.md (already documents `accounts/`'s JWT lifetimes, password policy, and throttling — consistent with the new Security & Deployment Requirements bullets added below)
- Follow-up TODOs: none
-->

# AI Therapist Backend Constitution

## Core Principles

### I. Data Isolation & Privacy (NON-NEGOTIABLE)

Every `MoodEntry` query MUST be scoped by `user_id`; no endpoint may return or
aggregate data across users. `user_id` MUST be validated against the strict
regex (`^[A-Za-z0-9_-]{3,128}$`) on every serializer that accepts it. New
endpoints that read or write mood/conversation data MUST filter by `user_id`
before any other condition is applied. For any app with authenticated users
(e.g. `accounts/`), every endpoint MUST scope reads and writes to
`request.user` — no endpoint may accept a client-supplied identifier to look
up or modify another account's data.
**Rationale**: This is a mental health application handling sensitive
personal disclosures. A single cross-user data leak is a trust-ending and
potentially harmful incident, not a recoverable bug. The same standard
applies whether isolation is enforced via a validated `user_id` field or via
authentication identity — the failure mode (one user seeing another's data)
is identical.

### II. Input & Contract Validation

All request input MUST be validated through a DRF serializer before touching
business logic or the database — no raw `request.data` access in views.
Read and write concerns MUST use distinct serializers (e.g.
`MoodEntrySerializer`/`MoodEntryCreateSerializer` in `therapist`,
`UserSerializer` plus per-action write serializers in `accounts`) so
that read-only fields (`id`, `ai_response`, `created_at`, `is_verified`,
`is_staff`, etc.) can never be client-supplied. API surface changes MUST stay
reflected in drf-spectacular schema output (`/api/docs/`, `/api/redoc/`).
**Rationale**: Class-based views plus serializer validation is the existing
convention; mixing concerns invites unvalidated input reaching the AI
service, the database, or the authentication layer.

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
(missing required field, missing/invalid identifier, external-call failure,
or — where applicable — rate-limit exceeded). Tests MUST mock
`generate_ai_response()`, `accounts`'s `send_password_reset_email()`/
`send_verification_email()` stubs, or any other external or stubbed call —
no test may perform a real network call to Groq or any other third-party
service. `python manage.py test <app>` MUST pass for every touched app
before a change is considered complete.
**Rationale**: Network-dependent tests are slow, flaky, and burn real API
quota; mocking is the only way to keep the suite fast and deterministic —
this applies equally to the AI integration and to any future external
integration (e.g. real email delivery).

### V. Simplicity & Statelessness

The AI service layer MUST remain a stateless wrapper over a remote API —
no local model loading, no in-process ML inference, no caching layer unless
a specific, demonstrated performance problem requires one. Features MUST be
implemented with the smallest change that satisfies the requirement; new
abstractions (base classes, generic helpers, config layers) require a
concrete second use case before being introduced.
**Rationale**: The project's stated value (`CLAUDE.md`) is a lightweight,
fast-cold-start backend with no GPU/local-model dependency — added
complexity directly undermines that property.

## Security & Deployment Requirements

- Secrets (`GROQ_API_KEY`, `SECRET_KEY`) MUST be supplied via environment
  variables; no secret may be hardcoded or committed, including in tests or
  fixtures. `SECRET_KEY` also signs any JWTs issued by the project — it MUST
  be a strong, non-default value in production.
- `DEBUG` MUST default to `False` and only be enabled via environment
  variable in non-production environments.
- Any new deployed domain MUST be added to both `ALLOWED_HOSTS` and
  `CSRF_TRUSTED_ORIGINS` in `core/settings.py`.
- New endpoints that accept user-supplied identifiers MUST validate them
  with an explicit regex or serializer field constraint — free-text fields
  used as lookup keys are not acceptable.
- Token-based authentication MUST use explicit, bounded access/refresh token
  lifetimes plus refresh-token rotation and blacklisting on logout (see
  `SIMPLE_JWT` in `core/settings.py`) — no endpoint may rely on
  indefinite-lifetime credentials.
- Any endpoint that accepts or sets a password MUST enforce a minimum
  server-side strength policy (see `accounts/validators.py`) — client-side
  validation alone is not acceptable.
- Authentication-sensitive endpoints (registration, sign-in, password
  reset, email verification) MUST be rate-limited per account and per
  originating IP address (see `accounts/throttling.py` for current
  thresholds).
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

**Version**: 1.1.0 | **Ratified**: 2026-06-19 | **Last Amended**: 2026-06-19
