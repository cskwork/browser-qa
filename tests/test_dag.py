"""User-story DAG storage, private replay bindings, execution, and migration coverage."""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

_TMP = tempfile.mkdtemp(prefix="superqa-dag-test-")
os.environ["SUPERQA_HOME"] = _TMP

from superqa_tui.cli import main  # noqa: E402
from superqa_tui.engine import Engine, RunResult, StepResult  # noqa: E402
from superqa_tui.report import write_reports  # noqa: E402
from superqa_tui.scenario import Scenario, ScenarioNode, Step, load_scenario  # noqa: E402
from superqa_tui.store import Store  # noqa: E402

FIXTURE = (REPO / "tests" / "fixtures" / "testsite.html").as_uri()


def _story(node_id: str, story: str, acceptance: list[str], *, depends_on: list[str] | None = None,
           steps: list[Step] | None = None) -> ScenarioNode:
    return ScenarioNode(
        id=node_id,
        depends_on=list(depends_on or []),
        story=story,
        acceptance=acceptance,
        steps=list(steps or []),
    )


def _dag(nodes: list[dict], name: str = "DAG-샘플") -> dict:
    return {
        "name": name,
        "site": "fixture",
        "base_url": FIXTURE,
        "language": "ko",
        "tags": ["dag"],
        "dag": {"nodes": nodes},
    }


def _invalid(raw: dict, expected: str) -> None:
    try:
        Scenario.from_dict(raw)
    except ValueError as error:
        assert expected in str(error), str(error)
    else:
        raise AssertionError(f"expected ValueError containing {expected!r}")


def test_legacy_steps_run_unchanged_then_migrate_explicitly() -> None:
    """v1 replay preserves its bytes; explicit migration creates a story DAG + private binding."""
    path = Path(_TMP) / "scenarios" / "fixture" / "legacy.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    original = f"""name: legacy-steps
site: fixture
base_url: {FIXTURE}
language: ko
steps:
  - action: goto
    url: {FIXTURE}
    description: 로그인 화면에 도착
  - action: expect_visible
    selector: \"#login-btn\"
    description: 로그인 시작점을 확인
"""
    path.write_text(original, encoding="utf-8")

    scenario = load_scenario(path)
    assert scenario.storage_format == "steps"
    assert [node.id for node in scenario.execution_nodes()] == ["journey"]
    assert scenario.execution_nodes()[0].story == "사용자는 legacy-steps 여정을 완료할 수 있다."
    result = asyncio.run(Engine(Store(), headed=False).run_scenario(scenario))
    assert result.status == "pass", [(r.node_id, r.status, r.error) for r in result.step_results]
    assert path.read_text(encoding="utf-8") == original
    assert main(["dag", "check", str(path)]) == 0

    assert main(["dag", "migrate", str(path)]) == 0
    migrated = yaml.safe_load(path.read_text(encoding="utf-8"))
    node = migrated["dag"]["nodes"][0]
    assert "steps" not in migrated and set(node) == {"id", "story", "depends_on", "acceptance"}
    assert "selector" not in yaml.safe_dump(migrated["dag"], allow_unicode=True)
    migrated_scenario = load_scenario(path)
    assert migrated_scenario.runtime_path and migrated_scenario.runtime_path.exists()
    runtime = yaml.safe_load(migrated_scenario.runtime_path.read_text(encoding="utf-8"))
    assert runtime["bindings"]["journey"]["steps"][1]["selector"] == "#login-btn"
    print("PASS test_legacy_steps_run_unchanged_then_migrate_explicitly")


def test_story_dag_roundtrip_topology_and_private_runtime() -> None:
    """The checked-in YAML is user-story-level; the browser mechanics stay local."""
    declaration = [
        _story(
            "reach-account", "회원으로서 내 계정에 접근하기 위해 로그인할 수 있다.",
            ["로그인 후 환영 문구와 계정 영역이 보인다."],
            depends_on=["recognize-login", "prepare-credentials"],
            steps=[
                Step(action="click", selector="#login-btn", description="로그인 제출"),
                Step(action="expect_visible", selector="#welcome", description="환영 문구 확인"),
            ],
        ),
        _story(
            "arrive", "방문자로서 서비스의 로그인 시작점에 도착할 수 있다.",
            ["로그인 입력 화면이 표시된다."],
            steps=[Step(action="goto", url=FIXTURE, description="로그인 화면 열기")],
        ),
        _story(
            "recognize-login", "방문자는 로그인 시작점을 이해할 수 있다.",
            ["로그인 버튼이 보인다."], depends_on=["arrive"],
            steps=[Step(action="expect_visible", selector="#login-btn", description="로그인 시작점 확인")],
        ),
        _story(
            "prepare-credentials", "등록 회원은 로그인 정보를 준비할 수 있다.",
            ["아이디와 비밀번호 입력란이 보인다."], depends_on=["arrive"],
            steps=[
                Step(action="fill", selector="#username", value="tester01", description="회원 아이디 입력"),
                Step(action="fill", selector="#password", value="pw", description="회원 비밀번호 입력"),
            ],
        ),
    ]
    scenario = Scenario(name="회원-로그인", site="fixture", base_url=FIXTURE, nodes=declaration)
    path = Path(_TMP) / "story-dag.yaml"
    scenario.save(path)

    stored = yaml.safe_load(path.read_text(encoding="utf-8"))
    dag_text = yaml.safe_dump(stored["dag"], allow_unicode=True)
    assert "selector" not in dag_text and "action" not in dag_text and "value" not in dag_text
    assert [node["id"] for node in stored["dag"]["nodes"]] == [node.id for node in declaration]
    assert stored["dag"]["nodes"][0]["story"].startswith("회원으로서")
    assert stored["dag"]["nodes"][0]["acceptance"] == ["로그인 후 환영 문구와 계정 영역이 보인다."]
    runtime_path = scenario.runtime_path
    assert runtime_path and runtime_path.exists() and runtime_path.parent.parent.name == "runtimes"
    assert "selector" in runtime_path.read_text(encoding="utf-8")

    loaded = load_scenario(path)
    expected_nodes = ["arrive", "recognize-login", "prepare-credentials", "reach-account"]
    assert [node.id for node in loaded.execution_nodes()] == expected_nodes
    graph = loaded.dag_data()
    assert [node["id"] for node in graph["nodes"]] == expected_nodes
    assert len(graph["edges"]) == 4
    assert all(set(node) == {"id", "story", "acceptance", "depends_on"} for node in graph["nodes"])

    store = Store(Path(_TMP) / "story-dag.db")
    events: list[dict] = []
    result = asyncio.run(Engine(store, headed=False, on_event=events.append).run_scenario(loaded))
    assert result.status == "pass", [(r.node_id, r.status, r.error) for r in result.step_results]
    assert [r.node_id for r in result.step_results] == [
        "arrive", "recognize-login", "prepare-credentials", "prepare-credentials", "reach-account", "reach-account"]
    assert [event["node_id"] for event in events if event["kind"] == "step_start"] == [
        r.node_id for r in result.step_results]
    md_path, html_path = write_reports(result, store)
    assert "사용자 스토리" in md_path.read_text(encoding="utf-8")
    assert "회원으로서 내 계정에 접근하기 위해 로그인할 수 있다." in html_path.read_text(encoding="utf-8")
    print("PASS test_story_dag_roundtrip_topology_and_private_runtime")


def test_story_dag_rejects_invalid_graphs_and_detail_fields() -> None:
    def story(node_id: str, **overrides) -> dict:
        node = {
            "id": node_id,
            "story": "사용자는 목표를 달성할 수 있다.",
            "acceptance": ["기대 결과가 보인다."],
        }
        node.update(overrides)
        return node

    base = lambda nodes: _dag(nodes, "invalid")
    _invalid(base([story("same"), story("same")]), "duplicate dag node id")
    _invalid(base([story("after", depends_on=["missing"])]), "missing node")
    _invalid(base([story("self", depends_on=["self"])]), "cannot depend on itself")
    _invalid(base([story("a", depends_on=["b"]), story("b", depends_on=["a"])]), "dag contains a cycle")
    _invalid(base([story("bad-dependencies", depends_on="open")]), "depends_on must be a list")
    _invalid(base([story(None)]), "non-empty trimmed string")
    _invalid(base([story("no-story", story="")]), "story must be a non-empty")
    _invalid(base([story("no-acceptance", acceptance=[])]), "acceptance must be a non-empty list")
    _invalid(base([story("no-selectors", action="click")]), "user-story-only")
    _invalid(base([]), "must contain at least one user-story")
    _invalid({"name": "mixed", "steps": [], "dag": {"nodes": []}}, "exactly one")
    _invalid({"name": "missing-format"}, "exactly one")
    _invalid({"name": "bad-dag", "dag": []}, "dag must be a mapping")
    print("PASS test_story_dag_rejects_invalid_graphs_and_detail_fields")


def test_runtime_paths_are_nested_and_stale_bindings_are_cleared() -> None:
    path = Path(_TMP) / "scenarios" / "fixture" / "first-flow" / "same-name.yaml"
    replayable = Scenario(name="첫 시나리오", site="fixture", nodes=[
        _story("old-story", "사용자는 기존 여정을 완료할 수 있다.", ["기존 결과가 보인다."],
               steps=[Step(action="goto", url=FIXTURE)]),
    ])
    replayable.save(path)
    first_runtime = replayable.runtime_path
    assert first_runtime and first_runtime.relative_to(Path(_TMP) / "runtimes" / "fixture").as_posix() == (
        "first-flow/same-name.yaml")

    # A newly saved review-only DAG must not inherit browser actions from the old story.
    replacement = Scenario(name="새 시나리오", site="fixture", nodes=[
        _story("new-story", "사용자는 새 여정을 검토할 수 있다.", ["검토 기준이 보인다."]),
    ])
    replacement.save(path)
    assert replacement.runtime_path == first_runtime
    assert yaml.safe_load(first_runtime.read_text(encoding="utf-8")) == {
        "version": 1, "bindings": {}}
    loaded = load_scenario(path)
    assert [node.id for node in loaded.missing_runtime_nodes()] == ["new-story"]

    same_stem_elsewhere = Scenario(name="다른 시나리오", site="fixture", nodes=[
        _story("other-story", "사용자는 다른 여정을 완료할 수 있다.", ["다른 결과가 보인다."],
               steps=[Step(action="goto", url=FIXTURE)]),
    ])
    same_stem_elsewhere.save(Path(_TMP) / "scenarios" / "fixture" / "second-flow" / "same-name.yaml")
    assert same_stem_elsewhere.runtime_path != first_runtime
    print("PASS test_runtime_paths_are_nested_and_stale_bindings_are_cleared")


def test_reports_escape_user_story_cells() -> None:
    scenario = Scenario(name="report-escape", site="fixture", nodes=[
        _story("story|id", "<b>사용자 스토리</b> | 줄바꿈\n다음 줄", ["결과가 보인다."],
               steps=[Step(action="wait")]),
    ])
    run_dir = Path(_TMP) / "report-escape"
    run_dir.mkdir(parents=True, exist_ok=True)
    result = RunResult(
        scenario=scenario,
        started_at=1,
        finished_at=2,
        run_dir=run_dir,
        status="pass",
        step_results=[StepResult(
            index=0, step=scenario.steps[0], status="pass", node_id="story|id",
            node_story="<b>사용자 스토리</b> | 줄바꿈\n다음 줄",
        )],
    )
    md_path, html_path = write_reports(result, Store(Path(_TMP) / "escape.db"))
    md = md_path.read_text(encoding="utf-8")
    html = html_path.read_text(encoding="utf-8")
    assert "&lt;b&gt;사용자 스토리&lt;/b&gt; \\| 줄바꿈 다음 줄" in md
    assert "&lt;b&gt;사용자 스토리&lt;/b&gt;" in html
    print("PASS test_reports_escape_user_story_cells")


def test_required_failure_stops_optional_failure_continues() -> None:
    required = Scenario(name="required-stop", site="fixture", base_url=FIXTURE, nodes=[
        _story("open", "방문자는 로그인 화면을 볼 수 있다.", ["로그인 버튼이 보인다."],
               steps=[Step(action="goto", url=FIXTURE)]),
        _story("required-missing", "사용자는 필수 동작을 완료할 수 있다.", ["필수 결과가 보인다."],
               depends_on=["open"], steps=[Step(action="click", selector="#does-not-exist", timeout_ms=300)]),
        _story("would-run-next", "사용자는 다음 여정을 진행할 수 있다.", ["로그인 버튼이 보인다."],
               depends_on=["open"], steps=[Step(action="expect_visible", selector="#login-btn")]),
    ])
    required_result = asyncio.run(Engine(Store(Path(_TMP) / "required.db"), headed=False)
                                  .run_scenario(required))
    assert required_result.status == "fail"
    assert [(r.node_id, r.status) for r in required_result.step_results] == [
        ("open", "pass"), ("required-missing", "fail")]

    optional = Scenario(name="optional-continue", site="fixture", base_url=FIXTURE, nodes=[
        _story("open", "방문자는 로그인 화면을 볼 수 있다.", ["로그인 버튼이 보인다."],
               steps=[Step(action="goto", url=FIXTURE)]),
        _story("optional-missing", "사용자는 선택 기능을 시도할 수 있다.", ["선택 기능의 결과를 기록한다."],
               depends_on=["open"], steps=[Step(action="click", selector="#does-not-exist", timeout_ms=300, optional=True)]),
        _story("after-optional", "사용자는 핵심 여정을 계속할 수 있다.", ["로그인 버튼이 보인다."],
               depends_on=["optional-missing"], steps=[Step(action="expect_visible", selector="#login-btn")]),
    ])
    optional_result = asyncio.run(Engine(Store(Path(_TMP) / "optional.db"), headed=False)
                                  .run_scenario(optional))
    assert optional_result.status == "pass"
    assert [(r.node_id, r.status) for r in optional_result.step_results] == [
        ("open", "pass"), ("optional-missing", "skipped"), ("after-optional", "pass")]
    print("PASS test_required_failure_stops_optional_failure_continues")


def test_human_dag_without_runtime_is_reviewable_but_not_replayable() -> None:
    scenario = Scenario.from_dict(_dag([{
        "id": "member-login",
        "story": "등록 회원은 계정에 로그인할 수 있다.",
        "acceptance": ["개인화된 환영 화면이 보인다."],
    }], "runtime-missing"))
    assert scenario.dag_data()["nodes"][0]["story"].startswith("등록 회원")
    result = asyncio.run(Engine(Store(Path(_TMP) / "missing.db"), headed=False).run_scenario(scenario))
    assert result.status == "error"
    assert result.step_results[0].node_id == "member-login"
    assert "runtime binding missing" in result.step_results[0].error
    print("PASS test_human_dag_without_runtime_is_reviewable_but_not_replayable")


if __name__ == "__main__":
    test_legacy_steps_run_unchanged_then_migrate_explicitly()
    test_story_dag_roundtrip_topology_and_private_runtime()
    test_story_dag_rejects_invalid_graphs_and_detail_fields()
    test_runtime_paths_are_nested_and_stale_bindings_are_cleared()
    test_reports_escape_user_story_cells()
    test_required_failure_stops_optional_failure_continues()
    test_human_dag_without_runtime_is_reviewable_but_not_replayable()
    print("ALL STORY DAG TESTS PASSED")
