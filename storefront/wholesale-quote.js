(()=>{'use strict';
 const $=id=>document.getElementById(id);const currency=n=>(n<0?'−':'')+Math.abs(Math.trunc(n)).toLocaleString('ko-KR')+'원';
 const fmtPct=n=>Number.isFinite(n)?n.toFixed(1)+'%':'—';
 const ids=['wh-sale','wh-cost','wh-logistics','wh-loss','wh-count'];
 const bound=x=>Number.isFinite(x)?Math.min(10000000,Math.max(0,x)):0;
 function calculate(){
  const [price,cost,shipping,loss,amount]=ids.map(id=>bound(Number($(id).value)));
  const count=Math.min(100000,Math.floor(amount));
  const margin=price-cost-shipping-loss;
  const rate=price>0?margin/price*100:0;
  $('wh-margin').textContent=currency(margin);
  $('wh-rate').textContent=fmtPct(rate);
  $('wh-revenue').textContent=currency(price*count);
  $('wh-monthly').textContent=currency(margin*count);
  $('wh-break-even').textContent=currency(cost+shipping+loss);
  $('wh-status').textContent=margin<0
    ?'현재 입력값은 납품할수록 손실이 발생하는 시나리오입니다. 매입·포장·물류·폐기 원가와 계약단가를 재검토하세요. 실거래 견적이 아닙니다.'
    :'가정된 월 기여이익은 고정비·인건비·세금·반품 및 추가 손실을 차감하기 전 금액입니다. 실거래 견적이 아닙니다.';
  return {margin,rate,count,monthly:margin*count};
 }
 const form=$('wholesale-calculator');if(!form)return;
 form.addEventListener('input',calculate);form.addEventListener('change',calculate);form.addEventListener('reset',()=>requestAnimationFrame(calculate));
 window.garakWholesaleCalculator={calculate};
 calculate();
})();