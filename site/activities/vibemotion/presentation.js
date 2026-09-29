
// ---------- particle network background ----------
(function(){
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.querySelectorAll('.slide').forEach(slide=>{
    const dark = slide.classList.contains('dark');
    const paper = slide.classList.contains('paper');
    const cv=document.createElement('canvas');
    cv.className='pcanvas';
    slide.insertBefore(cv,slide.firstChild);
    const ctx=cv.getContext('2d');
    let W,H,parts=[],raf=null,running=false;
    // color tuned per slide theme
    const dot = dark ? '0,230,118' : '8,10,9';
    const dotA = dark ? 0.55 : (paper?0.34:0.30);
    const lineA= dark ? 0.16 : (paper?0.10:0.13);
    const accentDot = dark ? '255,255,255' : '0,230,118';

    function size(){
      const r=slide.getBoundingClientRect();
      W=cv.width=r.width*devicePixelRatio; H=cv.height=r.height*devicePixelRatio;
      cv.style.width=r.width+'px'; cv.style.height=r.height+'px';
      const count=Math.min(58,Math.round(r.width*r.height/19000));
      parts=Array.from({length:count},()=>({
        x:Math.random()*W, y:Math.random()*H,
        vx:(Math.random()-.5)*0.22*devicePixelRatio,
        vy:(Math.random()-.5)*0.22*devicePixelRatio,
        r:(Math.random()*2.2+1.1)*devicePixelRatio,
        accent:Math.random()<0.16
      }));
    }
    const LINK=130*devicePixelRatio;
    function frame(){
      ctx.clearRect(0,0,W,H);
      for(let i=0;i<parts.length;i++){
        const p=parts[i];
        p.x+=p.vx; p.y+=p.vy;
        if(p.x<0||p.x>W)p.vx*=-1;
        if(p.y<0||p.y>H)p.vy*=-1;
        for(let j=i+1;j<parts.length;j++){
          const q=parts[j],dx=p.x-q.x,dy=p.y-q.y,d=Math.hypot(dx,dy);
          if(d<LINK){
            ctx.strokeStyle=`rgba(${dot},${lineA*(1-d/LINK)})`;
            ctx.lineWidth=devicePixelRatio;
            ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(q.x,q.y);ctx.stroke();
          }
        }
      }
      for(const p of parts){
        ctx.beginPath();
        ctx.fillStyle = p.accent ? `rgba(${accentDot},${dotA+0.25})` : `rgba(${dot},${dotA})`;
        ctx.rect(p.x-p.r,p.y-p.r,p.r*2,p.r*2); // square dots = data aesthetic
        ctx.fill();
      }
      if(!reduce) raf=requestAnimationFrame(frame);
    }
    function start(){ if(running||reduce)return; running=true; frame(); }
    function stop(){ running=false; if(raf)cancelAnimationFrame(raf); raf=null; }
    size();
    if(reduce){ frame(); } // draw one static frame
    // only animate slides in view (perf)
    const vis=new IntersectionObserver(es=>es.forEach(e=>{e.isIntersecting?start():stop();}),{threshold:0.05});
    vis.observe(slide);
    let rt; addEventListener('resize',()=>{clearTimeout(rt);rt=setTimeout(size,200);});
  });
})();

// ---------- video click-to-play (lazy src) ----------
document.querySelectorAll('.vcard .frame[data-vsrc]').forEach(frame=>{
  const v=frame.querySelector('video');
  const overlay=frame.querySelector('.play');
  const fsbtn=frame.querySelector('.fs');
  function ensureSrc(){ if(!v.src) v.src=frame.dataset.vsrc; }
  frame.addEventListener('click',()=>{
    ensureSrc();
    if(v.paused){
      document.querySelectorAll('.vcard video').forEach(o=>{if(o!==v&&!o.paused){o.pause();o.closest('.frame').querySelector('.play').classList.remove('hide');}});
      v.play().then(()=>overlay.classList.add('hide')).catch(()=>overlay.classList.remove('hide'));
    } else {
      v.pause(); overlay.classList.remove('hide');
    }
  });
  v.addEventListener('ended',()=>overlay.classList.remove('hide'));
  // fullscreen: don't toggle play, just go fullscreen (with native controls)
  if(fsbtn) fsbtn.addEventListener('click',e=>{
    e.stopPropagation();
    ensureSrc();
    v.setAttribute('controls','');           // show native controls in fullscreen
    const req=v.requestFullscreen||v.webkitRequestFullscreen||v.webkitEnterFullscreen;
    if(req){ req.call(v); }
    v.play().catch(()=>{}); overlay.classList.add('hide');
  });
  // strip controls again when leaving fullscreen (keep card minimal)
  ['fullscreenchange','webkitfullscreenchange'].forEach(ev=>document.addEventListener(ev,()=>{
    if(!document.fullscreenElement && !document.webkitFullscreenElement){ v.removeAttribute('controls'); }
  }));
});

// hex rain fill
const HEX="0123456789ABCDEF";
function genHex(len){let s="";for(let i=0;i<len;i++){s+=Math.random()<0.5?HEX[Math.floor(Math.random()*16)]:HEX[Math.floor(Math.random()*16)];if(Math.random()<0.18)s+=" ";}return s;}
document.querySelectorAll('.hexrain').forEach(el=>{el.textContent=genHex(2600);});

// reveal on view
const io=new IntersectionObserver((es)=>{es.forEach(e=>{if(e.isIntersecting)e.target.classList.add('in');});},{threshold:0.18});
document.querySelectorAll('.slide').forEach(s=>io.observe(s));

// progress
const deck=document.getElementById('deck'),prog=document.getElementById('prog');
deck.addEventListener('scroll',()=>{const max=deck.scrollHeight-deck.clientHeight;prog.style.width=(deck.scrollTop/max*100)+'%';},{passive:true});

// keyboard nav
const slides=[...document.querySelectorAll('.slide')];let cur=0;
function go(d){cur=Math.max(0,Math.min(slides.length-1,cur+d));slides[cur].scrollIntoView({behavior:'smooth'});}
addEventListener('keydown',e=>{if(['ArrowDown','PageDown',' '].includes(e.key)){e.preventDefault();go(1);}if(['ArrowUp','PageUp'].includes(e.key)){e.preventDefault();go(-1);}});
deck.addEventListener('scroll',()=>{const c=deck.clientHeight;cur=Math.round(deck.scrollTop/c);},{passive:true});
