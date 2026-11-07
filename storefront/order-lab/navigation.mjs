/* Ported from skvive/garakland game/navigation.mjs, verified 2026-11-07. */
/** GARAKLAND 3.1 — coupon-to-store Google Maps deep link (official Maps URLs).
 * No Google API key is required for an external Google Maps directions URL.
 * Do not claim door-to-door shop navigation when indoor coordinates are unknown.
 */
export const MARKET_ADDRESS = '서울특별시 송파구 양재대로 932 가락시장';
const GOOGLE_DIR = 'https://www.google.com/maps/dir/?api=1';
const TRAVEL_MODES = new Set(['walking', 'driving', 'transit']);

export function hasVerifiedGps(shop) {
  if (!shop || shop.isDemo || shop.coordinateStatus !== 'verified') return false;
  const lat = Number(shop.latitude), lng = Number(shop.longitude);
  return shop.latitude !== null && shop.latitude !== undefined && shop.latitude !== '' &&
    shop.longitude !== null && shop.longitude !== undefined && shop.longitude !== '' &&
    Number.isFinite(lat) && Number.isFinite(lng) &&
    lat >= 37.47 && lat <= 37.52 && lng >= 127.08 && lng <= 127.15;
}

export function buildDirections(shop, mode = 'walking') {
  const verified = hasVerifiedGps(shop);
  const travelmode = TRAVEL_MODES.has(mode) ? mode : 'walking';
  const destination = verified ? `${Number(shop.latitude)},${Number(shop.longitude)}` : MARKET_ADDRESS;
  const params = new URLSearchParams({ api: '1', destination, travelmode, dir_action: 'navigate' });
  const url = `https://www.google.com/maps/dir/?${params.toString()}`;
  const locationLabel = [shop?.building, shop?.floor, shop?.room].filter(Boolean).join(' · ');
  return {
    url,
    verified,
    mode: verified ? 'store' : 'market',
    destination,
    title: verified ? `${shop.name} 매장으로 길찾기` : '가락시장 입구까지 길찾기',
    buttonLabel: verified ? '🧭 이 매장으로 길찾기' : '🧭 가락시장까지 길찾기',
    locationLabel: locationLabel || '층·호실 정보 미등록',
    notice: verified
      ? 'Google 지도에서 등록·검증된 매장 GPS를 목적지로 사용합니다. 건물 내부 이동은 층·호실 안내를 확인하세요.'
      : (shop?.isDemo
          ? '가상 시연 매장에는 실제 좌표가 없습니다. Google 지도는 실제 가락시장 입구로만 안내합니다. 이 쿠폰은 실매장에서 사용할 수 없습니다.'
          : '이 매장의 정확한 GPS가 아직 검증되지 않았습니다. Google 지도는 가락시장까지 안내하며, 매장 내부는 층·호실을 직접 확인해야 합니다.'),
  };
}
