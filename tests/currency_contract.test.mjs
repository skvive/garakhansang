import test from 'node:test';
import assert from 'node:assert/strict';
import { krw, verifyPaymentQuote, calculateLineTotal } from '../integrations/currency_contract.mjs';
test('KRW integer only',()=>{assert.equal(krw(12000),12000);assert.throws(()=>krw(12000,'USD'),/KRW_REQUIRED/);assert.throws(()=>krw(1.55),/INVALID/);});
test('PG verified amount must match quote',()=>{assert.deepEqual(verifyPaymentQuote({quotedKrw:10000,chargedKrw:10000,currency:'KRW',orderId:'test1',pgOrderId:'pg1'}),{orderId:'test1',pgOrderId:'pg1',verifiedKrw:10000,currency:'KRW'});assert.throws(()=>verifyPaymentQuote({quotedKrw:10000,chargedKrw:9000,currency:'KRW',orderId:'t',pgOrderId:'pg'}),/MISMATCH/)});
test('Strict line total',()=>{assert.equal(calculateLineTotal({unitPriceKrw:55000,qty:2}),110000);assert.throws(()=>calculateLineTotal({unitPriceKrw:55000,qty:true}),/QUANTITY/);});
