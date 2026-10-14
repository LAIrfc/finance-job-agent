"""Collect campus-only public lists using request shapes observed in the anonymous UI."""
import json,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlencode,parse_qs
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data/research/2026-10-13'
def collect(sid):
 events=json.loads((DATA/(('campus-' if sid=='cms' else 'positions-')+sid+'-network.json')).read_text())
 endpoint={'icbc':'qryPostList','cmbc':'search.view','cms':'listPosition'}[sid]
 e=next(e for e in events if endpoint in e['url'] and (sid!='cmbc' or 'searchRecruitmentIds=campus' in (e.get('post_data') or '')))
 jobs={};logs=[];total=None;error=None
 try:
  for n in range(1,300):
   if sid=='icbc':
    body=json.loads(e['post_data']);body['private'].update(page=n,pageSize=100);data=json.dumps(body).encode();ct='application/json'
   else:
    body={k:v[0] for k,v in parse_qs(e['post_data'],keep_blank_values=True).items()};body['pageNo' if sid=='cmbc' else 'currentPage']=n;data=urlencode(body).encode();ct='application/x-www-form-urlencoded'
   req=Request(e['url'],data=data,headers={'Content-Type':ct,'User-Agent':'Mozilla/5.0','Referer':{'icbc':'https://job.icbc.com.cn/','cmbc':'https://career.cmbc.com.cn/','cms':'https://wecruit.hotjob.cn/'}[sid]})
   payload=json.loads(urlopen(req,timeout=30).read())
   if sid=='icbc':part=payload['data'];rows=part['dataList'];total=part['total'];idkey='postId'
   elif sid=='cmbc':part=payload['data'];rows=part['items'];total=part['totalLine'];idkey='id'
   else:part=payload['data']['pageForm'];rows=part['pageData'];total=part['dataCount'];idkey='postId'
   before=len(jobs)
   for j in rows:jobs[str(j[idkey])]=j
   logs.append(dict(page=n,rows=len(rows),total=total))
   print(sid,n,len(jobs),'/',total,flush=True)
   if len(jobs)>=total:break
   if not rows or len(jobs)==before:raise RuntimeError('pagination did not advance')
   time.sleep(.2)
 except Exception as exc:error=str(exc)
 if jobs:(DATA/(sid+'-jobs.json')).write_text(json.dumps(list(jobs.values()),ensure_ascii=False,indent=2)+'\n')
 (DATA/(sid+'-log.json')).write_text(json.dumps(dict(total=total,collected=len(jobs),complete=len(jobs)==total,error=error,pages=logs,observed_url=e['url']),ensure_ascii=False,indent=2)+'\n')
 print('RESULT',sid,len(jobs),total,error,flush=True)
if __name__=='__main__':
 with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(collect,['icbc','cmbc','cms']))
