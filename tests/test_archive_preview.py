"""Preview correctness and private-original boundaries using synthetic files only."""
import asyncio
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
import zipfile

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import archive_preview as preview
from access import Access
from history import History
from monitor import build_app
from file_archive import object_path, digest
from aiohttp.test_utils import make_mocked_request

MODEL = b'''<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" unit="millimeter"><resources><object id="1"><mesh><vertices><vertex x="0" y="0" z="0"/><vertex x="10" y="0" z="0"/><vertex x="0" y="10" z="5"/></vertices><triangles><triangle v1="0" v2="1" v3="2"/></triangles></mesh></object><object id="2"><components><component objectid="1" transform="1 0 0 0 1 0 0 0 1 5 0 0"/></components></object></resources><build><item objectid="2" transform="1 0 0 0 1 0 0 0 1 0 6 0"/></build></model>'''

def package(entries):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<Types/>')
        for name, data in entries.items(): z.writestr(name, data)
    return output.getvalue()


class PreviewTests(unittest.TestCase):
    def test_absolute_relative_extrusion_retract_and_travel(self):
        result = preview.toolpaths(b'G90\nM82\nG1 X10\nG1 Y10 E1\nG1 E0\nG92 E0\nM83\nG91\nG1 X5 E1\nG1 X2 E-1\n')
        self.assertEqual(result['segments'], [[10,0,0,10,10,0], [10,10,0,15,10,0]])

    def test_comments_and_homing_start_not_executed(self):
        result = preview.toolpaths(b'G28\nM104 S200\nG1 X0 Y0 Z0\nG1 X1 E1 ; G2 X9\n')
        self.assertEqual(result['segments'], [[0,0,0,1,0,0]])

    def test_unsupported_paths_are_not_silently_approximated(self):
        for data in [b'G2 X1 I1 E1', b'G28\nG1 X1 E1', b'G54\nG1 X1 E1', b'G1 X100001 E1', b'G1 X1', b'G1 X9999999999999999999999999999999999999 E1']:
            with self.subTest(data=data), self.assertRaises(ValueError): preview.toolpaths(data)

    def test_compact_gcode_does_not_treat_extruder_word_as_exponent(self):
        self.assertEqual(preview.toolpaths(b'G1X1Y2E1')['segments'], [[0,0,0,1,2,0]])

    def test_purge_then_homing_preserves_e_and_requires_known_xyz(self):
        result = preview.toolpaths(b'G1 X1 E2\nG28\nG1 X10 Y10 Z1\nG1 X11 E3\nG28\n')
        self.assertEqual(result['segments'], [[0,0,0,1,0,0], [10,10,1,11,10,1]])

    def test_axis_specific_homing_and_relative_move(self):
        result = preview.toolpaths(b'G1 X1 Y2 Z3 E1\nG28 Z\nG1 Z4\nG91\nM83\nG1 X2 E1')
        self.assertEqual(result['segments'][-1], [1,2,4,3,2,4])

    def test_geometry_bounds(self):
        with patch.object(preview, 'MAX_SEGMENTS', 1):
            with self.assertRaises(ValueError): preview.toolpaths(b'M83\nG1 X1 E1\nG1 X2 E1')
        with patch.object(preview, 'MAX_TRIANGLES', 0):
            with self.assertRaises(ValueError): preview.model(MODEL)

    def test_core_components_build_transforms_and_units(self):
        result = preview.model(MODEL)
        self.assertEqual(result['triangles'], [[5,6,0,15,6,0,5,16,5]])
        inch = preview.model(MODEL.replace(b'unit="millimeter"', b'unit="inch"'))
        self.assertAlmostEqual(inch['triangles'][0][0], 127)

    def test_xml_entities_cycles_indices_and_extensions_rejected(self):
        for data in [b'<!DOCTYPE x [<!ENTITY a "test">]>' + MODEL,
                     MODEL.decode().encode('utf-16'),
                     MODEL.replace(b'objectid="1"', b'objectid="2"'),
                     MODEL.replace(b'v1="0"', b'v1="-1"'),
                     MODEL.replace(b'unit="millimeter"', b'requiredextensions="p"'),
                     MODEL.replace(b'objectid="1"', b'xmlns:p="urn:extension" p:path="/other.model" objectid="1"')]:
            with self.subTest(data=data[:40]), self.assertRaises(ValueError): preview.model(data)

    def test_package_catalog_plate_selection_and_images(self):
        png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' + struct.pack('>II', 64, 64)
        with tempfile.TemporaryDirectory() as t:
            path = Path(t)/'test.3mf'
            path.write_bytes(package({'Metadata/plate_1.gcode': b'G1 X1 E1', 'Metadata/plate_2.gcode': b'G1 X2 E1', '3D/3dmodel.model': MODEL, 'Metadata/plate_1.png': png, 'Metadata/bad.png': b'<svg/>', 'private.json': b'secret'}))
            info = preview.catalog(path)
            self.assertEqual(len(info['sources']), 3)
            self.assertNotIn('secret', json.dumps(info))
            self.assertEqual(preview.geometry(path, 'Metadata/plate_2.gcode')['segments'][0][3], 2)
            self.assertEqual(preview.image(path, 'Metadata/plate_1.png'), png)
            for name in ['private.json', '../x.png', 'Metadata/bad.png']:
                with self.assertRaises(ValueError): preview.image(path, name)
            with self.assertRaises(ValueError): preview.geometry(path, 'private.json')
            with zipfile.ZipFile(path) as z, self.assertRaises(ValueError): preview.member(z, '3D/3dmodel.model', 10)


class PreviewHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def test_owner_only_integrity_and_unchanged_original(self):
        with tempfile.TemporaryDirectory() as t:
            h=History(Path(t)/'history.sqlite3');access=Access(t);access.account={'username':'fixture'}
            access.sessions['fixture']={'expires':access.clock()+100, 'csrf':'csrf'}
            app=build_app(SimpleNamespace(history=h,start=AsyncMock(),stop=AsyncMock()),access)
            token=h.files.new_client('fixture');client=h.files.authenticate(token)
            data=package({'Metadata/plate_1.gcode': b'G1 X1 E1'})
            incoming=h.files.incoming/'fixture.part';incoming.write_bytes(data)
            sha=hashlib.sha256(data).hexdigest();h.files.receive(incoming,'test.gcode.3mf',sha,len(data),client)
            async def call(query='',headers=None):
                request=make_mocked_request('GET','/api/archive/preview?sha256='+sha+query,headers={'Host':'localhost',**(headers or {})})
                match=await app.router.resolve(request);return await app.middlewares[0](request,match.handler)
            try:
                self.assertEqual((await call()).status,401)
                self.assertEqual((await call(headers={'Authorization':'Bearer '+token})).status,401)
                response=await call(headers={'Cookie':'kobra_session=fixture'})
                self.assertEqual(response.status,200);self.assertEqual(response.headers['Cache-Control'],'no-store')
                response=await call('&mode=geometry&name=Metadata/plate_1.gcode',{'Cookie':'kobra_session=fixture'})
                self.assertEqual(json.loads(response.text)['kind'],'gcode')
                path=object_path(h.files.root,sha);self.assertEqual(path.read_bytes(),data);self.assertEqual(digest(path),sha)
                path.write_bytes(b'changed')
                self.assertEqual((await call(headers={'Cookie':'kobra_session=fixture'})).status,400)
            finally:h.close()
