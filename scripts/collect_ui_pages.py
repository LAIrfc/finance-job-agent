"""Collect official campus lists by clicking normal anonymous browser pagination."""
import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data/research/2026-10-13'
async def one(browser,sid):
 ctx=await browser.new_context();page=await ctx.new_page();jobs={};events=[];logs=[];total=None;err=None;raw=[]
 async def capture(r):
  nonlocal total
  if ('/recruitposition/portalPage' if sid=='cib' else '/listPosition/') not in r.url:return
  try:
   data=await r.json()
   if sid=='cib':
    if json.loads(r.request.post_data).get('recruitType')!='CR':return
    part=data['data'];rows=part['list'];total=part['total'];idkey='positionId'
   else:part=data['data']['pageForm'];rows=part['pageData'];total=part['dataCount'];idkey='postId'
   raw.extend(rows)
   for j in rows:jobs[str(j[idkey])]=j
   logs.append(dict(rows=len(rows),unique=len(jobs),total=total,request=r.request.post_data))
   print(sid,len(jobs),'/',total,flush=True)
  except Exception:pass
 page.on('response',capture)
 try:
  await page.goto('https://job.cib.com.cn' if sid=='cib' else 'https://wecruit.hotjob.cn/SU629dbc0c0dcad452299bc0f7/pb/school.html',wait_until='domcontentloaded',timeout=30000)
  await page.wait_for_timeout(2500)
  if sid=='cib':await page.get_by_text('校园招聘',exact=True).first.click()
  await page.wait_for_timeout(3000)
  (DATA/(sid+'-pagination.html')).write_text(await page.content())
  if not jobs:raise RuntimeError('No public campus list loaded')
  if sid=='cib':
   previous=DATA/'cib-jobs.json'
   if previous.exists():
    for j in json.loads(previous.read_text()):jobs[str(j['positionId'])]=j
   await page.locator('.ant-pagination-options-size-changer').click()
   options=page.locator('.ant-select-dropdown-menu-item')
   print('PAGE SIZE OPTIONS',await options.all_text_contents(),flush=True)
   await options.last.click()
   await page.wait_for_timeout(1500)
   # Drop the initial 10-row load from this pass's completion counter.
   raw[:]=raw[10:]
  for n in range(1,100):
   if len(jobs)>=total or len(raw)>=total:break
   before=len(logs)
   if sid=='cib':
    button=page.locator('.ant-pagination-next').first
   else:
    button=page.locator('.ant-pagination-next').first
   await button.click(timeout=5000)
   for _ in range(30):
    await page.wait_for_timeout(300)
    if len(logs)>before:break
   if len(logs)==before:raise RuntimeError('Next-page click returned no response')
   await page.wait_for_timeout(250)
 except Exception as e:err=str(e)
 (DATA/(sid+'-all-rows.json')).write_text(json.dumps(raw,ensure_ascii=False,indent=2)+'\n')
 if jobs:(DATA/(sid+'-jobs.json')).write_text(json.dumps(list(jobs.values()),ensure_ascii=False,indent=2)+'\n')
 (DATA/(sid+'-log.json')).write_text(json.dumps(dict(total=total,collected=len(jobs),returned_rows=len(raw),complete=len(jobs)==total,error=err,pages=logs),ensure_ascii=False,indent=2)+'\n')
 print('RESULT',sid,len(jobs),total,err,flush=True)
 await ctx.close()
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=False,args=['--no-sandbox','--headless=new'])
  await one(browser,'cib');await browser.close()
if __name__=='__main__':asyncio.run(main())
