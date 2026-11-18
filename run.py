"""금융 인턴 공고 크롤러.

사용법:
    python run.py                  # 전체 소스 수집 → dashboard.html 생성
    python run.py --only 링커리어 캐치   # 일부 소스만
    python run.py --no-browser     # Playwright 필요한 소스(슈퍼루키, 회사 채용페이지) 제외

결과:
    dashboard.html  : 대시보드 (브라우저로 열기)
    data/jobs.json  : 수집 결과 + 처음 발견한 날짜 기록 (NEW 표시용)
"""
import argparse
import difflib
import json
import re
import sys
import time
import traceback
import datetime as dt
from pathlib import Path

from crawler.common import TODAY
from crawler.classify import classify, is_intern
from crawler.sources import ALL_SOURCES
from crawler.render import render

ROOT = Path(__file__).parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
STORE = DATA / "jobs.json"

SOURCE_HINT = {"벤처투자포털": "VC", "금융투자협회": "증권·IB"}
BROWSER_SOURCES = {"슈퍼루키", "회사 채용페이지"}


# 사이트마다 다르게 적는 회사명을 하나로 (중복 병합 + 표시용)
COMPANY_ALIASES = [
    (r"한영|\bEY\b|Ernst", "EY한영"),
    (r"안진|Deloitte|딜로이트", "딜로이트 안진"),
    (r"삼일|PwC|피더블유씨", "삼일PwC"),
    (r"삼정|KPMG", "삼정KPMG"),
    (r"IBK\s*기업은행|중소기업은행|^IBK$", "IBK기업은행"),
    (r"^ING|아이엔지", "ING 서울지점"),
    (r"스탠다드차타드|Standard\s*Chartered|SC제일", "SC제일은행"),
    (r"한국씨티|^Citi", "한국씨티은행"),
    (r"블랙록|BlackRock", "BlackRock"),
    (r"카카오벤처스", "카카오벤처스"),
    (r"커니|Kearney", "Kearney"),
    (r"새빛회계|Forvis\s*Mazars", "Forvis Mazars 새빛"),
    (r"다날투자파트너스", "다날투자파트너스"),
    (r"하나저축은행", "하나저축은행"),
    (r"메트라이프", "메트라이프생명"),
]

# 제목에 마감됐다고 적힌 공고 (금투협처럼 마감일 필드가 없는 게시판용)
CLOSED_RE = re.compile(r"마감\s*완료|\[\s*마감\s*\]|\(\s*마감\s*\)|접수\s*마감\)|채용\s*완료|모집\s*완료|지원서\s*접수\s*마감")


NOT_INTERN_TITLE = re.compile(r"경력직|정직원|정규직원|경력\s*(사원|채용|모집)|운용역|세무대리인")


# 금투협처럼 영문 약어를 한글 음차로 적는 경우 (케이비자산운용 → KB자산운용)
HANGUL_ABBR = [("케이비", "KB"), ("엔에이치", "NH"), ("엘에스", "LS"), ("디비", "DB"), ("에스케이", "SK"),
               ("아이비케이", "IBK"), ("디에스", "DS"), ("비엔케이", "BNK"), ("아이엠", "iM"), ("케이씨지아이", "KCGI"),
               ("유비에스", "UBS"), ("에이치디", "HD"), ("디지비", "DGB"), ("제이비", "JB"), ("엠지", "MG")]


def canon_company(s):
    for pat, name in COMPANY_ALIASES:
        if re.search(pat, s or "", re.I):
            return name
    s = re.sub(r"\s*(\(주\)|㈜|주식회사|\(유\)|유한회사)\s*", "", s or "").strip()
    for ko, en in HANGUL_ABBR:
        if s.startswith(ko) and re.match(r"(증권|자산운용|투자증권|캐피탈|인베스트|생명|손해|은행|금융|자산)", s[len(ko):]):
            return en + s[len(ko):]
    return s


def norm_company(s):
    s = canon_company(s)
    s = re.sub(r"co\.,?\s*ltd\.?|inc\.?|corp\.?|limited", "", s, flags=re.I)
    return re.sub(r"[^0-9a-z가-힣]", "", s.lower())


def similar(a, b):
    if not a or not b:
        return False
    if a == b:
        return True
    short, long_ = sorted((a, b), key=len)
    if len(short) >= 8 and short in long_:
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.78


def norm_title(title, company):
    t = title or ""
    # 제목 앞의 [회사명] 같은 태그 제거
    t = re.sub(r"^\s*(\[[^\]]*\]\s*)+", "", t)
    t = re.sub(r"\(\s*~?[^)]*(마감|까지|~)[^)]*\)", "", t)
    t = re.sub(r"[^0-9a-z가-힣]", "", t.lower())
    c = norm_company(company)
    if c and t.startswith(c):
        t = t[len(c):]
    return t


def merge(jobs):
    groups = {}
    for j in jobs:
        groups.setdefault(norm_company(j["company"]) or "_", []).append(j)
    out = []
    for comp, items in groups.items():
        merged = []
        for j in items:
            nt = norm_title(j["title"], j["company"])
            hit = None
            for m in merged:
                if comp == "_":
                    continue
                if similar(nt, m["_nt"]):
                    hit = m
                    break
            if hit:
                if not any(s["url"] == j["url"] or s["name"] == j["source"] for s in hit["sources"]):
                    hit["sources"].append({"name": j["source"], "url": j["url"]})
                for k in ("deadline", "posted", "deadline_note"):
                    if not hit.get(k) and j.get(k):
                        hit[k] = j[k]
                if len(j["title"]) > len(hit["title"]) and j["source"] not in ("사람인", "잡코리아"):
                    hit["title"] = j["title"]
            else:
                j = dict(j)
                j["_nt"] = nt
                j["company"] = canon_company(j["company"]) or j["company"]
                j["sources"] = [{"name": j["source"], "url": j["url"]}]
                merged.append(j)
        out.extend(merged)
    for j in out:
        j.pop("_nt", None)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--from-cache", action="store_true", help="다시 긁지 않고 지난 수집 원본으로 분류/대시보드만 다시 만들기")
    args = ap.parse_args()

    names = args.only or list(ALL_SOURCES)
    if args.no_browser:
        names = [n for n in names if n not in BROWSER_SOURCES]

    status = []
    raw = []
    raw_cache = DATA / "raw.json"
    if args.from_cache and raw_cache.exists():
        cached = json.loads(raw_cache.read_text(encoding="utf-8"))
        raw, status = cached["raw"], cached["status"]
        names = []
    for name in names:
        t0 = time.time()
        try:
            got = ALL_SOURCES[name]()
            raw.extend(j.to_dict() for j in got)
            status.append({"name": name, "ok": True, "fetched": len(got), "sec": round(time.time() - t0, 1)})
            print(f"[OK] {name}: {len(got)}건 ({time.time() - t0:.0f}s)", flush=True)
        except Exception as e:
            status.append({"name": name, "ok": False, "error": f"{type(e).__name__}: {e}"[:200], "fetched": 0,
                           "sec": round(time.time() - t0, 1)})
            print(f"[ERR] {name}: {e}", flush=True)
            traceback.print_exc(limit=2)

    if names:
        raw_cache.write_text(json.dumps({"raw": raw, "status": status}, ensure_ascii=False), encoding="utf-8")

    today = TODAY.isoformat()
    kept = []
    for j in raw:
        intern = j["intern"] or is_intern(j["title"]) or (
            # 고용형태 칸에만 '인턴'이 있고 제목은 경력직/정직원이면 제외
            is_intern(j["extra"]) and not NOT_INTERN_TITLE.search(j["title"]))
        if not intern:
            continue
        cat = classify(j["company"], j["title"], SOURCE_HINT.get(j["source"]))
        if not cat:
            continue
        if j["deadline"] and j["deadline"] < today:
            continue
        if CLOSED_RE.search(j["title"]):
            continue
        j["category"] = cat
        kept.append(j)

    jobs = merge(kept)

    # 처음 발견한 날짜 기록
    prev = {}
    if STORE.exists():
        try:
            for p in json.loads(STORE.read_text(encoding="utf-8")).get("jobs", []):
                for s in p.get("sources", []):
                    prev[s["url"]] = p.get("first_seen")
        except Exception:
            pass
    # 맨 처음 실행 때 잡힌 공고는 '새 공고'가 아니라 기준선이므로 NEW에서 뺀다
    baseline = min((v for v in prev.values() if v), default=today)
    cutoff = (TODAY - dt.timedelta(days=3)).isoformat()
    for j in jobs:
        seen = [prev.get(s["url"]) for s in j["sources"] if prev.get(s["url"])]
        j["first_seen"] = min(seen) if seen else today
        found_recently = j["first_seen"] > baseline and j["first_seen"] >= cutoff
        j["is_new"] = found_recently or (j.get("posted") or "") >= cutoff

    for s in status:
        s["kept"] = sum(1 for j in jobs if any(x["name"] == s["name"] for x in j["sources"]))

    payload = {"generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "today": today,
               "status": status, "jobs": jobs}
    STORE.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    out = render(payload, ROOT / "dashboard.html")
    print(f"\n수집 {len(raw)}건 → 금융 인턴 {len(kept)}건 → 중복 병합 후 {len(jobs)}건")
    print(f"대시보드: {out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
