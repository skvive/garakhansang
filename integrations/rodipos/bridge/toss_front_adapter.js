/* RODI POS / Toss Front SDK integration ADAPTER, NOT DEPLOYABLE WITHOUT PARTNER SETUP.
 * The Toss Front SDK object must be supplied by its official plugin bootstrap.
 * Never ship a permanent RODI_BRIDGE_TOKEN in public kiosk/frontend assets.
 * Production requires short-lived, device-bound authentication and merchant/amount reconciliation.
 */
export function makeRodiTossAdapter({ sdk, baseUrl, authToken }) {
  const headers = {'Content-Type':'application/json', 'Authorization':`Bearer ${authToken}`};
  async function api(path,method='GET',body) {
    const response=await fetch(baseUrl+path,{method,headers,body:body?JSON.stringify(body):undefined});
    const data=await response.json();
    if(!response.ok)throw new Error(data.error||'RODI API error');
    return data;
  }
  async function processPayments() {
    const {orders}=await api('/api/bridge/pending');
    for(const order of orders) {
      // In the real solution use one deterministic device claim/lease, then requestPayment.
      // Korean tax convention only; must use legally determined tax classification per SKU.
      const tax=Math.floor(order.total/11);
      try {
        const result=await sdk.payment.requestPayment({
          paymentKey:order.payment_key,tax,supplyValue:order.total-tax,taxExemptValue:0,
          tip:0,timeoutMs:60000,localeCode:'ko',excludePaymentTypes:['CASH']
        });
        // Save only a verified SUCCESS result; NEVER treat TIMEOUT/CANCELED as paid.
        await api('/api/bridge/payment-result','POST',{order_id:order.id,result});
      } catch(error) {
        console.error('결제 처리/승인 저장 실패: 단말기 조회 후 복구 필요',error);
      }
    }
  }
  async function processPrintJobs() {
    const {jobs}=await api('/api/bridge/print-jobs');
    for(const j of jobs) {
      try {
        await sdk.printer.printReceipt({
          paymentKey:j.payment_key, count:1,
          orderInfo:{orderItems:j.items.map(x=>({
            count:x.quantity,
            menu:{title:x.product_name,originPrice:x.unit_price,selectOptions:x.drink_option==='DEFAULT'?[]:[{title:x.drink_option,price:0}]},discounts:[]
          })), discounts:[]},
          additionalText:`RODI POS\nPICKUP NO: ${String(j.queue_no).padStart(3,'0')}\nPlease wait for your number.`
        });
        await api('/api/bridge/print-result','POST',{job_id:j.id,success:true});
      } catch(error) {
        await api('/api/bridge/print-result','POST',{job_id:j.id,success:false,error:String(error).slice(0,100)});
      }
    }
  }
  return {processPayments,processPrintJobs};
}
