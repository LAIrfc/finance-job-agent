#!/usr/bin/env python3
"""Local, dependency-free campus application workflow. No external submission."""
import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, date, timezone, timedelta
from pathlib import Path
from html.parser import HTMLParser
from urllib.request import Request, urlopen, HTTPRedirectHandler, build_opener
from urllib.parse import urlsplit, urljoin, urldefrag
SHANGHAI = timezone(timedelta(hours=8), name="Asia/Shanghai")

ROOT = Path(__file__).resolve().parent
DEGREES = {'专科': 1, '本科': 2, '硕士': 3, '博士': 4}
TRACKS = {'bank', 'securities', 'fund', 'insurance', 'regulatory'}
STATES = {'prepared', 'submitted', 'test', 'interview', 'offer', 'rejected', 'withdrawn'}

def now():
    return datetime.now(SHANGHAI).isoformat()

def read(path):
    return json.loads(Path(path).read_text())

def sources():
    return read(ROOT / 'data/sources.json')

def connect(path):
    db = sqlite3.connect(path)
    db.executescript('''CREATE TABLE IF NOT EXISTS jobs (key TEXT PRIMARY KEY, body TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, job_key TEXT, state TEXT, evidence TEXT, next_action TEXT, at TEXT);
    CREATE TABLE IF NOT EXISTS health (id INTEGER PRIMARY KEY, source_id TEXT, outcome TEXT, detail TEXT, at TEXT);''')
    return db

def normalize(job):
    job = dict(job)
    for key in ('source_id', 'org', 'org_unit', 'title', 'recruitment_cycle', 'apply_url'):
        if not isinstance(job.get(key), str) or not job[key].strip():
            raise ValueError(f'必填字段缺失: {key}')
        job[key] = job[key].strip()
    source = next((s for s in sources() if s['id'] == job['source_id']), None)
    if not source:
        raise ValueError('数据源未注册')
    if job.get('track') not in TRACKS or job.get('org_level') not in {'headquarters', 'branch', 'subsidiary', 'unknown'}:
        raise ValueError('赛道或机构层级不合法')
    if urlsplit(job['apply_url']).scheme != 'https':
        raise ValueError('投递 URL 必须为 HTTPS')
    if job.get('deadline'):
        date.fromisoformat(job['deadline'])
    if job.get('degree') is not None and job['degree'] not in DEGREES:
        raise ValueError('未知学历枚举')
    for key in ('locations', 'graduation_years', 'skills', 'required_majors', 'required_certificates', 'major_preference', 'hard_requirements', 'evidence'):
        job.setdefault(key, [])
        if not isinstance(job[key], list):
            raise ValueError(f'{key} 应为列表')
    identity = [job[k] for k in ('org', 'org_unit', 'org_level', 'recruitment_cycle')]
    identity += [job.get('official_job_id') or job['title']]
    if not job.get('official_job_id'):
        identity += [sorted(job['locations'])]
    job['job_key'] = hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()[:24]
    job['source_trust'] = source['trust']
    return job

def match(job, profile, today=None):
    today = today or datetime.now(SHANGHAI).date()
    failed, unknown, reasons = [], [], []
    deadline = job.get('deadline')
    if deadline and date.fromisoformat(deadline) < today:
        failed.append('岗位已截止')
    if not deadline:
        unknown.append('截止日期待核实')
    for key, label in [('graduation_years', '毕业届别'), ('required_majors', '专业'), ('required_certificates', '资格证')]:
        need = job.get(key, [])
        actual = profile.get({'graduation_years':'graduation_year', 'required_majors':'major', 'required_certificates':'certificates'}[key])
        if key == 'graduation_years' and not need:
            unknown.append('届别要求待核实')
        if need:
            if actual is None:
                unknown.append(label + '画像缺失')
            elif (key == 'required_certificates' and not set(need).issubset(set(actual))) or (key != 'required_certificates' and str(actual) not in {str(v) for v in need}):
                failed.append(label + '不符')
            else:
                reasons.append(label + '符合')
    minimum = job.get('degree')
    if minimum is None or profile.get('degree') not in DEGREES:
        unknown.append('学历待核实')
    elif DEGREES[profile['degree']] < DEGREES[minimum]:
        failed.append('最低学历不符')
    else:
        reasons.append('学历符合')
    if job.get('hard_requirements'):
        unknown.extend('需人工核实硬条件：' + str(v) for v in job['hard_requirements'])
    skills = set(job.get('skills', []))
    hit = skills & set(profile.get('skills', []))
    preferred = bool(set(job.get('locations', [])) & set(profile.get('locations', [])))
    bonus = 5 if profile.get('major') in job.get('major_preference', []) else 0
    score = round(25 + 50 * len(hit) / max(1, len(skills)) + 20 * preferred + bonus)
    if hit:
        reasons.append('技能匹配：' + '、'.join(sorted(hit)))
    if preferred:
        reasons.append('地点符合偏好')
    if bonus:
        reasons.append('符合 JD 专业软偏好')
    if not skills:
        unknown.append('技能要求未提取')
    return dict(job_key=job['job_key'], org=job['org'], title=job['title'], eligible=False if failed else None if unknown else True,
                match_score=None if failed else score, tier='排除' if failed else '待核实' if unknown else '保（暂定）' if score>=80 else '稳（暂定）' if score>=60 else '冲（暂定）',
                reasons=reasons, gaps=failed + sorted(skills-hit), unknown=unknown,
                note='关键词基线；冲稳保仅代表匹配程度，不是录用概率')

class SameHostRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).hostname != urlsplit(req.full_url).hostname or urlsplit(newurl).scheme != 'https':
            raise ValueError('跨域或非 HTTPS 跳转待核验并注册')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def fetch(db, sid, url=None):
    source = next(s for s in sources() if s['id'] == sid)
    if not source['enabled'] or not source['url']:
        raise ValueError('源未启用或缺少地址')
    url = url or source['url']
    target = urlsplit(url)
    if target.scheme != 'https' or target.hostname != urlsplit(source['url']).hostname or target.username or target.password or target.port not in (None, 443):
        raise ValueError('详情 URL 必须属于注册源的 HTTPS 域名')
    try:
        req = Request(url, headers={'User-Agent':'FinancialCampusResearch/0.1'})
        with build_opener(SameHostRedirect()).open(req, timeout=20) as response:
            raw = response.read(5_000_001)
            if len(raw)>5_000_000:
                raise ValueError('页面超过 5MB')
            content_type = response.headers.get('Content-Type', '')
        folder = ROOT/'data/raw'
        folder.mkdir(exist_ok=True)
        path = folder / (sid + '-' + datetime.now(SHANGHAI).strftime('%Y%m%d%H%M%S%f') + '.raw')
        path.write_bytes(raw)
        outcome, detail = 'page_fetched', str(path)
        path.with_suffix('.json').write_text(json.dumps(dict(source_id=sid,url=url,fetched_at=now(),content_type=content_type,sha256=hashlib.sha256(raw).hexdigest()),ensure_ascii=False,indent=2))
    except Exception as exc:
        outcome, detail = 'failed', str(exc)
    db.execute('INSERT INTO health(source_id,outcome,detail,at) VALUES(?,?,?,?)',(sid,outcome,detail,now()))
    db.commit()
    return dict(source_id=sid,outcome=outcome,detail=detail,warning='页面抓取不等于岗位解析；无新岗位不等于源故障')

class AnnouncementLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.href, self.label = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.href, self.label = dict(attrs).get('href'), []

    def handle_data(self, data):
        if self.href is not None:
            self.label.append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self.href is not None:
            self.links.append((' '.join(''.join(self.label).split()), self.href))
            self.href = None

def discover(raw_path, keyword):
    path = Path(raw_path)
    metadata = read(path.with_suffix('.json'))
    parser = AnnouncementLinks()
    parser.feed(path.read_text(encoding='utf-8', errors='replace'))
    found = {}
    for title, href in parser.links:
        url = urldefrag(urljoin(metadata['url'], href))[0]
        if keyword in title and urlsplit(url).scheme == 'https' and urlsplit(url).hostname == urlsplit(metadata['url']).hostname:
            found[url] = dict(title=title, url=url, source_id=metadata['source_id'])
    return list(found.values())

def health(db):
    result=[]
    for s in sources():
        rows=db.execute('SELECT outcome,at FROM health WHERE source_id=? ORDER BY id DESC',(s['id'],)).fetchall()
        failures=0
        for outcome,_ in rows:
            if outcome!='failed': break
            failures+=1
        result.append(dict(source_id=s['id'],attempts=len(rows),page_success_rate=sum(r[0]=='page_fetched' for r in rows)/len(rows) if rows else None,consecutive_failures=failures,last_success=next((r[1] for r in rows if r[0]=='page_fetched'),None),job_update_status='unknown'))
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',default=str(ROOT/'data/agent.sqlite3'))
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('sources'); sub.add_parser('health'); sub.add_parser('list-applications')
    f=sub.add_parser('fetch'); f.add_argument('source_id'); f.add_argument('--url')
    d=sub.add_parser('discover'); d.add_argument('raw_file'); d.add_argument('--keyword',default='校园招聘')
    i=sub.add_parser('import'); i.add_argument('file')
    m=sub.add_parser('match'); m.add_argument('profile')
    t=sub.add_parser('track'); t.add_argument('job_key'); t.add_argument('state',choices=sorted(STATES)); t.add_argument('--evidence',default=''); t.add_argument('--next-action',default='')
    a=p.parse_args()
    with connect(a.db) as db:
        if a.command=='sources': result=sources()
        elif a.command=='fetch': result=fetch(db,a.source_id,a.url)
        elif a.command=='discover': result=discover(a.raw_file,a.keyword)
        elif a.command=='health': result=health(db)
        elif a.command=='import':
            incoming=read(a.file)
            jobs=[normalize(j) for j in incoming] # validate entire batch before mutation
            counts={'inserted':0,'updated':0,'unchanged':0}
            for j in jobs:
                body=json.dumps(j,ensure_ascii=False,sort_keys=True)
                prev=db.execute('SELECT body FROM jobs WHERE key=?',(j['job_key'],)).fetchone()
                kind='inserted' if not prev else 'unchanged' if prev[0]==body else 'updated'
                counts[kind]+=1
                db.execute('INSERT INTO jobs VALUES(?,?) ON CONFLICT(key) DO UPDATE SET body=excluded.body',(j['job_key'],body))
            result=counts
        elif a.command=='match':
            profile=read(a.profile)
            result=[match(json.loads(row[0]),profile) for row in db.execute('SELECT body FROM jobs')]
            result.sort(key=lambda j: j['match_score'] if j['match_score'] is not None else -1,reverse=True)
        elif a.command=='track':
            if not db.execute('SELECT 1 FROM jobs WHERE key=?',(a.job_key,)).fetchone(): raise ValueError('岗位不存在')
            if a.state!='prepared' and not a.evidence.strip(): raise ValueError('真实状态变化须提供用户确认或回执证据')
            latest=db.execute('SELECT state,evidence,next_action FROM events WHERE job_key=? ORDER BY id DESC LIMIT 1',(a.job_key,)).fetchone()
            if latest != (a.state,a.evidence,a.next_action):
                db.execute('INSERT INTO events(job_key,state,evidence,next_action,at) VALUES(?,?,?,?,?)',(a.job_key,a.state,a.evidence,a.next_action,now()))
            result={'job_key':a.job_key,'state':a.state,'recorded':latest!=(a.state,a.evidence,a.next_action)}
        else:
            result=[dict(zip(('job_key','state','evidence','next_action','at'),r)) for r in db.execute('SELECT job_key,state,evidence,next_action,at FROM events ORDER BY id')]
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if a.command=='fetch' and result['outcome']=='failed':
        raise SystemExit(1)

if __name__=='__main__':
    main()
