# Testing

Becomes `docs/TESTING.md`. Tests are written first (Feature workflow, step 6); `check` runs unit and integration tests, `test:e2e` runs the end-to-end suite, and CI runs both on every PR.

## Levels

| Level | Covers | Runs against | Tools |
|---|---|---|---|
| Unit | Services and business rules, pure logic, validation schemas, DTO mappers, utilities, component behaviour | Fakes for external services; no database | Vitest (with Testing Library for components), pytest, go test, bun test |
| Integration | Repositories and queries, migrations, transactions, RLS or security rules, route handlers with the real stack | A real, isolated test database in Docker (`docs/DATABASE.md`) | The same runner; Testcontainers when useful |
| End-to-end | Critical user flows only | The built app on a freshly migrated and seeded database | Playwright with @axe-core/playwright |
| Load | Hot paths | Staging or a dedicated environment | k6 (`docs/SCALING.md`) |

## Unit and integration conventions

- Location: next to the code for TypeScript and Go (`markers.ts` and `markers.test.ts`); for Python, `tests/` mirroring the source tree. End-to-end tests in `tests/e2e/`, load tests in `tests/load/`.
- Names describe behaviour: `createMarker rejects a title longer than 120 characters`. One behaviour per test, arranged as arrange, act, assert.
- Test a module through its public functions, inputs and outputs, not its private helpers or call order, so refactoring does not break tests.
- Dependencies are passed in (`docs/ARCHITECTURE.md`), so unit tests pass fakes: in-memory or recording fakes for mail, storage, queue and analytics, a fixed clock, and seeded id and random generators. Prefer small hand-written fakes over mocking libraries, and fake only interfaces the project owns.
- Services can be unit tested with a fake repository for their business rules, but every repository function and query runs against the real test database in integration tests. Never mock the database there: a mocked query proves nothing about the SQL.
- Determinism: no real network (unexpected outbound requests fail the test), no sleeps (wait for a condition instead), fixed seeds for fake data, time zone set to UTC, and tests that pass in any order and in parallel.
- Test data comes from factories with sensible defaults (`makeUser({ role: 'admin' })`), not from shared fixture files.
- Required cases: every business rule; every error code; every access rule with negative tests (unauthenticated, wrong user, wrong role); invalid and oversized input; rate limits, quotas, breakers and security event thresholds (`docs/security/SAFEGUARDS.md`).
- Permission matrix: a test generated from the permission catalog states, for every role (including `anonymous`) and every permission, whether it is allowed; a role or permission without an expected answer fails it.
- Route coverage: a test lists every server entry point from the framework's routes (pages with server data, endpoints, form actions, Server Actions, remote functions) and fails when one is missing from the route access list (each entry point's required permission, or `public`). Integration tests call each entry point as every role and expect the matrix's answer.
- Every bug fix and security fix gets a regression test that fails before the fix.
- Property-based tests (fast-check, Hypothesis) suit parsers and money, date and geometry calculations.
- Snapshot tests only for small, stable serialized output, never for whole pages or components.

## Environment

- Tests run with `LOG_LEVEL=warn` and the `noop` analytics adapter unless a test targets logging or analytics.
- A separate test database, never the development one; integration tests are isolated per test (`docs/DATABASE.md`).

## End-to-end

- Critical flows only: sign-up and sign-in, the core create and view flow, payment if any, account export and deletion.
- The suite also runs axe accessibility checks on key pages in both themes, metadata checks on public routes (`docs/SEO.md`), consent checks (`docs/PRIVACY.md`), and the feedback message, role and error ref on key success and failure paths (`docs/DESIGN.md`).
- Locate elements by role and label (`getByRole`, `getByLabel`), never by CSS classes; this also exercises accessibility.
- CI may retry a failed e2e test up to twice to capture a trace; a test that passes only on retry is flaky.

## Flaky tests

A flaky test is a bug. Fix it at once, or quarantine it with an issue and an owner so it stops blocking CI, and fix it within a week. Never delete it, and never raise timeouts or add sleeps to hide it.

## Coverage

Coverage is reported in CI, not used as a target or a gate. What matters is that no business rule or access rule is untested: review the report for untested branches in services and authorization checks.

## Lean profile

Unit and integration tests as above. End-to-end tests cover only sign-in and the main task, with axe on those pages; no load tests.

## Strict profile additions

- Mutation testing (StrykerJS, mutmut, or an equivalent for the language) on auth, permissions and payment modules, on a schedule, to confirm the tests catch real faults.
- Contract tests for every external API the app consumes or provides.
- Coverage of auth, permission and payment modules reviewed in every PR that changes them.
