'use strict';
const $ = id => document.getElementById(id);
const sounds = [
  {kind:'tick', title:'Ordklocka', tag:'Lågt tick', color:'#78988a', file:'00_ordklocka_tick_var_30e_ord.wav', description:'Ett tick efter varje 30 ord. Markerar textens tempo, inte en misstanke.'},
  {kind:'pair', title:'Fraspar', tag:'Två flippertoner', color:'#b3e7bd', file:'01_fraspar_flipper_lag_hog.wav', description:'Två korta, balanserade nominala led kring ”och” eller ”eller”.'},
  {kind:'triad', title:'Treled', tag:'Tre stigande klockor', color:'#83beee', file:'02_treled_flipperklockor.wav', description:'En balanserad liststruktur: A, B och C.'},
  {kind:'contrast', title:'Retorisk kontrast', tag:'Två tivolitoner', color:'#c7a2ef', file:'04_kontrast_tivolisignal.wav', description:'Kontrastmallar som ”inte … utan” eller ”snarare”.'},
  {kind:'density', title:'Tätt strukturkluster', tag:'Mekaniskt dubbellarm', color:'#efbd76', file:'03_tathetsvarning_mekaniskt_dubbellarm.wav', description:'Flera hörbara strukturer nära varandra inom ett avsnitt på 180 ord.'},
  {kind:'wow', title:'Starkt strukturkluster', tag:'Långt wow-svep', color:'#f08d9a', file:'05_extremkluster_wow_svep.wav', description:'En särskilt stark ansamling av strukturer. Ingen slutsats om författarskap.'}
];
let data = null, audioBlob = null, audioUrl = null, demoAudio = null;
const audio = $('audio'), canvas = $('timeline');
for (const s of sounds) {
  const button = document.createElement('button'); button.type='button'; button.className='sound-card'; button.style.setProperty('--color', s.color);
  for (const [tag, cls, text] of [['span','tag',s.tag],['span','play','▶'],['h3','',s.title],['p','',s.description]]) {
    const child = document.createElement(tag); child.className=cls; child.textContent=text; button.append(child);
  }
  button.setAttribute('aria-label', `Lyssna på ${s.title}`);
  button.onclick = () => { if(demoAudio) demoAudio.pause(); audio.pause(); demoAudio=new Audio('/static/soundbank/'+s.file); demoAudio.play().catch(() => status('Ljudet kunde inte spelas upp.', true)); };
  $('sound-guide').append(button);
}
function status(message, error=false) { $('status').textContent=message; $('status').classList.toggle('error',error); }
$('text').addEventListener('input', () => { const words=$('text').value.match(/[\p{L}\p{N}]+/gu)||[]; $('word-count').textContent=`${words.length.toLocaleString('sv-SE')} ord`; });
function clearFile(){ $('file').value=''; $('file-label').textContent='Välj en textfil'; $('clear-file').hidden=true; }
$('clear-file').onclick=clearFile;
$('file').onchange=() => { const f=$('file').files[0]; $('file-label').textContent=f ? f.name : 'Välj en textfil'; $('clear-file').hidden=!f; if(f) status('Den valda filen används i stället för den inklistrade texten.'); };
$('example').onclick=() => {
  clearFile(); $('text').value='Utbildning handlar inte enbart om kunskap utan också om ansvar. Tydlighet, öppenhet och respekt skapar goda förutsättningar. Analys och reflektion hjälper oss att förstå materialet. Samarbete, dialog och återkoppling stödjer lärandet. Kvalitet och tillit är viktiga delar av undervisningen. Nyfikenhet, självständighet och kreativitet öppnar nya möjligheter. Det är inte resultatet utan processen som står i centrum. Jag läste boken och sedan skrev jag ned vad jag tänkte. Och jag ändrade min uppfattning när vi pratade om kapitlet.';
  $('text').dispatchEvent(new Event('input')); status('Exempeltext laddad. Den demonstrerar ljudsignaler, inte AI-författarskap.');
};
$('analyze').onclick=async () => {
  const file=$('file').files[0]; if(!file&&!$('text').value.trim()){status('Klistra in text eller välj en fil.',true);return;}
  if(file&&file.size>2*1024*1024){status('Filen är för stor. Max 2 MB.',true);return;}
  const form=new FormData(); if(file)form.append('file',file);else form.append('text',$('text').value);
  audio.pause(); if(demoAudio)demoAudio.pause(); $('analyze').disabled=true; status('Analyserar strukturer och skapar ljud…');
  try {
    const response=await fetch('/api/analyze',{method:'POST',body:form});
    const result=await response.json(); if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:'Analysen kunde inte genomföras.');
    data=result; const bytes=Uint8Array.from(atob(result.audio_base64), c=>c.charCodeAt(0)); audioBlob=new Blob([bytes],{type:'audio/wav'});
    if(audioUrl)URL.revokeObjectURL(audioUrl); audioUrl=URL.createObjectURL(audioBlob); audio.src=audioUrl; audio.load();
    $('empty').hidden=true; $('results').hidden=false; $('result-label').textContent='ANALYS KLAR';
    const report=data.report, info=report.audio;
    $('metric-words').textContent=report.features.words.toLocaleString('sv-SE'); $('metric-pairs').textContent=info.audible_pair_count; $('metric-triads').textContent=info.audible_triad_count;
    $('style-index').textContent=report.features.anomaly_index.toFixed(3);
    $('reasons').replaceChildren(...report.reasons.map(reason=>{const li=document.createElement('li');li.textContent=reason;return li;}));
    $('examples').replaceChildren(...report.coordination_examples.map(record=>{const p=document.createElement('p');p.textContent=`Ord ${record.word_index}: ${record.left || record.left_phrase || ''} ${record.conj || record.conjunction || 'och/eller'} ${record.right || record.right_phrase || ''} · ${record.audio_class}`;return p;}));
    $('now-text').textContent='Tryck på spela för att följa ljudhändelserna.'; draw(); status('Ljud och rapport är klara. Klicka i tidslinjen för att hoppa till ett avsnitt.');
  } catch(error){status(error.message || 'Servern kunde inte nås. Försök igen.',true);} finally{$('analyze').disabled=false;}
};
function clock(t){return `${Math.floor(t/60)}:${Math.floor(t%60).toString().padStart(2,'0')}`;}
function draw(){
  if(!data)return;
  const ratio=window.devicePixelRatio||1,w=canvas.clientWidth,h=canvas.clientHeight;
  if(canvas.width!==Math.round(w*ratio)||canvas.height!==Math.round(h*ratio)){canvas.width=Math.round(w*ratio);canvas.height=Math.round(h*ratio);}
  const ctx=canvas.getContext('2d');ctx.setTransform(ratio,0,0,ratio,0,0);ctx.clearRect(0,0,w,h);
  const duration=data.report.audio.seconds,time=audio.currentTime||0,events=data.report.timeline;
  sounds.forEach((s,i)=>{const y=16+i*24;ctx.strokeStyle='#263c30';ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();});
  for(const e of events){const index=sounds.findIndex(s=>s.kind===e.kind),x=e.time/duration*w,y=16+index*24;ctx.fillStyle=sounds[index].color;ctx.globalAlpha=e.time<=time?.85:.4;ctx.fillRect(x,y-4,Math.max(2,e.duration/duration*w),8);}
  ctx.globalAlpha=1;ctx.strokeStyle='#ecf6ed';ctx.beginPath();ctx.moveTo(time/duration*w,0);ctx.lineTo(time/duration*w,h);ctx.stroke();
  $('position').textContent=`Ord ${Math.min(data.report.features.words, Math.max(0,Math.floor((time-.45)*200))).toLocaleString('sv-SE')}`;
  $('time').textContent=`${clock(time)} / ${clock(duration)}`;
  const active=events.filter(e=>e.time<=time&&time<e.time+e.duration&&e.kind!=='tick');
  const kinds=[...new Set(active.map(e=>e.kind))];
  if(!audio.paused||time>0)$('now-text').textContent=kinds.length?kinds.map(k=>{const s=sounds.find(s=>s.kind===k);const event=active.find(e=>e.kind===k);return `${s.title} vid ord ${event.word} — ${s.description}`;}).join(' '):time<.45?'Inledning — textflödet börjar efter 0,45 sekunder.':'Ordklocka / inga pågående analysljud.';
}
let animation=null;
function animate(){draw();if(!audio.paused)animation=requestAnimationFrame(animate);else animation=null;}
audio.onplay=()=>{if(demoAudio)demoAudio.pause();audio.playbackRate=Number($('speed').value);if(animation===null)animate();};
audio.ontimeupdate=draw;audio.onseeked=draw;audio.onloadedmetadata=draw;audio.onended=draw;
$('speed').onchange=()=>{audio.playbackRate=Number($('speed').value);};
new ResizeObserver(draw).observe(canvas);
canvas.onclick=event=>{if(data){const bounds=canvas.getBoundingClientRect();audio.currentTime=Math.max(0,Math.min(data.report.audio.seconds,(event.clientX-bounds.left)/bounds.width*data.report.audio.seconds));draw();}};
function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
$('download-wav').onclick=()=>download(audioBlob,'textklang.wav');
$('download-json').onclick=()=>download(new Blob([JSON.stringify(data.report,null,2)],{type:'application/json'}),'textklang-rapport.json');
$('download-csv').onclick=()=>download(new Blob([data.csv],{type:'text/csv;charset=utf-8'}),'textklang-matt.csv');
