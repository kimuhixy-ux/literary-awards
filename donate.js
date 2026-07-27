// donate.js: フッターへのKo-fi寄付リンク表示
(function () {
  'use strict';

  function renderDonateLink() {
    var username = window.APP_CONFIG && window.APP_CONFIG.KOFI_USERNAME;
    if (!username) return;
    var footer = document.querySelector('.app-footer, .page-footer');
    if (!footer) return;

    var p = document.createElement('p');
    p.className = 'footer-donate';
    p.innerHTML = `<a href="https://ko-fi.com/${encodeURIComponent(username)}" target="_blank" rel="noopener">${window.S.kofiSupport}</a>`;
    footer.appendChild(p);
  }

  renderDonateLink();
})();
