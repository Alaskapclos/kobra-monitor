# SPDX-License-Identifier: GPL-3.0-only
"""Installation access code and short-lived browser sessions."""
import asyncio
import hmac
import os
from pathlib import Path
import secrets
import time
from urllib.parse import urlsplit
from aiohttp import web
from accounts import read_account, write_account, matches, username, password

class Access:
    def __init__(self,directory,clock=time.monotonic):
        self.clock=clock;self.sessions={};self.attempts={};self.global_attempts=[]
        self.directory=Path(directory);self.account=read_account(directory);self.busy=asyncio.Lock()
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
    def state(self,request):
        current=self.session(request)
        return {'authenticated':bool(current),'csrf':current['csrf'] if current else None,
                'account_configured':self.account is not None,
                'username':self.account['username'] if current and self.account else None,
                'read_only':True}

    def failure(self,peer,now):
        first,count=self.attempts.get(peer,(now,0))
        self.attempts[peer]=(first,count+1)
        self.global_attempts.append(now)

    def limited(self,peer,now):
        self.attempts={key:v for key,v in self.attempts.items() if now-v[0]<60}
        self.global_attempts=[at for at in self.global_attempts if now-at<60]
        return (self.attempts.get(peer,(now,0))[1]>=5 or len(self.global_attempts)>=30
                or (peer not in self.attempts and len(self.attempts)>=1024))

    def signed_in(self,request):
        now=self.clock()
        self.sessions={key:v for key,v in self.sessions.items() if v['expires']>now}
        if len(self.sessions)>=128:self.sessions.pop(next(iter(self.sessions)))
        key=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24)
        self.sessions[key]={'expires':now+43200,'csrf':csrf}
        response=web.json_response({'authenticated':True,'csrf':csrf,
            'account_configured':self.account is not None,
            'username':self.account['username'] if self.account else None,'read_only':True})
        secure=request.secure or request.headers.get('Origin','').startswith('https://')
        response.set_cookie('kobra_session',key,httponly=True,samesite='Strict',secure=secure,max_age=43200)
        return response

    async def login(self,request):
        if not self.same_origin(request) or request.content_type!='application/json':
            return web.json_response({'error':'Anmeldung nur von dieser Oberfläche erlaubt.'},status=403)
        now=self.clock();peer=request.remote or 'local'
        if self.limited(peer,now) or self.busy.locked():
            return web.json_response({'error':'Bitte eine Minute warten und erneut versuchen.'},status=429)
        try:body=await request.json()
        except (ValueError,TypeError):body={}
        if not isinstance(body,dict):body={}
        if self.busy.locked():
            return web.json_response({'error':'Bitte kurz warten und erneut versuchen.'},status=429)
        async with self.busy:
            if self.account:
                ok=await asyncio.to_thread(matches,self.account,body.get('username'),body.get('password'))
            else:
                code=body.get('code','')
                ok=isinstance(code,str) and hmac.compare_digest(code.encode(),self.token.encode())
            if not ok:
                self.failure(peer,now)
                return web.json_response({'error':'Die Anmeldedaten stimmen nicht.'},status=401)
            self.attempts.pop(peer,None)
            return self.signed_in(request)

    async def save_account(self,request):
        if not self.can_write(request) or request.content_type!='application/json':
            return web.json_response({'error':'Konto bitte aus dieser Oberfläche aufrufen.'},status=403)
        now=self.clock();peer=request.remote or 'local'
        if self.limited(peer,now) or self.busy.locked():
            return web.json_response({'error':'Bitte eine Minute warten und erneut versuchen.'},status=429)
        try:
            body=await request.json()
            name=username(body.get('username'));secret=password(body.get('password'))
            if secret!=body.get('password_confirmation'):
                raise ValueError('Die beiden Passwörter stimmen nicht überein.')
        except (ValueError,TypeError,AttributeError) as exc:
            return web.json_response({'error':str(exc) if isinstance(exc,ValueError) else 'Bitte alle Felder ausfüllen.'},status=400)
        if self.busy.locked():
            return web.json_response({'error':'Bitte kurz warten und erneut versuchen.'},status=429)
        async with self.busy:
            # Recheck after reading the body: another request may have replaced the account/session.
            if not self.can_write(request):
                return web.json_response({'error':'Bitte erneut anmelden.'},status=401)
            if self.account and not await asyncio.to_thread(matches,self.account,self.account['username'],body.get('current_password')):
                self.failure(peer,now)
                return web.json_response({'error':'Das bisherige Passwort stimmt nicht.'},status=401)
            self.account=await asyncio.to_thread(write_account,self.directory,name,secret)
            self.sessions.clear();self.attempts.pop(peer,None)
            return self.signed_in(request)

    async def logout(self,request):
        if not self.can_write(request):
            return web.json_response({'error':'Bitte erneut anmelden.'},status=403)
        self.sessions.pop(request.cookies.get('kobra_session',''),None)
        response=web.json_response({'authenticated':False,'read_only':True})
        response.del_cookie('kobra_session',httponly=True,samesite='Strict')
        return response
