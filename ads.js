// ads.js: Google AdSense自動広告の読み込み(カスタムドメイン経由のアクセス時のみ)
(function () {
  'use strict';

  function initAds() {
    var cfg = window.APP_CONFIG;
    if (!cfg || !cfg.ADS_ENABLED || !cfg.ADSENSE_CLIENT_ID) return;

    var script = document.createElement('script');
    script.async = true;
    script.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${encodeURIComponent(cfg.ADSENSE_CLIENT_ID)}`;
    script.crossOrigin = 'anonymous';
    document.head.appendChild(script);
  }

  initAds();
})();
