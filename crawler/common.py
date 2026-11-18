import re
import time
import datetime as dt
from dataclasses import dataclass, field, asdict

import requests
import urllib3

urllib3.disable_warnings()

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"}

TODAY = dt.date.today()

session = requests.Session()
session.headers.update(HEADERS)


def _request(method, url, **kw):
    kw.setdefault("timeout", 25)
    kw.setdefault("verify", False)
    last = None
    for attempt in range(4):
        try:
            r = session.request(method, url, **kw)
            if r.status_code in (429, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
            r.raise_for_status()
            if r.encoding in (None, "ISO-8859-1"):
                r.encoding = r.apparent_encoding
            time.sleep(0.5)  # 서버 부담 줄이기
            return r
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
            last = e
            if isinstance(e, requests.HTTPError) and e.response is not None and e.response.status_code < 429:
                raise
            time.sleep(3 * (attempt + 1))  # 연결이 끊기면 잠깐 쉬었다가 재시도
    raise last


def get(url, **kw):
    return _request("GET", url, **kw)


def post(url, **kw):
    return _request("POST", url, **kw)


@dataclass
class Job:
    source: str
    company: str
    title: str
    url: str
    deadline: str | None = None  # YYYY-MM-DD, None = 상시/미기재
    deadline_note: str | None = None  # "상시", "채용시 마감" 등
    posted: str | None = None  # YYYY-MM-DD
    intern: bool = True
    category: str | None = None
    extra: str = ""  # 분류에 쓰는 부가 텍스트 (직무, 고용형태 등)
    sources: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def iso(d: dt.date | dt.datetime | None):
    if d is None:
        return None
    if isinstance(d, dt.datetime):
        d = d.date()
    return d.isoformat()


def infer_year(month: int, day: int, ref: dt.date = TODAY, future=True) -> dt.date | None:
    """'11/19' 같은 월/일만 있을 때 연도 추정. future=True면 마감일(앞으로)로 간주."""
    try:
        d = dt.date(ref.year, month, day)
    except ValueError:
        return None
    if future and d < ref - dt.timedelta(days=60):
        d = dt.date(ref.year + 1, month, day)
    if not future and d > ref + dt.timedelta(days=7):
        d = dt.date(ref.year - 1, month, day)
    return d


def parse_date(s: str | None, future=True) -> dt.date | None:
    """여러 형식의 날짜 문자열을 date로."""
    if not s:
        return None
    s = s.strip()
    m = re.search(r"(20\d{2})[.\-/년 ]\s*(\d{1,2})[.\-/월 ]\s*(\d{1,2})", s)
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.search(r"(?<!\d)(\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})(?!\d)", s)
    if m:
        try:
            return dt.date(2000 + int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.search(r"(?<!\d)(\d{1,2})\s*[./월]\s*(\d{1,2})", s)
    if m:
        return infer_year(int(m.group(1)), int(m.group(2)), future=future)
    m = re.search(r"D\s*-\s*(\d+)", s)
    if m:
        return TODAY + dt.timedelta(days=int(m.group(1)))
    return None


def deadline_from_title(title: str) -> dt.date | None:
    """제목 속 '(~11/22)', '~11.30', '(11/15 마감)' 같은 표기에서 마감일 추출."""
    m = re.search(r"~\s*(\d{1,2})\s*[./월]\s*(\d{1,2})", title) or re.search(
        r"(\d{1,2})\s*[./]\s*(\d{1,2})\s*(\([^)]*\))?\s*(까지|마감)", title
    )
    if m:
        return infer_year(int(m.group(1)), int(m.group(2)))
    return None
