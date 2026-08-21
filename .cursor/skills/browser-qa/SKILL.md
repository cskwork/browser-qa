---
name: browser-qa
description: Browser QA for any website with reviewable YAML DAG scenarios, plus the engine choice and API request/response evidence underneath it. Use when the user says QA or browser test; gives a URL to verify; names a known domain or feature to re-QA; wants a regression sweep after a feature lands; asks for a quick smoke check; wants to record a test by clicking, schedule one, or open the QA dashboard; needs QA against a local stack because the shared environment is down or the cases are destructive; needs to see which API a screen actually called and what it returned; is stuck on a popup, viewer or new-tab flow; or is choosing between agent-browser, Playwright and MCP engines.
---

# browser-qa - browser QA on anything, for anyone

Skill `browser-qa`, runtime command `superqa`. Contract: prompt -> scenarios -> real
browser evidence -> report in the user's language.

## Mode (classify the request, state it in one line)

| Signal in request | Mode | Route |
|---|---|---|
| known domain / "QA <domain> <feature>" / repeat QA on something QA'd before | DOMAIN-QA | load the domain pack, QA per feature area, reuse archived scripts (`reference/domain-packs.md`) |
| "QA this <url>", vague target, no scenarios yet | EXPLORE-QA | explore live site, generate scenario cases, run them (`reference/agent-qa.md`) |
| scenarios exist / "run the cases" / feature finished, verify | REGRESSION | `superqa run --all --site <site>`; diff vs last run (`reference/agent-qa.md` step 5) |
| "quick check / smoke / is it up" | AUTO | `superqa auto <url> --site <site>` |
| non-dev wants to create a test by clicking | RECORD | `superqa record <url>` or TUI `n` key (`reference/tui.md`) |
| "every N minutes / daily / automate" | SCHEDULE | `superqa schedule add <scenario> --every <min>` + daemon (`reference/tui.md`) |
| "open the QA app / dashboard" | TUI | web dashboard `superqa serve`; terminal `bash scripts/superqa.sh` (`reference/tui.md`) |
| "test locally / without the dev server / offline", shared env down, destructive cases | LOCAL-OFFLINE | bring the stack up locally, run the same scenarios with `--var base_url=...` (`reference/local-offline.md`) |

## Hard rules

1. **Site knowledge stays local.** Entry URLs, accounts, login quirks, popup behavior live
   in `~/.superqa/sites/<site>/rules.md` + the var store. Never committed, never in a
   pushed scenario (`reference/site-rules.md`).
2. **Credentials via the var store only.** `superqa vars set <site> username|password <v>`;
   scenarios use `{{username}}` / `{{password}}`. Password-like keys auto-mask in reports.
3. **Evidence or it did not happen.** Every run writes
   `~/.superqa/reports/<stamp>-<name>/report.html` + per-step screenshots. Quote the path
   and the pass/fail counts.
4. **Report in the user's language.** Scenario `language:` drives report labels; your
   summary follows the conversation (`reference/report.md`).
5. **Side effects are findings.** Console errors, failed requests, 4xx/5xx, unexpected
   dialogs/tabs are collected, deduped, and diffed; new types = regression signal. Declare
   known noise in `ignore.yaml`, never by hand (`reference/side-effects.md`).
6. **Popups never block a run.** Policy auto-accepts dialogs and follows new tabs; scenario
   `policy:` overrides (`reference/scenario-format.md`).
7. **Local copies of shared data are read-only at source, subsetted, redacted, uncommitted.**
   Local config gets dummy secrets only (`reference/local-offline.md`).
8. **Archive reusable scripts.** Useful helpers go to
   `<packs_home>/<domain>/<feature>/scripts/` with a provenance header; check the pack
   before writing a new one (`reference/domain-packs.md`).
9. **Capability picks the engine, then the cascade.** Response bodies, popups, or Windows
   parity - go straight to the proven engine. One engine per page. Never lightpanda.
   Replay is always the browser-qa engine (`reference/engines.md`).
10. **The DAG is the review contract.** `dag.nodes` with stable `id`, `story`, `acceptance`,
    `depends_on` - no selectors or values, those live in the local runtime binding. Run
    `superqa dag check --all --site <site>` before executing. Legacy `steps:` files stay
    readable (`reference/scenario-format.md`).

## EXPLORE-QA loop (default when only a URL/prompt is given)

1. **Ground.** Read `~/.superqa/sites/<site>/rules.md` if present; ask for credentials
   only if login is required and vars are missing.
2. **Explore.** Drive the live site with the selected engine (snapshot -> click ->
   snapshot; `reference/engines.md`), mapping entry flow, login, menus,
   popups/new tabs (`reference/agent-qa.md`).
3. **Generate cases.** Write user-story `dag.nodes` YAMLs to
   `~/.superqa/scenarios/<site>/` covering happy path, validation, error paths, edge
   cases, and meaningful popup/tab transitions. Review story/acceptance/dependencies
   with `superqa dag check --all --site <site>` and the Admin graph, then create the
   separate local runtime binding (`reference/scenario-gen.md`).
4. **Run.** `superqa run --all --site <site> --headless`; without the installed command,
   `python3 -m superqa_tui run ...` from the checkout root, where `superqa_tui/` lives.
5. **Report.** Read the report, triage side effects, summarize for the user in their
   language with the report path. Update the local site rules file with what you learned.

## Non-dev lane (what you tell users)

- **`superqa serve`** - browser dashboard: every scenario with its story DAG, Run button,
  live progress, history, inline reports. Exposes node IDs, stories, acceptance and
  dependencies only; selectors and values stay local.
- **`bash scripts/superqa.sh`** - terminal TUI: `n` record by clicking, `r` run, `a` run
  all, `u` auto QA, `s` schedule, `v` accounts/vars, `o` open report.
- Recording floats a panel in the page (pause / add-assertion / save); typed passwords are
  stored as `{{password}}` (`reference/tui.md`).

## Reference map

| File | When |
|---|---|
| `reference/domain-packs.md` | DOMAIN-QA: per-domain/feature packs, script archiving, pack location config |
| `reference/engines.md` | capability gate + engine cascade; one-engine-per-page rule |
| `reference/agent-browser.md` | agent-browser + chrome-devtools-mcp commands, shared-Chrome login, measured gotchas |
| `reference/agent-qa.md` | EXPLORE-QA / REGRESSION procedure for the agent |
| `reference/scenario-gen.md` | prompt -> reviewable DAG scenario case design method |
| `reference/scenario-format.md` | user-story YAML DAG schema, local runtime binding, `{{vars}}`, policy |
| `reference/side-effects.md` | what is captured; triage rules |
| `reference/site-rules.md` | local per-site knowledge protocol (never commit) |
| `reference/report.md` | report structure + language rules |
| `reference/tui.md` | TUI / record / schedule usage for humans |
| `reference/local-offline.md` | LOCAL-OFFLINE: local stack + data subset, DB-derived fixtures, differential proof |

**Done =** mode stated. QA runs: scenarios exist as checked YAML DAGs under
`~/.superqa/scenarios/<site>/`; graph reviewed; run executed with the report path quoted;
side effects triaged; site rules updated, plus the domain pack in DOMAIN-QA; site data
still only in `~/.superqa/`. RECORD / SCHEDULE / TUI: the surface is up and the user knows
which keys drive it.
