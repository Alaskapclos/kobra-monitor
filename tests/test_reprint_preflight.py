"""Repeat preparation uses synthetic originals; no printer transport exists here."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from types import SimpleNamespace
from unittest.mock import AsyncMock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import reprint_preflight as preflight
from access import Access
from history import History
from monitor import build_app
from file_archive import object_path
from aiohttp.test_utils import make_mocked_request


def entries(tool=1):
    paint = json.dumps([{'paint_index':tool, 'material_type':'PLA', 'paint_color':[33,39,33]}])
    gcode = f'; paint_info = {paint}\nT{tool}\nG1 X1 Y1 E1\n; paint_info = {paint}\n'.encode()
    return {
        '[Content_Types].xml':b'<Types/>',
        'Metadata/plate_1.gcode':gcode,
        'Metadata/plate_1.gcode.md5':hashlib.md5(gcode, usedforsecurity=False).hexdigest().encode(),
        'Metadata/project_settings.config':json.dumps({'printer_model':preflight.MODEL,'nozzle_diameter':['0.4'],
            'printable_area':['0x0','250x0','250x250','0x250'],'printable_height':'250',
            'filament_type':['PLA']*4,'filament_colour':['#212721']*4,'filament_diameter':['1.75']*4}).encode(),
        'Metadata/slice_info.config':f'''<config><plate>
        <metadata key="index" value="1"/>
        <metadata key="printer_model_id" value="Anycubic Kobra S1"/>
        <metadata key="nozzle_diameters" value="0.4"/>
        <metadata key="outside" value="false"/>
        <object skipped="false"/>
        <filament id="{tool+1}" type="PLA" color="#212721" used_g="29.41"/>
        </plate></config>'''.encode(),
    }


def package(data):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name, content in data.items():z.writestr(name,content)
    return out.getvalue()


class PreflightTests(unittest.TestCase):
    def inspect(self, data):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'original.gcode.3mf';raw=package(data);path.write_bytes(raw)
            result=preflight.inspect(path)
            self.assertEqual(path.read_bytes(),raw)
            return result

    def test_sparse_tool_one_is_not_silently_changed_to_tool_zero(self):
        data=entries();result=self.inspect(data)
        self.assertEqual(result['materials'],[{'paint_index':1,'type':'PLA','color':'#212721','estimated_g':29.41}])
        self.assertEqual(result['gcode_sha256'],hashlib.sha256(data['Metadata/plate_1.gcode']).hexdigest())
        self.assertFalse(result['printer_commands_sent']);self.assertFalse(result['start_authorized'])

    def test_rejects_other_model_missing_ambiguous_and_multiplate_metadata(self):
        cases=[]
        data=entries();data['Metadata/project_settings.config']=b'{"printer_model":"Kobra X","nozzle_diameter":["0.4"]}';cases.append(data)
        data=entries();del data['Metadata/project_settings.config'];cases.append(data)
        data=entries();data['Metadata/project_settings.config']=b'{"printer_model":"Anycubic Kobra S1","printer_model":"Anycubic Kobra S1","nozzle_diameter":["0.4"]}';cases.append(data)
        data=entries();data['Metadata/plate_2.gcode']=b'T0';cases.append(data)
        data=entries();data['Metadata/slice_info.config']=data['Metadata/slice_info.config'].replace(b'0.4',b'0.6');cases.append(data)
        data=entries();data['Metadata/slice_info.config']=data['Metadata/slice_info.config'].replace(b'outside" value="false',b'outside" value="true');cases.append(data)
        data=entries();data['Metadata/slice_info.config']=data['Metadata/slice_info.config'].replace(b'skipped="false',b'skipped="true');cases.append(data)
        for data in cases:
            with self.subTest(keys=list(data)),self.assertRaises(ValueError):self.inspect(data)

    def test_changed_inner_gcode_is_not_trusted_even_in_a_valid_zip(self):
        data=entries();data['Metadata/plate_1.gcode']+=b'M104 S999\n'
        with self.assertRaisesRegex(ValueError,'Prüfsumme'):self.inspect(data)

    def test_metadata_cannot_hide_additional_tools_or_inconsistent_materials(self):
        for old,new in [(b'T1',b'T0'),(b'T1',b'T1\nT2'),(b'T1',b'T255'),
                        (b'T1',b'T1 R1'),(b'"paint_index": 1',b'"paint_index": 0')]:
            data=entries();data['Metadata/plate_1.gcode']=data['Metadata/plate_1.gcode'].replace(old,new)
            data['Metadata/plate_1.gcode.md5']=hashlib.md5(data['Metadata/plate_1.gcode'],usedforsecurity=False).hexdigest().encode()
            with self.subTest(new=new),self.assertRaises(ValueError):self.inspect(data)
        data=entries();data['Metadata/slice_info.config']=data['Metadata/slice_info.config'].replace(b'type="PLA"',b'type="PETG"')
        with self.assertRaises(ValueError):self.inspect(data)

    def test_xml_entities_utf16_and_oversized_sources_rejected(self):
        for xml in [b'<!DOCTYPE config [<!ENTITY x "foo">]><config/>',
                    '<!DOCTYPE config [<!ENTITY x "foo">]><config/>'.encode('utf-16'),
                    b'x'*(preflight.MAX_METADATA+1)]:
            data=entries();data['Metadata/slice_info.config']=xml
            with self.assertRaises(ValueError):self.inspect(data)
        data=entries();data['Metadata/plate_1.gcode']=b'x'*(preflight.MAX_LINE+1)
        with self.assertRaises(ValueError):self.inspect(data)

    def test_wrong_bed_profile_and_filament_diameter_are_blocked(self):
        for changes in ({'printable_height':'350'},{'printable_height':'NaN'},
                        {'printable_area':['0x0','350x0','350x350','0x350']},
                        {'filament_diameter':['2.85']*4},{'filament_colour':['#ffffff']*4},
                        {'filament_type':['PETG']*4}):
            data=entries();settings=json.loads(data['Metadata/project_settings.config']);settings.update(changes)
            data['Metadata/project_settings.config']=json.dumps(settings).encode()
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.inspect(data)

    def test_multimaterial_preserves_explicit_tool_numbers(self):
        data=entries(0)
        paint=json.dumps([{'paint_index':i,'material_type':'PLA','paint_color':[33,39,33]} for i in (0,2)])
        data['Metadata/plate_1.gcode']=f'; paint_info = {paint}\nT0\nG1 X1 E1\nT2\nG1 X2 E2\n'.encode()
        data['Metadata/plate_1.gcode.md5']=hashlib.md5(data['Metadata/plate_1.gcode'],usedforsecurity=False).hexdigest().encode()
        data['Metadata/slice_info.config']=data['Metadata/slice_info.config'].replace(b'</plate>',b'<filament id="3" type="PLA" color="#212721" used_g="1"/></plate>')
        self.assertEqual([m['paint_index'] for m in self.inspect(data)['materials']],[0,2])


class PreflightHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def test_owner_only_verified_original_and_no_printer_methods(self):
        with tempfile.TemporaryDirectory() as t:
            history=History(Path(t)/'history.sqlite3');access=Access(t)
            access.account={'username':'fixture'}
            access.sessions['fixture']={'expires':access.clock()+100,'csrf':'csrf'}
            # Deliberately no monitors, connections, senders or control manager.
            app=build_app(SimpleNamespace(history=history,start=AsyncMock(),stop=AsyncMock()),access)
            token=history.files.new_client('fixture');client=history.files.authenticate(token)
            raw=package(entries());sha=hashlib.sha256(raw).hexdigest()
            temporary=history.files.incoming/'fixture.part';temporary.write_bytes(raw)
            history.files.receive(temporary,'test.gcode.3mf',sha,len(raw),client)
            async def call(headers=None):
                request=make_mocked_request('GET','/api/archive/preview?mode=preflight&sha256='+sha,
                    headers={'Host':'localhost',**(headers or {})})
                match=await app.router.resolve(request)
                return await app.middlewares[0](request,match.handler)
            try:
                self.assertEqual((await call()).status,401)
                self.assertEqual((await call({'Authorization':'Bearer '+token})).status,401)
                result=await call({'Cookie':'kobra_session=fixture'})
                self.assertEqual(result.status,200)
                self.assertEqual(result.headers['Cache-Control'],'no-store')
                data=json.loads(result.text);self.assertEqual(data['original_sha256'],sha)
                self.assertFalse(data['start_authorized'])
                path=object_path(history.files.root,sha);self.assertEqual(path.read_bytes(),raw)
                path.write_bytes(package(entries(0)))
                self.assertEqual((await call({'Cookie':'kobra_session=fixture'})).status,400)
            finally:history.close()


if __name__=='__main__':unittest.main()
