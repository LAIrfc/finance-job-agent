"""Collect only links advertised in the public SCZQ campus listing; preserve provenance."""
import hashlib,json,re,sys
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urljoin,urlsplit
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/2026-10-13/pages'
source=next(s for s in json.loads((ROOT/'data/sources.json').read_text()) if s['id']=='sczq')

def get(url):
 if urlsplit(url).hostname!=urlsplit(source['url']).hostname: raise ValueError('unregistered host')
 name='sczq-'+hashlib.sha256(url.encode()).hexdigest()[:16]+'.html'
 path=OUT/name
 if not path.exists():
  with urlopen(Request(url,headers={'User-Agent':'FinancialCampusResearch/0.2'}),timeout=20) as r: path.write_bytes(r.read(2000000))
 return path,BeautifulSoup(path.read_bytes(),'html.parser')

def main():
 queue=[source['url']];visited=set();jobs={};errors=[]
 while queue:
  url=queue.pop(0)
  if url in visited: continue
  visited.add(url)
  path,soup=get(url)
  for a in soup.select('a[jobAdId]'):
   row=a.find_parent('tr'); cells=row.find_all('td')
   job=dict(source_id='sczq',org='首创证券招聘体系',title=a.get('title') or a.get_text(' ',strip=True),official_job_id=a.get('jobadid'),apply_url=urljoin(url,a['href']),locations_text=cells[-2].get_text(' ',strip=True),published_at=cells[-1].get_text(' ',strip=True),record_type='job',verification='official_list_verified',deadline=None,status='待核实截止时间',list_url=url,raw_list=str(path.relative_to(ROOT)))
   jobs[job['official_job_id']]=job
  for a in soup.find_all('a',href=True):
   next_url=urljoin(url,a['href'])
   if 'PageIndex=' in next_url and a.get_text(strip=True) in ('下一页','尾页') and next_url not in visited:queue.append(next_url)
  if len(visited)>30: raise RuntimeError('pagination safety limit')
 def detail(j):
  try:
   path,soup=get(j['apply_url'])
   for node in soup(['script','style']): node.decompose()
   text=soup.get_text('\n',strip=True)
   j.update(raw_detail=str(path.relative_to(ROOT)),description=text,verification='official_detail_fetched')
   return j
  except Exception as e:
   j['detail_error']=str(e);return j
 with ThreadPoolExecutor(max_workers=3) as pool: result=list(pool.map(detail,jobs.values()))
 (OUT.parent/'sczq-jobs.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(pages=len(visited),jobs=len(result),detail_success=sum('raw_detail' in j for j in result)),ensure_ascii=False))
 print(json.dumps(result[:1],ensure_ascii=False,indent=2)[:6500])
if __name__=='__main__':main()
