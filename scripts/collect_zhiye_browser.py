"""Observe each site's real public campus request, then read every page; no login/submission."""
import argparse,asyncio,json,sys
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/2026-10-13'
async def collect(browser,source):
 sid=source['id']; context=await browser.new_context(); page=await context.new_page(); observed=[]
 async def response_handler(response):
  if '/api/jobad/getjobadpagelist' in response.url.lower():
   try:
    observed.append(dict(url=response.url,method=response.request.method,body=json.loads(response.request.post_data or '{}'),result=await response.json()))
   except Exception:pass
 page.on('response',response_handler)
 log=dict(source_id=sid,url=source['url'],fetched_at=datetime.now(timezone(timedelta(hours=8))).isoformat())
 try:
  await page.goto(source.get('collection_url') or source['url'],wait_until='domcontentloaded',timeout=30000)
  await page.wait_for_timeout(6000)
  if not observed:
   links=await page.locator('a').evaluate_all('(els)=>els.map(a=>({text:a.innerText,href:a.href}))')
   (OUT/('browser-'+sid+'-links.json')).write_text(json.dumps(links,ensure_ascii=False,indent=2))
   candidates=[a for a in links if ('校园' in a['text'] or '职位投递' in a['text']) and urlsplit(a['href']).hostname==urlsplit(source['url']).hostname]
   if candidates:
    await page.goto(candidates[0]['href'],wait_until='domcontentloaded',timeout=30000)
    await page.wait_for_timeout(5000)
  (OUT/('browser-'+sid+'.txt')).write_text(await page.locator('body').inner_text())
  if not observed: raise ValueError('未观察到职位列表接口；页面需进一步解析')
  request=observed[-1]
  if request['method']!='POST' or urlsplit(request['url']).hostname!=urlsplit(source['url']).hostname:raise ValueError('请求不符合当前已验证适配方式')
  (OUT/('browser-'+sid+'-request.json')).write_text(json.dumps(request,ensure_ascii=False,indent=2))
  total=request['result'].get('Count',0)
  if total>10000: raise ValueError('超过本轮1万条/源上限，需分批')
  jobs={};pages=[];index=0
  while True:
   body=dict(request['body']); body['PageIndex']=index; body['PageSize']=100
   response=await context.request.post(request['url'],data=body,timeout=30000)
   payload=await response.json()
   if response.status!=200 or payload.get('Code')!=200: raise RuntimeError('公开列表请求失败：'+str(response.status))
   rows=payload.get('Data') or []
   pages.append(dict(page_index=index,total=payload.get('Count'),returned=len(rows)))
   if not rows:break
   before=len(jobs)
   for j in rows:jobs[str(j['Id'])]=j
   if len(jobs)==before: raise RuntimeError('分页重复，停止以免漏页误报')
   if len(jobs)>=payload.get('Count',total):break
   index+=1
   if index>1000:raise RuntimeError('分页上限')
   await page.wait_for_timeout(300)
  log.update(status='collected',advertised_count=total,collected_count=len(jobs),pages=pages,campus_filter=request['body'].get('Category'),observed_request_file='browser-'+sid+'-request.json')
  (OUT/('zhiye-'+sid+'-jobs.json')).write_text(json.dumps(list(jobs.values()),ensure_ascii=False,indent=2)+'\n')
 except Exception as e:log.update(status='needs_review',error=str(e))
 finally:
  (OUT/('zhiye-'+sid+'-log.json')).write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n')
  print(json.dumps(log,ensure_ascii=False),flush=True)
  await context.close()
async def main():
 parser=argparse.ArgumentParser();parser.add_argument('sources',nargs='+');args=parser.parse_args()
 registry={s['id']:s for s in json.loads((ROOT/'data/sources.json').read_text())}
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=False,args=['--no-sandbox','--headless=new'])
  sem=asyncio.Semaphore(2)
  async def limited(s):
   async with sem:await collect(browser,s)
  await asyncio.gather(*(limited(registry[sid]) for sid in args.sources))
  await browser.close()
if __name__=='__main__':asyncio.run(main())
