const root = window.GARAK_ROOT || '';
const path = location.pathname.replace(/\\/g, '/');
const isAdmin = path.includes('/admin');
const isHome = /\/$|\/index\.html$/i.test(path);
const mascotPages = /map\.html|merchant|cart\.html|community|support\.html|prices\.html|chefs|stories/i.test(path);

function asset(name) {
  return root + 'assets/brand/' + name;
}

function absUrl(rel) {
  return new URL(root + rel, location.href).href;
}

function setMeta(attr, key, value) {
  let el = document.querySelector(`meta[${attr}="${key}"]`);
  if (!el) {
    el = document.createElement('meta');
    el.setAttribute(attr, key);
    document.head.append(el);
  }
  el.setAttribute('content', value);
}

function injectCss() {
  if (document.querySelector('[data-garak-brand-css]')) return;
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = root + 'assets/css/brand.css';
  link.dataset.garakBrandCss = '1';
  document.head.append(link);
  const theme = document.querySelector('meta[name="theme-color"]');
  if (theme) theme.setAttribute('content', '#123D2A');
}

function injectShare() {
  const og = absUrl('assets/brand/og-image.jpg');
  const desc =
    document.querySelector('meta[name="description"]')?.content ||
    '가락시장 30년 전통의 맛. 좋은 먹거리가 만나는 곳.';
  setMeta('property', 'og:type', 'website');
  setMeta('property', 'og:site_name', '가락한상');
  setMeta('property', 'og:title', document.title || '가락한상');
  setMeta('property', 'og:description', desc);
  setMeta('property', 'og:image', og);
  setMeta('property', 'og:url', location.href.split('#')[0]);
  setMeta('name', 'twitter:card', 'summary_large_image');
  setMeta('name', 'twitter:image', og);
  if (!document.querySelector('link[rel="apple-touch-icon"]')) {
    const apple = document.createElement('link');
    apple.rel = 'apple-touch-icon';
    apple.href = root + 'assets/images/apple-touch-icon.png';
    document.head.append(apple);
  }
}

function replaceLogos() {
  document.querySelectorAll('a.logo').forEach((el) => {
    if (el.querySelector('.brand-logo-img')) return;
    el.classList.add('brand-lockup');
    const img = document.createElement('img');
    img.className = 'brand-logo-img';
    img.src = asset('logo-lockup.webp');
    img.alt = '가락한상';
    img.width = 240;
    img.height = 90;
    el.replaceChildren(img);
  });
}

function paintStrip() {
  const strip = document.querySelector('.top-strip');
  if (strip && !strip.dataset.brandCopy) {
    strip.dataset.brandCopy = '1';
    strip.innerHTML = '좋은 먹거리가 만나는 곳, <b>가락한상</b>에서 새로운 발견을! · 가락시장 30년 전통의 맛';
  }
}

function paintHome() {
  if (!isHome) return;
  document.body.classList.add('brand-home');
  const copy = document.querySelector('.story-hero-copy');
  if (copy) {
    const kicker = copy.querySelector('.story-kicker');
    if (kicker) kicker.textContent = '대한민국 최대 농수산물 시장';
    const h1 = copy.querySelector('h1');
    if (h1) {
      h1.replaceChildren();
      h1.append('가락시장에서', document.createElement('br'), '새로운 발견!');
    }
    const p = copy.querySelector(':scope > p');
    if (p && !p.classList.contains('story-caption')) {
      p.textContent = '신선한 먹거리, 특별한 혜택. 지금 가락한상에서 만나보세요.';
    }
  }
  const inner = document.querySelector('.story-hero-inner');
  if (inner && !inner.querySelector('.brand-mascot-hero')) {
    const mascot = document.createElement('img');
    mascot.className = 'brand-mascot-hero';
    mascot.src = asset('mascot.webp');
    mascot.alt = '가락한상 상인 캐릭터';
    const speech = document.createElement('p');
    speech.className = 'brand-speech';
    speech.textContent = '신선한 오늘이 더 맛있는 내일을 만듭니다.';
    inner.append(mascot, speech);
  }
  const kicker = document.querySelector('.story-section-spotlight .kicker');
  if (kicker) kicker.textContent = '오늘의 가락한상';
  const quote = document.querySelector('.story-market-quote strong');
  if (quote) quote.textContent = '가락시장의 이야기가 모이는 한 상';
}

function paintPageHero() {
  if (isHome || !mascotPages) return;
  const hero = document.querySelector('.page-hero');
  if (!hero || hero.querySelector('.brand-mascot-page')) return;
  const mascot = document.createElement('img');
  mascot.className = 'brand-mascot-page';
  mascot.src = asset('mascot.webp');
  mascot.alt = '';
  hero.append(mascot);
}

function paintFooter() {
  const col = document.querySelector('.footer-top > div');
  if (!col || col.querySelector('.brand-seal-footer')) return;
  const p = col.querySelector('p');
  if (p && !p.dataset.brandCopy) {
    p.dataset.brandCopy = '1';
    p.textContent = '가락시장 30년 전통의 맛. 신선한 오늘이 더 맛있는 내일을 만듭니다.';
  }
  const seal = document.createElement('img');
  seal.className = 'brand-seal-footer';
  seal.src = asset('seal.webp');
  seal.alt = '가락한상';
  col.append(seal);
}

if (!isAdmin) {
  injectCss();
  injectShare();
  replaceLogos();
  paintStrip();
  paintHome();
  paintPageHero();
  paintFooter();
}
