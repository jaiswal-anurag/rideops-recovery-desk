"""Run with: python -m unittest discover -s tests -v"""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from core import (
    load_tickets, summary, ticket_view, classify, validate_packet,
    packet_as_text, historical_months, score_ticket,
)
from app import initialize_db,make_handler

ROOT=Path(__file__).resolve().parent.parent
ROWS=load_tickets(ROOT/'data'/'rideops_support_tickets.csv')

class DataAndRulesTests(unittest.TestCase):
    def test_source_counts_and_month_end(self):
        x=summary(ROWS)
        self.assertEqual((x['total'],x['open'],x['open_escalated']), (1444,48,34))
        self.assertEqual([(m['arrivals'],m['estimated_backlog']) for m in x['monthly']], [(390,30),(462,23),(592,48)])
    def test_nonfix_and_72h(self):
        x=summary(ROWS)
        self.assertEqual((x['non_fix_escalations'],x['info_config_returned'],x['open_aged_72h']), (275,173,16))
        self.assertEqual(x['open_top_two'], 30)
    def test_queue_is_only_open(self):
        queue=[ticket_view(r) for r in ROWS if r['status']!='Closed']
        self.assertEqual(len(queue),48)
        self.assertTrue(all(t['age_days']>=0 for t in queue))
    def test_priority_is_not_overridden_by_age(self):
        items=[ticket_view(r) for r in ROWS if r['status']!='Closed']
        p1=[x['score'] for x in items if x['priority']=='P1']
        p2=[x['score'] for x in items if x['priority']=='P2']
        self.assertGreater(min(p1),max(p2))
    def test_returned_but_with_engineering_requires_owner_check(self):
        r=next(r for r in ROWS if r['status']=='Open - with Engineering' and r['eng_outcome']=='Insufficient info - returned to L1')
        self.assertEqual(classify(r)[0],'Confirm ownership')
    def test_validate_packet_rejects_incomplete(self):
        tid=next(r['ticket_id'] for r in ROWS if r['status']!='Closed')
        with self.assertRaisesRegex(ValueError,'required'):
            validate_packet({'ticket_id':tid,'impact':'twelve employees'}, {tid})
    def test_validate_packet_accepts_complete(self):
        t=next(r for r in ROWS if r['status']!='Closed')
        d={'ticket_id':t['ticket_id'],'impact':'12 affected trips','steps':'Shift -> roster -> refresh',
           'expected':'12 trips appear','observed':'3 trips missing','checks':'Confirmed cutoff and sync'}
        packet=validate_packet(d,{t['ticket_id']})
        self.assertIn('EXPECTED',packet_as_text(t,packet))
        self.assertIn(t['ticket_id'],packet_as_text(t,packet))
    def test_month_final_close_balance(self):
        flow=historical_months(ROWS)
        self.assertEqual(flow[0]['arrivals']-flow[0]['final_closures'],30)
        self.assertEqual(flow[1]['estimated_backlog'],23)

class HttpWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.db=Path(cls.tmp.name)/'actions.db'
        initialize_db(cls.db)
        cls.srv=ThreadingHTTPServer(('127.0.0.1',0),make_handler(ROWS,cls.db))
        cls.thread=threading.Thread(target=cls.srv.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.srv.server_address[1]}'
        cls.tid=next(r['ticket_id'] for r in ROWS if r['status']!='Closed')
    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown();cls.srv.server_close();cls.thread.join();cls.tmp.cleanup()
    def get(self,path):
        return json.load(urlopen(self.base+path))
    def post(self,path,payload):
        req=Request(self.base+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
        with urlopen(req) as r:return json.load(r)
    def test_summary_http(self):
        state=self.get('/api/state')
        self.assertEqual(len(state['queue']),48)
        self.assertEqual(state['stats']['open'],48)
    def test_handoff_then_action_persists(self):
        p={'ticket_id':self.tid,'impact':'12 impacted trips','steps':'Open roster then refresh',
           'expected':'All trips visible','observed':'Only three trips visible','checks':'Checked sync and cutoff'}
        result=self.post('/api/handoff',p)
        self.assertTrue(result['ok'])
        a=self.post('/api/action',{'ticket_id':self.tid,'action':'basic_checks_done','note':'Verified cutoff and roster sync'})
        self.assertTrue(a['ok'])
        detail=self.get('/api/ticket/'+self.tid)
        self.assertEqual(len(detail['handoffs']),1)
        self.assertEqual(detail['activity'][0]['action'],'basic_checks_done')
        self.assertEqual(self.get('/api/state')['stats']['open'],48) # no fabricated closure
    def test_verified_resolution_requires_note(self):
        with self.assertRaises(HTTPError) as ctx:
            self.post('/api/action',{'ticket_id':self.tid,'action':'verified_resolved','note':'yes'})
        self.assertEqual(ctx.exception.code,400)
    def test_export_csv(self):
        with urlopen(self.base+'/api/export/queue.csv') as r:
            data=r.read().decode('utf-8-sig')
        self.assertIn(self.tid,data)
        self.assertEqual(len(data.strip().splitlines()),49)

if __name__=='__main__':unittest.main()
