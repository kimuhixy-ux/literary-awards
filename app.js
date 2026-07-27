'use strict';

const APP_ROOT = new URL(window.ROOT, location.href).pathname;
const EN = window.LOCALE === 'en';
const S = window.S;
function pick(obj, jaKey, enKey) {
  if (!obj) return obj;
  if (EN && obj[enKey]) return obj[enKey];
  return obj[jaKey];
}
function awardName(award) {
  if (!award) return '';
  return EN && award.name_en ? award.name_en : award.name_ja;
}
function authorName(a) {
  if (!a) return '';
  return EN && a.name_en ? a.name_en : (a.name_ja || a.name_en || a.author_id);
}
function laureateAuthorLabel(r) {
  if (!r) return '';
  return EN ? (r.author_en || r.author_ja || r.author_id) : (r.author_ja || r.author_en || r.author_id);
}
function laureateWorkLabel(r) {
  if (!r) return '';
  return EN ? (r.work_en || r.work_original || r.work_ja) : (r.work_ja || r.work_original);
}
const SESSION_EN = { '上期': 'First Half', '下期': 'Second Half' };
function sessionLabel(r) {
  if (!r || !r.session) return '';
  const session = EN ? (SESSION_EN[r.session] || r.session) : r.session;
  const round = r.round ? (EN ? ` (Round ${r.round})` : ` 第${r.round}回`) : '';
  return `${session}${round}`;
}

/* ---------- data cache ---------- */
const cache = {};
async function loadJSON(path) {
  if (cache[path]) return cache[path];
  const res = await fetch(`${APP_ROOT}data/${path}`);
  if (!res.ok) throw new Error(`failed to load ${path}`);
  const json = await res.json();
  cache[path] = json;
  return json;
}
const loadAwards = () => loadJSON('awards.json');
const loadAuthors = () => loadJSON('authors.json');
const loadLaureates = (award) => loadJSON(award.data_file);

let ownedCache = null;
async function loadOwned() {
  // data/owned.jsonは個人の蔵書照合結果でgit管理外のため、公開サイトには存在しない。
  // 存在しない場合は空オブジェクトにフォールバックし、所蔵バッジ/フィルタを単に非表示にする。
  if (ownedCache) return ownedCache;
  try {
    const res = await fetch(`${APP_ROOT}data/owned.json`);
    ownedCache = res.ok ? await res.json() : {};
  } catch (e) {
    ownedCache = {};
  }
  return ownedCache;
}
function ownedKey(awardId, year, authorId) {
  return `${awardId}|${year}|${authorId}`;
}

/* ---------- helpers ---------- */
function h(tag, attrs = {}, children = []) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') el.className = v;
    else if (k === 'html') el.innerHTML = v;
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined) el.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (c === null || c === undefined) continue;
    el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  }
  return el;
}
function esc(s) {
  return (s ?? '').toString();
}
function translationBadge(jpt) {
  if (!jpt) return null;
  if (jpt.status === 'available') return h('span', { class: 'badge badge-available' }, S.badgeTranslationAvailable);
  if (jpt.status === 'unavailable' && jpt.note && jpt.note.includes('書誌')) return h('span', { class: 'badge' }, S.badgeBibliographyCheck);
  if (jpt.status === 'unavailable') return h('span', { class: 'badge badge-unavailable' }, S.badgeUntranslated);
  if (jpt.status === 'original-ja') return h('span', { class: 'badge badge-available' }, S.badgeOriginalJa);
  if (jpt.status === 'unverified') return h('span', { class: 'badge badge-unverified' }, S.badgeTranslationUnverified);
  return null;
}
function workTranslationInfo(jpt) {
  if (!jpt) return h('div', { class: 'work-translation is-unverified' }, S.workTranslationNone);
  if (jpt.status === 'available') {
    const bibliography = [jpt.translator, jpt.publisher, jpt.year].filter(Boolean).join(' / ');
    return h('div', { class: 'work-translation is-available' }, [
      `${S.workTranslationAvailablePrefix}${jpt.title_ja ? `: 『${jpt.title_ja}』` : ''}`,
      bibliography ? ` — ${bibliography}` : '',
    ]);
  }
  if (jpt.status === 'original-ja') return h('div', { class: 'work-translation is-available' }, S.workTranslationOriginalJa);
  if (jpt.status === 'unavailable') return h('div', { class: 'work-translation is-unavailable' }, S.workTranslationUnavailable);
  return h('div', { class: 'work-translation is-unverified' }, S.workTranslationUnverified);
}
function ownedBadge(entry) {
  if (!entry) return null;
  if (entry.status === 'exact') return h('span', { class: 'badge badge-owned' }, S.badgeOwned);
  if (entry.status === 'fuzzy') return h('span', { class: 'badge badge-owned-fuzzy' }, S.badgeOwnedFuzzy);
  return null;
}

/* ---------- scroll position memory ---------- */
const scrollMemory = new Map();
let lastHash = null;

/* ---------- router ---------- */
const routes = [
  { pattern: /^#\/$/, view: viewHome },
  { pattern: /^#\/award\/([^/]+)$/, view: viewAward },
  { pattern: /^#\/author\/([^/]+)$/, view: viewAuthor },
  { pattern: /^#\/connections$/, view: viewConnections },
  { pattern: /^#\/stats$/, view: viewStats },
];

async function router() {
  if (lastHash !== null) {
    scrollMemory.set(lastHash, window.scrollY);
  }
  const hash = location.hash || '#/';
  const app = document.getElementById('app');
  app.innerHTML = '';
  app.appendChild(h('div', { class: 'loading-state' }, S.loading));

  let matched = false;
  for (const r of routes) {
    const m = hash.match(r.pattern);
    if (m) {
      matched = true;
      try {
        await r.view(app, ...m.slice(1));
      } catch (e) {
        console.error(e);
        app.innerHTML = '';
        app.appendChild(h('div', { class: 'empty-state' }, S.loadError));
      }
      break;
    }
  }
  if (!matched) {
    app.innerHTML = '';
    app.appendChild(h('div', { class: 'empty-state' }, S.notFound));
  }

  const remembered = scrollMemory.get(hash);
  window.scrollTo(0, remembered || 0);
  lastHash = hash;
}

window.addEventListener('hashchange', router);
window.addEventListener('DOMContentLoaded', router);

/* ---------- to-top button ---------- */
const toTopBtn = document.getElementById('to-top');
if (toTopBtn) {
  window.addEventListener('scroll', () => {
    toTopBtn.hidden = window.scrollY < 400;
  });
  toTopBtn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
}

/* ================= HOME ================= */
async function viewHome(app) {
  const [awards, authors] = await Promise.all([loadAwards(), loadAuthors()]);
  app.innerHTML = '';

  const search = h('input', {
    class: 'search-box',
    type: 'text',
    placeholder: S.searchPlaceholder,
  });
  const results = h('div', { class: 'search-results' });
  search.addEventListener('input', () => {
    const q = search.value.trim().toLowerCase();
    results.innerHTML = '';
    if (!q) return;
    const hits = authors.filter((a) =>
      (a.name_ja && a.name_ja.toLowerCase().includes(q)) ||
      (a.name_en && a.name_en.toLowerCase().includes(q))
    ).slice(0, 20);
    if (hits.length === 0) {
      results.appendChild(h('div', { class: 'search-result-item' }, S.noAuthorFound));
      return;
    }
    for (const a of hits) {
      const awardNames = a.award_ids.map((id) => {
        const aw = awards.find((x) => x.id === id);
        return aw ? awardName(aw) : id;
      }).join(' / ');
      const item = h('a', { class: 'search-result-item', href: `#/author/${a.author_id}`, style: 'display:block;' }, [
        h('div', {}, `${a.name_ja || ''}${a.name_en ? ` (${a.name_en})` : ''}`),
        h('div', { class: 'meta' }, awardNames),
      ]);
      results.appendChild(item);
    }
  });

  app.appendChild(h('h2', { class: 'page-title' }, S.siteTitle));
  app.appendChild(h('p', { class: 'page-subtitle' }, S.siteSubtitle));
  app.appendChild(search);
  app.appendChild(results);

  const grid = h('div', { class: 'award-grid' });
  for (const award of awards) {
    const card = h('a', { class: 'award-card', href: `#/award/${award.id}` }, [
      h('h3', {}, awardName(award)),
      h('p', { class: 'organizer' }, `${pick(award, 'country', 'country_en')} / ${award.founded}${EN ? '' : '年'}〜`),
    ]);
    if (!award.data_file) {
      card.appendChild(h('p', { class: 'phase-note' }, S.preparing));
    }
    grid.appendChild(card);
  }
  app.appendChild(grid);
}

/* ================= AWARD TIMELINE ================= */
async function viewAward(app, awardId) {
  const awards = await loadAwards();
  const award = awards.find((a) => a.id === awardId);
  app.innerHTML = '';
  app.appendChild(h('a', { class: 'back-link', href: '#/' }, S.backToHome));

  if (!award) {
    app.appendChild(h('div', { class: 'empty-state' }, S.awardNotFound));
    return;
  }
  app.appendChild(h('h2', { class: 'page-title' }, awardName(award)));
  app.appendChild(h('p', { class: 'page-subtitle' }, pick(award, 'description', 'description_en')));

  if (!award.data_file) {
    app.appendChild(h('div', { class: 'empty-state' }, S.dataPreparing));
    renderRelated(app, award, awards);
    return;
  }

  const [laureates, authors, owned] = await Promise.all([loadLaureates(award), loadAuthors(), loadOwned()]);
  const authorMap = new Map(authors.map((a) => [a.author_id, a]));
  const hasOwnedData = Object.keys(owned).length > 0;

  const filterBar = h('div', { class: 'filter-bar' });
  const countryMap = new Map();
  const languageMap = new Map();
  for (const r of laureates) {
    if (r.country && !countryMap.has(r.country)) countryMap.set(r.country, pick(r, 'country', 'country_en'));
    if (r.language && !languageMap.has(r.language)) languageMap.set(r.language, pick(r, 'language', 'language_en'));
  }
  const countries = [...countryMap.keys()].sort();
  const languages = [...languageMap.keys()].sort();
  const decades = [...new Set(laureates.map((r) => Math.floor(r.year / 10) * 10))].sort((a, b) => b - a);

  const decadeSel = h('select', {}, [
    h('option', { value: '' }, S.filterDecadeAll),
    ...decades.map((d) => h('option', { value: String(d) }, S.filterDecadeLabel(d))),
  ]);

  const countrySel = h('select', {}, [
    h('option', { value: '' }, S.filterCountryAll),
    ...countries.map((c) => h('option', { value: c }, countryMap.get(c))),
  ]);
  const langSel = h('select', {}, [
    h('option', { value: '' }, S.filterLanguageAll),
    ...languages.map((l) => h('option', { value: l }, languageMap.get(l))),
  ]);
  const transSel = h('select', {}, [
    h('option', { value: '' }, S.filterTranslationAll),
    h('option', { value: 'available' }, S.filterTranslationAvailable),
    h('option', { value: 'unavailable' }, S.filterTranslationUnavailable),
    h('option', { value: 'unverified' }, S.filterTranslationUnverified),
  ]);
  filterBar.appendChild(decadeSel);
  filterBar.appendChild(countrySel);
  filterBar.appendChild(langSel);
  filterBar.appendChild(transSel);
  let ownedSel = null;
  if (hasOwnedData) {
    ownedSel = h('select', {}, [
      h('option', { value: '' }, S.filterOwnedAll),
      h('option', { value: 'owned' }, S.filterOwnedOnly),
      h('option', { value: 'not-owned' }, S.filterNotOwnedOnly),
    ]);
    filterBar.appendChild(ownedSel);
  }
  app.appendChild(filterBar);

  const list = h('div', { class: 'laureate-list' });
  app.appendChild(list);

  function matchesFilter(r) {
    if (decadeSel.value && Math.floor(r.year / 10) * 10 !== Number(decadeSel.value)) return false;
    if (countrySel.value && r.country !== countrySel.value) return false;
    if (langSel.value && r.language !== langSel.value) return false;
    const jpt = r.jp_translation || {};
    const unverified = jpt.status === 'unavailable' && jpt.note && jpt.note.includes('書誌');
    if (transSel.value === 'available' && !(jpt.status === 'available' || jpt.status === 'original-ja')) return false;
    if (transSel.value === 'unavailable' && !(jpt.status === 'unavailable' && !unverified)) return false;
    if (transSel.value === 'unverified' && !unverified) return false;
    if (hasOwnedData && ownedSel && ownedSel.value) {
      const isOwned = !!owned[ownedKey(award.id, r.year, r.author_id)];
      if (ownedSel.value === 'owned' && !isOwned) return false;
      if (ownedSel.value === 'not-owned' && isOwned) return false;
    }
    return true;
  }

  function render() {
    list.innerHTML = '';
    const sorted = [...laureates].sort((a, b) => {
      if (a.year !== b.year) return b.year - a.year;
      if (a.session && b.session) return a.session === '下期' ? -1 : 1;
      return 0;
    });
    const filtered = sorted.filter(matchesFilter);
    if (filtered.length === 0) {
      list.appendChild(h('div', { class: 'empty-state' }, S.noMatchingLaureates));
      return;
    }
    for (const r of filtered) {
      list.appendChild(renderLaureateItem(r, award, authorMap, awards, owned));
    }
  }
  decadeSel.addEventListener('change', render);
  countrySel.addEventListener('change', render);
  langSel.addEventListener('change', render);
  transSel.addEventListener('change', render);
  if (ownedSel) ownedSel.addEventListener('change', render);
  render();

  renderRelated(app, award, awards);
}

function renderLaureateItem(r, award, authorMap, awards, owned) {
  const isNoAward = !r.author_id;
  const item = h('div', { class: 'laureate-item' });
  const row = h('button', { class: 'laureate-row', type: 'button' });

  const yearLabel = h('span', { class: 'year' }, [
    String(r.year),
    r.session ? h('span', { class: 'round' }, sessionLabel(r)) : null,
  ]);
  row.appendChild(yearLabel);

  if (isNoAward) {
    row.appendChild(h('span', { class: 'names' }, h('span', { class: 'no-award' }, S.noQualifyingWork)));
  } else {
    const names = h('div', { class: 'names' }, [
      h('span', { class: 'author' }, laureateAuthorLabel(r)),
      laureateWorkLabel(r) ? h('span', { class: 'work' }, laureateWorkLabel(r)) : null,
    ]);
    row.appendChild(names);
    const badge = translationBadge(r.jp_translation);
    if (badge) row.appendChild(badge);
    const ob = ownedBadge(owned[ownedKey(award.id, r.year, r.author_id)]);
    if (ob) row.appendChild(ob);
  }

  item.appendChild(row);
  const detail = h('dl', { class: 'laureate-detail', hidden: '' });
  item.appendChild(detail);

  row.addEventListener('click', () => {
    const hidden = detail.hasAttribute('hidden');
    if (hidden) {
      fillDetail(detail, r, award, authorMap, awards, owned);
      detail.removeAttribute('hidden');
    } else {
      detail.setAttribute('hidden', '');
    }
  });

  return item;
}

function fillDetail(detail, r, award, authorMap, awards, owned) {
  if (detail.dataset.filled) return;
  detail.dataset.filled = '1';
  detail.innerHTML = '';
  const rows = [];
  if (r.author_id) {
    rows.push([S.labelAuthor, h('a', { href: `#/author/${r.author_id}` }, laureateAuthorLabel(r))]);
  }
  if (r.author_en && r.author_en !== r.author_ja) rows.push([S.labelOriginalSpelling, r.author_en]);
  if (r.country) rows.push([S.labelCountry, pick(r, 'country', 'country_en')]);
  if (r.work_ja || r.work_original) {
    const workVal = EN
      ? [r.work_en, r.work_original].filter(Boolean).join(' / ') || r.work_ja
      : [r.work_ja, r.work_original].filter(Boolean).join(' / ');
    rows.push([S.labelWork, workVal]);
  }
  if (r.theme_summary_ja) rows.push([S.labelAboutWork, pick(r, 'theme_summary_ja', 'theme_summary_en')]);
  if (r.translator_en) rows.push([S.labelTranslatorEn, r.translator_en]);
  if (r.citation_ja) rows.push([S.labelCitation, pick(r, 'citation_ja', 'citation_en')]);
  if (r.lecture_title || r.lecture_url) {
    const val = h('span', {}, [
      r.lecture_title ? `${r.lecture_title} ` : '',
      r.lecture_url ? h('a', { href: r.lecture_url, target: '_blank', rel: 'noopener' }, S.viewOfficialSite) : null,
    ]);
    rows.push([S.labelLecture, val]);
  }
  if (r.jp_translation) {
    const jpt = r.jp_translation;
    let val;
    if (jpt.status === 'available') {
      val = h('span', {}, [
        jpt.title_ja ? `『${jpt.title_ja}』 ` : '',
        [jpt.translator, jpt.publisher, jpt.year].filter(Boolean).join(' / '),
        jpt.note ? h('div', { class: 'note' }, pick(jpt, 'note', 'note_en')) : null,
      ]);
    } else if (jpt.status === 'original-ja') {
      val = S.originalJaText;
    } else if (jpt.status === 'unavailable') {
      val = h('span', {}, (jpt.note ? pick(jpt, 'note', 'note_en') : null) || S.untranslated);
    } else {
      val = S.notApplicable;
    }
    rows.push([S.labelJapaneseTranslation, val]);
  }
  if (r.author_id && owned) {
    const entry = owned[ownedKey(award.id, r.year, r.author_id)];
    if (entry) {
      const label = entry.status === 'exact' ? S.ownedYes : S.ownedMaybe;
      rows.push([S.badgeOwned, `${label}${S.ownedMatch(entry.matched_title)}`]);
    }
  }
  const amazonUrl = window.buildAffiliateLink && window.buildAffiliateLink(r.amazon_asin);
  if (amazonUrl) {
    rows.push([null, h('a', { href: amazonUrl, target: '_blank', rel: 'sponsored noopener' }, [S.findOnAmazon, h('span', { class: 'pr-label' }, 'PR')])]);
  }
  if (r.notes) rows.push([S.labelNotes, pick(r, 'notes', 'notes_en')]);
  if (r.source_urls && r.source_urls.length) {
    rows.push([S.labelSources, h('span', {}, r.source_urls.map((u, i) => h('a', { href: u, target: '_blank', rel: 'noopener', style: 'display:block;' }, u)))]);
  }

  // other awards for this author
  if (r.author_id) {
    const author = authorMap.get(r.author_id);
    if (author && author.awards.length > 1) {
      const others = author.awards.filter((e) => !(e.award_id === award.id && e.year === r.year));
      if (others.length) {
        const badges = h('div', { class: 'other-awards-badges' },
          others.map((e) => {
            const aw = awards.find((x) => x.id === e.award_id);
            return h('a', { class: 'other-award-badge', href: `#/author/${r.author_id}` }, `${aw ? awardName(aw) : e.award_id} (${e.year})`);
          })
        );
        rows.push([S.labelOtherAwards, badges]);
      }
    }
  }

  for (const [label, val] of rows) {
    if (label) detail.appendChild(h('dt', {}, label));
    detail.appendChild(h('dd', {}, val));
  }
}

function renderRelated(app, award, awards) {
  if (!award.related_awards || !award.related_awards.length) return;
  const wrap = h('div', {});
  wrap.appendChild(h('h3', { class: 'page-title', style: 'font-size:1.05rem;' }, S.relatedAwards));
  for (const rel of award.related_awards) {
    const relAward = awards.find((a) => a.id === rel.id);
    wrap.appendChild(h('div', { class: 'related-note' }, [
      h('h4', {}, h('a', { href: `#/award/${rel.id}` }, relAward ? awardName(relAward) : rel.id)),
      h('p', { style: 'margin:0;' }, pick(rel, 'note', 'note_en')),
    ]));
  }
  app.appendChild(wrap);
}

/* ================= AUTHOR DETAIL ================= */
async function viewAuthor(app, authorId) {
  const [authors, awards] = await Promise.all([loadAuthors(), loadAwards()]);
  const author = authors.find((a) => a.author_id === authorId);
  app.innerHTML = '';
  app.appendChild(h('a', { class: 'back-link', href: '#/' }, S.backToHome));

  if (!author) {
    app.appendChild(h('div', { class: 'empty-state' }, S.authorNotFound));
    return;
  }

  app.appendChild(h('h2', { class: 'page-title' }, `${author.name_ja || ''}${author.name_en ? ` / ${author.name_en}` : ''}`));
  app.appendChild(h('p', { class: 'page-subtitle' }, pick(author, 'country', 'country_en') || ''));

  if (author.is_multi_award) {
    app.appendChild(h('div', { class: 'related-note' }, [
      h('h4', {}, S.multiAwardTitle),
      h('p', { style: 'margin:0;' }, S.multiAwardText(author.award_ids.map((id) => {
        const aw = awards.find((x) => x.id === id);
        return aw ? awardName(aw) : id;
      }).join(' / '))),
    ]));
  }

  const timeline = h('ul', { class: 'author-timeline' });
  for (const e of author.awards) {
    const aw = awards.find((x) => x.id === e.award_id);
    timeline.appendChild(h('li', {}, [
      h('span', { class: 'tl-year' }, String(e.year)),
      ' ',
      h('a', { href: `#/award/${e.award_id}` }, aw ? awardName(aw) : e.award_id),
      e.session ? ` (${sessionLabel(e)})` : '',
      laureateWorkLabel(e) ? h('div', {}, laureateWorkLabel(e)) : null,
    ]));
  }
  app.appendChild(timeline);

  if (author.representative_works && author.representative_works.length) {
    app.appendChild(h('h3', { class: 'page-title', style: 'font-size:1.05rem;' }, S.representativeWorks));
    for (const w of author.representative_works) {
      const aw = awards.find((x) => x.id === w.award_id);
      const card = h('div', { class: 'work-card' }, [
        h('div', { class: 'work-title' }, laureateWorkLabel(w) || ''),
        h('div', { class: 'work-meta' }, `${aw ? awardName(aw) : w.award_id} (${w.year})`),
      ]);
      if (w.jp_translation_status === 'available' && w.jp_translation_title) {
        card.appendChild(h('div', { class: 'work-meta' }, S.jpTitleLabel(w.jp_translation_title)));
      }
      if (w.theme_summary_ja) {
        card.appendChild(h('p', { class: 'work-summary' }, pick(w, 'theme_summary_ja', 'theme_summary_en')));
      }
      app.appendChild(card);
    }
  }

  app.appendChild(h('h3', { class: 'page-title', style: 'font-size:1.05rem;' }, S.otherWorks));
  if (author.major_works && author.major_works.length) {
    app.appendChild(h('p', { class: 'page-subtitle' }, S.otherWorksCount(author.major_works.length)));
    const list = h('ul', { class: 'major-works-list' });
    for (const w of author.major_works) {
      const source = (w.source_urls || []).find((url) => url.includes('ndlsearch.ndl.go.jp'))
        || (w.source_urls || [])[0];
      list.appendChild(h('li', {}, [
        h('div', {}, [
          h('span', { class: 'work-title' }, w.title_original || ''),
          w.year ? h('span', { class: 'work-meta' }, ` (${w.year})`) : null,
          translationBadge(w.jp_translation),
        ]),
        workTranslationInfo(w.jp_translation),
        w.theme_summary_ja ? h('p', { class: 'work-summary' }, pick(w, 'theme_summary_ja', 'theme_summary_en')) : null,
        source
          ? h('a', { class: 'work-source', href: source, target: '_blank', rel: 'noopener' }, S.bibliographySource)
          : null,
      ]));
    }
    app.appendChild(list);
  } else {
    app.appendChild(h('div', { class: 'empty-state' }, S.noOtherWorks));
  }
}

/* ================= CONNECTIONS MAP ================= */
async function viewConnections(app) {
  const [authors, awards] = await Promise.all([loadAuthors(), loadAwards()]);
  app.innerHTML = '';
  app.appendChild(h('a', { class: 'back-link', href: '#/' }, S.backToHome));
  app.appendChild(h('h2', { class: 'page-title' }, S.connectionsTitle));
  app.appendChild(h('p', { class: 'page-subtitle' }, S.connectionsSubtitle));

  const multi = authors.filter((a) => a.is_multi_award);
  const relevantAwardIds = awards.filter((a) => a.data_file).map((a) => a.id);

  if (multi.length === 0) {
    app.appendChild(h('div', { class: 'empty-state' }, S.noMultiAwardAuthors));
  } else {
    const wrap = h('div', { class: 'connections-table-wrap' });
    const table = h('table', { class: 'connections-table' });
    const thead = h('thead', {}, h('tr', {}, [
      h('th', {}, S.tableAuthorHeader),
      ...relevantAwardIds.map((id) => {
        const aw = awards.find((x) => x.id === id);
        return h('th', {}, aw ? awardName(aw) : id);
      }),
    ]));
    table.appendChild(thead);
    const tbody = h('tbody', {});
    for (const a of multi) {
      const cells = relevantAwardIds.map((id) => {
        const hit = a.awards.find((e) => e.award_id === id);
        return h('td', { class: hit ? 'hit' : '' }, hit ? String(hit.year) : '—');
      });
      tbody.appendChild(h('tr', {}, [
        h('td', {}, h('a', { href: `#/author/${a.author_id}` }, a.name_ja || a.name_en || a.author_id)),
        ...cells,
      ]));
    }
    table.appendChild(tbody);
    wrap.appendChild(table);
    app.appendChild(wrap);
  }

  app.appendChild(h('h3', { class: 'page-title', style: 'font-size:1.05rem;' }, S.relatedAwards));
  for (const award of awards) {
    if (!award.related_awards || !award.related_awards.length) continue;
    for (const rel of award.related_awards) {
      if (award.id > rel.id) continue; // avoid duplicate pairs
      const relAward = awards.find((x) => x.id === rel.id);
      app.appendChild(h('div', { class: 'related-note' }, [
        h('h4', {}, `${awardName(award)} × ${relAward ? awardName(relAward) : rel.id}`),
        h('p', { style: 'margin:0;' }, pick(rel, 'note', 'note_en')),
      ]));
    }
  }
}

/* ================= STATS (Phase 2) ================= */
async function viewStats(app) {
  const [awards, authors, owned] = await Promise.all([loadAwards(), loadAuthors(), loadOwned()]);
  app.innerHTML = '';
  app.appendChild(h('a', { class: 'back-link', href: '#/' }, S.backToHome));
  app.appendChild(h('h2', { class: 'page-title' }, S.statsTitle));

  const withData = awards.filter((a) => a.data_file);
  const counts = withData.map((a) => ({
    label: awardName(a),
    count: authors.filter((au) => au.award_ids.includes(a.id)).length,
  }));
  const max = Math.max(1, ...counts.map((c) => c.count));
  const barW = 600, barH = 28, gap = 12;
  const svgH = counts.length * (barH + gap);
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', `0 0 ${barW} ${svgH}`);
  svg.setAttribute('width', '100%');
  svg.setAttribute('height', svgH);
  counts.forEach((c, i) => {
    const y = i * (barH + gap);
    const w = Math.round((c.count / max) * (barW - 160));
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('x', 150);
    rect.setAttribute('y', y);
    rect.setAttribute('width', w);
    rect.setAttribute('height', barH);
    rect.setAttribute('fill', 'var(--color-accent)');
    svg.appendChild(rect);
    const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    label.setAttribute('x', 0);
    label.setAttribute('y', y + barH * 0.7);
    label.setAttribute('font-size', '12');
    label.setAttribute('fill', 'var(--color-text)');
    label.textContent = c.label;
    svg.appendChild(label);
    const numLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    numLabel.setAttribute('x', 150 + w + 6);
    numLabel.setAttribute('y', y + barH * 0.7);
    numLabel.setAttribute('font-size', '12');
    numLabel.setAttribute('fill', 'var(--color-text)');
    numLabel.textContent = String(c.count);
    svg.appendChild(numLabel);
  });
  app.appendChild(h('p', { class: 'page-subtitle' }, S.statsSubtitle));
  app.appendChild(svg);

  if (Object.keys(owned).length > 0) {
    const laureatesByAward = await Promise.all(withData.map((a) => loadLaureates(a)));
    const ownership = withData.map((a, i) => {
      const records = laureatesByAward[i].filter((r) => r.author_id);
      const ownedCount = records.filter((r) => !!owned[ownedKey(a.id, r.year, r.author_id)]).length;
      return { label: awardName(a), total: records.length, ownedCount };
    });

    app.appendChild(h('h3', { class: 'page-title', style: 'font-size:1.05rem;' }, S.ownershipRateTitle));
    app.appendChild(h('p', { class: 'page-subtitle' }, S.ownershipRateSubtitle));

    const barW2 = 600, barH2 = 24, gap2 = 12;
    const svgH2 = ownership.length * (barH2 + gap2);
    const svg2 = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg2.setAttribute('viewBox', `0 0 ${barW2} ${svgH2}`);
    svg2.setAttribute('width', '100%');
    svg2.setAttribute('height', svgH2);
    ownership.forEach((o, i) => {
      const y = i * (barH2 + gap2);
      const rate = o.total ? o.ownedCount / o.total : 0;
      const w = Math.round(rate * (barW2 - 160));
      const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      rect.setAttribute('x', 150);
      rect.setAttribute('y', y);
      rect.setAttribute('width', Math.max(w, 1));
      rect.setAttribute('height', barH2);
      rect.setAttribute('fill', 'var(--color-badge-available-text)');
      svg2.appendChild(rect);
      const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      label.setAttribute('x', 0);
      label.setAttribute('y', y + barH2 * 0.7);
      label.setAttribute('font-size', '12');
      label.setAttribute('fill', 'var(--color-text)');
      label.textContent = o.label;
      svg2.appendChild(label);
      const numLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      numLabel.setAttribute('x', 150 + w + 6);
      numLabel.setAttribute('y', y + barH2 * 0.7);
      numLabel.setAttribute('font-size', '12');
      numLabel.setAttribute('fill', 'var(--color-text)');
      numLabel.textContent = `${o.ownedCount}/${o.total} (${Math.round(rate * 100)}%)`;
      svg2.appendChild(numLabel);
    });
    app.appendChild(svg2);
  }
}

/* ---------- service worker registration ---------- */
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register(`${APP_ROOT}sw.js?v=13-i18n-monetization`, { updateViaCache: 'none' })
      .then((registration) => registration.update())
      .catch(() => {});
  });
}
