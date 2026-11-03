(() => {
  'use strict';

  const plans = Object.freeze({
    basic: 110000,
    standard: 120000,
    pro: 330000,
    premium: 550000,
    platinum: 1100000,
  });
  const $ = id => document.getElementById(id);
  const won = value => (Math.trunc(value) < 0 ? '−' : '') + Math.abs(Math.trunc(value)).toLocaleString('ko-KR') + '원';
  const int = id => Number($(id).value);
  const set = (id, value) => { $(id).textContent = value; };

  function calculate() {
    const price = int('sale-price');
    const externalRate = int('benchmark-rate') / 100;
    const coupon = int('coupon-discount');
    const other = int('other-cost');
    const share = int('success-share') / 100;
    const orders = int('orders');
    const plan = $('selected-plan').value;
    const subscription = plans[plan] ?? plans.pro;

    // Only the *positive, modeled cost difference* is shareable.
    // This is a marketing/simulation formula, not a settlement or payment workflow.
    const externalFee = Math.round(price * externalRate);
    const headroom = Math.max(0, externalFee - coupon - other);
    const platformFee = Math.floor(headroom * share);
    const merchantSaving = externalFee - coupon - other - platformFee;
    const externalNet = price - externalFee;
    const merchantNet = price - coupon - other - platformFee;

    set('price-caption', won(price));
    set('rate-caption', String(Number((externalRate * 100).toFixed(1))) + '%');
    set('coupon-caption', won(coupon));
    set('cost-caption', won(other));
    set('share-caption', Math.round(share * 100) + '%');
    set('orders-caption', orders.toLocaleString('ko-KR') + '건');

    set('platform-fee', won(platformFee));
    set('external-fee', won(externalFee));
    set('coupon-total', won(coupon + other));
    set('merchant-saving', won(merchantSaving));
    set('external-net', won(externalNet));
    set('merchant-net', won(merchantNet));
    set('monthly-subscription', won(subscription));
    set('monthly-performance', won(platformFee * orders));
    set('monthly-platform', won(subscription + platformFee * orders));
    set('monthly-merchant', won(merchantSaving * orders - subscription));

    set('margin-status', headroom <= 0
      ? '모델상 양의 차액이 없으므로 건당 성과수수료는 0원입니다.'
      : '비교상 차액 ' + won(headroom) + ' 중 가락한상 ' + Math.round(share * 100) + '%');
    set('threshold-comment', merchantSaving > 0
      ? '동일한 조건에서 구독료를 비교상 절감액만으로 상쇄하려면 월 최소 ' +
        Math.ceil(subscription / merchantSaving).toLocaleString('ko-KR') +
        '건의 쿠폰 실사용 주문이 필요합니다. 추가 매출과 실제 원가도 별도로 분석하세요.'
      : '현재 조건에서는 주문당 비교상 절감액이 0원 이하입니다. 쿠폰 규모·추가비용·성과수수료 배분을 재검토하세요.');

    document.querySelectorAll('[data-plan-card]').forEach(el => {
      el.classList.toggle('selected', el.dataset.planCard === plan);
      el.querySelector('button')?.setAttribute('aria-pressed', String(el.dataset.planCard === plan));
    });

    return { price, externalFee, coupon, other, platformFee, merchantSaving,
             subscription, orders, platformMonthly: subscription + platformFee * orders,
             merchantMonthly: merchantSaving * orders - subscription };
  }

  const calc = $('margin-calc');
  if (!calc) return;

  calc.addEventListener('input', calculate);
  calc.addEventListener('change', calculate);
  calc.addEventListener('reset', () => { window.requestAnimationFrame(calculate); });
  document.querySelectorAll('[data-select-plan]').forEach(button => {
    button.addEventListener('click', () => {
      const value = button.dataset.selectPlan;
      if (!Object.prototype.hasOwnProperty.call(plans, value)) return;
      $('selected-plan').value = value;
      calculate();
      $('calculator').scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' });
      $('selected-plan').focus({ preventScroll: true });
    });
  });
  window.garakMarketingCalculator = { calculate };
  calculate();
})();