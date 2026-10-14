import unittest
from datetime import date
from pathlib import Path
import sys
import json
import tempfile
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import normalize, match, connect, health, discover, fetch

class WorkflowTest(unittest.TestCase):
    def job(self, **kw):
        j=dict(source_id='boc',org='中国银行',org_unit='深圳分行',org_level='branch',title='科技岗',track='bank',recruitment_cycle='2027秋招',apply_url='https://www.boc.cn/aboutboc/bi4/',degree='本科',graduation_years=[2027],skills=['Python'],locations=['深圳'],deadline='2026-10-20')
        j.update(kw)
        return normalize(j)
    def profile(self):
        return dict(degree='硕士',graduation_year=2027,skills=['Python'],locations=['深圳'],major='计算机',certificates=[])
    def test_separate_org_units_and_cycles(self):
        j=self.job()
        self.assertNotEqual(j['job_key'],self.job(org_unit='广州分行')['job_key'])
        self.assertNotEqual(j['job_key'],self.job(recruitment_cycle='2027春招')['job_key'])
        self.assertEqual(j['job_key'],self.job(deadline='2026-11-01')['job_key'])
    def test_expired_and_degree_filter(self):
        self.assertFalse(match(self.job(),self.profile(),date(2026,10,21))['eligible'])
        self.assertFalse(match(self.job(degree='博士'),self.profile(),date(2026,10,13))['eligible'])
    def test_unknown_never_eligible(self):
        self.assertIsNone(match(self.job(deadline=None),self.profile(),date(2026,10,13))['eligible'])
        profile=self.profile(); del profile['graduation_year']
        self.assertIsNone(match(self.job(),profile,date(2026,10,13))['eligible'])
    def test_soft_major_not_gate(self):
        result=match(self.job(major_preference=['金融']),self.profile(),date(2026,10,13))
        self.assertTrue(result['eligible'])
    def test_unregistered_source(self):
        with self.assertRaises(ValueError): self.job(source_id='nonexistent')
    def test_health_no_updates_not_failure(self):
        with connect(':memory:') as db:
            db.execute('INSERT INTO health(source_id,outcome,detail,at) VALUES(?,?,?,?)',('boc','page_fetched','no jobs','2026-10-13'))
            h=next(r for r in health(db) if r['source_id']=='boc')
            self.assertEqual(h['consecutive_failures'],0)
            self.assertEqual(h['job_update_status'],'unknown')
    def test_discovery_resolves_and_deduplicates_same_host_links(self):
        with tempfile.TemporaryDirectory() as directory:
            raw=Path(directory)/'page.raw'
            raw.write_text('<a href="./detail.html"><span>2027校园招聘</span></a><a href="detail.html#top">校园招聘</a><a href="https://example.org/">校园招聘</a>')
            raw.with_suffix('.json').write_text(json.dumps(dict(url='https://www.boc.cn/aboutboc/bi4/',source_id='boc')))
            links=discover(raw,'校园招聘')
            self.assertEqual(len(links),1)
            self.assertEqual(links[0]['url'],'https://www.boc.cn/aboutboc/bi4/detail.html')
    def test_fetch_rejects_unregistered_detail_host(self):
        with connect(':memory:') as db:
            with self.assertRaises(ValueError):
                fetch(db,'boc','https://example.org/jobs')
    def test_network_failure_updates_health(self):
        with connect(':memory:') as db, patch('agent.build_opener') as opener:
            opener.return_value.open.side_effect=TimeoutError('timeout')
            self.assertEqual(fetch(db,'boc')['outcome'],'failed')
            row=next(h for h in health(db) if h['source_id']=='boc')
            self.assertEqual(row['consecutive_failures'],1)
            self.assertIsNone(row['last_success'])

if __name__=='__main__': unittest.main()
