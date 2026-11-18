# 금융 인턴 레이더

PE·VC·자산운용·증권·컨설팅·회계법인(FAS)·신용평가 인턴 공고를 여러 채용 사이트에서 모아
마감 임박순 대시보드로 보여주는 크롤러.

- 대시보드: https://yeonam00.github.io/finance-intern-radar/
- 자동 실행: 매일 08:00, 18:00 (KST) — `.github/workflows/crawl.yml`
- 수동 실행: GitHub → Actions → "금융 인턴 공고 수집" → Run workflow

## 수집 사이트

링커리어, 자소설닷컴, 캐치, 원티드, 사람인, 잡코리아, 피플앤잡, 잡알리오, 벤처투자종합포털(KVCA),
금융투자협회 채용게시판, 고려대 경영대 CDC, 슈퍼루키, 일부 외국계 회사 채용 페이지(Citi, BCG, BlackRock, Bain, Macquarie)

## 로컬 실행

```bash
pip install -r requirements.txt
python -m playwright install chromium
python run.py                 # 전체 수집 → dashboard.html
python run.py --from-cache    # 다시 긁지 않고 분류/대시보드만 다시 만들기
python run.py --only 링커리어 캐치
```

## 구조

- `crawler/sources.py` — 사이트별 수집기
- `crawler/classify.py` — 인턴 여부·분야 분류 규칙 (오탐이 보이면 여기 정규식 수정)
- `crawler/render.py` — 대시보드 HTML, "직접 확인할 곳" 링크 목록
- `run.py` — 수집 → 분류 → 중복 병합 → `data/jobs.json`, `dashboard.html`
- `data/jobs.json` — 공고별 처음 발견한 날짜(NEW 표시용). Actions가 매번 커밋해서 유지
