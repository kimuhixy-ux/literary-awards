// affiliate.js: Amazonアソシエイトリンクの生成
(function () {
  'use strict';

  function buildAffiliateLink(asin) {
    var tag = window.APP_CONFIG && window.APP_CONFIG.AMAZON_ASSOCIATE_TAG;
    if (!asin || !tag) return null;
    return `https://www.amazon.co.jp/dp/${encodeURIComponent(asin)}/?tag=${encodeURIComponent(tag)}`;
  }

  window.buildAffiliateLink = buildAffiliateLink;
})();
