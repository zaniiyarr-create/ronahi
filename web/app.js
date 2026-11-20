"use strict";
const $=id=>document.getElementById(id);
const digits=n=>Number(n).toLocaleString('ar-IQ',{useGrouping:false});
function read(key,fallback){try{return JSON.parse(localStorage.getItem('ronahi.'+key))??fallback}catch{return fallback}}
function save(key,value){try{localStorage.setItem('ronahi.'+key,JSON.stringify(value))}catch{}}
function normal(s){return s.normalize('NFKD').replace(/[\u064b-\u065f\u0670\u06d6-\u06ed\u200cـ]/g,'').replace(/[أإآٱ]/g,'ا').replace(/ى/g,'ي').replace(/[٠-٩]/g,x=>x.charCodeAt(0)-1632).replace(/[۰-۹]/g,x=>x.charCodeAt(0)-1776).trim()}
let names=[],book=[],marks=new Set(read('marks',[])),last=read('last','1/1'),size=read('size',34),shown=48,playing,chapter;
const link=(c,v=1)=>'#'+c+'/'+v;
function element(tag,cls,txt){const el=document.createElement(tag);el.className=cls;el.textContent=txt;return el}
function act(label,fn){const el=element('button','',label);el.onclick=fn;return el}
function anchor(text,url,cls='pill'){const a=element('a',cls,text);a.href=url;return a}
const glosses = {"الصَّمَدُ": ["112:2", "خودایێ هەمی ئافراندی د پێدڤیێن خۆ دا بەرێ خۆ ددەنێ."], "الْفَلَقِ": ["113:1", "سپێدە، دەمێ ڕووناهییا ڕۆژێ دەردکەڤیت."], "أَعُوذُ": ["113:1", "ئەز پەنا دبەم و پاراستنێ دخوازم."], "الْخَنَّاسِ": ["114:4", "ئەوێ وسوەسێ دکەت و دەمێ مرۆڤ خودێ ب بیر دئینیت، پاشڤە دکێشیت."], "الصِّرَاطَ": ["1:6", "ڕێک. د ڤێ ئایەتێ دا داخوازی ژ خودێیە کو مە بەری ڕێکا ڕاست ببەت."]};
function verseGlosses(paragraph, line, chapter, verse) {
 const entries = Object.entries(glosses).filter(([,data]) => data[0] === chapter+':'+verse);
 if (!entries.length) return;
 const note = element('span','','');
 note.setAttribute('aria-live','polite');
 paragraph.replaceChildren();
 for (const token of line.split(/(\s+)/)) {
   const match = entries.find(([word]) => normal(word) === normal(token) || normal(word) === normal(token.replaceAll('ٰ','ا')));
   if (!match) { paragraph.append(token); continue; }
   const button = act(token, () => {
     note.replaceChildren(match[1][1]+' ',anchor('تفسیر السعدي','https://quran.ksu.edu.sa/tafseer/saadi/sura'+chapter+'-aya'+verse+'.html'));
   });
   button.style.font='inherit';
   paragraph.append(button);
 }
 paragraph.append(document.createElement('br'),note);
}
function card(c,v,text){
 const a=anchor('',link(c,v),'card');a.append(element('span','num',digits(c)));
 const box=element('div','','');box.append(element('strong','',names[c-1]),document.createElement('br'),element('small','',text));a.append(box);return a
}
const juzStarts = [[1, 1], [2, 142], [2, 253], [3, 93], [4, 24], [4, 148], [5, 82], [6, 111], [7, 88], [8, 41], [9, 93], [11, 6], [12, 53], [15, 1], [17, 1], [18, 75], [21, 1], [23, 1], [25, 21], [27, 56], [29, 46], [33, 31], [36, 28], [39, 32], [41, 47], [46, 1], [51, 31], [58, 1], [67, 1], [78, 1]];
function listing(){
 const saved=location.hash==='#saved',q=normal($('search').value),matches=[];
 const juz=location.hash==='#juz';
 $('byJuz').setAttribute('aria-current',juz?'page':'false');
 $('bySurah').setAttribute('aria-current',!saved&&!juz?'page':'false');
 if(juz){
   $('heading').textContent='٣٠ جوز';$('search').hidden=true;$('more').hidden=true;
   $('grid').replaceChildren(...juzStarts.map(([c,v],i)=>{
     const entry=card(c,v,names[c-1]+' · ئایەت '+digits(v));
     entry.querySelector('strong').textContent='جوز '+digits(i+1);
     entry.querySelector('.num').textContent=digits(i+1);
     return entry;
   }));
   updateResume();return;
 }
 $('heading').textContent=saved?'نیشانێن من':'سوورەت';$('search').hidden=saved;
 if(saved){for(const k of marks){const [c,v]=k.split('/').map(Number);matches.push([c,v,'ئایەت '+digits(v)])}}
 else{
 names.forEach((name,i)=>{if(!q||normal(name).includes(q)||String(i+1)===q)matches.push([i+1,1,digits(book[i].length)+' ئایەت'])});
 if(q){const ref=q.match(/^(\d+)\s*[:/]\s*(\d+)$/);if(ref&&book[ref[1]-1]?.[ref[2]-1])matches.unshift([+ref[1],+ref[2],'ئایەت '+digits(ref[2])]);
 if(q.length>=2&&!/^\d/.test(q))book.forEach((rows,i)=>rows.forEach((line,j)=>{if(normal(line).includes(q))matches.push([i+1,j+1,line.slice(0,85)])}))}
 }
 $('grid').replaceChildren(...matches.slice(0,shown).map(r=>card(...r)));
 if(!matches.length)$('grid').textContent=saved?'د دەمێ خواندنێ دا ئایەتەکێ نیشان بکە.':'ئەنجام نەهاتە دیتن.';
 $('more').hidden=matches.length<=shown;
 updateResume();
}
function updateResume(){
 $('resume').href='#'+last;$('resume').textContent=read('last',null)?'بەردەوام بە · '+names[Number(last.split('/')[0])-1]:'دەست ب خواندنێ بکە'
}
function markButton(c,v){const k=c+'/'+v;const b=act('',()=>{if(marks.has(k))marks.delete(k);else marks.add(k);save('marks',[...marks]);update()});function update(){b.textContent=marks.has(k)?'نیشانکری':'نیشان بکە';b.setAttribute('aria-pressed',String(marks.has(k)))}update();return b}
function selectVerse(c,v){
 last=c+'/'+v;save('last',last);$('ayah').value=v;
 document.querySelector('article.active')?.classList.remove('active');
 const article=$('v'+v);article.classList.add('active');if(v>1)article.scrollIntoView({block:'start'});else window.scrollTo(0,0)
}
function stopAudio(){
 $('audio').pause();
 playing=null;
 $('player').hidden=true;
}
for(const id of ['reciter','repeats']){
 const select=$(id);
 const stored=read(id,select.value);
 if([...select.options].some(o=>o.value===stored))select.value=stored;
 select.onchange=()=>{
   save(id,select.value);
   if(playing)play(playing.c,playing.v);
 };
}
$('stopAudio').onclick=stopAudio;
function play(c,v,round=1){
 const state={c,v,round};
 playing=state;
 const audio=$('audio'),reciter=$('reciter');
 $('player').hidden=false;
 $('track').textContent=reciter.selectedOptions[0].text+' · '+names[c-1]+' · '+digits(v)+'　'+digits(round)+' / '+digits($('repeats').value);
 $('error').textContent='';
 audio.src='https://everyayah.com/data/'+reciter.value+'/'+String(c).padStart(3,'0')+String(v).padStart(3,'0')+'.mp3';
 audio.play().catch(()=>{if(playing===state)$('error').textContent='پەیوەندیا ئینتەرنێتێ بپشکنە و پەخشێ دووبارە بکە.'});
 history.replaceState(null,'',link(c,v));
 selectVerse(c,v);
}
function view(){
 const m=location.hash.match(/^#(\d+)(?:\/(\d+))?$/),c=Number(m?.[1]),v=Number(m?.[2]||1);
 $('audio').pause();playing=null;$('player').hidden=true;
 if(!book[c-1]?.[v-1]){$('reader').hidden=true;$('home').hidden=false;chapter=null;listing();window.scrollTo(0,0);return}
 $('reader').hidden=false;$('home').hidden=true;
 if(c!==chapter){chapter=c;$('title').textContent='سورة '+names[c-1];$('chapter').value=c;
 $('ayah').replaceChildren(...book[c-1].map((_,i)=>new Option('ئایەت '+digits(i+1),i+1)));
 $('verses').replaceChildren(...book[c-1].map((line,i)=>{const n=i+1,el=element('article','','');el.id='v'+n;
 const p=element('p','verse',line);p.lang='ar';verseGlosses(p,line,c,n);const row=element('div','row','');
 row.append(anchor(digits(c)+' : '+digits(n),link(c,n)),act('گوهداری',()=>play(c,n)),markButton(c,n),act('جهێ من هەلگرە',()=>{history.replaceState(null,'',link(c,n));selectVerse(c,n)}));el.append(p,row);return el}));
 $('paging').replaceChildren();if(c>1)$('paging').append(anchor(names[c-2],link(c-1)));if(c<114)$('paging').append(anchor(names[c],link(c+1)))
 }
 requestAnimationFrame(()=>selectVerse(c,v))
}
function theme(n){document.body.classList.toggle('night',n);$('theme').textContent=n?'ڕەنگێ ڕۆژێ':'ڕەنگێ شەڤێ';save('night',n)}
theme(read('night',false));$('theme').onclick=()=>theme(!document.body.classList.contains('night'));
function resize(delta){size=Math.max(24,Math.min(54,size+delta));document.body.style.setProperty('--size',size+'px');save('size',size)}
resize(0);$('larger').onclick=()=>resize(2);$('smaller').onclick=()=>resize(-2);
$('chapter').onchange=e=>location.hash=link(+e.target.value);$('ayah').onchange=e=>location.hash=link(chapter,+e.target.value);
$('audio').onended=()=>{
 if(!playing)return;
 const {c,v,round}=playing;
 if(round<Number($('repeats').value))play(c,v,round+1);
 else if(v<book[c-1].length)play(c,v+1);
 else stopAudio();
};
$('audio').onerror=()=>{$('error').textContent='تلاوەت نەهاتە بارکرن. پەیوەندیێ بپشکنە.'};
$('more').onclick=()=>{shown+=48;listing()};$('search').oninput=()=>{shown=48;listing()};
Promise.all(['chapters.json','quran.txt'].map(async path=>{const r=await fetch(path);if(!r.ok)throw Error(path);return r.text()})).then(([meta,text])=>{
 names=JSON.parse(meta);book=names.map(()=>[]);
 for(const line of text.split(/\r?\n/)){const m=line.match(/^(\d+)\|(\d+)\|(.+)$/);if(m)book[m[1]-1].push(m[3])}
 $('chapter').replaceChildren(...names.map((name,i)=>new Option(digits(i+1)+' · '+name,i+1)));view();window.addEventListener('hashchange',view)
}).catch(()=>{$('grid').textContent='دەق نەهاتە بارکرن. پەڕێ دووبارە ڤەکە.'});
