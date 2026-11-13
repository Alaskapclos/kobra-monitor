/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
window.kobraPreview=(()=>{
  const $=id=>document.getElementById(id);
  const node=(tag,value)=>{const n=document.createElement(tag);if(value)n.textContent=value;return n;};
  const url=(sha,mode='catalog',name='')=>'/api/archive/preview?'+new URLSearchParams({sha256:sha,mode,name});
  let generation=0,controller=null,dispose=()=>{},focus=null;
  async function request(sha,mode,name,signal){
    const response=await fetch(url(sha,mode,name),{signal,cache:'no-store'});
    const data=await response.json();if(!response.ok)throw new Error(data.error||'Vorschau nicht verfügbar.');return data;
  }
  function button(label,action){const b=node('button',label);b.type='button';b.className='timeline-button';b.addEventListener('click',action);return b;}
  function close(){generation++;controller?.abort();dispose();dispose=()=>{};$('file-preview').hidden=true;$('file-preview-body').replaceChildren();focus?.focus();}
  $('file-preview-close').addEventListener('click',close);
  window.addEventListener('hashchange',close);
  window.addEventListener('keydown',event=>{if(event.key==='Escape'&&!$('file-preview').hidden)close();});
  function accelerated(canvas,data,center,span){
    const gl=canvas.getContext('webgl',{antialias:true,alpha:false});if(!gl)return null;
    const shader=(kind,source)=>{const s=gl.createShader(kind);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error('3D-Darstellung konnte nicht vorbereitet werden.');return s;};
    const vertex=shader(gl.VERTEX_SHADER,`attribute vec3 position;attribute float top;attribute float shade;uniform vec3 center;uniform float span;uniform vec2 scale;uniform vec2 angle;varying float height;varying float light;void main(){vec3 p=(position-center)/span;float a=p.x*cos(angle.x)-p.y*sin(angle.x);float b=p.x*sin(angle.x)+p.y*cos(angle.x);float y=p.z*cos(angle.y)-b*sin(angle.y);float depth=b*cos(angle.y)+p.z*sin(angle.y);gl_Position=vec4(a*scale.x,y*scale.y,-depth*.2,1.);height=top;light=shade;}`);
    const fragment=shader(gl.FRAGMENT_SHADER,`precision mediump float;uniform float layer;uniform vec3 color;varying float height;varying float light;void main(){if(height>layer+.001)discard;gl_FragColor=vec4(color*light,1.);}`);
    const program=gl.createProgram();gl.attachShader(program,vertex);gl.attachShader(program,fragment);gl.linkProgram(program);
    if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error('3D-Darstellung wird von diesem Browser nicht unterstützt.');
    const shapes=data.kind==='model'?data.triangles:data.segments,count=shapes.length*(data.kind==='model'?3:2),values=new Float32Array(count*5);let offset=0;
    for(const shape of shapes){
      let shade=.55+.45*Math.abs((shape[3]-shape[0])/(Math.hypot(shape[3]-shape[0],shape[4]-shape[1])||1));
      if(data.kind==='model'){
        const a=[shape[3]-shape[0],shape[4]-shape[1],shape[5]-shape[2]],b=[shape[6]-shape[0],shape[7]-shape[1],shape[8]-shape[2]],n=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
        const length=Math.hypot(...n)||1;shade=.45+.55*Math.abs((n[0]*.3+n[1]*.4+n[2]*.866)/length);
      }
      const top=data.kind==='model'?0:Math.max(shape[2],shape[5]);
      for(let i=0;i<shape.length;i+=3){values[offset++]=shape[i];values[offset++]=shape[i+1];values[offset++]=shape[i+2];values[offset++]=top;values[offset++]=shade;}
    }
    const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,values,gl.STATIC_DRAW);gl.useProgram(program);
    for(const [name,size,offset] of [['position',3,0],['top',1,12],['shade',1,16]]){const location=gl.getAttribLocation(program,name);gl.enableVertexAttribArray(location);gl.vertexAttribPointer(location,size,gl.FLOAT,false,20,offset);}
    const uniform=name=>gl.getUniformLocation(program,name);
    gl.uniform3fv(uniform('center'),center);gl.uniform1f(uniform('span'),span);gl.uniform3fv(uniform('color'),data.kind==='model'?[.65,.78,.42]:[.25,.4,.17]);gl.clearColor(.945,.953,.914,1);gl.enable(gl.DEPTH_TEST);
    return {draw(yaw,pitch,zoom,layer){
      gl.viewport(0,0,canvas.width,canvas.height);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
      const small=Math.min(canvas.width,canvas.height);gl.uniform2f(uniform('scale'),1.3*small/canvas.width*zoom,1.3*small/canvas.height*zoom);gl.uniform2f(uniform('angle'),yaw,pitch);gl.uniform1f(uniform('layer'),Number.isFinite(layer)?layer:1e9);gl.drawArrays(data.kind==='model'?gl.TRIANGLES:gl.LINES,0,count);
    },dispose(){gl.deleteBuffer(buffer);gl.deleteProgram(program);gl.deleteShader(vertex);gl.deleteShader(fragment);gl.getExtension('WEBGL_lose_context')?.loseContext();}};
  }
  function viewer(host,data){
    const canvas=node('canvas');canvas.className='archive-canvas';canvas.tabIndex=0;canvas.setAttribute('aria-label','3D-Vorschau. Mit Ziehen oder Pfeiltasten drehen, mit Plus und Minus zoomen.');
    const controls=node('div');controls.className='notify-actions';
    host.append(canvas,controls,node('p','Ziehen zum Drehen · Mausrad oder +/− zum Zoomen · Pfeiltasten zum Drehen.'),node('p',data.note));
    const shapes=data.kind==='model'?data.triangles:data.segments;
    const minimum=[Infinity,Infinity,Infinity],maximum=[-Infinity,-Infinity,-Infinity];
    for(const shape of shapes)for(let i=0;i<shape.length;i++){
      const axis=i%3;minimum[axis]=Math.min(minimum[axis],shape[i]);maximum[axis]=Math.max(maximum[axis],shape[i]);
    }
    const center=minimum.map((v,i)=>(v+maximum[i])/2),span=Math.max(...maximum.map((v,i)=>v-minimum[i]),1);
    let yaw=.6,pitch=.95,zoom=1,frame=0,drag=null,layer=Infinity;
    const gpu=accelerated(canvas,data,center,span),context=gpu?null:canvas.getContext('2d');
    if(!gpu&&(!context||shapes.length>50000))throw new Error('Diese große Vorschau benötigt WebGL. Bitte das Vorschaubild verwenden oder einen Browser mit 3D-Unterstützung öffnen.');
    function project(shape){
      const points=[];
      for(let i=0;i<shape.length;i+=3){
        const x=shape[i]-center[0],y=shape[i+1]-center[1],z=shape[i+2]-center[2];
        const a=x*Math.cos(yaw)-y*Math.sin(yaw),b=x*Math.sin(yaw)+y*Math.cos(yaw);
        const scale=Math.min(canvas.width,canvas.height)*.65/span*zoom;
        points.push([canvas.width/2+a*scale,canvas.height/2-(z*Math.cos(pitch)-b*Math.sin(pitch))*scale,b*Math.cos(pitch)+z*Math.sin(pitch)]);
      }return points;
    }
    function draw(){
      frame=0;const rect=canvas.getBoundingClientRect(),ratio=Math.min(window.devicePixelRatio||1,2);
      canvas.width=Math.max(1,Math.round(rect.width*ratio));canvas.height=Math.max(1,Math.round(rect.height*ratio));
      if(gpu){gpu.draw(yaw,pitch,zoom,layer);return;}
      context.clearRect(0,0,canvas.width,canvas.height);context.lineWidth=ratio;
      let visible=shapes;
      if(data.kind==='gcode')visible=shapes.filter(s=>Math.max(s[2],s[5])<=layer+.001);
      const projected=visible.map(project);
      if(data.kind==='model')projected.sort((a,b)=>a.reduce((s,p)=>s+p[2],0)-b.reduce((s,p)=>s+p[2],0));
      for(const points of projected){
        context.beginPath();context.moveTo(points[0][0],points[0][1]);for(const p of points.slice(1))context.lineTo(p[0],p[1]);
        if(data.kind==='model'){context.closePath();context.fillStyle='#b8ca8a';context.fill();context.strokeStyle='#61734d';}else context.strokeStyle='#557844';
        context.stroke();
      }
    }
    function schedule(){if(!frame)frame=requestAnimationFrame(draw);}
    function zoomBy(factor){zoom=Math.max(.2,Math.min(8,zoom*factor));schedule();}
    controls.append(button('+',()=>zoomBy(1.2)),button('−',()=>zoomBy(1/1.2)),button('Ansicht zurücksetzen',()=>{yaw=.6;pitch=.95;zoom=1;schedule();}));
    if(data.kind==='gcode'){
      const levels=[...new Set(shapes.map(s=>Math.max(s[2],s[5])))].sort((a,b)=>a-b);
      const label=node('label','Druckbahnen bis Höhe: '),output=node('output'),slider=node('input');slider.type='range';slider.min='0';slider.max=String(levels.length-1);slider.value=slider.max;
      const update=()=>{layer=levels[Number(slider.value)];output.textContent=layer.toLocaleString('de-DE',{maximumFractionDigits:2})+' mm';schedule();};
      slider.addEventListener('input',update);label.append(output,slider);host.append(label);update();
    }
    canvas.addEventListener('pointerdown',event=>{drag=[event.clientX,event.clientY];canvas.setPointerCapture(event.pointerId);});
    canvas.addEventListener('pointermove',event=>{if(!drag)return;yaw+=(event.clientX-drag[0])*.01;pitch=Math.max(-1.5,Math.min(1.5,pitch+(event.clientY-drag[1])*.01));drag=[event.clientX,event.clientY];schedule();});
    for(const event of ['pointerup','pointercancel','lostpointercapture'])canvas.addEventListener(event,()=>{drag=null;});
    canvas.addEventListener('wheel',event=>{event.preventDefault();zoomBy(event.deltaY<0?1.1:1/1.1);},{passive:false});
    canvas.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','-'].includes(event.key))return;event.preventDefault();if(event.key==='ArrowLeft')yaw-=.1;if(event.key==='ArrowRight')yaw+=.1;if(event.key==='ArrowUp')pitch+=.1;if(event.key==='ArrowDown')pitch-=.1;if(event.key==='+')zoomBy(1.2);if(event.key==='-')zoomBy(1/1.2);schedule();});
    const observer=new ResizeObserver(schedule);observer.observe(canvas);schedule();
    return ()=>{observer.disconnect();if(frame)cancelAnimationFrame(frame);gpu?.dispose();};
  }
  async function open(file,trigger){
    close();focus=trigger;const current=++generation;controller=new AbortController();const signal=controller.signal;
    $('file-preview').hidden=false;$('file-preview-title').textContent=file.names.join(' / ');
    const body=$('file-preview-body');body.replaceChildren(node('p','Vorschau wird geladen …'));
    $('file-preview-close').focus();
    try{
      const info=await request(file.sha256,'catalog','',signal);if(current!==generation)return;
      body.replaceChildren();const choices=node('div'),display=node('div'),message=node('p');choices.className='notify-actions';message.setAttribute('role','status');body.append(choices,message,display);
      let selection=0;
      const showImage=name=>{const selected=++selection;dispose();display.replaceChildren();const img=node('img');img.className='archive-large-image';img.alt='Eingebettetes Vorschaubild';img.src=url(file.sha256,'image',name);img.addEventListener('error',()=>{if(current===generation&&selected===selection)message.textContent='Das eingebettete Bild kann nicht dargestellt werden.';});display.append(img);message.textContent='Vorschaubild des Slicers';};
      for(const name of info.images)choices.append(button('Bild: '+name.split('/').pop(),()=>showImage(name)));
      for(const source of info.sources)choices.append(button((source.kind==='model'?'3D-Modell: ':'3D-Druckbahnen: ')+source.name.split('/').pop(),async()=>{
        const selected=++selection;dispose();display.replaceChildren();message.textContent='3D-Daten werden vorbereitet …';
        try{const data=await request(file.sha256,'geometry',source.name,signal);if(current!==generation||selected!==selection)return;message.textContent='';dispose=viewer(display,data);}
        catch(error){if(current===generation&&selected===selection&&error.name!=='AbortError')message.textContent=error.message;}
      }));
      if(info.images.length)showImage(info.images[0]);else message.textContent=info.sources.length?'Kein Vorschaubild eingebettet. Bitte eine 3D-Quelle auswählen.':'Keine unterstützten Vorschaudaten enthalten.';
      const download=node('a','Originaldatei herunterladen');download.className='timeline-button';download.href='/api/archive/original?sha256='+file.sha256;download.download='';body.append(download);
    }catch(error){if(current===generation&&error.name!=='AbortError')body.replaceChildren(node('p',error.message));}
  }
  // One lazy thumbnail request at a time; invisible cards do not load originals.
  let queue=Promise.resolve();
  function thumbnail(host,file){
    const placeholder=node('span','Keine Bildvorschau');host.append(placeholder);
    if(typeof IntersectionObserver==='undefined')return ()=>{};
    const observer=new IntersectionObserver(entries=>{
      if(!entries.some(entry=>entry.isIntersecting))return;observer.disconnect();
      queue=queue.then(async()=>{
        if(!host.isConnected||!window.kobraAuth.authenticated)return;
        try{const info=await request(file.sha256);if(!host.isConnected||!info.images.length)return;
          const response=await fetch(url(file.sha256,'image',info.images[0]),{cache:'no-store'});if(!response.ok)return;
          const blob=await response.blob();if(!host.isConnected)return;const image=node('img');image.alt='';const local=URL.createObjectURL(blob);image.src=local;image.onload=image.onerror=()=>URL.revokeObjectURL(local);host.replaceChildren(image);
        }catch{/* Thumbnail absence never disables opening or downloading. */}
      });
    });observer.observe(host);return ()=>observer.disconnect();
  }
  return {open,close,thumbnail};
})();
