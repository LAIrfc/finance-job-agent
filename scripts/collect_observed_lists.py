"""Replay public listing requests observed in normal browser navigation; preserve their filters."""
import json,time
from pathlib import Path
from urllib.parse import urlencode,parse_qs
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data/research/2026-10-13'
def main():
 for sid,endpoint in [('bocom','querySocietyRecruitInfo.do'),('cms','listPosition')]:
  events=json.loads((DATA/('campus-'+sid+'-network.json')).read_text())
  e=next(e for e in events if endpoint in e['url']);jobs={};pages=[]
  for n in range(1,101):
   if sid=='cib':
    body=json.loads(e['post_data']);body['pagination'].update(pageIndex=n,pageSize=100);data=json.dumps(body).encode();ct='application/json'
   elif sid=='bocom':
    body=json.loads(parse_qs(e['post_data'])['REQ_MESSAGE'][0]);body['REQ_BODY']['params']['pagePara'].update(pageNum=n,pageSize=100);data=urlencode({'REQ_MESSAGE':json.dumps(body)}).encode();ct='application/x-www-form-urlencoded'
   else:
    body={k:v[0] for k,v in parse_qs(e['post_data']).items()};body.update(currentPage=n,pageSize=100);data=urlencode(body).encode();ct='application/x-www-form-urlencoded'
   req=Request(e['url'],data=data,headers={'Content-Type':ct,'User-Agent':'FinancialCampusResearch/0.2'})
   payload=json.loads(urlopen(req,timeout=25).read())
   if sid=='cib':rows=payload['data']['list'];total=payload['data']['total'];idkey='positionId'
   elif sid=='bocom':rows=payload['RSP_BODY']['results']['policyList'];total=payload['RSP_BODY']['results']['total'];idkey='positionId'
   else:rows=payload['data']['pageForm']['pageData'];total=payload['data']['pageForm']['dataCount'];idkey='postId'
   pages.append(dict(page=n,rows=len(rows),total=total));before=len(jobs)
   for j in rows:jobs[str(j[idkey])]=j
   if len(jobs)>=total:break
   if not rows or before==len(jobs):raise RuntimeError(sid+' pagination mismatch')
   time.sleep(.25)
  assert len(jobs)==total,(sid,len(jobs),total)
  (DATA/(sid+'-jobs.json')).write_text(json.dumps(list(jobs.values()),ensure_ascii=False,indent=2)+'\n')
  (DATA/(sid+'-log.json')).write_text(json.dumps(dict(total=total,collected=len(jobs),pages=pages,observed_url=e['url']),ensure_ascii=False,indent=2)+'\n')
  print(sid,total,'all pages collected',flush=True)
if __name__=='__main__':main()
