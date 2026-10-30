/**
 * Garak v7 integration seam. Unit-safe validation only; no payments, FX conversion,
 * checkout side effects, or live database changes.
 * Use a verified PG amount in KRW; NEVER treat products.price_usd as KRW.
 */
export function krw(amount, currency = 'KRW') {
  if (currency !== 'KRW') throw new Error('KRW_REQUIRED: No implicit USD -> KRW conversion');
  if (!Number.isSafeInteger(amount) || amount < 0) throw new Error('INVALID_KRW_INTEGER');
  return amount;
}
export function verifyPaymentQuote({quotedKrw, chargedKrw, currency, orderId, pgOrderId}) {
  if (typeof orderId !== 'string' || !orderId.trim() || typeof pgOrderId !== 'string' || !pgOrderId.trim()) throw new Error('MISSING_ORDER_ID');
  const quoted = krw(quotedKrw, currency);
  const charged = krw(chargedKrw, currency);
  if (quoted !== charged) throw new Error('PAYMENT_AMOUNT_MISMATCH');
  return Object.freeze({orderId, pgOrderId, verifiedKrw: charged, currency: 'KRW'});
}
export function calculateLineTotal({unitPriceKrw, qty}) {
  const price = krw(unitPriceKrw);
  if (!Number.isSafeInteger(qty) || qty < 1 || qty > 50) throw new Error('INVALID_QUANTITY');
  return krw(price * qty);
}
