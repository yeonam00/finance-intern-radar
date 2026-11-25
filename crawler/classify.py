"""공고 분류: 인턴 여부 + 금융 분야 카테고리."""
import re

# 카테고리 표시 순서 (대시보드에서도 이 순서로 보여줌)
CATEGORIES = [
    "PE",
    "VC",
    "자산운용",
    "증권·IB",
    "컨설팅",
    "회계법인·FAS",
    "신용평가",
    "외국계 금융",
    "정책금융·공공",
    "은행·보험·기타",
]

INTERN_RE = re.compile(
    r"인턴|\bintern(ship)?s?\b|체험형|research\s*assistant|\bRA\b|summer\s*analyst|winter\s*analyst|"
    r"off[\s-]?cycle|student\s*researcher|spring\s*week|insight\s*program|"
    r"\bBA\s*인턴|리서치\s*어시스턴트|연구\s*보조",
    re.I,
)

# 인턴처럼 보이지만 실제로는 아닌 것
NOT_INTERN_RE = re.compile(r"인턴십\s*(설명회|박람회)|인턴\s*출신|인턴\s*경력\s*우대", re.I)
# RA가 Regulatory Affairs(인허가)인 경우
RA_REGULATORY = re.compile(r"Regulatory|인허가|의료\s*기기|의료\s*진단|임상|제약|바이오\s*의약|식약처|\bQA\b", re.I)

CREDIT = re.compile(
    r"신용평가|한국기업평가|한기평|한신평|NICE\s*신용|나이스신용|서울신용평가|이크레더블|"
    r"채권평가|KIS\s*자산평가|한국자산평가|FN\s*자산평가|NICE\s*P&I|나이스피앤아이|"
    r"Moody|무디스|S&P\s*Global|Fitch|피치\s*(레이팅|ratings|신용)",
    re.I,
)

ACCOUNTING = re.compile(
    r"회계법인|PwC|삼일|KPMG|삼정|Deloitte|딜로이트|안진|\bEY\b|EY한영|한영회계|Ernst|"
    r"\bFAS\b|Deal\s*Advisory|Deals|재무실사|\bFDD\b|\bValuation\b|밸류에이션|Transaction\s*Services",
    re.I,
)

CONSULTING_FIRMS = re.compile(
    r"McKinsey|맥킨지|\bBCG\b|Boston\s*Consulting|보스턴\s*컨설팅|Bain\s*&\s*Company|베인앤드?컴퍼니|"
    r"Kearney|에이티\s*커니|AT\s*커니|커니\s*코리아|Oliver\s*Wyman|올리버\s*와이만|Roland\s*Berger|롤랜드\s*버거|Strategy&|"
    r"L\.?E\.?K\.?\s*Consulting|Arthur\s*D\.?\s*Little|\bADL\b|Accenture\s*Strategy|"
    r"Parthenon|파르테논|Simon[\s-]*Kucher|Alvarez|AlixPartners|FTI\s*Consulting",
    re.I,
)
CONSULTING_TITLE = re.compile(r"전략\s*컨설팅|경영\s*컨설팅|Strategy\s*Consult|Management\s*Consult|M&A\s*컨설팅|재무\s*컨설팅", re.I)

FOREIGN = re.compile(
    r"Goldman|골드만|Morgan\s*Stanley|모건\s*스탠리|J\.?\s*P\.?\s*Morgan|JP모간|제이피모간|\bCiti\b|Citibank|^씨티|한국씨티|씨티은행|씨티그룹|씨티글로벌|"
    r"Bank\s*of\s*America|BofA|뱅크오브아메리카|Deutsche|도이치|\bUBS\b|HSBC|Standard\s*Chartered|SC제일|스탠다드차타드|"
    r"Macquarie|맥쿼리|Nomura|노무라|BNP|Soci[eé]t[eé]\s*G[eé]n[eé]rale|소시에테|\bING\b|아이엔지|Natixis|나티시스|"
    r"CLSA|Barclays|바클레이즈|Cr[eé]dit\s*Agricole|크레디아그리콜|Mizuho|미즈호|MUFG|SMBC|미쓰비시\s*UFJ|Jefferies|"
    r"Lazard|라자드|Rothschild|로스차일드|PIMCO|핌코|BlackRock|블랙록|KKR|Carlyle|칼라일|Blackstone|블랙스톤|"
    r"Affinity|어피니티|Bain\s*Capital|베인캐피탈|Brookfield|브룩필드|Apollo|아폴로|TPG|Warburg|Hillhouse|힐하우스|"
    r"Fidelity|피델리티|Schroders|슈로더|Invesco|인베스코|Franklin|프랭클린|AllianceBernstein|얼라이언스번스틴|"
    r"Nuveen|누빈|Manulife|매뉴라이프|State\s*Street|스테이트\s*스트리트|Northern\s*Trust|Wellington\s*Management|"
    r"CVC\s*Capital|Permira|Hahn\s*&\s*Co|Partners\s*Group|Hamilton\s*Lane|Temasek|테마섹|CPPIB|"
    r"Natwest|Credit\s*Suisse|Daiwa|다이와|Evercore|Moelis|Houlihan|ICG|Intermediate\s*Capital|"
    # 짧은 약어는 대소문자 구분 + 단어 경계 (Strategic 안의 GIC 같은 오탐 방지)
    r"(?-i:\b(?:GIC|EQT|TPG|ANZ|DBS|SBI|BNY|Ares|BNP|ING|UBS|KKR|CLSA|MUFG|SMBC|BofA)\b)",
    re.I,
)

PE = re.compile(
    r"프라이빗\s*에쿼티|private\s*equity|사모\s*펀드|사모투자|(?<![A-Za-z])PE(?![A-Za-z])|바이아웃|buy[\s-]?out|"
    r"MBK|한앤컴퍼니|한앤코|IMM\s*(PE|프라이빗|인베스트)|스틱인베스트|VIG\s*파트너스|어펄마|글랜우드|스카이레이크|"
    r"프랙시스|JKL|큐캐피탈|유니슨캐피탈|헬리오스|키스톤|오퍼스|웰투시|케이스톤|LB\s*프라이빗|파인트리|"
    r"H&Q|에이치엔큐|어센트|이음\s*PE|노틱|SG\s*PE|도미누스|센트로이드|E&F|이앤에프|프리미어파트너스|"
    r"코스톤|원익투자|스톤브릿지",
    re.I,
)

VC = re.compile(
    r"벤처\s*캐피탈|벤처캐피털|벤처\s*투자|창업\s*투자|창투|인베스트먼트|investment|ventures?\b|벤처스|"
    r"액셀러레이터|accelerator|투자\s*심사|심사역|신기술\s*사업|신기술사업금융|기술지주|(?<![A-Za-z])VC(?![A-Za-z])|CVC|"
    r"투자\s*파트너스|임팩트\s*투자|스타트업\s*투자|시드\s*투자|디캠프|D\.?CAMP|퓨처플레이|스파크랩|프라이머(?!리)|매쉬업|"
    r"카카오벤처스|본엔젤스|알토스|소프트뱅크벤처스|KB인베스트|한국투자파트너스|에이티넘|(?-i:\bDSC\b)|LB인베스트|"
    r"캡스톤|컴퍼니케이|IMM인베스트|SV인베스트|대성창투|TS인베스트|우리벤처|NH벤처|하나벤처스|신한벤처",
    re.I,
)

ASSET_MGMT = re.compile(
    r"자산\s*운용|운용사|asset\s*management|asset\s*mgmt|투자\s*자문|\bAMC\b|(?<![가-힣])리츠|\bREITs?\b|자산\s*신탁|"
    r"대체\s*투자|alternative\s*invest|펀드\s*매니저|fund\s*manag|포트폴리오\s*매니저|portfolio\s*manag|"
    r"주식\s*운용|채권\s*운용|퀀트",
    re.I,
)

SECURITIES = re.compile(
    r"증권|securities|금융\s*투자|(?<![A-Za-z])IB(?![A-Za-z])|investment\s*bank|기업\s*금융|M&A|\bECM\b|\bDCM\b|"
    r"리서치\s*센터|애널리스트|analyst|capital\s*markets|global\s*markets|sales\s*&\s*trading|트레이딩",
    re.I,
)

PUBLIC = re.compile(
    r"산업은행|KDB|수출입은행|기업은행|IBK\s*기업|한국투자공사|\bKIC\b|국민연금|기금운용|한국벤처투자|KVIC|한국성장금융|"
    r"예금보험|주택금융|신용보증|기술보증|신용보증기금|기술보증기금|자산관리공사|캠코|KAMCO|한국거래소|KRX|"
    r"예탁결제원|증권금융|금융감독원|금감원|한국은행|공무원연금|사학연금|교직원공제|군인공제|행정공제|"
    r"서민금융|금융결제원|국제금융센터|코스콤|한국자산관리|농업정책보험금융원|중소벤처기업진흥|무역보험|"
    r"한국벤처캐피탈협회|금융투자협회|여신금융협회|은행연합회|생명보험협회|손해보험협회|보험개발원|신용정보원",
    re.I,
)

OTHER_FIN = re.compile(
    r"은행|(?<![A-Za-z])bank(?![A-Za-z])|카카오뱅크|토스뱅크|케이뱅크|보험|생명(?!공학|과학|연구)|손해|화재|(?<!명함)카드|캐피탈|capital|저축은행|금융|finance|financial|"
    r"신탁|금융\s*지주|핀테크|fintech|페이먼츠|자산\s*관리|wealth|PB\s*(센터|팀|사업)|프라이빗\s*뱅킹",
    re.I,
)

# 금융처럼 보이지만 아닌 회사/공고 (오탐 방지)
EXCLUDE = re.compile(
    r"보험\s*설계|설계사|보험\s*영업|텔레마케|TM\s*상담|콜센터|상담원|채권\s*추심|대출\s*상담|"
    r"헤드헌터|HR\s*컨설턴트|커리어\s*컨설턴트|인재\s*컨설턴트|분양|부동산\s*중개|공인중개|"
    r"카드\s*뉴스|명함|보안\s*요원|경비|미화|운전|배송|물류센터|생산직|판매직|매장|병원\s*영업|의료\s*소모품|건강보험공단|병원|수련생|아카데미|부트캠프|교육생\s*모집",
    re.I,
)


def is_intern(*texts: str) -> bool:
    t = " ".join(x for x in texts if x)
    if NOT_INTERN_RE.search(t):
        return False
    m = INTERN_RE.search(t)
    if not m:
        return False
    # 'RA' 하나로만 걸렸는데 인허가(Regulatory Affairs) 공고면 제외
    hits = {x.group(0).lower() for x in INTERN_RE.finditer(t)}
    if hits <= {"ra"} and RA_REGULATORY.search(t):
        return False
    return True


def classify(company: str, title: str, hint: str | None = None) -> str | None:
    """회사명/제목으로 카테고리 판정. 해당 없으면 None (= 관심 분야 아님).

    hint: 소스 자체가 특정 분야인 경우(예: VCS=VC, KOFIA=증권·운용) 기본값.
    """
    company = company or ""
    title = title or ""
    both = f"{company} {title}"

    if EXCLUDE.search(both):
        return None

    if CREDIT.search(both):
        return "신용평가"
    if CONSULTING_FIRMS.search(company) or CONSULTING_FIRMS.search(title):
        return "컨설팅"
    if ACCOUNTING.search(company) or (re.search(r"회계법인", both)):
        return "회계법인·FAS"
    if re.search(r"증권|securities|금융투자", company, re.I) and not re.search(r"증권금융|증권거래소", company):
        return "증권·IB"
    if PUBLIC.search(company):
        return "정책금융·공공"
    if FOREIGN.search(company) or (FOREIGN.search(title) and re.search(r"Korea|Seoul|서울|한국", both, re.I)):
        return "외국계 금융"
    if PE.search(both):
        return "PE"
    if ASSET_MGMT.search(company):
        return "자산운용"
    if re.search(r"증권|securities|금융투자", company, re.I):
        return "증권·IB"
    if VC.search(company):
        return "VC"
    # 회사명으로 못 정하면 제목으로
    if ASSET_MGMT.search(title) and not re.search(r"자산\s*관리\s*(시스템|솔루션)", title):
        return "자산운용"
    if re.search(r"투자\s*심사|심사역|벤처\s*캐피탈|(?<![A-Za-z])VC(?![A-Za-z])|액셀러레이터", title, re.I):
        return "VC"
    if CONSULTING_TITLE.search(title) or (re.search(r"컨설팅", company) and re.search(r"전략|경영|M&A|재무", title)
                                          and not RA_REGULATORY.search(title)):
        return "컨설팅"
    if ACCOUNTING.search(title) and re.search(r"Deal|FAS|실사|\bValuation\b|밸류|M&A|Transaction", title, re.I):
        return "회계법인·FAS"
    if re.search(r"(?<![A-Za-z])IB(?![A-Za-z])|investment\s*bank|M&A|\bECM\b|\bDCM\b|리서치\s*센터|기업\s*금융", title, re.I):
        return "증권·IB"
    if PUBLIC.search(title):
        return "정책금융·공공"
    if OTHER_FIN.search(company):
        return "은행·보험·기타"
    if hint:
        return hint
    return None
