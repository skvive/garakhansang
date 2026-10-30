import { getSession } from './client.mjs';

const link = document.querySelector('[data-garak-login]');
if (link) {
  getSession()
    .then((data) => {
      if (data?.user) {
        link.textContent = data.user.name || data.user.email || '내 계정';
      }
    })
    .catch(() => {});
}
