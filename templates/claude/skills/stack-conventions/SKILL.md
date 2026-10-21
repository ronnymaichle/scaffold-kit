---
name: stack-conventions
description: "How this project writes code in {{STACK_SUMMARY}}: the conventional and the currently recommended way for each framework and version in use, the project's choice where they differ, and the old APIs not to use. Load before planning, writing or reviewing code."
---

# Stack conventions

The versions below are the ones in the lockfile. Every entry was written from the official documentation for that version and names its source and the date it was checked. Where this file and memory disagree, this file wins; where this file and the official docs for the version in use disagree, the docs win and this file is fixed in the same PR.

Architecture, data, security and design rules live in `docs/` and the root `CLAUDE.md`; this file covers only how the language and frameworks are used. It is refreshed on every major upgrade and in the quarterly `chore(agents)` review (`docs/AGENT-TEAM.md`).

## Versions in use

| Runtime, framework or library | Version | Supported until | Checked |
|---|---|---|---|
| {{NAME}} | {{VERSION}} | {{END_OF_SUPPORT}} | {{YYYY-MM-DD}} |

When the developer uses Context7 (`docs/AGENT-TEAM.md`), each library's Context7 ID, the official repository's and never a fork's, is added after its version, so a lookup takes one call.

## Conventional and recommended

One row per topic where the version in use has a preferred way: for example project structure, data loading, forms and mutations, state, routing, styling, error handling, async work, testing. When the long-established way and the currently recommended way differ, both are named and the project's choice links its ADR.

| Topic | Conventional way | Recommended now, if different | Project's choice |
|---|---|---|---|
| {{TOPIC}} | {{CONVENTIONAL}} | {{RECOMMENDED_OR_SAME}} | {{CHOICE_AND_ADR}} |

## Traps

APIs and patterns from earlier versions that still look plausible but are wrong or deprecated here, each with the form to use instead. Add a line whenever an agent or a review catches one.

- {{OLD_FORM}}: use {{NEW_FORM}} ({{SOURCE}})

## Sources

The official pages this file was written from, each with the date checked. They are also listed in `docs/SOURCES.md`.

- {{OFFICIAL_DOC_URL}} (checked {{YYYY-MM-DD}})
