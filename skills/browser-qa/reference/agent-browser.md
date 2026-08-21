# agent-browser + chrome-devtools-mcp

Two Chrome-backed engines. agent-browser is the cheap default; chrome-devtools-mcp
is for when the question is "what did the API actually return".

> Site specifics (entry URLs, accounts, which button opens which popup) belong in
> `~/.superqa/sites/<site>/rules.md`, never here.

## agent-browser

```bash
npm i -g agent-browser && agent-browser install   # one tarball ships macOS/Linux/Windows binaries
```

```bash
agent-browser --session qa open <url>
agent-browser --session qa snapshot -i            # interactive elements as @e1, @e2 refs
agent-browser --session qa scrollintoview @e10    # REQUIRED before click
agent-browser --session qa click @e10
agent-browser --session qa tab list               # popups appear as t2, t3; active tab marked
agent-browser --session qa network requests --type xhr,fetch
agent-browser --session qa network request <id> --json    # includes responseBody
agent-browser --session qa screenshot ./evidence.png
agent-browser --session qa connect <port>         # attach to an already-running Chrome
```

`--session <name>` isolates parallel runs. `batch` runs several commands per invocation.

### Gotchas (each one measured, not guessed)

1. **Clicks report false success.** `click @ref` on an element outside the viewport
   prints `✓ Done` and does nothing. `find role button click --name "X"` also prints
   `Done` when the accessible name is only a partial match and nothing was hit.
   Always `scrollintoview` first, then confirm with `get url` / `tab list` /
   `network requests`. A `Done` is not evidence.
2. **Refs are per-snapshot.** `@e1` is not stable across navigations, and the same
   label can sit at a different ref under a different engine. Re-snapshot after every
   navigation and read the ref off that snapshot.
3. **HAR bodies are empty by default.** `network har stop f.har` writes entries with
   blank `content.text`. Pass `--content all`, or use `network request <id> --json`.

## chrome-devtools-mcp on a shared Chrome

Lets a human do the login by hand; the agent then inspects that session. Removes the
need to automate SSO at all.

```bash
scripts/qa-chrome.sh          # macOS/Linux: port 9333, dedicated profile, reuses if running
powershell -File scripts/qa-chrome.ps1   # Windows
```

Register once, at user scope:

```bash
claude mcp add chrome-devtools -s user -- \
  npx -y chrome-devtools-mcp@latest --browser-url http://127.0.0.1:9333 --no-usage-statistics
```

The dedicated profile means the user's own Chrome is never taken over. Change the port
and you must change the registration too.

Flow: `navigate_page` -> act -> `list_network_requests` -> `get_network_request`.
`get_network_request` returns request headers, response headers, status, and the full
**Response Body**. `list_pages` / `select_page` switch between popup windows.

**It only records pages it navigated itself** - see `reference/engines.md`, "One engine
per page."

## lightpanda - measured limits

Ran the full login -> menu -> document-list -> viewer-popup flow on a Vue SPA:

| Stage | Chrome | lightpanda |
|---|---|---|
| SPA render, XHR-driven lists | ok | ok |
| login API chain (auth + session) | ok | ok, all 200 |
| post-login home | ok | URL updates but the DOM is not swapped; re-`open` the URL to recover |
| document list | ok | ok |
| **viewer popup** | opens as a new tab | **never opens**, zero viewer API calls |
| viewer URL opened directly | ok | blocked by the site's browser-version gate (UA is not Chrome) |
| screenshot | real pixels | placeholder image, no rendering engine |
| Windows | native | WSL2 only |

Useful ceiling: API-contract smoke up to the point a popup is required. Not a QA engine.

lightpanda moves fast; this is a point-in-time measurement. Before trusting the table
again, re-run one popup click and one screenshot - those two are the whole verdict.
