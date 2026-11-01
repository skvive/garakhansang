/* KAMIS verified Seoul wholesale reference. Not Garak auction and not merchant sale prices. */
(()=>{
"use strict";
const target=document.getElementById("official-prices-panel");
if(!target)return;
const safe=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const won=n=>Number(n).toLocaleString("ko-KR")+"원";
async function init(){
 try{
  const req=await fetch("data/seoul-seafood-wholesale-latest.json",{cache:"no-cache"});
  if(!req.ok)throw Error("not-yet-available");
  const d=await req.json();
  if(d.status!=="verified_wholesale_reference" || d.isGarakAuction!==false || d.isStorePrice!==false || !Array.isArray(d.items)||!d.items.length)throw Error("invalid-dataset");
  const date=/^\d{4}-\d{2}-\d{2}$/.test(d.latestTradeDate)?d.latestTradeDate:"확인 필요";
  const items=d.items.filter(x=>x&&x.source==="KAMIS"&&Number.isInteger(x.priceWon)&&x.priceWon>0&&x.unit&&x.tradeDate).slice(0,100);
  if(!items.length)throw Error("missing-valid-rows");
  target.innerHTML='<h2>공식 수산물 서울 도매 참고가격</h2><p class="official-price-lead">한국농수산식품유통공사 KAMIS · 서울 지역 · 수산물 도매가격 · 기준 거래일: <b>'+safe(date)+'</b></p>'
  +'<p class="official-price-important">이 표는 <b>가락시장 개별 경락가격이나 상인 판매가격이 아닙니다.</b> 품목·품종·등급·단위가 다른 가격은 직접 비교하지 마세요.</p>'
  +'<div class="official-prices-table-wrap"><table class="data-table"><thead><tr><th>품목·품종</th><th>등급</th><th>조사단위</th><th>도매 참고가격</th><th>조사일</th></tr></thead><tbody>'
  +items.map(x=>'<tr><td>'+safe(x.itemName)+(x.variety?' <small>'+safe(x.variety)+'</small>':'')+'</td><td>'+safe(x.grade||"—")+'</td><td>'+safe(x.unit)+'</td><td><strong>'+won(x.priceWon)+'</strong></td><td>'+safe(x.tradeDate)+'</td></tr>').join('')
  +'</tbody></table></div><p class="official-price-source">출처: <a target="_blank" rel="noopener noreferrer" href="https://www.kamis.or.kr/customer/reference/openapi_list.do?action=detail&amp;boardno=1">KAMIS 공식 가격정보 Open API</a> · 조회 성공 시에만 표시하며 실제 값의 발표일은 위 날짜를 따릅니다.</p>';
 }catch(e){
  target.innerHTML='<h2>공식 수산물 도매 참고가격</h2><p>공식 가격 데이터가 아직 연결되지 않았거나 확인할 수 없습니다. 표시되지 않은 가격을 추측하지 않습니다.</p><p class="official-price-source"><a target="_blank" rel="noopener noreferrer" href="https://www.kamis.or.kr/customer/reference/openapi_list.do?action=detail&amp;boardno=1">KAMIS 공식 가격정보 확인하기</a></p>';
 }
}
init();
})();
