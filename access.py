# SPDX-License-Identifier: GPL-3.0-only
"""Installation access code and short-lived browser sessions."""
import hmac
import os
from pathlib import Path
import secrets
import time
from urllib.parse import urlsplit
from aiohttp import web

class Access:
    def __init__(self,directory,clock=time.monotonic):
        self.clock=clock;self.sessions={};self.attempts={}
        directory=Path(directory);directory.mkdir(parents=True,exist_ok=True,mode=0o700)
        path=directory/'access-token'
        supplied=os.environ.get('KOBRA_ACCESS_TOKEN')
        if supplied:
            if len(supplied)<24:raise ValueError('KOBRA_ACCESS_TOKEN muss mindestens 24 Zeichen lang sein.')
            self.token=supplied
        else:
            try:
                with path.open('x') as out:
                    os.chmod(path,0o600);out.write(secrets.token_urlsafe(24)+'\n')
            except FileExistsError:pass
            self.token=path.read_text().strip()
            if len(self.token)<24:raise ValueError('Lokaler Zugangscode ist ungültig.')
            os.chmod(path,0o600)
    def session(self,request):
        key=request.cookies.get('kobra_session','')
        value=self.sessions.get(key)
        if value and value['expires']>self.clock():return value
        self.sessions.pop(key,None)
        return None
    @staticmethod
    def same_origin(request):
        origin=request.headers.get('Origin')
        if request.headers.get('Sec-Fetch-Site')=='cross-site':return False
        if not origin:return True # CLI clients still need the access code or CSRF token.
        try:parsed=urlsplit(origin)
        except ValueError:return False
        return parsed.scheme in ('http','https') and parsed.netloc==request.host
    def can_write(self,request):
        session=self.session(request)
        return bool(session and self.same_origin(request) and
                    hmac.compare_digest(request.headers.get('X-Kobra-CSRF','').encode(),session['csrf'].encode()))
    async def login(self,request):
        if not self.same_origin(request) or request.content_type!='application/json':
            return web.json_response({'error':'Anmeldung nur von dieser Oberfläche erlaubt.'},status=403)
        now=self.clock();peer=request.remote or 'local'
        self.attempts={key:v for key,v in self.attempts.items() if now-v[0]<60}
        count=self.attempts.get(peer,(now,0))
        if count[1]>=5:return web.json_response({'error':'Bitte eine Minute warten und erneut versuchen.'},status=429)
        try:body=await request.json()
        except (ValueError,TypeError):body={}
        code=body.get('code','') if isinstance(body,dict) else ''
        if not isinstance(code,str) or not hmac.compare_digest(code.encode(),self.token.encode()):
            if len(self.attempts)>1024:self.attempts.clear()
            self.attempts[peer]=(count[0],count[1]+1)
            return web.json_response({'error':'Der Zugangscode stimmt nicht.'},status=401)
        self.attempts.pop(peer,None)
        self.sessions={key:v for key,v in self.sessions.items() if v['expires']>now}
        if len(self.sessions)>=128:self.sessions.pop(next(iter(self.sessions)))
        key=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24)
        self.sessions[key]={'expires':now+43200,'csrf':csrf}
        response=web.json_response({'authenticated':True,'csrf':csrf,'read_only':True})
        secure=request.secure or request.headers.get('Origin','').startswith('https://')
        response.set_cookie('kobra_session',key,httponly=True,samesite='Strict',secure=secure,max_age=43200)
        return response
