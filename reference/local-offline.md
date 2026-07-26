# LOCAL-OFFLINE - QA against a local copy of the stack

Run the whole test against services and data on your machine: no shared dev/stg server,
no network dependency, no risk of dirtying an environment other people are using.

Use it when the user asks to "test locally", "without the dev server", "offline", when the
shared environment is down or slow, or when the cases are destructive (create/delete/reset)
and must not touch shared data.

## Hard rules

1. **The source environment is read-only.** Extraction may SELECT and dump; it must never
   write, lock, or migrate the shared database. Prefer a replica/read endpoint.
2. **Subset, do not clone.** Pick anchor rows, then pull only what they reference. A full
   copy is slow, usually impossible, and multiplies the blast radius if it leaks.
3. **Sensitive data stays out.** Redact or scramble personal data during extraction, not
   after. Dumps, snapshots and fixture files are local artifacts - never committed, never
   attached to a report.
4. **Local secrets are dummies.** Encrypted or vault-backed properties get local
   placeholder values. Putting a real shared-environment credential into local config to
   "make it boot" is a hard failure - it grants a local process production reach.
5. **The stack recipe is site-local knowledge.** How to bring this particular stack up
   lives in `~/.superqa/sites/<site>/local-stack.md`, never in this repo
   (`reference/site-rules.md`).

## Procedure

### 1. Choose the seam

List every component the case actually exercises, and decide per component: run locally,
stub, or leave out. Leaving components out is fine and usually necessary - but it decides
what you are allowed to assert later (step 6). Write the decision down; it is the first
section of `local-stack.md`.

### 2. Extract a data subset (read-only against the source)

Anchor-based extraction: choose a small set of anchor rows that represent the flows under
test, then follow foreign keys outward until closed. Record row counts per table so the
next person can tell a bad load from a small one.

### 3. Bring up local infrastructure and load

Containers for datastores (database, cache, queue) with the **same engine version,
collation, timezone and case-sensitivity settings as the source** - these silently change
query results and are the usual cause of "works on dev, fails locally".

### 4. Point services at local infrastructure

Inject configuration from outside the source tree (an extra config file, environment
variables, or profile overlay) so nothing in the repo changes and nothing can be committed
by accident. Expect these to need local overrides: datastore URLs and credentials, cache,
message broker, object storage, and every encrypted property (step 4 of Hard rules).

### 5. Point the frontend at local backends

Two failure modes account for most lost time here:

- **Absolute URLs baked into config.** A frontend config that names a host and port for a
  backend call keeps pointing at the old target even when the page itself is served
  locally. Change the port in one place and you must change it in all of them.
- **Ports that look free but are not.** A process bound to IPv4 only and another bound to
  IPv6 only can share the same port number; `localhost` then resolves to whichever the
  client prefers, and requests silently reach the wrong server. Check both stacks
  (`lsof -nP -iTCP:<port> -sTCP:LISTEN`) and prefer a port nothing else uses.

### 6. Derive fixtures from the local database

This is the technique that makes local QA stronger than remote QA, not merely cheaper.

The code under test branches on data state. So select test accounts/records **by querying
that same state** rather than by picking whatever the UI offers:

1. Read the predicate the code evaluates (the exact query or condition it branches on).
2. Fetch the candidate list the UI actually offers.
3. Classify candidates against the local database and pick one per class - including the
   classes that only exist as an absence (no row yet, first-time user, empty history).
4. Store the chosen identifiers in `local-stack.md` with the classifying query beside them,
   so the fixture can be re-derived when the data subset is refreshed.

If a class has no candidate in the subset, say so in the report rather than quietly
skipping it - an unrepresented class is an untested branch. You may also provision it
deliberately by mutating the local database (it is disposable); record how to restore.

### 7. Run the scenarios against the local target

Scenarios stay identical to the remote ones - only the target changes:

```bash
python3 -m superqa_tui run --all --site <site> --headless \
  --var base_url=http://localhost:<port>
```

`--var KEY=VALUE` overrides the var store for that run only; nothing is persisted, so the
stored remote target survives. Use it for staging and production targets too.

For interactive exploration of the local stack, `playwright-cli` works everywhere; on
macOS `ego-browser` (ego-lite) is a good alternative - it reuses your logged-in browser
state in an isolated agent space, so exploring a screen behind a login costs nothing.

### 8. Scope assertions to what you chose to run

Assert the behavior under test, not the components you deliberately left out. If the
authorization decision is the subject, assert the authorization outcome (admitted vs
rejected, token issued vs error route) - not that every dashboard widget rendered, because
a widget that fails only because its backing service is not running is a false alarm that
trains people to ignore the suite.

Put the "everything renders" checks in a separate scenario that only runs where the full
stack exists.

### 9. Prove the case can fail (differential run)

A case that has never failed is not yet evidence. Before trusting it:

1. Run it with the change under test **disabled** - it should pass.
2. Run it with the change **enabled** - a regression case must now fail, and the control
   cases must still pass.
3. Restore the original state and confirm the suite returns to green.

Record both columns in the report. "Passed once" is not a result; "flips exactly when the
behavior flips" is.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Page loads but a list is empty / "communication failed" | a backend call is proxied to a host you did not move locally |
| Requests reach an unrelated server | port shared by IPv4-only and IPv6-only listeners; or an absolute URL still naming the old port |
| Service will not boot: cannot decrypt property | encrypted config value with no local dummy override |
| Service will not boot: logging/appender error | logging config referencing a shared-environment sink; use a console-only local config |
| Joins return nothing that returns rows on the shared env | collation / case-sensitivity / timezone mismatch between local and source datastore |
| Every case passes, including ones that should fail | assertions scoped too loosely, or the change under test is not actually active - do step 9 |

## `local-stack.md` template (lives in `~/.superqa/sites/<site>/`, never committed)

```markdown
# <site> local stack
updated: YYYY-MM-DD

## Seam
| component | local? | how | note |
|---|---|---|---|

## Data subset
- extraction command, anchors used, row counts per table, refresh date
- redaction applied

## Bring-up
1. infra: <command>
2. services: <command per service, incl. external config path>
3. frontend: <command, port, config keys that must agree>

## Ports
| port | owner | note (IPv4/IPv6) |

## Fixtures
| class | identifier | classifying query |

## Known local gaps
- components not running and the assertions they invalidate
```
