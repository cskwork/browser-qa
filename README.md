<p align="center"><img src="logo.png" width="120" alt="logo" /></p>

# SuperQA

Browser QA on any website - dev, staging, or prod - for anyone.

Give it a URL and a one-line prompt, and SuperQA explores the site, generates test
scenario cases, drives a real browser through them, detects side effects the flow
itself would never assert (console errors, JS exceptions, failed requests, unexpected
dialogs/popups/tabs), and writes a report a non-developer can read - in your language.

Two ways to use it:

- **As a Claude Code skill** - the agent reads `SKILL.md`, explores with
  `playwright-cli`, writes scenario YAMLs, runs them deterministically, and triages the
  findings for you.
- **As a standalone app** - a Textual TUI plus CLI. Record a scenario by clicking
  through the site in a real browser, then run, schedule, and automate it. No code.

## Why

- QA after every feature: a developer finishes a backend/frontend change, you run the
  site's saved cases (`superqa run --all --site myshop`) and get a regression verdict
  with evidence in minutes.
- Non-developers own the tests: recording is literally clicking through the site while
  a floating SuperQA panel captures each step with a human-readable description.
- Side effects are first-class: every run watches the whole browser context - including
  popups - so a 500 on an API, an uncaught exception, or an unexpected new tab shows up
  even when every asserted step passed. Duplicates are counted, known noise is split
  out via per-site ignore rules.
- Every run auto-compares against the previous run of the same scenario: new failures
  and newly appeared side-effect types are flagged as regressions; identical runs get
  a clean "no regression" verdict.
- Visual regression built in: accept a trusted run as baseline (`superqa baseline`),
  and later runs pixel-diff every step screenshot, flagging layout changes with a
  red-overlay diff image. Failing runs also save a Playwright `trace.zip` replay.
- Reviewable user-story DAGs: each new case stores stable IDs, user stories, visible
  acceptance criteria, and prerequisites in YAML. `superqa dag check` validates the
  graph, and the local Admin draws branches and joins without exposing browser mechanics,
  values, or secrets.
- CI-ready: `--junit results.xml` renders runs as native test results in
  Jenkins/GitHub Actions; `superqa doctor` checks the environment in plain language.

## Install

```bash
git clone https://github.com/cskwork/superqa-skill ~/.claude/skills/browser-qa
cd ~/.claude/skills/browser-qa
pip3 install textual playwright pyyaml && python3 -m playwright install chromium
# optional: pip3 install -e .   ->  gives you the `superqa` command
```

Requirements: Python 3.10+, Chromium via Playwright (installed above).

## Quick start (no code)

```bash
superqa serve                        # web admin: click Run on any scenario
bash scripts/superqa.sh              # or the terminal TUI
```

The **web admin** (`superqa serve` -> http://127.0.0.1:8760) is the most clickable
surface: every scenario - recorded or agent-authored - with a reviewable dependency
DAG, a Run button, live progress, run history, and inline reports. It shares the
TUI/CLI data.

- `n` - record: a Chrome window opens with a SuperQA panel (bottom-right). Click
  through the site; every click/input becomes a step. Passwords are stored as
  `{{password}}` placeholders, never plain text. Press "저장 후 종료" to save.
- `r` - run the selected scenario and watch the browser replay it.
- `a` - run everything (regression sweep). `u` - one-button smoke QA for any URL.
- `s` - schedule a scenario every N minutes. `v` - manage accounts/variables.
- `o` - open the latest HTML report.

## Quick start (CLI / CI)

```bash
superqa record https://myshop.example.com --site myshop --name 로그인-정상
superqa vars set myshop username myid
superqa vars set myshop password s3cret          # auto-masked in reports
superqa dag check --all --site myshop             # validate YAML DAGs before replay
superqa run --all --site myshop --headless        # exit code 0 = green
superqa auto https://myshop.example.com           # smoke QA, zero setup
superqa schedule add 로그인-정상 --every 30 && superqa schedule daemon

# same cases against another target (local stack, staging) - nothing is persisted
superqa run --all --site myshop --headless --var base_url=http://localhost:3000
```

## Running against a local stack

`--var KEY=VALUE` retargets a run without rewriting the stored variables, so one scenario
set covers shared environments and a copy of the stack running on your machine. Testing
against local services and a local data subset is the way to cover destructive cases and
first-time-user states that shared environments cannot hold -
[`reference/local-offline.md`](reference/local-offline.md) has the procedure, including how
to derive fixtures from the local database and how to prove a case can actually fail.

## What a run produces

`~/.superqa/reports/<stamp>-<scenario>/`:

- `report.html` - pass/fail badges, step table with inline screenshots, side-effect
  table. Self-contained; send it to anyone.
- `report.md` - the same, paste-ready.
- `step-NN.png` - screenshot after every step.

Report language follows the scenario's `language:` field (Korean and English built in).

## Scenario format

Plain YAML that non-developers can read and edit - see
[reference/scenario-format.md](reference/scenario-format.md):

```yaml
name: 로그인-정상
site: myshop
language: ko
policy: { dialogs: accept, popups: follow }
dag:
  nodes:
    - id: arrive-login
      story: "방문자로서 서비스의 로그인 시작점에 도착할 수 있다."
      depends_on: []
      acceptance: ["로그인 입력 화면이 표시된다."]
    - id: prepare-login
      story: "등록 회원은 자신의 로그인 정보를 준비할 수 있다."
      depends_on: [arrive-login]
      acceptance: ["아이디와 비밀번호를 입력할 수 있다."]
    - id: reach-account
      story: "회원으로서 내 계정에 접근하기 위해 로그인할 수 있다."
      depends_on: [prepare-login]
      acceptance: ["환영 문구와 계정 영역이 표시된다."]
```

The checked YAML contains no `action`, `selector`, or input value. The recorder/QA agent
keeps the detailed browser binding locally under `~/.superqa/runtimes/`; one story can
therefore replay several browser operations without becoming several review nodes. Nodes
execute serially in stable topological order (YAML declaration order breaks ties), while
the DAG makes their branches and joins reviewable. Existing `steps:` files remain readable
without a rewrite; use `superqa dag migrate` only when you want to convert one.

## Domain QA packs

Repeat QA on the same product should not start from zero. A **pack**
(`~/.superqa/packs/<domain>/` by default; location is asked once and stored in
`~/.superqa/config.yaml`) keeps the domain's feature map (`pack.md`), per-feature
notes, and **archived reusable scripts** - the data-discovery SQL, probes, and
harnesses that would otherwise die in ticket folders. Saying "QA \<domain\>
\<feature\>" loads the pack and runs what already exists; only gaps get explored.
See [reference/domain-packs.md](reference/domain-packs.md).

Interactive exploration picks the best installed engine automatically:
ego-browser (ego-lite) first on macOS, then Playwright MCP, then `playwright-cli`,
then other drivers ([reference/engines.md](reference/engines.md)). Deterministic
replay and reports always come from the SuperQA engine.

## Site data stays local

Everything site-specific lives under `~/.superqa/` - never in this repo:

```
~/.superqa/
├── superqa.db               # accounts/vars (SQLite; secret keys masked in reports)
├── config.yaml              # pack home + exploration engine choice
├── scenarios/<site>/*.yaml  # your test cases
├── runtimes/<site>/*.yaml   # local browser bindings; never the review artifact
├── reports/                 # run evidence
├── packs/<domain>/          # feature map + archived reusable QA scripts
└── sites/<site>/rules.md    # per-site playbook the agent maintains
```

## Architecture

```
SKILL.md + reference/        agent lane: explore -> generate cases -> run -> triage
superqa_tui/
├── engine.py                Playwright driver: replay, record, auto-smoke,
│                            side-effect collectors (context-wide, incl. popups)
├── recorder_overlay.js      injected shadow-DOM panel: record / assert / save
├── scenario.py  store.py    YAML DAG/legacy models; SQLite vars + run history
├── report.py    i18n.py     md/html reports, ko/en strings, secret masking
├── visual.py    junit.py    screenshot baselines; JUnit XML for CI
├── diff.py      scheduler.py run-to-run diff; interval schedules
├── admin.py                 web admin server (stdlib http, DAG review + click-to-run)
├── app.py                   Textual TUI
└── cli.py                   headless CLI (CI-friendly exit codes)
```

## Tests

```bash
python3 tests/test_engine_smoke.py   # replay + record + auto QA on local fixtures
python3 tests/test_tui_smoke.py      # Textual pilot smoke
python3 tests/test_dag.py            # DAG validation, migration, execution semantics
python3 tests/test_admin.py          # Admin graph rendering + one real replay
```

Verified against live sites: full pipeline (scenarios, dialogs, multi-tab popup
chains, login via stored vars) ran 3 consecutive green rounds on two independent
sites, and the side-effect collector surfaced a real uncaught JS exception on one
of them.

## License

MIT
