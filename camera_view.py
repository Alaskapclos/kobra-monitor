# SPDX-License-Identifier: GPL-3.0-only
"""Read existing stock S1 FLV streams; never publish camera/device commands."""
import asyncio
import contextlib
from functools import lru_cache
import subprocess
import shutil
import time
from aiohttp import web


@lru_cache(maxsize=1)
def decoder_available():
    executable=shutil.which('ffmpeg')
    if not executable:return False
    try:
        result=subprocess.run([executable,'-hide_banner','-h','protocol=http'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=3)
        return result.returncode==0 and b'max_redirects' in result.stdout
    except (OSError,subprocess.TimeoutExpired):return False


class CameraViews:
    """One shared JPEG decoder per viewed printer; idle readers are stopped."""
    def __init__(self, clock=time.monotonic, idle_seconds=15, limit=2):
        self.clock=clock; self.idle_seconds=idle_seconds; self.limit=limit
        self.readers={}; self.touched={}; self.janitor=None

    def available(self):
        return decoder_available()

    def _reader(self, ip):
        # Reuse the bundled bridge's FLV decoding and JPEG extraction. Its general
        # ensure_running() starts three output types; this adapter starts only JPEG.
        from kobrax_moonraker_bridge import CameraCache
        class SnapshotReader(CameraCache):
            def _input_args(self, url):
                return super()._input_args(url)+[
                    '-protocol_whitelist','http,tcp','-max_redirects','0','-f','flv','-threads','1']
        reader=SnapshotReader()
        reader.set_url(f'http://{ip}:18088/flv')
        return reader

    async def start(self, app):
        self.janitor=asyncio.create_task(self._cleanup_loop())

    async def _stop_reader(self, ip):
        reader=self.readers.pop(ip, None); self.touched.pop(ip, None)
        if reader is None:return
        task=reader._task_jpeg
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):await task
        reader.latest_jpeg=b''

    async def prune(self, configured=None):
        now=self.clock()
        for ip in list(self.readers):
            if ((configured is not None and ip not in configured) or
                    now-self.touched.get(ip,0)>self.idle_seconds):
                await self._stop_reader(ip)

    async def _cleanup_loop(self):
        while True:
            await asyncio.sleep(3)
            await self.prune()

    async def stop(self, app):
        if self.janitor is not None:
            self.janitor.cancel()
            with contextlib.suppress(asyncio.CancelledError):await self.janitor
        for ip in list(self.readers):await self._stop_reader(ip)

    async def frame(self, ip, configured):
        # Only configured literal printer IPs may become an input. Never accept a
        # stream URL from a browser or printer payload, and never follow redirects
        # to another protocol (ffmpeg's protocol/format allowlist is above).
        if ip not in configured:
            return web.json_response({'error':'Dieser Drucker ist nicht eingerichtet.'},status=400)
        if not self.available():
            return web.json_response({'error':'Die Kamera benötigt aktuelles FFmpeg auf dem Monitor-Rechner. Im NAS-Paket ist es enthalten.'},status=503)
        await self.prune(configured)
        reader=self.readers.get(ip)
        if reader is None:
            if len(self.readers)>=self.limit:
                return web.json_response({'error':'Gerade werden bereits zwei Kameras angesehen. Schließe eine andere Kamera und versuche es gleich erneut.'},status=503)
            reader=self._reader(ip);self.readers[ip]=reader
        self.touched[ip]=self.clock()
        if reader._task_jpeg is None or reader._task_jpeg.done():
            reader._task_jpeg=asyncio.create_task(reader._run_jpeg_loop())
        deadline=self.clock()+6
        while not reader.latest_jpeg and self.clock()<deadline:
            await asyncio.sleep(.1)
        if not reader.latest_jpeg or time.time()-reader.latest_jpeg_ts>10:
            return web.json_response({'error':'Noch kein aktuelles Kamerabild. Prüfe, ob die Kamera im LAN-Modus verfügbar ist.'},status=503)
        return web.Response(body=reader.latest_jpeg,content_type='image/jpeg',headers={
            'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
