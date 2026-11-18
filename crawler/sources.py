"""사이트별 수집기. 각 함수는 list[Job]을 반환한다.

인턴 여부/분야 분류는 run.py에서 공통으로 처리하고,
여기서는 사이트가 주는 구조화된 정보(고용형태 등)만 extra/intern에 담는다.
"""
import json
import re
import datetime as dt
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup

from .common import Job, get, post, clean, iso, parse_date, deadline_from_title, TODAY, UA

# 키워드 검색형 사이트에서 돌릴 검색어
FIN_QUERIES = [
    "증권 인턴", "자산운용 인턴", "운용 인턴", "투자 인턴", "벤처캐피탈 인턴", "VC 인턴",
    "PE 인턴", "사모펀드 인턴", "투자심사 인턴", "컨설팅 인턴", "회계법인 인턴",
    "신용평가 인턴", "금융 인턴", "은행 인턴", "IB 인턴", "리서치 인턴", "RA 인턴",
    "M&A 인턴", "체험형 인턴 금융", "캐피탈 인턴",
    "FAS 인턴", "재무자문 인턴", "회계법인 RA", "실사 인턴", "Valuation 인턴", "Deal Advisory",
]


# ---------------------------------------------------------------- 링커리어
def linkareer(max_pages=80):
    jobs = []
    page = 1
    total_pages = None
    while page <= max_pages:
        r = get(f"https://linkareer.com/list/intern?page={page}")
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
        if not m:
            break
        ap = json.loads(m.group(1))["props"]["pageProps"]["__APOLLO_STATE__"]
        root = ap.get("ROOT_QUERY", {})
        conn = next((v for k, v in root.items() if k.startswith("activities(")), None)
        if not conn:
            break
        if total_pages is None:
            total_pages = (conn.get("totalCount", 0) + 19) // 20
        nodes = conn.get("nodes", [])
        if not nodes:
            break
        for ref in nodes:
            a = ap.get(ref["__ref"], {})
            cats = [ap.get(c["__ref"], {}).get("name", "") for c in a.get("categories", []) if "__ref" in c]
            close = a.get("recruitCloseAt")
            dl = dt.datetime.fromtimestamp(close / 1000).date() if close else None
            note = "상시" if a.get("recruitType") == "ALWAYS" else None
            if note and dl and (dl - TODAY).days > 300:
                dl = None
            jobs.append(Job(
                source="링커리어", company=clean(a.get("organizationName")), title=clean(a.get("title")),
                url=f"https://linkareer.com/activity/{a.get('id')}", deadline=iso(dl), deadline_note=note,
                intern=True, extra=" ".join(cats),
            ))
        page += 1
        if total_pages and page > total_pages:
            break
    return jobs


# ---------------------------------------------------------------- 자소설닷컴
def jasoseol():
    start = (TODAY - dt.timedelta(days=90)).isoformat()
    end = (TODAY + dt.timedelta(days=120)).isoformat()
    r = post("https://jasoseol.com/employment/calendar_list.json",
             json={"start_time": f"{start}T00:00:00.000Z", "end_time": f"{end}T00:00:00.000Z"})
    jobs = []
    for e in r.json().get("employment", []):
        end_t = (e.get("end_time") or "")[:10]
        if end_t and end_t < TODAY.isoformat():
            continue
        divs = {x.get("division") for x in e.get("employments", [])}
        jobs.append(Job(
            source="자소설닷컴", company=clean(e.get("name")), title=clean(e.get("title")),
            url=f"https://jasoseol.com/recruit/{e.get('id')}", deadline=end_t or None,
            posted=(e.get("start_time") or "")[:10] or None,
            intern=3 in divs, extra=e.get("business_type") or "",
        ))
    return jobs


# ---------------------------------------------------------------- 캐치
def catch():
    jobs, seen = [], set()
    for kw in ["인턴", "intern", "체험형", "RA"]:
        page = 1
        while page <= 10:
            r = get("https://www.catch.co.kr/api/v1.0/recruit/information/getRecruitList",
                    params={"Keyword": kw, "Sort": 0, "curpage": page, "pageSize": 100, "onRecruitYN": "Y"})
            d = r.json()
            data = d.get("recruitData") or []
            for x in data:
                rid = x.get("RecruitID")
                if rid in seen:
                    continue
                seen.add(rid)
                end = (x.get("ApplyEndDatetime") or "")
                dl = None
                if end:
                    dl = (dt.datetime.fromisoformat(end.replace("Z", "+00:00")) + dt.timedelta(hours=9)).date()
                note = x.get("ApplyEndCode") if x.get("ApplyEndCode") in ("채용시 마감", "상시채용") else None
                if note and dl and (dl - TODAY).days > 300:
                    dl = None
                jobs.append(Job(
                    source="캐치", company=clean(x.get("CompName")), title=clean(x.get("RecruitTitle")),
                    url=f"https://www.catch.co.kr/NCS/RecruitInfoDetails/{rid}", deadline=iso(dl), deadline_note=note,
                    posted=iso((dt.datetime.fromisoformat(x["ApplyStartDatetime"].replace("Z", "+00:00"))
                                + dt.timedelta(hours=9)).date()) if x.get("ApplyStartDatetime") else None,  # UTC→KST
                    intern="인턴" in (x.get("GubunCode") or ""),
                    extra=" ".join(filter(None, [x.get("GubunCode"), x.get("Depth"), x.get("RecruitCategory")])),
                ))
            if len(data) < 100:
                break
            page += 1
    return jobs


# ---------------------------------------------------------------- 원티드
def wanted():
    queries = ["투자 인턴", "심사역", "VC", "벤처캐피탈", "자산운용", "증권", "PE", "사모펀드",
               "컨설팅 인턴", "금융 인턴", "Research Assistant", "M&A", "투자", "IB", "회계법인"]
    jobs, seen = [], set()
    for q in queries:
        offset = 0
        while offset < 200:
            r = get("https://www.wanted.co.kr/api/chaos/search/v1/position",
                    params={"query": q, "country": "kr", "years": -1, "sort": "job.latest_order",
                            "limit": 20, "offset": offset})
            data = r.json().get("data") or []
            for x in data:
                if x["id"] in seen:
                    continue
                seen.add(x["id"])
                jobs.append(Job(
                    source="원티드", company=clean(x["company"]["name"]), title=clean(x.get("position")),
                    url=f"https://www.wanted.co.kr/wd/{x['id']}", deadline_note="채용시 마감",
                    intern=x.get("employment_type") == "intern", extra=x.get("employment_type") or "",
                ))
            if len(data) < 20:
                break
            offset += 20
    return jobs


# ---------------------------------------------------------------- 사람인
def saramin():
    jobs, seen = [], set()
    for q in FIN_QUERIES:
        r = get("https://www.saramin.co.kr/zf_user/search/recruit",
                params={"searchword": q, "recruitPageCount": 100, "recruitSort": "relation"})
        s = BeautifulSoup(r.text, "lxml")
        for it in s.select(".item_recruit"):
            rid = it.get("value")
            if not rid or rid in seen:
                continue
            seen.add(rid)
            a = it.select_one(".job_tit a")
            corp = it.select_one(".corp_name a") or it.select_one(".corp_name")
            date = clean(it.select_one(".job_date .date").get_text()) if it.select_one(".job_date .date") else ""
            cond = clean(it.select_one(".job_condition").get_text(" ")) if it.select_one(".job_condition") else ""
            sector = clean(it.select_one(".job_sector").get_text(" ")) if it.select_one(".job_sector") else ""
            dl = None if re.search(r"상시|채용시", date) else parse_date(date)
            jobs.append(Job(
                source="사람인", company=clean(corp.get_text()) if corp else "", title=clean(a.get("title") or a.get_text()),
                url=f"https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx={rid}",
                deadline=iso(dl), deadline_note=date if not dl else None,
                intern=False, extra=f"{cond} {sector}",
            ))
    return jobs


# ---------------------------------------------------------------- 잡코리아
def jobkorea():
    jobs, seen = [], set()
    for q in FIN_QUERIES:
        r = get(f"https://www.jobkorea.co.kr/Search/?stext={quote(q)}&tabType=recruit")
        s = BeautifulSoup(r.text, "lxml")
        for card in s.select('[data-sentry-component="CardJob"]'):
            links = [a for a in card.select('a[href*="/Recruit/GI_Read/"]') if clean(a.get_text())]
            if not links:
                continue
            href = links[0]["href"]
            m = re.search(r"GI_Read/(\d+)", href)
            if not m or m.group(1) in seen:
                continue
            seen.add(m.group(1))
            title = clean(links[0].get_text())
            logo = card.select_one("img[alt$='로고']")
            company = clean(logo["alt"][:-2]) if logo else ""
            if not company and len(links) > 1:
                company = clean(links[1].get_text())
            text = clean(card.get_text(" | "))
            dl = None
            mm = re.search(r"~\s*(\d{1,2})/(\d{1,2})", text)
            if mm:
                dl = parse_date(f"{mm.group(1)}/{mm.group(2)}")
            jobs.append(Job(
                source="잡코리아", company=company, title=title,
                url=f"https://www.jobkorea.co.kr/Recruit/GI_Read/{m.group(1)}",
                deadline=iso(dl), deadline_note=None if dl else ("상시" if "상시" in text else None),
                intern=False, extra=text[:300],
            ))
    return jobs


# ---------------------------------------------------------------- 피플앤잡
def peoplenjob(pages=6):
    jobs, seen = [], set()
    for q in ["인턴", "intern", "internship", "RA"]:
        for p in range(1, pages + 1):
            r = get("https://www.peoplenjob.com/jobs", params={"field": "all", "q": q, "page": p})
            s = BeautifulSoup(r.text, "lxml")
            cards = s.select(".jd-card")
            if not cards:
                break
            for c in cards:
                a = c.select_one(".jd-card-title a")
                if not a:
                    continue
                m = re.search(r"/jobs/(\d+)", a["href"])
                if not m or m.group(1) in seen:
                    continue
                seen.add(m.group(1))
                comp = c.select_one(".jd-card-company")
                fin = c.select_one(".job-fin-date")
                meta = clean(c.select_one(".jd-card-meta").get_text(" ")) if c.select_one(".jd-card-meta") else ""
                start = re.search(r"(\d{1,2})\.(\d{1,2})\s*~", meta)
                dl = parse_date(fin.get_text()) if fin else None
                jobs.append(Job(
                    source="피플앤잡", company=clean(comp.get_text()) if comp else "", title=clean(a.get_text()),
                    url=f"https://www.peoplenjob.com/jobs/{m.group(1)}", deadline=iso(dl),
                    posted=iso(parse_date(f"{start.group(1)}/{start.group(2)}", future=False)) if start else None,
                    intern=False, extra=meta,
                ))
    return jobs


# ---------------------------------------------------------------- 잡알리오 (공공기관)
def alio(max_pages=15):
    jobs = []
    for page in range(1, max_pages + 1):
        data = {
            "pageNo": page, "s_date": (TODAY - dt.timedelta(days=120)).strftime("%Y.%m.%d"),
            "e_date": TODAY.strftime("%Y.%m.%d"), "work_type": ["R1060", "R1070"], "ing": "2",
        }
        r = post("https://job.alio.go.kr/recruit.do", data=data)
        r.encoding = "utf-8"
        s = BeautifulSoup(r.text, "lxml")
        tbl = s.select_one("table.tbl.type_03")
        rows = tbl.select("tbody tr") if tbl else []
        got = 0
        for tr in rows:
            td = tr.find_all("td")
            if len(td) < 8:
                continue
            a = td[2].find("a")
            m = re.search(r"idx=(\d+)", a["href"]) if a else None
            if not m:
                continue
            got += 1
            jobs.append(Job(
                source="잡알리오", company=clean(td[3].get_text()), title=clean(td[2].get_text()),
                url=f"https://job.alio.go.kr/recruitview.do?idx={m.group(1)}",
                deadline=iso(parse_date(td[7].get_text())), posted=iso(parse_date(td[6].get_text(), future=False)),
                intern=True, extra=clean(td[5].get_text()),
            ))
        if got == 0:
            break
    return jobs


# ---------------------------------------------------------------- 벤처투자종합포털 (KVCA 채용게시판 포함)
def vcs_company(title):
    """'[퓨처플레이]재무…', '(주)리젠트파트너스 투자팀…', '프리미어파트너스(유) BIO본부…' → 회사명"""
    t = title.strip()
    m = re.match(r"^\[([^\]]+)\]", t)
    if m:
        name = m.group(1)
    else:
        t2 = re.sub(r"^\s*(\(주\)|㈜|\(유\)|주식회사)\s*", "", t)
        name = t2.split()[0] if t2.split() else ""
    name = re.sub(r"\((주|유|유한|합자)\)?|㈜|주식회사|유한회사", "", name)
    name = re.split(r"[(\[]", name)[0]
    return clean(name)


def vcs(max_pages=10):
    jobs = []
    cutoff = TODAY - dt.timedelta(days=75)
    for page in range(1, max_pages + 1):
        r = get("https://www.vcs.go.kr/web/portal/recruitment/list",
                params={"cp": page, "pageSize": 50, "sortOrder": "REG_DDTM", "sortDirection": "DESC", "tabCode": "all"})
        s = BeautifulSoup(r.text, "lxml")
        items = s.select(".tbl_box_list li")
        stop = False
        for li in items:
            a = li.find("a", href=True)
            tit = li.select_one(".tit")
            if not a or not tit:
                continue
            title = clean(re.sub(r"NEW|&nbsp;?|\xa0", " ", tit.get_text(" ")))
            dd = li.select_one(".employment_status .date")
            regs = [clean(x.get_text()) for x in li.select(".post_info dd")]
            posted = parse_date(regs[0], future=False) if regs else None
            if posted and posted < cutoff:
                stop = True
                continue
            company = vcs_company(title)
            jobs.append(Job(
                source="벤처투자포털", company=company, title=title,
                url=urljoin("https://www.vcs.go.kr", a["href"].split("?")[0]),
                deadline=iso(parse_date(dd.get_text())) if dd else None, posted=iso(posted),
                intern=False, extra="VC 투자사",
            ))
        if stop or not items:
            break
    return jobs


# ---------------------------------------------------------------- 금융투자협회 채용게시판
def kofia(max_pages=8):
    jobs, seen = [], set()
    cutoff = TODAY - dt.timedelta(days=60)
    for word in ["인턴", "RA", "체험형", "Intern"]:
        for page in range(1, max_pages + 1):
            r = get("https://www.kofia.or.kr/brd/m_96/list.do",
                    params={"page": page, "srchWord": word, "srchTp": "0"})
            s = BeautifulSoup(r.text, "lxml")
            rows = s.select("table tbody tr")
            stop = False
            for tr in rows:
                td = tr.find_all("td")
                if len(td) < 5:
                    continue
                a = tr.find("a", href=True)
                m = re.search(r"seq=(\d+)", a["href"]) if a else None
                if not m:
                    continue
                posted = parse_date(td[-1].get_text(), future=False)
                if posted and posted < cutoff:
                    stop = True
                    continue
                if m.group(1) in seen:
                    continue
                seen.add(m.group(1))
                title = clean(td[2].get_text())
                dl = deadline_from_title(title)
                jobs.append(Job(
                    source="금융투자협회", company=clean(td[1].get_text()), title=title,
                    url=f"https://www.kofia.or.kr/brd/m_96/view.do?seq={m.group(1)}",
                    deadline=iso(dl), posted=iso(posted), intern=False, extra="금융투자회사",
                ))
            if stop or not rows:
                break
    return jobs


# ---------------------------------------------------------------- 고려대 경영대 CDC
def korea_univ(max_pages=12):
    jobs = []
    cutoff = TODAY - dt.timedelta(days=75)
    for page in range(1, max_pages + 1):
        r = get("https://biz.korea.ac.kr/cdc/recruitment/recruitment.html", params={"page": page})
        s = BeautifulSoup(r.text, "lxml")
        conts = s.select(".rec_grid .cont")
        stop = False
        for c in conts:
            a = c.find("a", href=True)
            m = re.search(r"no=(\d+)", a["href"]) if a else None
            if not m:
                continue
            info = {}
            for li in c.select(".context li"):
                lab = li.select_one(".tit_label")
                if lab:
                    info[clean(lab.get_text()).rstrip(":")] = clean(li.get_text().replace(lab.get_text(), ""))
            date = c.select_one(".info .date")
            posted = parse_date(date.get_text(), future=False) if date else None
            if posted and posted < cutoff:
                stop = True
                continue
            if "마감" in info.get("채용마감 여부", "") and "진행" not in info.get("채용마감 여부", ""):
                continue
            title = clean(c.select_one(".tit").get_text()) if c.select_one(".tit") else ""
            dl_txt = info.get("채용마감일", "")
            dl = parse_date(dl_txt) if re.search(r"\d", dl_txt) else None
            jobs.append(Job(
                source="고려대 경영CDC", company=info.get("회사명", ""), title=title,
                url=f"https://biz.korea.ac.kr/cdc/recruitment/recruitment_view.html?no={m.group(1)}",
                deadline=iso(dl), deadline_note=None if dl else (dl_txt or None), posted=iso(posted),
                intern="인턴" in info.get("채용구분", ""),
                extra=f"{info.get('모집부문', '')} {info.get('채용구분', '')}",
            ))
        if stop or not conts:
            break
    return jobs


# ---------------------------------------------------------------- 브라우저 렌더링이 필요한 사이트들
def _browser_pages(targets):
    """targets: [(name, url, href_regex, keep_regex|None)] → {name: [(title, href)]}"""
    from playwright.sync_api import sync_playwright

    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(locale="ko-KR", user_agent=UA)
        for name, url, pat, keep in targets:
            pg = ctx.new_page()
            try:
                pg.goto(url, timeout=45000, wait_until="domcontentloaded")
                pg.wait_for_timeout(6000)
                for _ in range(3):
                    pg.mouse.wheel(0, 4000)
                    pg.wait_for_timeout(1200)
                links = pg.eval_on_selector_all(
                    "a[href]", "els=>els.map(e=>[e.href,(e.innerText||'').trim()])")
                res = []
                for href, text in links:
                    if re.search(pat, href) and text and (keep is None or re.search(keep, text + href, re.I)):
                        res.append((clean(text), href))
                out[name] = res
            except Exception as e:  # noqa
                out[name] = e
            finally:
                pg.close()
        b.close()
    return out


def superookie(max_pages=8):
    """슈퍼루키: 브라우저로 목록 페이지를 열고 화면에 렌더링된 카드를 읽는다."""
    from playwright.sync_api import sync_playwright

    jobs, seen = [], set()
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(locale="ko-KR", user_agent=UA)
        pg = ctx.new_page()
        for page in range(1, max_pages + 1):
            pg.goto(f"https://www.superookie.com/jobs?page={page}", timeout=45000, wait_until="domcontentloaded")
            pg.wait_for_timeout(4500)
            links = pg.eval_on_selector_all("a[href*='/jobs/']", "els=>els.map(e=>[e.href,(e.innerText||'').trim()])")
            new = 0
            for href, text in links:
                m = re.search(r"/jobs/([0-9a-f]{12,})", href)
                if not m or m.group(1) in seen or not text:
                    continue
                seen.add(m.group(1))
                new += 1
                lines = [clean(x) for x in text.split("\n") if clean(x)]
                company = lines[0] if lines else ""
                title = lines[1] if len(lines) > 1 else company
                rest = " ".join(lines[2:])
                dl = None
                mm = re.search(r"(\d{1,2})/(\d{1,2})\s*[\d:]*\s*마감", rest)
                if mm:
                    dl = parse_date(f"{mm.group(1)}/{mm.group(2)}")
                jobs.append(Job(source="슈퍼루키", company=company, title=title, url=href.split("?")[0],
                                deadline=iso(dl), deadline_note="채용시 마감" if "채용시" in rest else None,
                                intern="인턴" in rest, extra=rest[:200]))
            if new == 0:
                break
        b.close()
    return jobs


def foreign_direct():
    """외국계 회사 채용 페이지 직접 확인 (서울/한국 공고)."""
    targets = [
        ("Citi", "https://jobs.citi.com/search-jobs/Seoul", r"jobs\.citi\.com/job/", None),
        ("BlackRock", "https://careers.blackrock.com/search-jobs/Seoul", r"/job/", r"seoul|korea"),
        ("BCG", "https://careers.bcg.com/global/en/search-results?keywords=Korea", r"/job/\d+", r"korea|seoul"),
        ("BCG", "https://careers.bcg.com/global/en/search-results?keywords=Seoul", r"/job/\d+", None),
        ("Bain & Company", "https://www.bain.com/careers/find-a-role/?filters=offices(275)", r"jobid=", r"seoul"),
        ("Macquarie", "https://recruitment.macquarie.com/en_US/careers/SearchJobs/?listFilterMode=1&jobRecordsPerPage=50&keywords=Seoul",
         r"JobDetail\?jobId=", r"seoul|korea"),
    ]
    jobs, seen = [], set()
    res = _browser_pages(targets)
    errors = []
    for name, links in res.items():
        if isinstance(links, Exception):
            errors.append(f"{name}: {links}")
            continue
        for text, href in links:
            key = href.split("?")[0] if "jobId" not in href and "jobid" not in href else href
            if key in seen or text.lower() in ("view details", "apply", "자세히 보기"):
                continue
            seen.add(key)
            title = re.split(r"\s*Location:", text.split("\n")[0])[0][:160]
            jobs.append(Job(source="회사 채용페이지", company=name, title=title, url=href,
                            intern=False, extra=text.replace("\n", " ")[:300]))
    return jobs


ALL_SOURCES = {
    "링커리어": linkareer,
    "자소설닷컴": jasoseol,
    "캐치": catch,
    "원티드": wanted,
    "사람인": saramin,
    "잡코리아": jobkorea,
    "피플앤잡": peoplenjob,
    "잡알리오": alio,
    "벤처투자포털": vcs,
    "금융투자협회": kofia,
    "고려대 경영CDC": korea_univ,
    "슈퍼루키": superookie,
    "회사 채용페이지": foreign_direct,
}
