const PINS = [
  { id: 'market', name: '가락시장', kind: '시장 본관', addr: '서울 송파구 양재대로 932', lat: 37.4935, lng: 127.1119 },
  { id: 'ondosu', name: '온도수산', kind: '수산', addr: '가락시장 수산동', lat: 37.49435, lng: 127.11255 },
  { id: 'youngjae', name: '영재수산', kind: '수산', addr: '가락시장 수산동', lat: 37.49412, lng: 127.11162 },
  { id: 'daege', name: '가락대게', kind: '수산', addr: '가락시장 수산동', lat: 37.49388, lng: 127.11302 },
  { id: 'namdo', name: '남도수산', kind: '수산', addr: '가락시장 수산동', lat: 37.4932, lng: 127.1127 },
  { id: 'donghae', name: '동해수산', kind: '수산', addr: '가락시장 수산동', lat: 37.49285, lng: 127.1114 },
  { id: 'jeju', name: '제주직송', kind: '수산·농산', addr: '가락시장 주변', lat: 37.4925, lng: 127.11315 },
  { id: 'chuksan', name: '가락축산', kind: '축산', addr: '가락시장 축산동', lat: 37.49395, lng: 127.11055 },
  { id: 'chungwa', name: '가락청과', kind: '청과', addr: '가락시장 청과동', lat: 37.49255, lng: 127.1108 },
  { id: 'maru', name: '초장집 마루', kind: '곁들임', addr: '가락시장 주변', lat: 37.4946, lng: 127.11115 }
];

const statusEl = document.querySelector('#map-status');
const listEl = document.querySelector('#map-list-pins');
const mapEl = document.querySelector('#garak-map');
// Market-only mode avoids presenting unverified demo shops as real GPS locations.
const activePins = mapEl?.dataset.mapMode === 'market-only' ? PINS.slice(0, 1) : PINS;

function setStatus(msg, isError) {
  if (!statusEl) return;
  statusEl.textContent = msg;
  statusEl.classList.toggle('error', Boolean(isError));
}

function renderList(onPick) {
  if (!listEl) return;
  listEl.replaceChildren();
  for (const pin of activePins) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'map-pin';
    btn.dataset.id = pin.id;
    const title = document.createElement('strong');
    title.textContent = pin.name;
    const meta = document.createElement('span');
    meta.textContent = pin.kind + ' · ' + pin.addr;
    btn.append(title, meta);
    btn.addEventListener('click', () => onPick(pin.id));
    listEl.append(btn);
  }
}

function loadMapsScript(key) {
  return new Promise((resolve, reject) => {
    if (window.google?.maps) {
      resolve(window.google.maps);
      return;
    }
    const timer = setTimeout(() => reject(new Error('Google Maps callback timeout')), 15000);
    window.__garakMapsReady = () => { clearTimeout(timer); window.google?.maps ? resolve(window.google.maps) : reject(new Error('Maps library unavailable')); };
    window.gm_authFailure = () => { clearTimeout(timer); reject(new Error('Google Maps key rejected')); };
    const s = document.createElement('script');
    s.src = 'https://maps.googleapis.com/maps/api/js?key=' + encodeURIComponent(key) + '&language=ko&region=KR&v=weekly&callback=__garakMapsReady';
    s.async = true;
    s.defer = true;
    s.onerror = () => { clearTimeout(timer); reject(new Error('Google Maps script failed to load')); };
    document.head.append(s);
  });
}

async function boot() {
  if (!mapEl) return;
  renderList(() => {});
  try {
    const cfg = await fetch((window.GARAK_ROOT || '') + 'maps/config.public.json', { cache: 'no-store' }).then((r) => {
      if (!r.ok) throw new Error('config missing');
      return r.json();
    });
    if (!cfg.mapsKey) throw new Error('mapsKey missing');
    setStatus('지도를 불러오는 중입니다…');
    const maps = await loadMapsScript(cfg.mapsKey);
    const center = cfg.center || activePins[0];
    const map = new maps.Map(mapEl, {
      center: { lat: center.lat, lng: center.lng },
      zoom: 16,
      mapTypeControl: false,
      streetViewControl: false,
      fullscreenControl: true,
      gestureHandling: 'greedy'
    });
    const markers = new Map();
    const info = new maps.InfoWindow();
    function activate(id) {
      const pin = activePins.find((p) => p.id === id);
      if (!pin) return;
      listEl?.querySelectorAll('.map-pin').forEach((el) => el.classList.toggle('active', el.dataset.id === id));
      map.panTo({ lat: pin.lat, lng: pin.lng });
      map.setZoom(17);
      info.setContent('<strong>' + pin.name + '</strong><br>' + pin.kind + '<br>' + pin.addr);
      info.open({ map, anchor: markers.get(id) });
    }
    for (const pin of activePins) {
      const marker = new maps.Marker({
        position: { lat: pin.lat, lng: pin.lng },
        map,
        title: pin.name
      });
      marker.addListener('click', () => activate(pin.id));
      markers.set(pin.id, marker);
    }
    renderList(activate);
    activate('market');
    setStatus(mapEl.dataset.mapMode === 'market-only'
      ? 'Google Maps 연결 완료 · 가락시장 대표 위치만 표시합니다.'
      : 'Google Maps · 개별 상인 위치는 시연용 좌표입니다.');
  } catch (err) {
    setStatus('Google 지도 로딩 실패 · API 키의 도메인 제한과 Google Cloud 결제 설정을 확인하세요.', true);
    if (mapEl) {
      const fallback = document.createElement('div');
      fallback.className = 'garak-map-fallback';
      const heading = document.createElement('strong');
      heading.textContent = '지도 연결이 지연되고 있습니다.';
      const link = document.createElement('a');
      link.href = 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent('가락시장 서울 송파구 양재대로 932');
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = 'Google 지도에서 가락시장 열기 ↗';
      fallback.append(heading, link);
      mapEl.replaceChildren(fallback);
    }
    console.warn('garak maps', err);
  }
}

boot();
