// strings.js: 日本語/英語のUI文言辞書(app.jsが動的に描画する部分)。LOCALEに応じてSオブジェクトの値が決まる。
(function () {
  'use strict';
  var en = window.LOCALE === 'en';

  window.S = {
    siteTitle: en ? 'World Literary Prizes Overview' : '世界文学賞総覧',
    siteSubtitle: en
      ? 'Search and browse winners and winning works across major world literary prizes.'
      : '主要な世界の文学賞の受賞者・受賞作を横断して調べられます。',
    navHome: en ? 'Home' : 'ホーム',
    navConnections: en ? 'Connections' : '関連性マップ',
    navStats: en ? 'Stats' : '統計',
    toTop: en ? 'Back to top' : 'トップへ戻る',
    backToHome: en ? '← Back to home' : '← ホームへ戻る',
    loading: en ? 'Loading...' : '読み込み中...',
    loadError: en ? 'Failed to load data.' : 'データの読み込みに失敗しました。',
    notFound: en ? 'Page not found.' : 'ページが見つかりません。',

    searchPlaceholder: en ? 'Search authors (e.g. Ishiguro)' : '作家名で横断検索(例: イシグロ、Ishiguro)',
    noAuthorFound: en ? 'No matching authors found.' : '該当する作家が見つかりません。',
    preparing: en ? 'Coming soon' : '準備中(Phase 2)',
    awardNotFound: en ? 'Award not found.' : '賞が見つかりません。',
    dataPreparing: en ? 'This data is coming soon.' : 'このデータは準備中です(Phase 2で追加予定)。',
    noQualifyingWork: en ? 'No qualifying work' : '該当作品なし',
    noMatchingLaureates: en ? 'No matching laureates.' : '該当する受賞者がいません。',

    filterDecadeAll: en ? 'Decade: All' : '年代: すべて',
    filterDecadeLabel: function (d) { return en ? `${d}s` : `${d}年代`; },
    filterCountryAll: en ? 'Country/Region: All' : '国・地域: すべて',
    filterLanguageAll: en ? 'Language: All' : '言語: すべて',
    filterTranslationAll: en ? 'Japanese translation: All' : '邦訳: すべて',
    filterTranslationAvailable: en ? 'Translated only' : '邦訳ありのみ',
    filterTranslationUnavailable: en ? 'Untranslated only' : '未邦訳のみ',
    filterTranslationUnverified: en ? 'Unverified bibliography only' : '書誌要確認のみ',
    filterOwnedAll: en ? 'Owned: All' : '所蔵: すべて',
    filterOwnedOnly: en ? 'Owned only' : '所蔵のみ',
    filterNotOwnedOnly: en ? 'Not owned only' : '未所蔵のみ',

    badgeTranslationAvailable: en ? 'Translated' : '邦訳あり',
    badgeBibliographyCheck: en ? 'Bibliography unverified' : '書誌要確認',
    badgeUntranslated: en ? 'Untranslated' : '未邦訳',
    badgeOriginalJa: en ? 'Original: Japanese' : '日本語原文',
    badgeTranslationUnverified: en ? 'Translation unverified' : '邦訳未確認',
    badgeOwned: en ? 'Owned' : '所蔵',
    badgeOwnedFuzzy: en ? 'Owned? (unverified)' : '所蔵?(要確認)',

    workTranslationNone: en ? 'Japanese translation: no information' : '邦訳: 情報なし',
    workTranslationAvailablePrefix: en ? 'Japanese translation available' : '邦訳あり',
    workTranslationOriginalJa: en ? 'Japanese translation: original work in Japanese' : '邦訳: 日本語原著',
    workTranslationUnavailable: en ? 'No Japanese translation (bibliography verified)' : '邦訳なし（書誌確認済み）',
    workTranslationUnverified: en
      ? 'Japanese translation: bibliography unverified (this does not mean untranslated)'
      : '邦訳: 書誌未確認（未邦訳とは限りません）',

    labelAuthor: en ? 'Author' : '作家',
    labelOriginalSpelling: en ? 'Name in original script' : '原綴り',
    labelCountry: en ? 'Country/Region' : '国・地域',
    labelWork: en ? 'Winning work' : '受賞作',
    labelAboutWork: en ? 'About the work' : '作品について',
    labelTranslatorEn: en ? 'English translator' : '英訳者',
    labelCitation: en ? 'Citation (summary)' : '受賞理由(要旨)',
    labelLecture: en ? 'Prize lecture' : '記念講演',
    viewOfficialSite: en ? 'View on official site' : '公式サイトで見る',
    labelJapaneseTranslation: en ? 'Japanese translation' : '邦訳情報',
    originalJaText: en ? 'Originally written in Japanese.' : '日本語で書かれた原文です',
    untranslated: en ? 'Untranslated' : '未邦訳',
    notApplicable: en ? 'Not applicable' : '対象外',
    ownedYes: en ? 'You own this' : '所蔵しています',
    ownedMaybe: en ? 'Possibly owned (unverified)' : '所蔵の可能性があります(要確認)',
    ownedMatch: function (title) {
      return en
        ? ` — matched with "${title}" in your library vault`
        : ` — 蔵書vault内『${title}』と照合`;
    },
    labelNotes: en ? 'Notes' : '備考',
    labelSources: en ? 'Sources' : '出典',
    labelOtherAwards: en ? 'Other awards' : '他の受賞',
    relatedAwards: en ? 'Related prizes' : '関連する賞',

    authorNotFound: en ? 'Author information not found.' : '作家情報が見つかりません。',
    multiAwardTitle: en ? 'Winner of multiple literary prizes' : '複数の文学賞を受賞',
    multiAwardText: function (names) {
      return en ? `Has won ${names}.` : `${names} を受賞しています。`;
    },
    representativeWorks: en ? 'Representative works' : '代表作',
    jpTitleLabel: function (title) {
      return en ? `Japanese title: "${title}"` : `邦題: 『${title}』`;
    },
    otherWorks: en ? 'Other works' : '受賞作以外の収録作品',
    otherWorksCount: function (n) {
      return en
        ? `${n} works (authors confirmed via public bibliographic sources)`
        : `${n}作品（公開書誌で著者を確認できた作品）`;
    },
    bibliographySource: en ? 'Bibliographic source' : '書誌出典',
    noOtherWorks: en
      ? 'No additional works besides the prize-winning work could be confirmed in public bibliographic sources.'
      : '公開書誌で受賞作以外の作品を確認できませんでした。',

    connectionsTitle: en ? 'Connections Map' : '関連性マップ',
    connectionsSubtitle: en
      ? 'Authors who have won more than one literary prize.'
      : '複数の文学賞を受賞した作家の一覧です。',
    noMultiAwardAuthors: en ? 'No multi-award authors found.' : '複数受賞の作家が見つかりません。',
    tableAuthorHeader: en ? 'Author' : '作家',

    statsTitle: en ? 'Stats' : '統計',
    statsSubtitle: en
      ? 'Number of laureates across all 8 prizes covered. Joint winners are counted individually.'
      : '収録する全8賞の受賞者数を集計。共同受賞は個別に数えています。',
    ownershipRateTitle: en ? 'Ownership rate by prize' : '各賞の所蔵率',
    ownershipRateSubtitle: en
      ? 'Share of winning works matched against your library vault (shown only when browsing locally).'
      : '蔵書vaultと照合できた受賞作の割合(ローカル閲覧時のみ表示)。',

    kofiSupport: en ? '☕ Support on Ko-fi' : '☕ Ko-fiで応援する',
    findOnAmazon: en ? 'Find on Amazon' : 'Amazonで探す',
  };
})();
