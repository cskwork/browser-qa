"""Scenario model + YAML IO.

A scenario is a human-editable YAML file. Non-devs read/edit its user-story DAG, while
the engine runs a separate local runtime binding. Runtime ``Step`` selectors accept
either a plain string (CSS, or "text=...") or a dict with a fallback chain:
{testid, css, role, name, text}.

New scenarios use ``dag.nodes`` as a human-readable review artifact. Browser
locators and values live in a local runtime binding under ``~/.superqa/runtimes``;
they are never written into the scenario DAG. Legacy ``steps`` files are still read
as an implicit linear DAG and are never rewritten unless the caller explicitly
migrates them. The engine always receives a stable, topologically ordered node
sequence once its local runtime bindings are available.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

VALID_ACTIONS = {
    "goto", "click", "dblclick", "fill", "press", "select", "check", "uncheck",
    "hover", "wait", "expect_visible", "expect_text", "expect_url",
    "screenshot", "switch_tab", "close_tab", "scroll", "login",
}

DEFAULT_HOME = Path.home() / ".superqa"


def safe_name(name: str) -> str:
    return re.sub(r"[^\w\-가-힣]+", "-", name).strip("-")[:60] or "run"


def superqa_home() -> Path:
    import os
    home = Path(os.environ.get("SUPERQA_HOME", DEFAULT_HOME))
    for sub in ("scenarios", "reports", "sites", "schedules", "runtimes"):
        (home / sub).mkdir(parents=True, exist_ok=True)
    return home


@dataclass
class Step:
    action: str
    selector: Any = None          # str | dict | None
    value: str | None = None      # fill text / press key / select option / expect text
    url: str | None = None        # goto / expect_url (substring match)
    description: str = ""         # human-readable, user's language
    timeout_ms: int = 10000
    optional: bool = False        # optional step failure does not fail the scenario
    expect_popup: bool = False    # click is expected to open a new tab/popup
    retry: int = 0                # extra attempts on failure (flaky UIs)

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"action": self.action}
        for key in ("selector", "value", "url"):
            v = getattr(self, key)
            if v is not None:
                d[key] = v
        if self.description:
            d["description"] = self.description
        if self.timeout_ms != 10000:
            d["timeout_ms"] = self.timeout_ms
        if self.optional:
            d["optional"] = True
        if self.expect_popup:
            d["expect_popup"] = True
        if self.retry:
            d["retry"] = self.retry
        return d

    @staticmethod
    def from_dict(d: dict) -> "Step":
        if not isinstance(d, dict):
            raise ValueError("step must be a mapping")
        action = str(d.get("action", "")).strip()
        if action not in VALID_ACTIONS:
            raise ValueError(f"unknown action: {action!r}")
        return Step(
            action=action,
            selector=d.get("selector"),
            value=None if d.get("value") is None else str(d.get("value")),
            url=d.get("url"),
            description=str(d.get("description", "")),
            timeout_ms=int(d.get("timeout_ms", 10000)),
            optional=bool(d.get("optional", False)),
            expect_popup=bool(d.get("expect_popup", False)),
            retry=max(0, int(d.get("retry", 0))),
        )


@dataclass
class ScenarioNode:
    """One user-story DAG node with optional private browser replay steps."""

    id: str
    depends_on: list[str]
    story: str
    acceptance: list[str]
    steps: list[Step] = field(default_factory=list, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip() or self.id != self.id.strip():
            raise ValueError("dag node id must be a non-empty trimmed string")
        if not isinstance(self.depends_on, list):
            raise ValueError(f"dag node {self.id!r} depends_on must be a list")
        for dependency in self.depends_on:
            if (not isinstance(dependency, str) or not dependency.strip()
                    or dependency != dependency.strip()):
                raise ValueError(f"dag node {self.id!r} dependencies must be non-empty strings")
        if len(set(self.depends_on)) != len(self.depends_on):
            raise ValueError(f"dag node {self.id!r} has duplicate dependencies")
        if self.id in self.depends_on:
            raise ValueError(f"dag node {self.id!r} cannot depend on itself")
        if (not isinstance(self.story, str) or not self.story.strip()
                or self.story != self.story.strip()):
            raise ValueError(f"dag node {self.id!r} story must be a non-empty trimmed string")
        if not isinstance(self.acceptance, list) or not self.acceptance:
            raise ValueError(f"dag node {self.id!r} acceptance must be a non-empty list")
        for criterion in self.acceptance:
            if (not isinstance(criterion, str) or not criterion.strip()
                    or criterion != criterion.strip()):
                raise ValueError(f"dag node {self.id!r} acceptance entries must be non-empty strings")
        if not isinstance(self.steps, list) or not all(isinstance(step, Step) for step in self.steps):
            raise ValueError(f"dag node {self.id!r} runtime binding must be a list of Steps")

    @staticmethod
    def from_dict(d: dict, steps: list[Step] | None = None) -> "ScenarioNode":
        if not isinstance(d, dict):
            raise ValueError("dag.nodes entries must be mappings")
        allowed = {"id", "depends_on", "story", "acceptance"}
        unsupported = sorted(set(d) - allowed)
        if unsupported:
            raise ValueError("dag nodes are user-story-only; unsupported keys: "
                             + ", ".join(unsupported))
        return ScenarioNode(
            id=d.get("id"),
            depends_on=d.get("depends_on", []),
            story=d.get("story"),
            acceptance=d.get("acceptance"),
            steps=list(steps or []),
        )

    def to_dict(self) -> dict:
        output = {
            "id": self.id,
            "story": self.story,
            "depends_on": list(self.depends_on),
            "acceptance": list(self.acceptance),
        }
        return output


def _legacy_story(name: str) -> str:
    return f"사용자는 {name} 여정을 완료할 수 있다."


def _legacy_acceptance(steps: list[Step]) -> list[str]:
    assertions = [step.description.strip() for step in steps
                  if step.action.startswith("expect_") and step.description.strip()]
    return assertions or ["시나리오가 오류 없이 완료된다."]


def _linear_nodes(name: str, steps: list[Step]) -> list[ScenarioNode]:
    """Represent old executable steps as one high-level user-story node in memory."""
    if not steps:
        return []
    return [ScenarioNode(
        id="journey",
        depends_on=[],
        story=_legacy_story(name),
        acceptance=_legacy_acceptance(steps),
        steps=list(steps),
    )]


def _runtime_story(step: Step) -> str:
    return step.description.strip() or "사용자는 이 QA 여정을 완료할 수 있다."


def _runtime_acceptance(step: Step) -> list[str]:
    return [step.description.strip() or "동작이 오류 없이 완료된다."]


def _ordered_nodes(nodes: list[ScenarioNode]) -> list[ScenarioNode]:
    """Validate a DAG and return Kahn order, tied by YAML declaration order."""
    if not nodes:
        return []
    by_id: dict[str, ScenarioNode] = {}
    declaration_order: dict[str, int] = {}
    for index, node in enumerate(nodes):
        if node.id in by_id:
            raise ValueError(f"duplicate dag node id: {node.id!r}")
        by_id[node.id] = node
        declaration_order[node.id] = index

    children: dict[str, list[str]] = {node.id: [] for node in nodes}
    indegree: dict[str, int] = {node.id: 0 for node in nodes}
    for node in nodes:
        for dependency in node.depends_on:
            if dependency not in by_id:
                raise ValueError(f"dag node {node.id!r} depends on missing node {dependency!r}")
            children[dependency].append(node.id)
            indegree[node.id] += 1

    ready = [node.id for node in nodes if indegree[node.id] == 0]
    ordered: list[ScenarioNode] = []
    while ready:
        ready.sort(key=declaration_order.__getitem__)
        node_id = ready.pop(0)
        ordered.append(by_id[node_id])
        for child_id in children[node_id]:
            indegree[child_id] -= 1
            if indegree[child_id] == 0:
                ready.append(child_id)

    if len(ordered) != len(nodes):
        cycle_ids = [node.id for node in nodes if indegree[node.id] > 0]
        raise ValueError("dag contains a cycle involving: " + ", ".join(cycle_ids))
    return ordered


@dataclass
class Policy:
    dialogs: str = "accept"       # accept | dismiss | fail
    popups: str = "follow"        # follow (switch to new tab) | ignore | fail
    fail_on_console_error: bool = False
    fail_on_http_error: bool = False
    ignore_effects: list[str] = field(default_factory=list)  # substrings -> noise
    visual_threshold: float = 1.0  # % pixels changed vs baseline before flagging

    def to_dict(self) -> dict:
        d = {
            "dialogs": self.dialogs,
            "popups": self.popups,
            "fail_on_console_error": self.fail_on_console_error,
            "fail_on_http_error": self.fail_on_http_error,
        }
        if self.ignore_effects:
            d["ignore_effects"] = list(self.ignore_effects)
        if self.visual_threshold != 1.0:
            d["visual_threshold"] = self.visual_threshold
        return d

    @staticmethod
    def from_dict(d: dict | None) -> "Policy":
        if d is None:
            d = {}
        if not isinstance(d, dict):
            raise ValueError("policy must be a mapping")
        ignore_effects = d.get("ignore_effects") or []
        if not isinstance(ignore_effects, list):
            raise ValueError("policy.ignore_effects must be a list")
        return Policy(
            dialogs=str(d.get("dialogs", "accept")),
            popups=str(d.get("popups", "follow")),
            fail_on_console_error=bool(d.get("fail_on_console_error", False)),
            fail_on_http_error=bool(d.get("fail_on_http_error", False)),
            ignore_effects=[str(x) for x in ignore_effects],
            visual_threshold=float(d.get("visual_threshold", 1.0)),
        )


def site_ignore_patterns(site: str, home: Path | None = None) -> list[str]:
    """Noise substrings from ~/.superqa/sites/<site>/ignore.yaml (a plain list)."""
    p = (home or superqa_home()) / "sites" / site / "ignore.yaml"
    if not p.exists():
        return []
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        return [str(x) for x in data] if isinstance(data, list) else []
    except Exception:
        return []


def _runtime_path_for(scenario_path: Path, site: str) -> Path:
    """Keep replay mechanics local and separate from the human scenario YAML."""
    home = superqa_home()
    scenario_root = home / "scenarios" / site
    try:
        relative = scenario_path.resolve().relative_to(scenario_root.resolve()).with_suffix("")
    except ValueError:
        # Explicit paths outside ~/.superqa/scenarios (for example a temporary review
        # file) keep the established flat fallback without colliding with normal files.
        relative = Path(safe_name(scenario_path.stem))
    safe_relative = Path(*(safe_name(part) for part in relative.parts)).with_suffix(".yaml")
    return home / "runtimes" / safe_name(site) / safe_relative


def _load_runtime_bindings(scenario_path: Path | None, site: str) -> tuple[dict[str, list[Step]], Path | None]:
    if scenario_path is None:
        return {}, None
    runtime_path = _runtime_path_for(scenario_path, site)
    if not runtime_path.exists():
        return {}, runtime_path
    data = yaml.safe_load(runtime_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("bindings"), dict):
        raise ValueError(f"runtime bindings must be a mapping: {runtime_path}")
    bindings: dict[str, list[Step]] = {}
    for node_id, raw_binding in data["bindings"].items():
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError(f"runtime binding ID must be a non-empty string: {runtime_path}")
        if not isinstance(raw_binding, dict) or not isinstance(raw_binding.get("steps"), list):
            raise ValueError(f"runtime binding {node_id!r} must contain a steps list")
        bindings[node_id] = [Step.from_dict(raw_step) for raw_step in raw_binding["steps"]]
    return bindings, runtime_path


@dataclass
class Scenario:
    name: str
    site: str = "default"
    base_url: str = ""
    language: str = "ko"
    tags: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    nodes: list[ScenarioNode] = field(default_factory=list, repr=False)
    policy: Policy = field(default_factory=Policy)
    path: Path | None = None      # where it was loaded from / saved to
    runtime_path: Path | None = field(default=None, repr=False, compare=False)
    storage_format: str = field(default="dag", repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.steps and self.nodes:
            raise ValueError("scenario cannot define both steps and DAG nodes")
        if self.storage_format not in {"steps", "dag"}:
            raise ValueError(f"unknown scenario storage format: {self.storage_format!r}")
        if self.nodes:
            # Validate now, but retain declaration order for a human reviewing or
            # explicitly saving YAML. execution_nodes() calculates run order.
            _ordered_nodes(list(self.nodes))
        else:
            self.nodes = _linear_nodes(self.name, list(self.steps))
        # Keep the established runtime surface for the engine. A hand-authored DAG
        # may intentionally have no local bindings until it is recorded or wired up.
        self.steps = [step for node in self.execution_nodes() for step in node.steps]

    def execution_nodes(self) -> tuple[ScenarioNode, ...]:
        return tuple(_ordered_nodes(self.nodes))

    def missing_runtime_nodes(self) -> tuple[ScenarioNode, ...]:
        return tuple(node for node in self.execution_nodes() if not node.steps)

    def append_step(self, step: Step) -> ScenarioNode:
        """Append an internally generated step as the next node in a linear flow."""
        candidate = len(self.nodes) + 1
        existing = {node.id for node in self.nodes}
        node_id = f"story-{candidate:02d}"
        while node_id in existing:
            candidate += 1
            node_id = f"story-{candidate:02d}"
        depended_on = {dependency for existing_node in self.nodes
                        for dependency in existing_node.depends_on}
        dependencies = [existing_node.id for existing_node in self.execution_nodes()
                        if existing_node.id not in depended_on]
        node = ScenarioNode(id=node_id, depends_on=dependencies,
                            story=_runtime_story(step), acceptance=_runtime_acceptance(step),
                            steps=[step])
        self.nodes.append(node)
        self.steps = [runtime_step for execution_node in self.execution_nodes()
                      for runtime_step in execution_node.steps]
        return node

    def dag_data(self) -> dict:
        """Human review metadata only; runtime locators and values never leave disk."""
        nodes = [
            {"id": node.id, "story": node.story, "acceptance": list(node.acceptance),
             "depends_on": list(node.depends_on)}
            for node in self.execution_nodes()
        ]
        return {
            "format": self.storage_format,
            "node_count": len(nodes),
            "nodes": nodes,
            "edges": [
                {"from": dependency, "to": node.id}
                for node in self.execution_nodes() for dependency in node.depends_on
            ],
        }

    def to_dict(self, *, storage_format: str | None = None) -> dict:
        output = {
            "name": self.name,
            "site": self.site,
            "base_url": self.base_url,
            "language": self.language,
            "tags": list(self.tags),
            "policy": self.policy.to_dict(),
        }
        fmt = storage_format or self.storage_format
        if fmt == "steps":
            if self.missing_runtime_nodes():
                raise ValueError("cannot write legacy steps without runtime bindings")
            output["steps"] = [step.to_dict() for node in self.nodes for step in node.steps]
        elif fmt == "dag":
            output["dag"] = {"nodes": [node.to_dict() for node in self.nodes]}
        else:
            raise ValueError(f"unknown scenario storage format: {fmt!r}")
        return output

    @staticmethod
    def from_dict(d: dict, path: Path | None = None) -> "Scenario":
        if not isinstance(d, dict):
            raise ValueError("scenario must be a mapping")
        has_steps = "steps" in d
        has_dag = "dag" in d
        if has_steps == has_dag:
            raise ValueError("scenario must define exactly one of steps or dag.nodes")
        raw_tags = d.get("tags") or []
        if not isinstance(raw_tags, list):
            raise ValueError("scenario tags must be a list")
        common = {
            "name": str(d.get("name", path.stem if path else "scenario")),
            "site": str(d.get("site", "default")),
            "base_url": str(d.get("base_url", "")),
            "language": str(d.get("language", "ko")),
            "tags": [str(tag) for tag in raw_tags],
            "policy": Policy.from_dict(d.get("policy")),
            "path": path,
        }
        if has_steps:
            raw_steps = d["steps"]
            if not isinstance(raw_steps, list):
                raise ValueError("steps must be a list")
            return Scenario(
                **common,
                steps=[Step.from_dict(step) for step in raw_steps],
                storage_format="steps",
            )
        raw_dag = d["dag"]
        if not isinstance(raw_dag, dict):
            raise ValueError("dag must be a mapping with a nodes list")
        raw_nodes = raw_dag.get("nodes")
        if not isinstance(raw_nodes, list):
            raise ValueError("dag.nodes must be a list")
        if not raw_nodes:
            raise ValueError("dag.nodes must contain at least one user-story node")
        bindings, runtime_path = _load_runtime_bindings(path, common["site"])
        nodes: list[ScenarioNode] = []
        for raw_node in raw_nodes:
            if not isinstance(raw_node, dict):
                raise ValueError("dag.nodes entries must be mappings")
            raw_id = raw_node.get("id")
            nodes.append(ScenarioNode.from_dict(
                raw_node, steps=bindings.get(raw_id) if isinstance(raw_id, str) else None))
        unknown_bindings = sorted(set(bindings) - {node.id for node in nodes})
        if unknown_bindings:
            raise ValueError("runtime bindings reference unknown DAG nodes: "
                             + ", ".join(unknown_bindings))
        return Scenario(
            **common,
            nodes=nodes,
            runtime_path=runtime_path,
            storage_format="dag",
        )

    def save(self, path: Path | None = None, *, as_dag: bool | None = None) -> Path:
        """Persist without silently migrating a legacy file.

        New/recorded scenarios default to DAG storage. A loaded legacy scenario
        remains ``steps`` until ``as_dag=True`` (or ``migrate_to_dag``) is used.
        """
        target = path or self.path
        if target is None:
            safe = re.sub(r"[^\w\-가-힣]+", "-", self.name).strip("-") or "scenario"
            target = superqa_home() / "scenarios" / self.site / f"{safe}.yaml"
        target.parent.mkdir(parents=True, exist_ok=True)
        storage_format = ("dag" if as_dag is True else "steps" if as_dag is False
                          else self.storage_format)
        target.write_text(
            yaml.safe_dump(self.to_dict(storage_format=storage_format),
                           allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        if storage_format == "dag":
            bindings = {
                node.id: {"steps": [step.to_dict() for step in node.steps]}
                for node in self.nodes if node.steps
            }
            # Replacing with an explicit empty map is safer than reusing a stale
            # binding: a new human story must not replay an old browser operation.
            runtime_path = _runtime_path_for(target, self.site)
            runtime_path.parent.mkdir(parents=True, exist_ok=True)
            runtime_path.write_text(
                yaml.safe_dump({"version": 1, "bindings": bindings},
                               allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            self.runtime_path = runtime_path
        self.path = target
        self.storage_format = storage_format
        return target

    def migrate_to_dag(self, path: Path | None = None) -> Path:
        return self.save(path, as_dag=True)


def load_scenario(path: Path) -> Scenario:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: not a scenario file")
    return Scenario.from_dict(data, path=path)


def list_scenarios(home: Path | None = None) -> list[Scenario]:
    root = (home or superqa_home()) / "scenarios"
    out: list[Scenario] = []
    for p in sorted(root.rglob("*.yaml")):
        try:
            out.append(load_scenario(p))
        except Exception:
            continue  # surfaced separately via broken_scenarios()
    return out


def broken_scenarios(home: Path | None = None) -> list[tuple[Path, str]]:
    """Scenario files that fail to load - shown as warnings so they never vanish silently."""
    root = (home or superqa_home()) / "scenarios"
    out: list[tuple[Path, str]] = []
    for p in sorted(root.rglob("*.yaml")):
        try:
            load_scenario(p)
        except Exception as e:
            out.append((p, str(e).splitlines()[0][:120]))
    return out


def find_scenario(name_or_path: str, home: Path | None = None) -> Scenario:
    p = Path(name_or_path).expanduser()
    if p.exists():
        return load_scenario(p)
    for sc in list_scenarios(home):
        if sc.name == name_or_path or (sc.path and sc.path.stem == name_or_path):
            return sc
    raise FileNotFoundError(f"scenario not found: {name_or_path}")
