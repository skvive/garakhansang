/**
 * Integration adapter for an OFFICIAL Toss FRONT plugin template.
 * This file must be included in the official plugin's SDK-initialized environment.
 * No arbitrary browser can execute this adapter as a card-terminal implementation.
 * NOT APPROVED FOR LIVE PAYMENTS: needs partner certification, device pairing,
 * server-side reconciliation, refund workflow and signed payment notifications.
 * Docs: https://docs.tossplace.com/guide/front-integration/plugin/develop/partner-integration-guide.html
 */
export function makeRodiTossBridge({sdk,server,token}) {
  if (!sdk?.payment?.requestPayment || !sdk?.printer?.printReceipt) {
    throw new Error('토스 프론트 공식 플러그인 SDK가 초기화되어야 합니다.');
  }
  const root = server.replace(/\/$/,'');
  if (!root.startsWith('https://'))throw new Error('실제 단말기 통신은 HTTPS가 필요합니다.');
  if (!token)throw new Error('유효한 단말 인증 자격 증명이 필요합니다.');
  async function request(path,method='GET',body){
    const r=await fetch(root+path,{method,headers:{'Authorization':`Bearer ${token}`,...(body?{'Content-Type':'application/json'}:{})},body:body?JSON.stringify(body):undefined});
    const json=await r.json();if(!r.ok)throw Error(json.error||'서버 연동 실패');return json;
  }
  async function runPendingOnce(){
    const {order}=await request('/api/terminal/pending');
    if(!order)return null;
    const tax=Math.floor(order.amount/11),supplyValue=order.amount-tax;
    // In a production implementation, server must lease jobs to avoid simultaneous terminals.
    const result=await sdk.payment.requestPayment({
      paymentKey:order.payment_key,tax,supplyValue,taxExemptValue:0,tip:0,
      timeoutMs:60000,localeCode:'ko',excludePaymentTypes:['CASH']
    });
    if(result.type!=='SUCCESS'){
      // TIMEOUT is uncertain: do NOT treat as decline automatically.
      // Recover on the SAME terminal using sdk.payment.getPayment({paymentKey}).
      if(result.type==='TIMEOUT')throw Error('결제 결과 불명: 원거래 조회 후 수동 복구 필요');
      await request('/api/terminal/complete','POST',{order_id:order.id,payment_key:order.payment_key,
        result:result.type==='CANCELED'?'CANCELED':'FAILED',payment_method:'',approval_number:'',timestamp:0});
      return null;
    }
    const pay=result.response;
    const detail=pay.card||pay.barcode;
    const completed=await request('/api/terminal/complete','POST',{
      order_id:order.id,payment_key:order.payment_key,result:'SUCCESS',
      payment_method:pay.paymentMethod,approval_number:detail?.approvalNumber||'',timestamp:detail?.timestamp||0
    });
    const p=completed.order;
    try{
      await sdk.printer.printReceipt({
        paymentKey:order.payment_key,count:1,
        orderInfo:{orderItems:p.items.map(i=>({count:i.qty,menu:{title:i.name,
          originPrice:i.unit_price,selectOptions:i.option==='기본'?[]:[{title:i.option,price:0}]},discounts:[]})),discounts:[]},
        additionalText:`RODI POS / 대기번호 ${String(p.queue_number).padStart(3,'0')}`
      });
      await request('/api/terminal/print-status','POST',{order_id:order.id,status:'printed'});
    } catch(error){
      await request('/api/terminal/print-status','POST',{order_id:order.id,status:'failed'});
      throw error; // Card payment remains paid and order remains queued.
    }
    return p;
  }
  return {runPendingOnce};
}
