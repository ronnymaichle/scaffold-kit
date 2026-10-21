# Roadmap

The features planned for this app, in build order. Launch tasks are in `docs/LAUNCH-CHECKLIST.md`, and bugs and outside requests in the git host's issues; neither is listed here.

## Rows

- Each row is one feature that fits one PR (the size limit is in `CONTRIBUTING.md`): a thin vertical slice a user can try from start to end, with its screens, server code, data and tests. It names the Planned actions it builds (`docs/ARCHITECTURE.md`).
- Each row has a fixed id (`R1`, `R2`), never renumbered or reused, so the branches and PRs that cite it stay findable when rows move.
- A feature too big for one PR gets the status `split`, and its parts follow it as rows of their own (`R7a`, `R7b`). A row that depends on it is ready when all its parts are done.
- Status: `planned`, `split`, `dropped`, or `done (#14)` with the PR number (`!14` on GitLab). Done and dropped rows stay, so the file also shows progress.

## Order

First what other rows depend on (sign-up and sign-in, the core data), then the riskiest unknowns (paid providers, real-time, payments), so surprises come early, then the rest by value to users. Together, the first rows make the main task work end to end in its simplest form; later rows deepen it.

## Working with it

- A row is ready when every row in its Depends on column is done. When the user names no feature, the lead proposes the first ready row.
- The feature's branch and PR carry its id: `feat/r7-marker-comments`, and `Roadmap: R7` in the PR description. Right after opening the PR, the lead sets the row to `done (#14)` and pushes that commit to the same branch, so the row reaches `main` together with the feature and links to its PR.
- A feature that is not listed gets a row in its own PR. Adding, dropping and reordering rows is the user's decision.

## Features

| ID | Feature: what a user can do afterwards | Depends on | Status |
|---|---|---|---|
| R1 | {{FEATURES: one row per feature in the confirmed plan, in build order, starting with sign-up and sign-in when the app has accounts}} | | planned |
