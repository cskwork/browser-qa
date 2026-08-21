# Scenario YAML schema

Location: `~/.superqa/scenarios/<site>/<name>.yaml`. This is the file a product
owner reviews: it describes a user journey, not browser mechanics.

```yaml
name: 로그인-정상            # shown in TUI and reports
site: myshop                 # var-store scope + grouping
base_url: https://myshop.example.com
language: ko                 # report language (ko|en)
tags: [smoke, login]
policy:
  dialogs: accept            # accept | dismiss | fail
  popups: follow             # follow (switch to new tab) | ignore | fail
  fail_on_console_error: false
  fail_on_http_error: false
  ignore_effects:
    - "[Analytics]"          # recorded, but separated as known noise in reports

dag:
  nodes:
    - id: arrive-login
      story: "방문자로서 서비스의 로그인 시작점에 도착할 수 있다."
      depends_on: []
      acceptance:
        - "로그인 입력 화면이 표시된다."

    - id: prepare-login
      story: "등록 회원은 자신의 로그인 정보를 준비할 수 있다."
      depends_on: [arrive-login]
      acceptance:
        - "아이디와 비밀번호를 입력할 수 있다."

    - id: clear-notice
      story: "방문자는 안내 알림을 처리하고 로그인 여정을 계속할 수 있다."
      depends_on: [arrive-login]
      acceptance:
        - "알림을 닫은 뒤에도 로그인 화면을 계속 볼 수 있다."

    - id: reach-account
      story: "회원으로서 내 계정에 접근하기 위해 로그인할 수 있다."
      depends_on: [prepare-login, clear-notice]
      acceptance:
        - "환영 문구와 계정 영역이 표시된다."
```

## What a DAG node means

Every `dag.nodes` entry has exactly four review fields:

| field | meaning |
|---|---|
| `id` | stable, short identifier used for dependencies and runtime wiring |
| `story` | one user-story-level capability, written in the user's language |
| `depends_on` | the user stories that must already hold; `[]` for a starting point |
| `acceptance` | one or more visible outcomes that make the story acceptable |

Use one node for a meaningful capability or state transition, not one node for each
click, input, selector, or assertion. A browser replay may need several operations to
prove one story; those operations do not belong in the reviewed YAML.

The graph must be acyclic. Duplicate IDs, missing/self dependencies, cycles, empty
stories, empty acceptance lists, and browser-detail fields in a node are rejected while
loading.

## Local runtime binding

To replay a reviewed story DAG, browser-qa keeps its detailed browser binding locally at:

```text
~/.superqa/runtimes/<site>/<scenario-file-name>.yaml
```

The recorder or an agent maps each story ID to its ordered browser operations there.
That local file can contain selectors, actions, input values, retries, and popup details;
it is deliberately separate from the user-story YAML and must not be committed as the
review artifact. A story DAG without a binding is still valid for review and the Admin
graph, but replay stops with a clear “local runtime binding missing” error rather than
inventing interactions.

Browser-operation details are an implementation concern. When they need maintenance,
use the recorder or the engine reference; do not add `action`, `selector`, `value`, or
`description` keys under `dag.nodes`.

## Review and replay semantics

Before replay, validate all selected files and inspect the user-story graph:

```bash
superqa dag check --all --site myshop
superqa serve                         # open http://127.0.0.1:8760
```

The Admin graph exposes only IDs, user stories, acceptance criteria, and dependencies.
It never sends local locators, input values, or resolved secrets to the browser. Run
reports retain ordinal browser-operation screenshots for evidence and label each result
with its user-story ID and story text.

Replay is intentionally serial. browser-qa visits ready stories in stable topological order;
when two stories are ready, YAML declaration order breaks the tie. The operations within
one story’s local binding run in their recorded order. A required failed operation stops
the scenario; an optional failed operation is recorded as skipped and replay continues.

## Legacy `steps:` files

Existing `steps:` YAML remains valid and is read unchanged. Reading or running it never
rewrites the file. Migrate only when the owner asks for a storage change:

```bash
superqa dag migrate path/to/scenario.yaml
superqa dag migrate --all --site myshop
```

Migration creates one high-level journey story plus a local runtime binding. Refine that
story and split it into meaningful user-story nodes only after reviewing the product flow.
`steps:` and `dag:` cannot appear together in one scenario.

## Variables and policy

`{{key}}` values are resolved only from the local SQLite var store at replay time. Set
them with `superqa vars set <site> <key> <value>`; password-like keys are masked in
reports. They belong in local runtime bindings, never in the user-story DAG.

Dialogs and new tabs follow `policy` and are still recorded as side effects. The policy
is scenario-level because it describes the expected product environment, not an individual
user-story step.
