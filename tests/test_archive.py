import sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,Mock
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from history import History
from monitor import build_app
from aiohttp.test_utils import make_mocked_request

class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.h=History(Path(self.tmp.name)/'history.db');self.ip='192.168.1.102'
        for i in range(67):
            self.h.db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (f'{i:032x}',self.ip,'',f'Grüner_Halter_{i}.gcode','completed',1000+i,1100+i,1100+i,1,100,10,10,10))
        self.h.db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                ('a'*32,self.ip,'',"100%_Halter's.gcode",'paused',2000,2020,None,1,50,5,10,5))
        self.h.db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                ('b'*32,'192.168.1.101','','Halter.gcode','cancelled',2001,2021,2021,0,10,1,10,1))
        self.h.db.commit()
    def tearDown(self):self.h.close();self.tmp.cleanup()
    def test_full_archive_beyond_former_fifty_job_limit_and_no_duplicates(self):
        seen=[]
        for page in range(7):
            result=self.h.archive(self.ip,page=page)
            seen.extend(j['id'] for j in result['jobs'])
        self.assertEqual(len(seen),68);self.assertEqual(len(set(seen)),68)
        self.assertEqual(result['total'],68);self.assertEqual(result['pages'],7)
    def test_unicode_search_is_case_insensitive_and_percent_is_literal(self):
        self.assertEqual(self.h.archive(self.ip,search='GRÜNER')['total'],67)
        result=self.h.archive(self.ip,search="100%_Halter's")
        self.assertEqual(result['total'],1);self.assertEqual(result['jobs'][0]['id'],'a'*32)
        self.assertEqual(self.h.archive(self.ip,search="' OR 1=1 --")['total'],0)
    def test_filters_and_counts_are_printer_specific_and_summary_is_not_filtered(self):
        active=self.h.archive(self.ip,state='active')
        self.assertEqual(active['total'],1);self.assertEqual(active['jobs'][0]['state'],'paused')
        self.assertEqual(active['summary'],{'total':68,'completed':67,'cancelled':0,'active':1})
        self.assertEqual(self.h.archive('192.168.1.101',state='cancelled')['total'],1)
        self.assertEqual(self.h.archive(self.ip,state='cancelled')['total'],0)
    def test_out_of_range_page_clamps_and_invalid_input_is_rejected(self):
        self.assertEqual(self.h.archive(self.ip,page=500)['page'],6)
        self.assertEqual(self.h.archive(self.ip,search='missing',page=500)['page'],0)
        for kwargs in ({'page':-1},{'search':'a'*201},{'state':"completed' OR 1=1 --"}):
            with self.assertRaises(ValueError):self.h.archive(self.ip,**kwargs)

class ArchiveEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_archive_is_read_only_and_rejects_unknown_device_and_invalid_queries(self):
        h=SimpleNamespace(archive=Mock(return_value={'read_only':True,'jobs':[]}))
        app=build_app(SimpleNamespace(history=h,ips=['192.168.1.102'],start=AsyncMock(),stop=AsyncMock()))
        async def call(method,path):
            r=make_mocked_request(method,path);match=await app.router.resolve(r)
            return await app.middlewares[0](r,match.handler)
        base='/api/jobs?ip=192.168.1.102'
        self.assertEqual((await call('GET',base+'&page=2&search=PETG&state=completed')).status,200)
        h.archive.assert_called_once_with('192.168.1.102',search='PETG',state='completed',page=2)
        h.archive.reset_mock()
        for path in ('/api/jobs?ip=192.0.2.1',base+'&page=-1',base+'&page=abc',base+'&page=999999999'):
            self.assertEqual((await call('GET',path)).status,400)
        self.assertEqual((await call('POST',base)).status,403)
        h.archive.assert_not_called()

if __name__=='__main__':unittest.main()
