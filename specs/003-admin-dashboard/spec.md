# Feature Specification: Admin Dashboard

**Feature Branch**: `003-admin-dashboard`

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "Build a proper admin dashboard for Lueur on top of Django Admin — reusing existing user/content management and account-deletion logic. Modern-looking, secure internal tool for day-to-day ops, content moderation, and basic analytics on user and journal-entry data, including a controlled way to process manual account-deletion requests."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Review and moderate journal content (Priority: P1)

A staff operator needs to browse and search user accounts and journal entries to investigate a support request, moderate content, or review flagged entries — without having to run raw database queries.

**Why this priority**: This is the baseline operational need the dashboard exists for; without it, staff have no supported way to look at user/content data at all.

**Independent Test**: Can be fully tested by logging in as a staff user, opening the account list and the journal-entry list, and confirming entries can be searched, filtered, and opened to view full detail without needing a separate tool.

**Acceptance Scenarios**:

1. **Given** a staff operator is logged into the dashboard, **When** they open the journal entries list, **Then** they see a readable list (long text truncated) that can be filtered by date and by whether an entry was flagged as crisis-related, and can search by content.
2. **Given** a staff operator opens a single journal entry, **When** they view its detail page, **Then** they see the full, untruncated text and cannot edit the entry's creation timestamp.
3. **Given** a staff operator opens the user account list, **When** they view it, **Then** they can filter by account status (active, verified, staff) and see accounts ordered with the most recently created first.
4. **Given** a staff operator is viewing a single user account, **When** they look at that account's detail, **Then** they see how many journal entries that user has and can jump to a pre-filtered list of just that user's entries.

---

### User Story 2 - Process a manual account-deletion request (Priority: P2)

A staff operator receives an account-deletion request from a user who can't access the app (e.g., via the privacy-policy support email) and needs to fulfill it without using a command line.

**Why this priority**: This directly satisfies an existing, documented promise in the privacy policy (deletion requests for users without app access) and is a recurring, real operational task — but it's secondary to basic read/browse access, since deletion is comparatively rare.

**Independent Test**: Can be fully tested by locating a specific user account in the dashboard, invoking the delete action, confirming the action, and verifying the account and all of that user's journal entries are gone.

**Acceptance Scenarios**:

1. **Given** a staff operator has located the target user account, **When** they trigger the delete-account action, **Then** the system requires an explicit confirmation step before anything is deleted.
2. **Given** the operator confirms deletion, **When** the deletion completes successfully, **Then** the user's external identity, all of their journal entries, and their local account record are all removed, using the exact same deletion process as the self-service and email-request paths (no separate/duplicate deletion logic).
3. **Given** the operator confirms deletion, **When** the external identity deletion step fails, **Then** the local account and journal entries are left untouched (nothing is partially deleted) and the operator sees a clear error.

---

### User Story 3 - Check overall app health at a glance (Priority: P3)

A staff operator or the app owner wants a quick, high-level read on how the app is being used and whether anything looks operationally concerning (e.g., a spike in crisis-flagged entries), without exporting data or writing a report.

**Why this priority**: Valuable for day-to-day awareness and lightweight oversight, but not required for the dashboard to be useful — browsing and deletion (P1/P2) deliver value on their own.

**Independent Test**: Can be fully tested by logging in and viewing a summary screen showing current aggregate counts, without needing to configure or export anything.

**Acceptance Scenarios**:

1. **Given** a staff operator logs into the dashboard, **When** they view the summary/overview screen, **Then** they see the total number of active user accounts, the number of new journal entries in the last 7 and last 30 days, the number of crisis-flagged entries in the last 7 and last 30 days, and the average check-in streak across users who have at least one entry.
2. **Given** the underlying data changes (new entries, deletions), **When** the operator reloads the summary screen, **Then** the numbers reflect the current state of the data (not a stale cached snapshot from before the change).

---

### Edge Cases

- What happens when a staff operator tries to trigger the delete-account action on an account that has already been deleted or has no journal entries? System should complete without error and simply report nothing further to delete.
- What happens when a non-staff user (e.g., a regular app user whose Firebase identity happens to exist as a Django user row) tries to reach the dashboard? Access must be denied — dashboard access is restricted to staff accounts only, consistent with existing Django Admin behavior.
- What happens when the summary/overview screen is viewed while there are zero users or zero journal entries? Counts should show zero rather than erroring, and the average-streak figure should show zero or a clear "no data" state rather than dividing by zero.
- What happens when a journal entry's flagged-crisis status changes after the entry was created (if that ever becomes possible)? Out of scope for this feature — the dashboard reflects flagged status as currently stored/derived at view time.
- What happens if two staff operators attempt to delete the same account at nearly the same time? The second attempt should find no matching account/entries left to delete and complete without corrupting data, consistent with the underlying deletion process already being idempotent-safe on a missing record.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a staff-only internal dashboard for browsing, searching, and filtering user accounts and journal entries; access MUST be denied to any account that is not marked as staff.
- **FR-002**: Dashboard MUST display journal entries in a list view with long text fields (thoughts, AI response) shown in a readable, truncated form, while the full untruncated text MUST be visible on that entry's detail view.
- **FR-003**: Dashboard MUST allow filtering the journal-entry list by creation date and by whether the entry was flagged as crisis-related.
- **FR-004**: Dashboard MUST prevent a journal entry's creation timestamp from being edited through the dashboard.
- **FR-005**: Dashboard MUST allow filtering the user-account list by account status (active, verified, staff) and MUST order the list with the most recently created accounts first by default.
- **FR-006**: Dashboard MUST show, for each user account, how many journal entries that user has, and MUST provide a way to navigate directly to that user's filtered entry list.
- **FR-007**: Dashboard MUST provide a staff-triggerable action that permanently deletes a user's account, their external authentication identity, and all of their journal entries, using the same deletion logic already used by the self-service in-app deletion and the email-request deletion process — this feature MUST NOT introduce a second, separate implementation of account deletion.
- **FR-008**: The delete-account action MUST require an explicit confirmation step before performing any deletion, since the action is irreversible.
- **FR-009**: If the external identity deletion step of the delete-account action fails, the system MUST leave the local account and journal entries untouched and MUST report the failure clearly to the operator — matching the existing fail-closed guarantee of the other deletion paths.
- **FR-010**: Dashboard MUST provide a summary/overview view showing: total active user accounts; count of journal entries created in the last 7 days; count of journal entries created in the last 30 days; count of crisis-flagged entries in the last 7 days; count of crisis-flagged entries in the last 30 days; and the average check-in streak across users who have at least one journal entry.
- **FR-011**: Summary/overview figures MUST reflect the current underlying data at the time the view is loaded, not a stale precomputed snapshot.
- **FR-012**: Dashboard MUST NOT expose full journal-entry text (thoughts or AI response content) anywhere outside the dedicated entry list/detail views — including in any activity/audit trail the dashboard records of staff actions.
- **FR-013**: Dashboard MUST be reachable and fully functional (including its visual styling and static assets) in the production deployment environment, not only in local development.

### Key Entities

- **User Account**: An existing app user record (email, status flags, verification state, creation date, linked external identity). The dashboard reads and filters this data and can trigger its permanent deletion; it does not introduce new user-facing fields.
- **Journal Entry**: An existing per-user mood/thoughts/AI-response record with a creation timestamp and a crisis-flagged status. The dashboard reads, filters, and displays this data; it does not change how entries are created.
- **Deletion Action Record**: Not a new stored entity — refers to the built-in staff-action audit trail the dashboard framework may keep of who ran the delete action and when, which per FR-012 must not itself contain journal content.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A staff operator can locate a specific user's full journal history (search + open detail) in under 1 minute without using any tool other than the dashboard.
- **SC-002**: A manual account-deletion request received by email can be fully processed by a staff operator through the dashboard, start to finish, without touching a command line.
- **SC-003**: 100% of completed manual deletions performed via the dashboard result in the same end state (identity removed, entries removed, account removed) as deletions performed through the existing self-service and command-line paths — there is no divergent or partial-deletion outcome specific to the dashboard.
- **SC-004**: The summary/overview screen loads and displays all six aggregate figures (active users, 7/30-day entries, 7/30-day crisis-flagged entries, average streak) in a single view, with no manual computation or export required by the operator.
- **SC-005**: No non-staff account can reach any dashboard view, in 100% of access attempts.
- **SC-006**: The dashboard renders with its intended visual styling (not broken/unstyled) when accessed on the live production deployment, not just on a local machine.

## Assumptions

- "Staff" means the existing Django `is_staff` flag already used to gate admin access — no new role/permission model is introduced by this feature.
- The dashboard is built as an enhancement of the existing Django Admin interface rather than a separate application, reusing existing account, journal-entry, and deletion logic rather than duplicating it.
- "Crisis-flagged" filtering assumes flagged status is available as queryable data on the journal entry at the time this feature is planned; if it currently exists only as a value computed at response time rather than stored per entry, how to make it filterable is an implementation decision for the planning phase, not this specification.
- Analytics in this feature are limited to the aggregate figures explicitly listed (FR-010); building broader reporting, data export, or charting is out of scope for this feature.
- Restricting dashboard network access further (e.g., by IP address at the infrastructure level) is a defense-in-depth option considered but not committed to as a requirement of this feature; staff-account gating (FR-001) is the enforced access control.
- The dashboard is for internal staff use only; it is not a user-facing feature and has no end-user-visible surface.
