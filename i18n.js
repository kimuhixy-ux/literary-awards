// i18n.js: URLパス(/en/を含むか)からロケールを判定する
(function () {
  'use strict';
  window.LOCALE = location.pathname.includes('/en/') ? 'en' : 'ja';
  // 相対パスの基点。/en/配下のページから見て、data/などアプリ直下のファイルは1階層上になる
  window.ROOT = window.LOCALE === 'en' ? '../' : './';
})();
