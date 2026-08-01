# Scenario generation - from a simple prompt to reviewable user stories

Input: a URL plus at most one sentence of intent ("QA this", "test login",
"check the new upload feature"). Output: scenario YAMLs a non-developer can review
before any browser details are wired up.

## Case design stencil (apply per feature you found while exploring)

1. **Happy path** - the capability a normal user completes; state the visible success
   outcome (welcome text, created item, changed page).
2. **Validation** - the user leaves required input empty or uses a wrong format; state
   the understandable error and that the user can recover.
3. **Error/negative** - wrong credentials, cancelled dialogs, or a rejected request;
   state that the app stays usable rather than reaching a dead end.
4. **Edge** - empty state, long/Unicode input, repeat submission, or back navigation;
   state the meaningful product result.
5. **Transitions** - new tabs, popups, and alerts are separate user stories only when
   they change what a user can accomplish or introduce a distinct risk.

Cover breadth first (one happy path per menu), then depth on the feature the prompt
names. Five to ten scenarios is a good first pass for a whole site; two to four for one
feature.

## Rules

- One scenario = one user goal. Name it in the user's language:
  `로그인-정상`, `자료등록-필수값누락`.
- One DAG node = one capability or state a user can describe in a sentence, for example:
  `방문자로서 로그인 시작점에 도착할 수 있다.` or
  `회원으로서 내 계정에 접근하기 위해 로그인할 수 있다.`
- Each node has a stable goal-shaped `id`, a `story`, direct `depends_on`, and one
  or more user-visible `acceptance` criteria. Prefer `prepare-login` to
  `fill-password`; a person should be able to review the graph without knowing the UI.
- Do **not** put `action`, `selector`, `value`, or a click-by-click description in
  `dag.nodes`. The recorder or QA agent creates the separate local runtime binding
  after the story graph is agreed.
- Model branches and joins when story dependencies matter. Replay remains serial: ready
  stories run in YAML declaration order, so a DAG never claims concurrent browser changes.
- An acceptance criterion is an observable product result, not a test-engine command:
  `환영 문구와 계정 영역이 표시된다.`, not `expect_visible #welcome`.
- Credentials and per-user values belong to the local var store/runtime binding, never
  in the checked scenario YAML.
- Before running, use `superqa dag check --all --site <site>` and open
  `superqa serve` to review the story graph. The local Admin shows only IDs, stories,
  acceptance criteria, and dependencies.
- After review, record or wire the local runtime binding. A story DAG without a binding
  is intentionally reviewable but not replayable.

## Post-feature testing (developer handoff)

When the prompt is "I finished feature X, test it": generate only X's user-story cases
with the stencil, add them to the site's existing scenario directory, review them with
the owner, then run the whole site sweep so side effects in neighboring screens are
caught too.
