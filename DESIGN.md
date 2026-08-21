# Design — browser-qa

Recorded from the built landing surface (`docs/index.html`), not from intention.

## Thesis

The product is the evidence a run leaves behind, so the surface leads with that artifact:
a contact sheet of one run, frames numbered, statuses stamped, the failure circled in
grease pencil. The page refuses the category's feature-card grid and terminal hero.

## World

A photographic contact sheet on a proofing bench. Film-rebate black owns whole bands
(header, the sheet, the footer); paper carries the reading.

## Color

Committed: black fields own regions, one saturated mark colour, one archival support.

| Role | Value | Where |
|---|---|---|
| Paper ground | `#E9E9E4` | page ground, frames |
| Paper shade | `#DFDFD8` | scrollbar track, frame fills |
| Film rebate | `#121310` | header, contact sheet, code blocks, footer |
| Ink | `#1A1B18` | body text |
| Grease pencil | `#E0350E` | failures, the circled frame, hover, selection |
| Archival blue | `#1B3A6B` | passes |
| Dim | `#5E605A` | captions, edge lettering |
| Rule | `#C6C6BE` | row rules, panel seams |

Light, not dark: the use scene is a work laptop in an office, mid-decision.

## Type

| Role | Face |
|---|---|
| Display / headings (Latin) | Archivo Black |
| Body (Latin) | Archivo |
| Korean, all roles | Pretendard (800 for headings) |
| Edge lettering, captions, code, measurement | JetBrains Mono |

Korean sets with `word-break: keep-all`; the Korean headline runs a smaller clamp than
the Latin one so both hold two lines in the hero column.

## Composition

Rules and strips, never cards. `.row` is a two-column ruled record (label | body).
The only grid of equal cells is the contact sheet itself and the three-principle strip,
both seamed with 1px rules rather than floated as cards.

## Motion

One authored moment: the eight frames develop — blur 7px to sharp, opacity 0 to 1,
70ms stagger, `cubic-bezier(.16,1,.3,1)`, once on load. Nothing else animates on scroll.
Disabled entirely under `prefers-reduced-motion`.

## Browser surfaces

Selection is grease pencil on paper. Scrollbar is rebate on paper-shade, 11px.
Focus ring is a 2px grease-pencil outline at 3px offset.

## Bilingual rule

Both languages ship in the DOM. `[data-l]` nodes are hidden by default and revealed by
`html[lang]`. The initial language comes from `navigator.language`; the KO/EN stamp in the
rebate band overrides it and persists in `localStorage` under `bqa-lang`.

## Known gaps

The Impeccable design detector ran degraded on this machine (HTML parser modules absent),
so its empty finding list is an undercount, not a clean pass. The shipped finish reviewer
and documenter agents are not available in this harness; this file and the review pass
were written in-thread.
