(() => {"use strict";
  document.addEventListener('click',e=>{const b=e.target.closest('[data-menu]');if(b){setTimeout(()=>{const expanded=document.querySelector('.mobile-menu')?.classList.contains('open');b.setAttribute('aria-expanded',String(!!expanded));},0)}
    if(e.target.closest('.mobile-menu a')){document.querySelector('.mobile-menu')?.classList.remove('open');document.querySelector('[data-menu]')?.setAttribute('aria-expanded','false');}});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'){document.querySelector('.mobile-menu')?.classList.remove('open');document.querySelector('[data-menu]')?.setAttribute('aria-expanded','false')}});
  // Search page can be opened directly with q=... from the shared header.
  const q=new URLSearchParams(location.search).get('q');
  if(q&&document.querySelector('#search-form')){const input=document.querySelector('#search-form input');if(input){input.value=q;requestAnimationFrame(()=>{const button=document.querySelector('#search-form button[type="submit"]');if(button)button.click();else document.querySelector('#search-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))})}}
  // Keyboard/accessibility, no fabricated purchase claims.
  for(const a of document.querySelectorAll('.story-shortcut-row a,.story-nav-ribbon a')){
    if(a.pathname===location.pathname)a.setAttribute('aria-current','page');}
})();