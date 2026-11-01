import { getSession } from './client.mjs';

const link = document.querySelector('[data-garak-login]');
if (link) {
  getSession()
    .then((data) => {
      if (data?.user) {
        link.textContent = '마이페이지'; link.href = (window.GARAK_ROOT || '') + 'mypage.html';
      }
    })
    .catch(() => {});
}
