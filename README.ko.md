# browser-qa

어떤 웹사이트든 - 개발/스테이징/운영 - 누구나 할 수 있는 브라우저 QA.

URL 하나와 한 줄 요청만 주면 browser-qa가 사이트를 탐색해 테스트 시나리오 케이스를
만들고, 실제 브라우저로 실행하고, 흐름만 봐서는 못 잡는 부작용(콘솔 오류, JS 예외,
네트워크 요청 실패, 예상 밖 알림창/팝업/새 탭)을 감지해, 비개발자도 읽을 수 있는
리포트를 사용자의 언어로 만들어 줍니다.

사용 방법은 두 가지:

- **Claude Code 스킬로** - 에이전트가 `SKILL.md`를 읽고 `playwright-cli`로 탐색,
  시나리오 YAML 생성, 결정적 실행, 결과 분류까지 대신합니다.
- **독립 앱으로** - Textual TUI + CLI. 실제 브라우저에서 클릭만 하면 시나리오가
  기록되고, 실행/스케줄/자동화까지 코드 없이 됩니다.

## 왜 필요한가

- **기능 개발 완료 후 QA**: 개발자가 백엔드/프론트 기능을 끝내면
  `superqa run --all --site myshop` 한 줄로 저장된 케이스 전체를 회귀 실행하고
  증적이 첨부된 판정을 몇 분 안에 받습니다.
- **비개발자가 테스트를 소유**: 기록은 말 그대로 사이트를 클릭하는 것. 떠 있는
  browser-qa 패널이 각 단계를 사람이 읽는 설명과 함께 캡처합니다.
- **부작용이 일급 시민**: 매 실행마다 팝업을 포함한 브라우저 전체를 감시하므로,
  단언한 단계가 전부 성공해도 API 500, 미처리 예외, 예상 밖 새 탭이 드러납니다.
  중복은 횟수로 합쳐지고, 알려진 노이즈는 사이트별 ignore 규칙으로 분리됩니다.
- **실행할 때마다 자동 비교**: 같은 시나리오의 직전 실행과 비교해 새 실패·새 부작용
  유형만 회귀로 짚어주고, 변화가 없으면 "회귀 없음" 판정을 줍니다.
- **화면 변화 감지(시각 회귀)**: 믿을 수 있는 실행을 기준선으로 채택하면
  (`superqa baseline`), 이후 실행마다 단계별 스크린샷을 픽셀 비교해 레이아웃 변화가
  빨간색 diff 이미지와 함께 표시됩니다. 실패한 실행은 Playwright `trace.zip`으로
  실패 순간을 되돌려볼 수 있습니다.
- **검토 가능한 사용자 스토리 DAG**: 새 케이스는 안정적인 ID, 사용자 스토리, 눈에
  보이는 인수 기준, 선행 조건을 YAML에 저장합니다. `superqa dag check`가 구조를
  검사하고, 로컬 Admin은 브라우저 동작·값·비밀을 보이지 않은 채 분기와 합류를 그려 줍니다.
- **CI 연동**: `--junit results.xml`로 Jenkins/GitHub Actions에서 네이티브 테스트
  결과로 표시. `superqa doctor`가 환경 문제를 우리말로 진단합니다.

## 설치

```bash
git clone https://github.com/cskwork/browser-qa ~/.claude/skills/browser-qa
cd ~/.claude/skills/browser-qa
pip3 install textual playwright pyyaml && python3 -m playwright install chromium
# 선택: pip3 install -e .   ->  `superqa` 명령 사용 가능
```

요구사항: Python 3.10+, Playwright Chromium(위에서 설치).

## 빠른 시작 (코드 없이)

```bash
superqa serve                        # 웹 admin: 시나리오마다 실행 버튼 클릭
bash scripts/superqa.sh              # 또는 터미널 TUI
```

**웹 admin**(`superqa serve` -> http://127.0.0.1:8760)이 가장 클릭하기 쉬운 화면입니다.
녹화·에이전트 생성 시나리오 전부를 의존성 DAG와 실행 버튼으로 보여주고, 실시간 진행·
실행 이력·리포트 열람까지 됩니다. TUI/CLI와 같은 데이터를 공유합니다.

- `n` - 기록: 크롬 창이 열리고 우측 하단에 browser-qa 패널이 뜹니다. 평소처럼
  클릭하면 각 클릭/입력이 단계가 됩니다. 비밀번호는 평문이 아닌 `{{password}}`로
  저장됩니다. "저장 후 종료"를 누르면 끝.
- `r` - 선택한 시나리오 실행(브라우저가 재현하는 것을 지켜볼 수 있음).
- `a` - 전체 실행(회귀 스윕). `u` - URL만 넣는 원버튼 스모크 QA.
- `s` - N분마다 스케줄 실행. `v` - 계정/변수 관리.
- `o` - 최신 HTML 리포트 열기.

## 빠른 시작 (CLI / CI)

```bash
superqa record https://myshop.example.com --site myshop --name 로그인-정상
superqa vars set myshop username myid
superqa vars set myshop password s3cret          # 리포트에서 자동 마스킹
superqa dag check --all --site myshop             # 재생 전 YAML DAG 검사
superqa run --all --site myshop --headless        # 종료 코드 0 = 전부 성공
superqa auto https://myshop.example.com           # 설정 없는 스모크 QA
superqa schedule add 로그인-정상 --every 30 && superqa schedule daemon

# 같은 시나리오를 다른 대상으로 (로컬 스택, 스테이징) — 저장된 값은 그대로 둔다
superqa run --all --site myshop --headless --var base_url=http://localhost:3000
```

## 로컬 스택으로 실행하기

`--var KEY=VALUE` 는 저장된 변수를 건드리지 않고 그 실행에서만 대상을 바꾼다. 하나의 시나리오
세트로 공용 환경과 내 PC 위의 스택을 모두 검증할 수 있다. 공용 환경에서는 만들기 어려운 파괴적
케이스나 "최초 사용자" 상태는 로컬 서비스 + 로컬 데이터 서브셋으로 다루는 편이 낫다. 절차는
[`reference/local-offline.md`](reference/local-offline.md) 에 있다 — 로컬 DB에서 픽스처를
도출하는 방법과, 그 케이스가 실제로 실패할 수 있음을 증명하는 방법까지 포함한다.

## 실행 결과물

`~/.superqa/reports/<시각>-<시나리오>/`:

- `report.html` - 성공/실패 배지, 단계별 스크린샷 표, 부작용 표. 단일 파일이라
  누구에게든 그대로 전달 가능.
- `report.md` - 채팅/PR에 붙여넣기용.
- `step-NN.png` - 매 단계 스크린샷.

리포트 언어는 시나리오의 `language:` 필드를 따릅니다(한국어/영어 내장).

## 시나리오 형식

비개발자도 읽고 고칠 수 있는 YAML -
[reference/scenario-format.md](reference/scenario-format.md) 참고:

```yaml
name: 로그인-정상
site: myshop
language: ko
policy: { dialogs: accept, popups: follow }
dag:
  nodes:
    - id: arrive-login
      story: "방문자로서 서비스의 로그인 시작점에 도착할 수 있다."
      depends_on: []
      acceptance: ["로그인 입력 화면이 표시된다."]
    - id: prepare-login
      story: "등록 회원은 자신의 로그인 정보를 준비할 수 있다."
      depends_on: [arrive-login]
      acceptance: ["아이디와 비밀번호를 입력할 수 있다."]
    - id: reach-account
      story: "회원으로서 내 계정에 접근하기 위해 로그인할 수 있다."
      depends_on: [prepare-login]
      acceptance: ["환영 문구와 계정 영역이 표시된다."]
```

검토용 YAML에는 `action`, `selector`, 입력값이 없습니다. 녹화기/QA 에이전트가 상세
브라우저 바인딩을 `~/.superqa/runtimes/`에 로컬로만 두므로, 하나의 스토리가 여러
브라우저 동작을 재현해도 검토 그래프는 잘게 쪼개지지 않습니다. 노드는 안정적인 위상
순서로 하나씩 실행하며(동률은 YAML 선언 순서), DAG는 그 분기와 합류를 사람이 검토하게
해 줍니다. 기존 `steps:` 파일은 읽거나 실행해도 바뀌지 않으며, 바꾸고 싶을 때만
`superqa dag migrate`를 실행합니다.

## 도메인 QA 팩

같은 제품을 반복 QA할 때마다 처음부터 다시 파악하지 않도록, **팩**
(기본 `~/.superqa/packs/<domain>/`; 위치는 최초 1회 물어보고
`~/.superqa/config.yaml` 에 기록)이 도메인의 기능 맵(`pack.md`), 기능별 노트,
그리고 **재사용 QA 스크립트 보관소**를 유지합니다 — 티켓 폴더에서 사라질
데이터 탐색 SQL, 프로브, 하네스가 여기 남습니다. "QA \<도메인\> \<기능\>" 이라고
하면 팩을 읽고 이미 있는 것부터 실행하며, 빈 곳만 새로 탐색합니다.
[reference/domain-packs.md](reference/domain-packs.md) 참조.

탐색용 브라우저 엔진은 설치된 것 중 최선을 자동 선택합니다: macOS에서는
ego-browser(ego-lite) 우선, 다음 Playwright MCP, `playwright-cli`, 기타 드라이버
순서 ([reference/engines.md](reference/engines.md)). 결정적 재생과 리포트는
항상 browser-qa 엔진이 담당합니다.

## 사이트 정보는 로컬에만

사이트 고유 정보는 전부 `~/.superqa/` 아래에만 있고 이 저장소에는 절대 들어가지
않습니다:

```
~/.superqa/
├── superqa.db               # 계정/변수 (SQLite; 비밀 키는 리포트에서 마스킹)
├── config.yaml              # 팩 위치 + 탐색 엔진 선택
├── scenarios/<site>/*.yaml  # 테스트 케이스
├── runtimes/<site>/*.yaml   # 로컬 브라우저 바인딩; 검토용 YAML과 분리
├── reports/                 # 실행 증적
├── packs/<domain>/          # 기능 맵 + 재사용 QA 스크립트 보관소
└── sites/<site>/rules.md    # 에이전트가 관리하는 사이트별 플레이북
```

## 테스트

```bash
python3 tests/test_engine_smoke.py   # 로컬 픽스처로 재현/기록/자동QA 검증
python3 tests/test_tui_smoke.py      # Textual 파일럿 스모크
python3 tests/test_dag.py            # DAG 검사·마이그레이션·실행 의미 검증
python3 tests/test_admin.py          # Admin 그래프 렌더링 + 실제 재생
```

실제 운영 중인 사이트 2곳에서 전체 파이프라인(시나리오, 알림창, 다중 탭 팝업 체인,
저장된 계정 로그인)을 3회 연속 전부 성공으로 검증했고, 그 과정에서 부작용 수집기가
실제 미처리 JS 예외 1건을 찾아냈습니다.

## 라이선스

MIT
