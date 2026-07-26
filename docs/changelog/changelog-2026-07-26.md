# Changelog 2026-07-26 - LOCAL-OFFLINE mode

## `--var KEY=VALUE` - retarget a run without touching the var store

`superqa run` accepts repeatable `--var` overrides that win over both the site scope and
the global `*` scope, for that run only. Nothing is persisted, so the stored target for a
shared environment survives while the same scenario set runs somewhere else:

```bash
superqa run --all --site myshop --headless --var base_url=http://localhost:3000
```

- `Store.set_overrides()` holds an in-memory overlay consulted first by `get_var()`, so
  every existing `{{key}}` consumer (URLs, values, the `login` macro) picks it up with no
  further changes.
- `KEY=VALUE` splits on the first `=` only, so values containing `=` (tokens, query
  strings) survive intact. A malformed `--var` exits with a message instead of silently
  running against the wrong target.

## LOCAL-OFFLINE procedure (`reference/local-offline.md`)

A mode for testing against a copy of the stack on the developer's machine - no shared
dev/staging server. It covers the cases shared environments cannot: destructive flows, and
states that only exist as an absence (first-time user, no history yet).

The parts worth reading even if you never run offline:

- **Fixtures derived from the local database.** Pick test records by querying the same
  predicate the code under test branches on, then cover every class of that predicate -
  including the "no row yet" class. An unrepresented class is an untested branch and is
  reported as such rather than skipped.
- **Assertion scoping.** Assert the behavior under test, not components deliberately left
  out of the local stack. A widget that fails only because its backing service is not
  running is a false alarm that trains people to ignore the suite.
- **Differential proof.** A case that has never failed is not evidence. Run it with the
  change disabled (passes), enabled (the regression case fails, controls still pass), then
  restore. "Flips exactly when the behavior flips" is the bar.
- **Troubleshooting table** for the failures that eat the most time: absolute URLs baked
  into frontend config, ports shared by IPv4-only and IPv6-only listeners, encrypted
  properties with no local dummy, collation/timezone drift between local and source
  datastores.

Hard rule added to `SKILL.md`: a local copy of shared data is read-only at the source,
subsetted, redacted, never committed - and local config gets dummy secrets only. Putting a
real shared-environment credential into local config to make something boot is a hard
failure. The per-stack recipe lives in `~/.superqa/sites/<site>/local-stack.md` (template
in the reference), never in this repo.

`playwright-cli` remains the portable exploration tool; on macOS `ego-browser` (ego-lite)
is a good alternative, reusing existing logged-in browser state in an isolated agent space.
