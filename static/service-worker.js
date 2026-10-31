/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
// No page, login, API, or camera caching. The service worker only handles push.
self.addEventListener('push',event=>{
  let data={};try{data=event.data?.json()||{};}catch{}
  const text=value=>typeof value==='string'?value.slice(0,200):'';
  event.waitUntil(self.registration.showNotification(text(data.title)||'Kobra Monitor',{
    body:text(data.body)||'Eine neue Meldung ist verfügbar.',tag:text(data.tag)||undefined,
    icon:'/assets/app-icon.svg',data:{url:'/'},timestamp:Date.now()
  }));
});
self.addEventListener('notificationclick',event=>{
  event.notification.close();
  event.waitUntil((async()=>{
    const target=new URL('/',self.location.origin).href;
    for(const client of await self.clients.matchAll({type:'window',includeUncontrolled:true})){
      if(new URL(client.url).origin===self.location.origin&&'focus' in client){await client.navigate(target);return client.focus();}
    }
    return self.clients.openWindow(target);
  })());
});
