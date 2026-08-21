# Domain QA packs - per-domain, per-feature QA that survives the session

A **pack** is the durable home for one domain's QA: its feature map, reusable
scripts, and pointers to scenarios/rules. Goal: invoking browser-qa on a known
domain requires zero rediscovery - read the pack, pick the feature, run.

Packs are user data, never repo content. Same hard rule as site rules:
no pack content is ever committed to this skill repo or any public repo.

## Location (ask once, then remember)

Default pack home: `~/.superqa/packs/`. On the FIRST pack creation for a user,
ask where packs should live (offer the default; a project-local path like
`<repo>/.superqa/packs/` is fine **only if** that path is gitignored - verify
with `git check-ignore` and add the ignore entry if missing). Record the answer:

```yaml
# ~/.superqa/config.yaml
packs_home: ~/.superqa/packs        # global default
packs:                              # optional per-domain overrides
  <domain>: /path/to/elsewhere
```

Never ask again once `packs_home` exists - just use it.

## Pack layout

```
<packs_home>/<domain>/
├── pack.md                     # THE map - read this first, always
├── <feature>/                  # one dir per feature area
│   ├── notes.md                # feature-specific findings, judgement criteria
│   └── scripts/                # archived reusable scripts (see below)
└── stack.md                    # how to bring the target up locally (optional;
                                #   may be a pointer to canonical docs elsewhere)
```

`pack.md` structure:

```markdown
# <domain> QA pack
updated: <date>

## Feature map
| feature | what it covers | how to QA | scripts / scenarios |
|---|---|---|---|
| entry   | login + landing | dedicated skill X / scenarios site=<s> | entry/scripts/... |
| billing | plans, invoices | scenarios billing-*.yaml               | billing/scripts/probe.sh |

## Stack & data
- bring-up: <stack.md or canonical doc path>
- fixtures/reset: <snapshot command, seed script>

## Delegation
- <feature> -> <dedicated skill or harness>, when one exists

## Gaps
- features with no coverage yet, ordered by risk
```

Relationship to existing stores (packs do NOT replace them):

- `~/.superqa/scenarios/<site>/*.yaml` - stays where the engine reads it;
  pack.md references scenarios by site+name.
- `~/.superqa/sites/<site>/rules.md` - screen-level navigation knowledge;
  pack.md links to it. Add a `pack:` pointer line at the top of rules.md.
- Pack = the layer above: which features exist, which tool proves each one,
  which scripts are already written.

## stack.md / troubleshooting - the two doc shapes worth keeping

When QA depends on bringing the target up locally (LOCAL-OFFLINE), the pack
keeps (or points to) two documents. If the target's own repo already has them,
pack.md links there instead of duplicating - the pack copy is only for content
that has no durable home.

**stack.md** - measured facts only, no "should work" guesses:

- service : port : health-endpoint : source table (call out port collisions
  and how they were resolved)
- exact start commands, with config injected EXTERNALLY (env vars, additional
  config locations) - never by editing the target's source
- connection points that break silently: proxy targets, values that must be
  absolute URLs, outbound calls that must be re-pointed at local peers
- data: where fixtures come from, selection criteria for QA-safe records,
  snapshot/restore commands - **snapshot before screen QA**, screen QA mutates
  real data

**troubleshooting.md** - append-only log of things that ACTUALLY blocked a
run, each as symptom -> cause -> fix (include the exact error string so the
next grep finds it). Re-read it before debugging any bring-up failure.

## Script archiving rule

QA work constantly produces helper scripts: data-discovery SQL, fixture
pickers, curl probes, stack health checks, API test harnesses. They usually
die in ticket folders or /tmp. The rule:

1. **Before writing a script, check the pack.** `ls <pack>/<feature>/scripts/`
   - reuse or extend instead of rewriting.
2. **After a script proves useful (used twice, or clearly reusable), archive it**
   to `<pack>/<feature>/scripts/` with a provenance header:

   ```bash
   #!/usr/bin/env bash
   # pack: <domain>/<feature>  archived: <date>
   # origin: <ticket folder / session where it was born>
   # needs: <env vars, files, running services it assumes>
   ```

3. **Parameterize paths on archive.** Scripts born in a ticket folder often
   compute repo-relative paths; on archive, switch to an env var with the old
   behavior as fallback (`ROOT="${MYPROJ_ROOT:-<old default>}"`) so the copy
   runs from the pack.
4. **Scripts already committed to a durable repo are referenced, not copied**
   - pack.md records the path. Copy only what would otherwise be lost
   (gitignored folders, /tmp, chat scrollback).
5. Same secret rules as everywhere: `{{vars}}` / env vars, never literal
   credentials in an archived script.

## One source & portability

**One source.** A domain's QA lives in exactly one place: its pack. Do not keep
a parallel per-domain skill, harness folder, or doc set alive next to it.

- Absorbing an existing per-domain skill/harness: move runbook + scripts into
  the pack, leave a short DEPRECATED pointer stub at the old home (never a
  content copy), and update every doc that referenced the old home.
- Docs that canonically belong to the target's own repo (local-stack bring-up,
  repo troubleshooting) stay there; the pack links to them. The pack owns only
  what has no better durable home.

**Portability.** A pack must survive `packs_home` moving to another machine:

- No user-absolute paths in scripts. Roots come from env vars with portable
  defaults (`ROOT="${MYPROJ_ROOT:-$HOME/path}"`), evidence goes to `/tmp` or
  pack-relative dirs, and every external need is declared in the provenance
  header (`# needs:`).
- Prefer scripts that depend only on network endpoints + env vars over ones
  that reach into a repo checkout.
- For cross-machine durability, make `packs_home` a **private** git repo -
  packs are plain text + small scripts, so git handles them well.

**Files ARE the database.** Do not add a SQLite (or any binary index) for the
script library - it breaks git diffs, merging, and portability, and creates a
second source of truth. Provenance headers + pack.md tables are the metadata;
grep is the query engine. If a pack outgrows grep (hundreds of scripts),
GENERATE a plain-text index from the headers (`INDEX.md`) instead of hand-
maintaining one. Run history and account vars already live in the engine's
`superqa.db` - if structured script metadata ever becomes truly necessary,
extend that existing DB as a registry (paths + headers only), never as storage.

## DOMAIN-QA flow (mode row in SKILL.md)

1. Resolve pack: `config.yaml` -> `<packs_home>/<domain>/pack.md`. No pack yet?
   Create the skeleton (ask location per above), seed the feature map from what
   the user names, then continue as EXPLORE-QA - archiving as you go.
2. Read pack.md; narrow to the feature area(s) the user asked about.
3. If the feature row delegates to a dedicated skill/harness - use it, don't
   duplicate it.
4. Otherwise run its scenarios (`run --all --site <site>` or per-scenario) and
   its archived scripts; explore only what the pack marks as gap or changed.
5. After the run: update pack.md (feature map rows touched, new gaps),
   archive any new reusable script, update site rules.md as usual.
