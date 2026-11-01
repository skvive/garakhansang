/* Separate floor-map accessibility UI, independent of Google Maps SDK. */
(()=>{
 'use strict';
 document.addEventListener('click',event=>{
   const open=event.target.closest('[data-floor-map-open]');
   if(open){
     const dialog=document.getElementById('floor-map-dialog');
     if(dialog && typeof dialog.showModal==='function')dialog.showModal();
     else window.open('assets/maps/garakmall-1f-user-concept-v1.webp','_blank','noopener');
     return;
   }
   if(event.target.closest('[data-floor-map-close]')){
     document.getElementById('floor-map-dialog')?.close();
     return;
   }
   const dialog=document.getElementById('floor-map-dialog');
   if(dialog && event.target===dialog)dialog.close();
 });
})();