#!/usr/bin/env python3
"""Repeatable CLI verification in a separate database. --live also checks official pages."""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    folder=ROOT/'data/verification'/datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    db=folder/'demo.sqlite3'
    results={'demo_only':True,'external_submission':False,'checks':{}}
    def run(*argv, expect=0):
        p=subprocess.run([sys.executable,str(ROOT/'agent.py'),'--db',str(db),*argv],capture_output=True,text=True)
        if p.returncode!=expect:
            raise RuntimeError(f'{argv}: {p.stdout}\n{p.stderr}')
        return json.loads(p.stdout) if p.stdout else p.stderr
    def save(name,value):
        (folder/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
        return value
    if args.live:
        for sid in ['boc','psbc']:
            output=run('fetch',sid)
            save('fetch-'+sid,output)
            results['checks']['live-'+sid]=output['outcome']
            if sid=='boc':
                links=save('announcements',run('discover',output['detail'],'--keyword','2027年全球校园招聘'))
                if len(links)!=1: raise RuntimeError('公告唯一性需人工核验')
                detail=run('fetch',sid,'--url',links[0]['url'])
                save('fetch-announcement',detail)
                results['checks']['live-detail']=detail['outcome']
    first=run('import',str(ROOT/'examples/boc-2027-jobs.json'))
    second=run('import',str(ROOT/'examples/boc-2027-jobs.json'))
    assert first==dict(inserted=3,updated=0,unchanged=0),first
    assert second==dict(inserted=0,updated=0,unchanged=3),second
    results['checks']['import-and-dedupe']='passed'
    matches=save('matches',run('match',str(ROOT/'examples/demo-profile.json')))
    assert len(matches)==3
    assert all(j['eligible'] is False and '岗位已截止' in j['gaps'] for j in matches)
    results['checks']['expired-jobs-excluded']='passed'
    key=matches[0]['job_key']
    assert run('track',key,'prepared','--next-action','仅测试状态记录，不实际申请')['recorded']
    assert not run('track',key,'prepared','--next-action','仅测试状态记录，不实际申请')['recorded']
    run('track',key,'submitted',expect=1)
    run('track',key,'submitted','--evidence','模拟回执，仅限隔离测试数据库；未进行真实投递')
    events=save('events',run('list-applications'))
    assert len(events)==2
    results['checks']['tracking-idempotency-and-evidence']='passed'
    save('health',run('health'))
    save('result',results)
    print(json.dumps(dict(report=str(folder/'result.json'),**results),ensure_ascii=False,indent=2))

if __name__=='__main__': main()
