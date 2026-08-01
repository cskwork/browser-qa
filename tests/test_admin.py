"""Web admin: server serves the page, lists scenarios, runs one, serves report."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

_TMP = tempfile.mkdtemp(prefix="superqa-admin-test-")
os.environ["SUPERQA_HOME"] = _TMP

from superqa_tui import admin  # noqa: E402
from superqa_tui.scenario import Scenario, ScenarioNode, Step  # noqa: E402

FIXTURE = (REPO / "tests" / "fixtures" / "testsite.html").as_uri()


def _seed() -> None:
    # The committed/reviewed DAG has only user stories and acceptance criteria.
    # save() keeps the browser-level mechanics in SUPERQA_HOME/runtimes instead.
    Scenario(
        name="admin-샘플", site="fixture", base_url=FIXTURE,
        language="ko", tags=["dag", "admin"],
        nodes=[
            ScenarioNode(
                id="reach-account", depends_on=["clear-notice", "prepare-login"],
                story="회원으로서 내 계정에 접근하기 위해 로그인할 수 있다.",
                acceptance=["환영 문구와 계정 영역이 표시된다."],
                steps=[
                    Step(action="click", selector="#login-btn", description="로그인 제출"),
                    Step(action="expect_visible", selector="#welcome", description="환영 문구 확인"),
                ],
            ),
            ScenarioNode(
                id="arrive", depends_on=[],
                story="방문자로서 서비스의 로그인 시작점에 도착할 수 있다.",
                acceptance=["로그인 입력 화면이 표시된다."],
                steps=[Step(action="goto", url=FIXTURE, description="로그인 화면 열기")],
            ),
            ScenarioNode(
                id="clear-notice", depends_on=["arrive"],
                story="방문자는 안내 알림을 처리하고 로그인 여정을 계속할 수 있다.",
                acceptance=["알림을 닫은 뒤 로그인 화면을 계속 볼 수 있다."],
                steps=[Step(action="click", selector="#alert-btn", description="안내 알림 처리")],
            ),
            ScenarioNode(
                id="prepare-login", depends_on=["arrive"],
                story="등록 회원은 자신의 로그인 정보를 준비할 수 있다.",
                acceptance=["아이디와 비밀번호를 입력한 상태가 된다."],
                steps=[
                    Step(action="fill", selector="#username", value="tester01", description="회원 아이디 입력"),
                    Step(action="fill", selector="#password", value="pw", description="회원 비밀번호 입력"),
                ],
            ),
        ],
    ).save()
    # Arbitrary human-authored stories must remain escaped text in the SVG.
    Scenario(
        name="admin-unsafe-label", site="fixture", base_url=FIXTURE,
        nodes=[ScenarioNode(
            id="unsafe-story", depends_on=[],
            story="<img src=x onerror=alert(1)>",
            acceptance=["HTML처럼 보이는 글도 텍스트로만 보인다."],
            steps=[Step(action="goto", url=FIXTURE)],
        )],
    ).save()


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())


def _post(url: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def test_admin_end_to_end() -> None:
    _seed()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), admin.Handler)
    port = httpd.server_address[1]
    base = f"http://127.0.0.1:{port}"
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        # page renders
        with urllib.request.urlopen(f"{base}/", timeout=10) as r:
            html = r.read().decode()
        assert "SuperQA" in html and "Admin" in html

        # scenario listed
        state = _get(f"{base}/api/state")
        names = [s["name"] for s in state["scenarios"]]
        assert "admin-샘플" in names, names
        sample = next(s for s in state["scenarios"] if s["name"] == "admin-샘플")
        assert sample["dag"]["format"] == "dag"
        assert [node["id"] for node in sample["dag"]["nodes"]] == [
            "arrive", "clear-notice", "prepare-login", "reach-account"]
        assert len(sample["dag"]["edges"]) == 4
        assert all(set(node) == {"id", "depends_on", "story", "acceptance"}
                   for node in sample["dag"]["nodes"])
        graph_json = json.dumps(sample["dag"], ensure_ascii=False)
        assert "selector" not in graph_json and "value" not in graph_json and "action" not in graph_json

        # A real browser must render the sample as nodes and arrows, while an
        # HTML-looking story stays text instead of becoming an injected DOM element.
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            page.goto(base, wait_until="networkidle")
            page.wait_for_selector(".dag-svg")
            assert page.locator(".dag-node").count() == 5
            assert page.locator(".dag-edge").count() == 4
            assert page.locator(".dag-review summary").first.inner_text().startswith("사용자 스토리 DAG 검토")
            assert page.locator("svg img").count() == 0
            browser.close()

        # run it headless
        resp = _post(f"{base}/api/run", {"scenario": "admin-샘플", "headless": True})
        assert resp.get("token"), resp

        # poll until finished (or timeout)
        report_url = None
        for _ in range(60):
            st = _get(f"{base}/api/state")
            active = st["active"]
            done = [a for a in active if a["status"] != "running"]
            if done and done[0].get("report"):
                report_url = st["runs"][0].get("report_url")
                assert done[0]["status"] == "pass", done[0]
                break
            time.sleep(1)
        assert report_url, "run did not finish with a report"

        # report served through the admin, with its screenshot.
        # report_url from the API is already percent-encoded; request it as-is.
        with urllib.request.urlopen(f"{base}{report_url}", timeout=10) as r:
            rep_html = r.read().decode()
        assert "admin-샘플" in rep_html
        shot_url = report_url.rsplit("/", 1)[0] + "/step-00.png"
        with urllib.request.urlopen(f"{base}{shot_url}", timeout=10) as r:
            assert r.read()[:4] == b"\x89PNG"
        print("PASS test_admin_end_to_end")
    finally:
        httpd.shutdown()


def test_admin_path_traversal_blocked() -> None:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), admin.Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        code = 0
        try:
            urllib.request.urlopen(
                f"http://127.0.0.1:{port}/report/../../../etc/passwd", timeout=10)
        except urllib.error.HTTPError as e:
            code = e.code
        assert code in (403, 404), code
        print("PASS test_admin_path_traversal_blocked")
    finally:
        httpd.shutdown()


if __name__ == "__main__":
    test_admin_end_to_end()
    test_admin_path_traversal_blocked()
    print("ALL ADMIN TESTS PASSED")
