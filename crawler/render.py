"""수집 결과 → 단일 HTML 대시보드 (데이터 내장, 오프라인에서도 열림)."""
import json
from pathlib import Path

from .classify import CATEGORIES

# 자동 수집이 안 되거나(로그인/봇 차단) 직접 보는 게 나은 곳
MANUAL_LINKS = [
    ("전략컨설팅", [
        ("McKinsey (Seoul)", "https://www.mckinsey.com/careers/search-jobs?locations=Seoul", "봇 차단"),
        ("Kearney", "https://www.kearney.com/careers", ""),
        ("Oliver Wyman", "https://www.oliverwyman.com/careers.html", ""),
        ("Roland Berger", "https://www.rolandberger.com/en/Join/", ""),
        ("Strategy& (PwC)", "https://www.strategyand.pwc.com/kr/ko/careers.html", ""),
        ("L.E.K. Consulting", "https://www.lek.com/careers", ""),
    ]),
    ("외국계 IB", [
        ("Goldman Sachs (Seoul)", "https://higher.gs.com/results?LOCATION=Seoul", "봇 차단"),
        ("Morgan Stanley (Seoul)", "https://morganstanley.eightfold.ai/careers?location=Seoul", "동적 페이지"),
        ("J.P. Morgan (Seoul)", "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs?location=Seoul%2C+South+Korea", "동적 페이지"),
        ("Bank of America", "https://careers.bankofamerica.com/en-us/job-search?search=getAllJobs&keywords=seoul", "봇 차단"),
        ("Deutsche Bank", "https://careers.db.com/students-graduates/", ""),
        ("UBS", "https://www.ubs.com/global/en/careers/search-jobs.html", ""),
        ("HSBC", "https://mycareer.hsbc.com/en_GB/external/SearchJobs", ""),
        ("Standard Chartered (Korea)", "https://jobs.standardchartered.com/go/Korea/", ""),
        ("Nomura", "https://www.nomuraholdings.com/careers/", ""),
    ]),
    ("신용평가사", [
        ("한국신용평가", "https://www.kisrating.com", "공고는 자소설·링커리어에도 올라옴"),
        ("한국기업평가", "https://www.korearatings.com", ""),
        ("NICE신용평가", "https://www.nicerating.com", ""),
        ("서울신용평가", "https://www.scri.co.kr", ""),
    ]),
    ("Big4 회계법인", [
        ("삼일PwC", "https://www.pwc.com/kr/ko/careers.html", ""),
        ("삼정KPMG", "https://kpmg.com/kr/ko/home/careers.html", ""),
        ("EY한영", "https://www.ey.com/ko_kr/careers", ""),
        ("딜로이트 안진", "https://www.deloitte.com/kr/ko/careers.html", ""),
    ]),
    ("로컬 회계법인 FAS", [
        ("이촌회계법인 채용 (잡코리아)", "https://www.jobkorea.co.kr/company/43182734/recruit", "작년 FAS 인턴 12월 중순 공고"),
        ("Forvis Mazars 새빛 (링커리어 검색)", "https://linkareer.com/search?keyword=%EC%83%88%EB%B9%9B%ED%9A%8C%EA%B3%84%EB%B2%95%EC%9D%B8", "작년 FAS 인턴 9~12월"),
        ("삼덕회계법인 채용 (잡코리아)", "https://www.jobkorea.co.kr/company/46639999/recruit", ""),
        ("대주회계법인 채용 (잡코리아)", "https://www.jobkorea.co.kr/company/46323267/recruit", ""),
        ("한국공인회계사회 구인게시판", "https://www.kicpa.or.kr/home/jobOffrSrchGnrl/list.face", "회계사 게시판은 로그인 필요"),
        ("LinkedIn: FAS / Transaction Advisory (Seoul)", "https://www.linkedin.com/jobs/search/?keywords=Transaction%20Advisory%20OR%20FAS&location=Seoul", "Job Alert 권장"),
    ]),
    ("로그인 필요 / 기타", [
        ("연세대 경력개발팀", "https://career.yonsei.ac.kr", "로그인 필요"),
        ("서울대 경력개발센터", "https://career.snu.ac.kr", "로그인 필요"),
        ("고려대 경력개발센터", "https://career.korea.ac.kr", "로그인 필요 (경영대 CDC는 자동 수집 중)"),
        ("LinkedIn Jobs (Seoul)", "https://www.linkedin.com/jobs/search/?keywords=intern%20finance&location=Seoul", "Job Alert 메일 설정 권장"),
        ("THE VC 채용", "https://thevc.kr/jobs", "봇 차단"),
        ("InsightBay", "https://www.insightbay.co.kr", "채용 게시판 없음"),
        ("CareerJump", "https://www.careerjump.co.kr", "접속 불안정"),
    ]),
]


def render(payload: dict, out_path: Path) -> Path:
    data = json.dumps({**payload, "categories": CATEGORIES, "manual": MANUAL_LINKS}, ensure_ascii=False)
    data = data.replace("</", "<\\/")
    html = TEMPLATE.replace("__DATA__", data)
    out_path.write_text(html, encoding="utf-8")
    return out_path


TEMPLATE = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>금융 인턴 레이더</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap">
<style>
/* Layout: 상단 요약 → 분야 칩 → 필터 → 마감순 공고 원장(ledger) → 수집 현황/직접 확인 링크 */
:root{
  --bg:#f3f5f7; --surface:#ffffff; --ink:#14202b; --muted:#5d6a77; --line:#dfe4e9; --soft:#eef1f4;
  --accent:#1747b8; --accent-soft:#e6ecfa;
  --urgent:#b42d22; --urgent-soft:#fbe9e7; --soon:#9a6200; --soon-soft:#fbf1dc; --ok:#2b6f48; --ok-soft:#e5f2ea;
  --font:"IBM Plex Sans KR","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,"Cascadia Mono",Consolas,monospace;
  --c0:#6b3fa0; --c1:#0f7c6e; --c2:#1747b8; --c3:#b0451a; --c4:#7a5a00; --c5:#2f6f2f; --c6:#a3245a; --c7:#235b8f; --c8:#5a6470; --c9:#7b6f63;
  color-scheme:light;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#0f141a; --surface:#161d25; --ink:#e4e9ee; --muted:#93a0ad; --line:#26313c; --soft:#1c252f;
  --accent:#7fa2ff; --accent-soft:#1d2a47;
  --urgent:#ff8a7d; --urgent-soft:#3a1d1a; --soon:#f0bd5a; --soon-soft:#352a12; --ok:#7fd3a0; --ok-soft:#14301f;
  --c0:#b99cf0; --c1:#5fd0bf; --c2:#8eaaff; --c3:#f39a72; --c4:#e0c160; --c5:#8fd48f; --c6:#f08ab5; --c7:#86b8ea; --c8:#a9b3bd; --c9:#c7b8a8;
  color-scheme:dark;}}
:root[data-theme="dark"]{
  --bg:#0f141a; --surface:#161d25; --ink:#e4e9ee; --muted:#93a0ad; --line:#26313c; --soft:#1c252f;
  --accent:#7fa2ff; --accent-soft:#1d2a47;
  --urgent:#ff8a7d; --urgent-soft:#3a1d1a; --soon:#f0bd5a; --soon-soft:#352a12; --ok:#7fd3a0; --ok-soft:#14301f;
  --c0:#b99cf0; --c1:#5fd0bf; --c2:#8eaaff; --c3:#f39a72; --c4:#e0c160; --c5:#8fd48f; --c6:#f08ab5; --c7:#86b8ea; --c8:#a9b3bd; --c9:#c7b8a8;
  color-scheme:dark;}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--bg);color:var(--ink);font:14px/1.5 var(--font);-webkit-font-smoothing:antialiased}
a{color:inherit}
.wrap{max-width:1180px;margin:0 auto;padding-block:28px 64px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
header{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:12px 24px;margin-bottom:22px}
h1{font-size:26px;line-height:1.2;margin:0;font-weight:700;letter-spacing:-.01em;text-wrap:balance}
h1 small{display:block;font-size:12px;font-weight:500;color:var(--muted);letter-spacing:.06em;text-transform:uppercase;margin-bottom:6px;font-family:var(--mono)}
.stamp{font-family:var(--mono);font-size:12px;color:var(--muted);text-align:right}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:10px;overflow:hidden;margin-bottom:18px}
.kpi{background:var(--surface);padding:14px 16px;min-width:0}
.kpi b{display:block;font:600 26px/1.1 var(--mono);font-variant-numeric:tabular-nums}
.kpi span{color:var(--muted);font-size:12.5px}
.kpi.urgent b{color:var(--urgent)} .kpi.fresh b{color:var(--accent)}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
.chip{appearance:none;border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:999px;padding:5px 11px;font:500 13px var(--font);cursor:pointer;display:inline-flex;align-items:center;gap:7px}
.chip i{width:8px;height:8px;border-radius:50%;background:var(--cc,var(--muted));display:inline-block}
.chip em{font:500 12px var(--mono);color:var(--muted);font-style:normal}
.chip[aria-pressed="true"]{background:var(--ink);color:var(--surface);border-color:var(--ink)}
.chip[aria-pressed="true"] em{color:inherit;opacity:.75}
.chip:focus-visible,.tool:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.tools{display:flex;flex-wrap:wrap;gap:8px 10px;align-items:center;margin-bottom:14px}
.tools input[type=search]{flex:1 1 220px;min-width:0;border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:8px;padding:8px 11px;font:14px var(--font)}
.tools select{border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:8px;padding:8px 10px;font:13px var(--font)}
.tools label{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--muted);cursor:pointer;user-select:none}
.count{font:12.5px var(--mono);color:var(--muted);margin-left:auto}
.ledger{background:var(--surface);border:1px solid var(--line);border-radius:10px;overflow:hidden}
table{width:100%;border-collapse:collapse}
th{font:500 11.5px var(--mono);letter-spacing:.05em;text-transform:uppercase;color:var(--muted);text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);background:var(--soft);white-space:nowrap}
td{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
tr.done td{opacity:.45}
.dday{font:600 12.5px var(--mono);font-variant-numeric:tabular-nums;padding:3px 7px;border-radius:6px;white-space:nowrap;display:inline-block;min-width:52px;text-align:center}
.d-urgent{background:var(--urgent-soft);color:var(--urgent)} .d-soon{background:var(--soon-soft);color:var(--soon)} .d-ok{background:var(--ok-soft);color:var(--ok)} .d-open{background:var(--soft);color:var(--muted)}
.cat{font-size:12px;font-weight:600;color:var(--cc);white-space:nowrap;display:inline-flex;align-items:center;gap:6px}
.cat::before{content:"";width:7px;height:7px;border-radius:2px;background:var(--cc)}
.co{font-weight:600;white-space:nowrap;max-width:190px;overflow:hidden;text-overflow:ellipsis}
.ti a{text-decoration:none;font-weight:500}
.ti a:hover{text-decoration:underline;text-underline-offset:3px;color:var(--accent)}
.new{font:600 10.5px var(--mono);color:var(--accent);background:var(--accent-soft);padding:1px 5px;border-radius:4px;margin-left:6px;vertical-align:1px}
.date{font:12.5px var(--mono);color:var(--muted);white-space:nowrap}
.src-list{display:flex;flex-wrap:wrap;gap:4px}
.src a{font-size:11.5px;color:var(--muted);border:1px solid var(--line);border-radius:4px;padding:1px 6px;text-decoration:none;white-space:nowrap}
.src a:hover{color:var(--accent);border-color:var(--accent)}
.acts{white-space:nowrap}
.acts button{appearance:none;border:1px solid transparent;background:none;color:var(--muted);cursor:pointer;font-size:15px;line-height:1;padding:4px 5px;border-radius:6px}
.acts button:hover{border-color:var(--line)}
.acts button[aria-pressed="true"].star{color:#d39b00}
.acts button[aria-pressed="true"].done{color:var(--ok)}
.empty{padding:40px 16px;text-align:center;color:var(--muted)}
section.aux{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:18px;margin-top:28px}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px 18px;min-width:0}
.panel h2{font-size:15px;margin:0 0 4px}
.panel p.hint{margin:0 0 12px;color:var(--muted);font-size:12.5px}
.status td,.status th{padding:7px 8px;font-size:13px}
.status td.num{font-family:var(--mono);text-align:right;font-variant-numeric:tabular-nums}
.ok{color:var(--ok)} .err{color:var(--urgent)}
.manual h3{font:600 12px var(--mono);letter-spacing:.05em;text-transform:uppercase;color:var(--muted);margin:14px 0 6px}
.manual h3:first-of-type{margin-top:0}
.manual ul{list-style:none;margin:0;padding:0;display:grid;gap:4px}
.manual li{display:flex;justify-content:space-between;gap:10px;font-size:13.5px}
.manual li a{font-weight:500;text-decoration:none;color:var(--accent)}
.manual li span{color:var(--muted);font-size:12px;text-align:right}
@media (max-width:860px){
  .kpis{grid-template-columns:repeat(2,minmax(0,1fr))}
  section.aux{grid-template-columns:minmax(0,1fr)}
  thead{display:none}
  table,tbody,tr,td{display:block;width:100%}
  tr{padding:12px 14px;border-bottom:1px solid var(--line);display:grid;grid-template-columns:auto 1fr auto;gap:4px 10px;align-items:center}
  tr:last-child{border-bottom:0}
  td{padding:0;border:0}
  td.c-d{grid-row:1;grid-column:1} td.c-cat{grid-row:1;grid-column:2} td.acts{grid-row:1;grid-column:3}
  td.co{grid-column:1/-1;max-width:none;white-space:normal} td.ti{grid-column:1/-1} td.date{grid-column:1/-1} td.src{grid-column:1/-1}
  td.date:empty{display:none}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1><small>Finance Internship Radar</small>금융 인턴 레이더</h1>
    <div class="stamp" id="stamp"></div>
  </header>

  <div class="kpis" id="kpis"></div>
  <div class="chips" id="chips" role="group" aria-label="분야 필터"></div>

  <div class="tools">
    <input type="search" id="q" placeholder="회사·공고명 검색 (예: 리서치, 투자심사, Summer)" aria-label="검색">
    <select id="src" aria-label="출처"></select>
    <select id="sort" aria-label="정렬">
      <option value="deadline">마감 임박순</option>
      <option value="new">최근 발견순</option>
      <option value="company">회사명순</option>
    </select>
    <label><input type="checkbox" id="onlyStar"> ★만</label>
    <label><input type="checkbox" id="hideDone" checked> 지원완료 숨기기</label>
    <label><input type="checkbox" id="hideOther"> 은행·보험·기타 숨기기</label>
    <span class="count" id="count"></span>
  </div>

  <div class="ledger">
    <table>
      <thead><tr><th>마감</th><th>분야</th><th>회사</th><th>공고</th><th>마감일</th><th>출처</th><th></th></tr></thead>
      <tbody id="rows"></tbody>
    </table>
    <div class="empty" id="empty" hidden>조건에 맞는 공고가 없어요. 분야 칩이나 검색어를 바꿔 보세요.</div>
  </div>

  <section class="aux">
    <div class="panel">
      <h2>수집 현황</h2>
      <p class="hint">사이트별로 가져온 공고 수와, 그중 금융 인턴으로 남은 수예요. 실패한 소스는 다음 실행 때 다시 시도해요.</p>
      <div style="overflow-x:auto"><table class="status" id="status"></table></div>
    </div>
    <div class="panel manual">
      <h2>직접 확인할 곳</h2>
      <p class="hint">로그인이 필요하거나 자동 수집을 막아 둔 사이트예요. 주 1회 정도 직접 열어 보세요.</p>
      <div id="manual"></div>
    </div>
  </section>
</div>

<script id="payload" type="application/json">__DATA__</script>
<script>
(function(){
  const D = JSON.parse(document.getElementById('payload').textContent);
  const today = new Date(D.today + 'T00:00:00');
  const CAT_VAR = {}; D.categories.forEach((c,i)=>CAT_VAR[c]='var(--c'+i+')');
  const $ = id => document.getElementById(id);

  const store = {
    get(k, d){ try{ const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; }catch(e){ return d; } },
    set(k, v){ try{ localStorage.setItem(k, JSON.stringify(v)); }catch(e){} }
  };
  let stars = new Set(store.get('fir-stars', []));
  let done = new Set(store.get('fir-done', []));
  let activeCats = new Set(store.get('fir-cats', []));

  const keyOf = j => j.sources[0].url;
  const days = j => j.deadline ? Math.round((new Date(j.deadline+'T00:00:00') - today)/86400000) : null;

  function ddayCell(j){
    const d = days(j);
    if (d === null) return '<span class="dday d-open">'+esc(j.deadline_note && /상시/.test(j.deadline_note) ? '상시' : '수시')+'</span>';
    const cls = d <= 3 ? 'd-urgent' : d <= 7 ? 'd-soon' : 'd-ok';
    return '<span class="dday '+cls+'">'+(d===0?'D-DAY':'D-'+d)+'</span>';
  }
  function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
  function fmtDate(s){ if(!s) return ''; const [y,m,d]=s.split('-'); const w='일월화수목금토'[new Date(s+'T00:00:00').getDay()]; return m+'.'+d+' ('+w+')'; }

  // KPI
  const jobs = D.jobs;
  const urgent = jobs.filter(j=>{const d=days(j); return d!==null && d<=7;}).length;
  const fresh = jobs.filter(j=>j.is_new).length;
  const okSrc = D.status.filter(s=>s.ok).length;
  $('kpis').innerHTML =
    '<div class="kpi"><b>'+jobs.length+'</b><span>진행 중인 금융 인턴 공고</span></div>'+
    '<div class="kpi urgent"><b>'+urgent+'</b><span>7일 안에 마감</span></div>'+
    '<div class="kpi fresh"><b>'+fresh+'</b><span>최근 3일 새로 올라옴</span></div>'+
    '<div class="kpi"><b>'+okSrc+'<small style="font-size:14px;color:var(--muted)">/'+D.status.length+'</small></b><span>수집 성공한 사이트</span></div>';
  $('stamp').innerHTML = '수집 '+esc(D.generated_at)+' KST<br>매일 08시·18시 자동 갱신';

  // 출처 select
  const srcNames = [...new Set(jobs.flatMap(j=>j.sources.map(s=>s.name)))].sort();
  $('src').innerHTML = '<option value="">모든 출처</option>' + srcNames.map(s=>'<option>'+esc(s)+'</option>').join('');

  function renderChips(){
    const counts = {}; jobs.forEach(j=>counts[j.category]=(counts[j.category]||0)+1);
    $('chips').innerHTML = '<button class="chip" data-cat="" aria-pressed="'+(activeCats.size===0)+'">전체 <em>'+jobs.length+'</em></button>' +
      D.categories.filter(c=>counts[c]).map(c=>
        '<button class="chip" data-cat="'+esc(c)+'" style="--cc:'+CAT_VAR[c]+'" aria-pressed="'+activeCats.has(c)+'"><i></i>'+esc(c)+' <em>'+counts[c]+'</em></button>').join('');
  }
  $('chips').addEventListener('click', e=>{
    const b = e.target.closest('.chip'); if(!b) return;
    const c = b.dataset.cat;
    if (!c) activeCats.clear(); else activeCats.has(c) ? activeCats.delete(c) : activeCats.add(c);
    store.set('fir-cats', [...activeCats]); renderChips(); renderRows();
  });

  function renderRows(){
    const q = $('q').value.trim().toLowerCase();
    const src = $('src').value, sort = $('sort').value;
    let list = jobs.filter(j=>{
      if (activeCats.size && !activeCats.has(j.category)) return false;
      if ($('hideOther').checked && j.category==='은행·보험·기타') return false;
      if (src && !j.sources.some(s=>s.name===src)) return false;
      if ($('onlyStar').checked && !stars.has(keyOf(j))) return false;
      if ($('hideDone').checked && done.has(keyOf(j))) return false;
      if (q && !(j.company+' '+j.title+' '+j.category).toLowerCase().includes(q)) return false;
      return true;
    });
    const big = 1e9;
    if (sort==='deadline') list.sort((a,b)=>((days(a)??big)-(days(b)??big)) || a.company.localeCompare(b.company,'ko'));
    else if (sort==='new') list.sort((a,b)=>(b.first_seen+(b.posted||'')).localeCompare(a.first_seen+(a.posted||'')));
    else list.sort((a,b)=>a.company.localeCompare(b.company,'ko'));

    $('rows').innerHTML = list.map(j=>{
      const k = keyOf(j);
      return '<tr class="'+(done.has(k)?'done':'')+'">'+
        '<td class="c-d">'+ddayCell(j)+'</td>'+
        '<td class="c-cat"><span class="cat" style="--cc:'+CAT_VAR[j.category]+'">'+esc(j.category)+'</span></td>'+
        '<td class="co" title="'+esc(j.company)+'">'+esc(j.company)+'</td>'+
        '<td class="ti"><a href="'+esc(j.sources[0].url)+'" target="_blank" rel="noopener">'+esc(j.title)+'</a>'+(j.is_new?'<span class="new">NEW</span>':'')+'</td>'+
        '<td class="date">'+(j.deadline ? fmtDate(j.deadline) : (j.posted ? '게시 '+fmtDate(j.posted) : ''))+'</td>'+
        '<td class="src"><div class="src-list">'+j.sources.map(s=>'<a href="'+esc(s.url)+'" target="_blank" rel="noopener">'+esc(s.name)+'</a>').join('')+'</div></td>'+
        '<td class="acts"><button class="star" data-k="'+esc(k)+'" aria-pressed="'+stars.has(k)+'" title="관심 공고">★</button>'+
        '<button class="done" data-k="'+esc(k)+'" aria-pressed="'+done.has(k)+'" title="지원 완료">✓</button></td></tr>';
    }).join('');
    $('empty').hidden = list.length>0;
    $('count').textContent = list.length+'건 표시';
  }
  $('rows').addEventListener('click', e=>{
    const b = e.target.closest('button[data-k]'); if(!b) return;
    const set = b.classList.contains('star') ? stars : done;
    const k = b.dataset.k; set.has(k) ? set.delete(k) : set.add(k);
    store.set('fir-stars',[...stars]); store.set('fir-done',[...done]); renderRows();
  });
  ['q','src','sort','onlyStar','hideDone','hideOther'].forEach(id=>$(id).addEventListener(id==='q'?'input':'change', renderRows));

  // 수집 현황
  $('status').innerHTML = '<thead><tr><th>사이트</th><th>상태</th><th style="text-align:right">가져온 공고</th><th style="text-align:right">금융 인턴</th></tr></thead><tbody>'+
    D.status.map(s=>'<tr><td>'+esc(s.name)+'</td><td class="'+(s.ok?'ok':'err')+'" title="'+esc(s.error||'')+'">'+(s.ok?'성공':'실패')+'</td><td class="num">'+s.fetched+'</td><td class="num">'+(s.kept||0)+'</td></tr>').join('')+'</tbody>';

  // 직접 확인 링크
  $('manual').innerHTML = D.manual.map(([g,items])=>'<h3>'+esc(g)+'</h3><ul>'+items.map(([n,u,note])=>
    '<li><a href="'+esc(u)+'" target="_blank" rel="noopener">'+esc(n)+'</a><span>'+esc(note)+'</span></li>').join('')+'</ul>').join('');

  renderChips(); renderRows();
})();
</script>
</body>
</html>
"""
