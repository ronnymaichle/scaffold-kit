# Agent metrics

One row per feature or fix PR, which the lead adds in the same commit that marks the roadmap row done (Feature workflow step 10). Together the rows show how well the agent team works and whether a change to its model or agents made it better or worse (`docs/AGENT-TEAM.md`, Measuring the team).

- Row: the roadmap id (`R7`), or `-` for work without a row.
- PR: the pull request number.
- Model: the lead's model and effort, for example `opus-5.5 xhigh`.
- Slices: slices delegated to implementers; 0 when the lead worked alone.
- Extra attempts: fix-and-rerun rounds after a slice's first failed check, summed over the slices.
- Blocked or failed: agents that stopped `blocked` or `failed`, or ended without a report.
- Findings: what the reviewing agents found at step 8 before the fixes, as critical/high/medium/low.
- Corrections: times the user changed the lead's restatement, options or plan, or sent the work back after the report.
- Fixes: for a fix, the roadmap row of the feature the bug came from; each one counts as an escaped bug of that feature.

| Row | PR | Model | Slices | Extra attempts | Blocked or failed | Findings C/H/M/L | Corrections | Fixes |
|---|---|---|---|---|---|---|---|---|
