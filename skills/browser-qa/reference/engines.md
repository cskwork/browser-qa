# Browser engines - what drives the exploration

Two layers, do not confuse them:

- **Deterministic replay** of scenario YAMLs is always the browser-qa engine
  (`python3 -m superqa_tui run ...`, Playwright underneath). Reports, side
  effects, diffs come from here. Engines below do NOT replace it.
- **Interactive exploration / ad-hoc driving** (EXPLORE-QA step 2, one-off
  checks, archived driving scripts) uses an engine from the cascade below.

## Capability gate (check before the cascade)

| Task needs | Use |
|---|---|
| API request **and response body** | `agent-browser network request <id> --json`, or chrome-devtools-mcp `get_network_request` |
| popup / multi-window flow | `agent-browser tab list`, or chrome-devtools-mcp `list_pages` + `select_page` |
| a login the user already has | ego-browser, or shared Chrome with a hand-done login |
| Windows parity | agent-browser, playwright-cli (both ship native win32 binaries) |
| plain exploration | cascade order |

## Cascade (first available wins)

| # | Engine | Detect | Use via |
|---|---|---|---|
| 1 | **agent-browser** - default: cheapest loop, popups and network built in, native on macOS/Linux/Windows | `command -v agent-browser` | `reference/agent-browser.md` |
| 2 | **ego-browser** (ego-lite) - macOS only; take it when the target needs the user's own logged-in session | `command -v ego-browser` | the `ego-browser` skill if installed, else `ego-browser nodejs <<'EOF' ... EOF` heredocs |
| 3 | Playwright MCP | playwright/browser MCP tools present in the session | its `browser_*` tools |
| 4 | `playwright-cli` | `command -v playwright-cli` | commands in `reference/agent-qa.md` step 2 |
| 5 | chrome-devtools-mcp - deep network only | `chrome-devtools` MCP tools present | `reference/agent-browser.md` |

Record the working choice per machine so detection runs once:

```yaml
# ~/.superqa/config.yaml
engine: ego-browser        # exploration engine; replay is always superqa
```

If the recorded engine stops working, fall through the cascade again and
update the value.

## One engine per page

chrome-devtools-mcp records traffic **only for pages it navigated itself**.
Drive with agent-browser and inspect with the MCP and `list_network_requests`
returns `No requests found`. Pick one engine per page before you start; do not
hand a page off mid-flow.

## When to prefer ego-browser

It gives an isolated agent task space that reuses the user's login state - authenticated
exploration without stealing the user's browser. Take it on macOS whenever the target
needs a real logged-in session and you would otherwise be automating the login. It is
macOS-only, so anything that must also run on Windows stays on agent-browser, which
covers the same ground with the shared-Chrome flow in `reference/agent-browser.md`.
For anonymous public pages any engine is equivalent; don't churn engines mid-task.

## Never: lightpanda

No graphical rendering engine, so screenshots are impossible - it returns a
placeholder image. `window.open` yields a `[object CrossOriginWindow]` stub, so
popup and viewer flows are unreachable. No native Windows binary (WSL2 only).
Measured limits: `reference/agent-browser.md`.

## Engine-agnostic exploration contract

Whatever the engine, step 2 of EXPLORE-QA must produce the same artifacts:

- entry flow + login steps recorded in `sites/<site>/rules.md`
- menu -> URL map; which clicks open tabs/popups/dialogs
- console errors and failed requests noted
- screenshots for anything surprising

Archived driving scripts (see `reference/domain-packs.md`) should state their
engine in the provenance header (`# engine: ego-browser nodejs`), so the next
run knows what it needs.
