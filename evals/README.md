# Evals for the scaffold-project skill

Repeatable dry runs of the skill's planning step. Each case is an idea with the user's complete answers to step 1, and the checklist the resulting plan must meet. They run before merging a change to the skill's process or to what its plan covers (the scaffold-kit-maintainer skill, "Trying a process change"), and the result goes into the PR. They are not copied into projects.

## Cases

| Case | Mode and profile | What it tests |
|---|---|---|
| `lean-internal-tool.md` | new project, lean | the lean reductions for an internal tool behind sign-in, and a short plan |
| `standard-public-app.md` | new project, standard | the full plan and draft for a public product: tenancy, safeguards, SEO, two languages |
| `strict-health-app.md` | new project, strict | health data and payments: the strict additions, including the agent sandbox |
| `upgrade-existing-repo.md` | upgrade mode | a read-only inventory, critical findings and spending caps first, a gap report and a plan of PRs |

## How to run a case

1. In a new scratch folder, export the kit version under test without its git history: `git -C <kit clone> archive <branch or tag> | tar -x -C <scratch>/kit`, and create `<scratch>/run/tmp`. For the upgrade case, copy the fixture it names to `<scratch>/run/project` and commit it there (`git init -q && git add -A && git commit -qm init`), so any change the run makes shows in `git status`.
2. Start a fresh agent that has not seen the change, either a new Claude Code session or a general-purpose subagent, with the prompt below. Fill in the paths, and paste the case's Answers section where the prompt says so.
3. Grade with a second fresh agent, or by hand: go through the case's "The plan must" and "The plan must not" lists item by item, and mark each pass or fail with the line of the plan that shows it.
4. In the PR, give for each case the items passed out of the total, each failed item with its fix or the reason the checklist changed, and every instruction the run reported as unclear.

## Prompt

```text
You are doing a dry run of a Claude skill, to test whether its written instructions can be followed as they are. Act exactly as a real session using the skill would, but stop where these rules say.

- Read <KIT>/skill/scaffold-project/SKILL.md in full and follow it. <KIT> is the local copy of the kit ($KIT): do not fetch the kit, and never change anything inside it. Read each kit reference before the step that needs it.
- Work only inside <RUN>/. Before any shell command that uses the skill's ${TMPDIR:-/tmp} paths, run `export TMPDIR=<RUN>/tmp`.
- The user's answers are complete, so ask no questions:
<ANSWERS>
- Make no web searches or fetches; where the skill says to check current facts in the trusted sources, write "would check: <source>". Install nothing, run no framework CLIs, and do not create a project.
- New project: steps 1 to 3 only. Write the plan summary, treat it as confirmed, build the draft as step 3 describes (with palette.py writing into the draft folder), treat the draft as approved, and stop before step 4.
- Upgrade: the existing repository is <RUN>/project. Follow upgrade mode up to the plan of PRs, and stop where it waits for the user's approval.

Deliverables:
1. <RUN>/plan.md: the plan exactly as you would show it to the user (for an upgrade: the findings, the gap report and the plan of PRs).
2. For a new project, the draft at <RUN>/tmp/plan-preview/index.html with its themes/ folder.
3. A final reply with (a) the deliverables' paths; (b) every instruction that was unclear, contradictory, missing a needed detail or impossible to follow, with the file and section, what happened and what you did instead; (c) anything you had to guess. Report only problems and guesses, or "none" for a part with nothing to report.
```
