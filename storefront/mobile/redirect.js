/* Mobile-first routing without changing canonical desktop URLs.
   Touch-only and explicit opt-in; ?desktop=1 always preserves original page. */
(function () {
  "use strict";
  var params=new URLSearchParams(location.search);
  if(params.get("desktop")==="1") { try { sessionStorage.setItem("garak-pc-mode","1"); } catch (_) {} return; }
  try { if(sessionStorage.getItem("garak-pc-mode")==="1") return; } catch (_) {}
  var touch=Boolean(navigator.maxTouchPoints>0 && matchMedia("(pointer:coarse)").matches);
  var isPhone=/Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent||"");
  var isTouchTablet=touch && screen.width<=1200;
  if(!(params.get("mobile")==="1" || isPhone || isTouchTablet)) return;
  var origin=location.pathname;
  var target=document.currentScript && document.currentScript.getAttribute("data-mobile-target");
  if(!target) {
    var match=origin.match(/\/recipes\/(recipe-\d{3})\.html$/);
    if(match)target="../mobile/recipe.html?id="+encodeURIComponent(match[1]);
  }
  if(!target) return;
  if(location.hash && target.indexOf("#")===-1) target+=location.hash;
  location.replace(target);
})();
