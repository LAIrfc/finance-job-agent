"""Snapshot discovered public recruitment pages, registering each exact URL first."""
import json,hashlib
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/2026-10-13'
rows=json.loads((OUT/'discovered-pages.json').read_text())
rows=[r for r in rows if '.pdf' not in r['url'].lower() and 'events.fdsm' not in r['url']]
sources=json.loads((ROOT/'data/sources.json').read_text()); ids={s['id'] for s in sources}
for r in rows:
 r['id']='research-'+hashlib.sha256(r['url'].encode()).hexdigest()[:12]
 if r['id'] not in ids:
  host=urlsplit(r['url']).hostname
  sources.append(dict(id=r['id'],name=r['title'] or host,track='research',url=r['url'],trust='B' if '.edu.cn' in host or 'ncss.cn' in host else 'A',provenance='web_search',verification='search_found',enabled=True,adapter='public_page',system_type='unknown',priority=2,notes='研究快照入口；并非独立用人机构，不计入机构覆盖数'))
(ROOT/'data/sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
def get(r):
 path=OUT/'pages'/(r['id']+'.html')
 try:
  if not path.exists():
   with urlopen(Request(r['url'],headers={'User-Agent':'FinancialCampusResearch/0.2'}),timeout=18) as response:
    content=response.read(4000000)
    r['final_url']=response.url
    path.write_bytes(content)
  soup=BeautifulSoup(path.read_bytes(),'html.parser')
  for el in soup(['script','style','header','footer','nav']):el.decompose()
  text=soup.get_text('\n',strip=True)
  path.with_suffix('.txt').write_text(text)
  r.update(status='fetched',raw_file=str(path.relative_to(ROOT)),text_file=str(path.with_suffix('.txt').relative_to(ROOT)),text_chars=len(text),has_2027='2027' in text,tables=[[[cell.get_text(' ',strip=True) for cell in tr.find_all(['td','th'],recursive=False)] for tr in table.find_all('tr')] for table in soup.find_all('table')])
 except Exception as e:r.update(status='failed',error=str(e))
 return r
with ThreadPoolExecutor(max_workers=4) as pool: result=list(pool.map(get,rows))
(OUT/'research-pages.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(attempted=len(result),fetched=sum(r['status']=='fetched' for r in result),content_2027=sum(r.get('has_2027',False) for r in result)),ensure_ascii=False))
for r in result:
 print(r['id'],r['status'],r.get('text_chars'),r.get('has_2027'),r['title'][:40])
