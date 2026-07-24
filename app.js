'use strict';

const APP_ROOT = new URL('.', location.href).pathname;

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
  if (jpt.status === 'available') return h('span', { class: 'badge badge-available' }, '邦訳あり');
  if (jpt.status === 'unavailable' && jpt.note && jpt.note.includes('書誌')) return h('span', { class: 'badge' }, '書誌要確認');
  if (jpt.status === 'unavailable') return h('span', { class: 'badge badge-unavailable' }, '未邦訳');
  if (jpt.status === 'original-ja') return h('span', { class: 'badge badge-available' }, '日本語原文');
  return null;
}
function awardShortName(award) {
  return award ? award.name_ja : '';
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
  app.appendChild(h('div', { class: 'loading-state' }, '読み込み中...'));

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
        app.appendChild(h('div', { class: 'empty-state' }, 'データの読み込みに失敗しました。'));
      }
      break;
    }
  }
  if (!matched) {
    app.innerHTML = '';
    app.appendChild(h('div', { class: 'empty-state' }, 'ページが見つかりません。'));
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
    placeholder: '作家名で横断検索(例: イシグロ、Ishiguro)',
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
      results.appendChild(h('div', { class: 'search-result-item' }, '該当する作家が見つかりません。'));
      return;
    }
    for (const a of hits) {
      const awardNames = a.award_ids.map((id) => {
        const aw = awards.find((x) => x.id === id);
        return aw ? aw.name_ja : id;
      }).join(' / ');
      const item = h('a', { class: 'search-result-item', href: `#/author/${a.author_id}`, style: 'display:block;' }, [
        h('div', {}, `${a.name_ja || ''}${a.name_en ? ` (${a.name_en})` : ''}`),
        h('div', { class: 'meta' }, awardNames),
      ]);
      results.appendChild(item);
    }
  });

  app.appendChild(h('h2', { class: 'page-title' }, '世界文学賞総覧'));
  app.appendChild(h('p', { class: 'page-subtitle' }, '主要な世界の文学賞の受賞者・受賞作を横断して調べられます。'));
  app.appendChild(search);
  app.appendChild(results);

  const grid = h('div', { class: 'award-grid' });
  for (const award of awards) {
    const card = h('a', { class: 'award-card', href: `#/award/${award.id}` }, [
      h('h3', {}, award.name_ja),
      h('p', { class: 'organizer' }, `${award.country} / ${award.founded}年〜`),
    ]);
    if (award.phase === 2 || !award.data_file) {
      card.appendChild(h('p', { class: 'phase-note' }, '準備中(Phase 2)'));
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
  app.appendChild(h('a', { class: 'back-link', href: '#/' }, '← ホームへ戻る'));

  if (!award) {
    app.appendChild(h('div', { class: 'empty-state' }, '賞が見つかりません。'));
    return;
  }
  app.appendChild(h('h2', { class: 'page-title' }, award.name_ja));
  app.appendChild(h('p', { class: 'page-subtitle' }, award.description));

  if (!award.data_file) {
    app.appendChild(h('div', { class: 'empty-state' }, 'このデータは準備中です(Phase 2で追加予定)。'));
    renderRelated(app, award, awards);
    return;
  }

  const [laureates, authors] = await Promise.all([loadLaureates(award), loadAuthors()]);
  const authorMap = new Map(authors.map((a) => [a.author_id, a]));

  const filterBar = h('div', { class: 'filter-bar' });
  const countries = [...new Set(laureates.map((r) => r.country).filter(Boolean))].sort();
  const languages = [...new Set(laureates.map((r) => r.language).filter(Boolean))].sort();
  const decades = [...new Set(laureates.map((r) => Math.floor(r.year / 10) * 10))].sort((a, b) => b - a);

  const decadeSel = h('select', {}, [
    h('option', { value: '' }, '年代: すべて'),
    ...decades.map((d) => h('option', { value: String(d) }, `${d}年代`)),
  ]);

  const countrySel = h('select', {}, [
    h('option', { value: '' }, '国・地域: すべて'),
    ...countries.map((c) => h('option', { value: c }, c)),
  ]);
  const langSel = h('select', {}, [
    h('option', { value: '' }, '言語: すべて'),
    ...languages.map((l) => h('option', { value: l }, l)),
  ]);
  const transSel = h('select', {}, [
    h('option', { value: '' }, '邦訳: すべて'),
    h('option', { value: 'available' }, '邦訳ありのみ'),
    h('option', { value: 'unavailable' }, '未邦訳のみ'),
    h('option', { value: 'unverified' }, '書誌要確認のみ'),
  ]);
  filterBar.appendChild(decadeSel);
  filterBar.appendChild(countrySel);
  filterBar.appendChild(langSel);
  filterBar.appendChild(transSel);
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
      list.appendChild(h('div', { class: 'empty-state' }, '該当する受賞者がいません。'));
      return;
    }
    for (const r of filtered) {
      list.appendChild(renderLaureateItem(r, award, authorMap, awards));
    }
  }
  decadeSel.addEventListener('change', render);
  countrySel.addEventListener('change', render);
  langSel.addEventListener('change', render);
  transSel.addEventListener('change', render);
  render();

  renderRelated(app, award, awards);
}

function renderLaureateItem(r, award, authorMap, awards) {
  const isNoAward = !r.author_id;
  const item = h('div', { class: 'laureate-item' });
  const row = h('button', { class: 'laureate-row', type: 'button' });

  const yearLabel = h('span', { class: 'year' }, [
    String(r.year),
    r.session ? h('span', { class: 'round' }, `${r.session}${r.round ? ` 第${r.round}回` : ''}`) : null,
  ]);
  row.appendChild(yearLabel);

  if (isNoAward) {
    row.appendChild(h('span', { class: 'names' }, h('span', { class: 'no-award' }, '該当作品なし')));
  } else {
    const names = h('div', { class: 'names' }, [
      h('span', { class: 'author' }, `${r.author_ja || r.author_en || r.author_id}`),
      (r.work_ja || r.work_original) ? h('span', { class: 'work' }, r.work_ja || r.work_original) : null,
    ]);
    row.appendChild(names);
    const badge = translationBadge(r.jp_translation);
    if (badge) row.appendChild(badge);
  }

  item.appendChild(row);
  const detail = h('dl', { class: 'laureate-detail', hidden: '' });
  item.appendChild(detail);

  row.addEventListener('click', () => {
    const hidden = detail.hasAttribute('hidden');
    if (hidden) {
      fillDetail(detail, r, award, authorMap, awards);
      detail.removeAttribute('hidden');
    } else {
      detail.setAttribute('hidden', '');
    }
  });

  return item;
}

function fillDetail(detail, r, award, authorMap, awards) {
  if (detail.dataset.filled) return;
  detail.dataset.filled = '1';
  detail.innerHTML = '';
  const rows = [];
  if (r.author_id) {
    rows.push(['作家', h('a', { href: `#/author/${r.author_id}` }, r.author_ja || r.author_en || r.author_id)]);
  }
  if (r.author_en && r.author_en !== r.author_ja) rows.push(['原綴り', r.author_en]);
  if (r.country) rows.push(['国・地域', r.country]);
  if (r.work_ja || r.work_original) {
    rows.push(['受賞作', [r.work_ja, r.work_original].filter(Boolean).join(' / ')]);
  }
  if (r.theme_summary_ja) rows.push(['作品について', r.theme_summary_ja]);
  if (r.translator_en) rows.push(['英訳者', r.translator_en]);
  if (r.citation_ja) rows.push(['受賞理由(要旨)', r.citation_ja]);
  if (r.lecture_title || r.lecture_url) {
    const val = h('span', {}, [
      r.lecture_title ? `${r.lecture_title} ` : '',
      r.lecture_url ? h('a', { href: r.lecture_url, target: '_blank', rel: 'noopener' }, '公式サイトで見る') : null,
    ]);
    rows.push(['記念講演', val]);
  }
  if (r.jp_translation) {
    const jpt = r.jp_translation;
    let val;
    if (jpt.status === 'available') {
      val = h('span', {}, [
        jpt.title_ja ? `『${jpt.title_ja}』 ` : '',
        [jpt.translator, jpt.publisher, jpt.year].filter(Boolean).join(' / '),
        jpt.note ? h('div', { class: 'note' }, jpt.note) : null,
      ]);
    } else if (jpt.status === 'original-ja') {
      val = '日本語で書かれた原文です';
    } else if (jpt.status === 'unavailable') {
      val = h('span', {}, jpt.note || '未邦訳');
    } else {
      val = '対象外';
    }
    rows.push(['邦訳情報', val]);
  }
  if (r.notes) rows.push(['備考', r.notes]);
  if (r.source_urls && r.source_urls.length) {
    rows.push(['出典', h('span', {}, r.source_urls.map((u, i) => h('a', { href: u, target: '_blank', rel: 'noopener', style: 'display:block;' }, u)))]);
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
            return h('a', { class: 'other-award-badge', href: `#/author/${r.author_id}` }, `${aw ? aw.name_ja : e.award_id} (${e.year})`);
          })
        );
        rows.push(['他の受賞', badges]);
      }
    }
  }

  for (const [label, val] of rows) {
    detail.appendChild(h('dt', {}, label));
    detail.appendChild(h('dd', {}, typeof val === 'string' ? val : val));
  }
}

function renderRelated(app, award, awards) {
  if (!award.related_awards || !award.related_awards.length) return;
  const wrap = h('div', {});
  wrap.appendChild(h('h3', { class: 'page-title', style: 'font-size:1.05rem;' }, '関連する賞'));
  for (const rel of award.related_awards) {
    const relAward = awards.find((a) => a.id === rel.id);
    wrap.appendChild(h('div', { class: 'related-note' }, [
      h('h4', {}, h('a', { href: `#/award/${rel.id}` }, relAward ? relAward.name_ja : rel.id)),
      h('p', { style: 'margin:0;' }, rel.note),
    ]));
  }
  app.appendChild(wrap);
}

/* ================= AUTHOR DETAIL ================= */
async function viewAuthor(app, authorId) {
  const [authors, awards] = await Promise.all([loadAuthors(), loadAwards()]);
  const author = authors.find((a) => a.author_id === authorId);
  app.innerHTML = '';
  app.appendChild(h('a', { class: 'back-link', href: '#/' }, '← ホームへ戻る'));

  if (!author) {
    app.appendChild(h('div', { class: 'empty-state' }, '作家情報が見つかりません。'));
    return;
  }

  app.appendChild(h('h2', { class: 'page-title' }, `${author.name_ja || ''}${author.name_en ? ` / ${author.name_en}` : ''}`));
  app.appendChild(h('p', { class: 'page-subtitle' }, author.country || ''));

  if (author.is_multi_award) {
    app.appendChild(h('div', { class: 'related-note' }, [
      h('h4', {}, '複数の文学賞を受賞'),
      h('p', { style: 'margin:0;' }, `${author.award_ids.map((id) => {
        const aw = awards.find((x) => x.id === id);
        return aw ? aw.name_ja : id;
      }).join(' / ')} を受賞しています。`),
    ]));
  }

  const timeline = h('ul', { class: 'author-timeline' });
  for (const e of author.awards) {
    const aw = awards.find((x) => x.id === e.award_id);
    timeline.appendChild(h('li', {}, [
      h('span', { class: 'tl-year' }, String(e.year)),
      ' ',
      h('a', { href: `#/award/${e.award_id}` }, aw ? aw.name_ja : e.award_id),
      e.session ? ` (${e.session}${e.round ? ` 第${e.round}回` : ''})` : '',
      (e.work_ja || e.work_original) ? h('div', {}, e.work_ja || e.work_original) : null,
    ]));
  }
  app.appendChild(timeline);

  if (author.representative_works && author.representative_works.length) {
    app.appendChild(h('h3', { class: 'page-title', style: 'font-size:1.05rem;' }, '代表作'));
    for (const w of author.representative_works) {
      const aw = awards.find((x) => x.id === w.award_id);
      const card = h('div', { class: 'work-card' }, [
        h('div', { class: 'work-title' }, w.work_ja || w.work_original || ''),
        h('div', { class: 'work-meta' }, `${aw ? aw.name_ja : w.award_id} (${w.year})`),
      ]);
      if (w.jp_translation_status === 'available' && w.jp_translation_title) {
        card.appendChild(h('div', { class: 'work-meta' }, `邦題: 『${w.jp_translation_title}』`));
      }
      if (w.theme_summary_ja) {
        card.appendChild(h('p', { class: 'work-summary' }, w.theme_summary_ja));
      }
      app.appendChild(card);
    }
  }

  if (author.major_works && author.major_works.length) {
    app.appendChild(h('h3', { class: 'page-title', style: 'font-size:1.05rem;' }, 'その他の主要作品'));
    const list = h('ul', { class: 'major-works-list' });
    for (const w of author.major_works) {
      list.appendChild(h('li', {}, [
        h('div', {}, [
          h('span', { class: 'work-title' }, w.title_original || ''),
          w.title_ja ? h('span', { class: 'work-meta' }, ` 『${w.title_ja}』`) : null,
          w.year ? h('span', { class: 'work-meta' }, ` (${w.year})`) : null,
        ]),
        w.theme_summary_ja ? h('p', { class: 'work-summary' }, w.theme_summary_ja) : null,
      ]));
    }
    app.appendChild(list);
  }
}

/* ================= CONNECTIONS MAP ================= */
async function viewConnections(app) {
  const [authors, awards] = await Promise.all([loadAuthors(), loadAwards()]);
  app.innerHTML = '';
  app.appendChild(h('a', { class: 'back-link', href: '#/' }, '← ホームへ戻る'));
  app.appendChild(h('h2', { class: 'page-title' }, '関連性マップ'));
  app.appendChild(h('p', { class: 'page-subtitle' }, '複数の文学賞を受賞した作家の一覧です。'));

  const multi = authors.filter((a) => a.is_multi_award);
  const relevantAwardIds = awards.filter((a) => a.data_file).map((a) => a.id);

  if (multi.length === 0) {
    app.appendChild(h('div', { class: 'empty-state' }, '複数受賞の作家が見つかりません。'));
  } else {
    const wrap = h('div', { class: 'connections-table-wrap' });
    const table = h('table', { class: 'connections-table' });
    const thead = h('thead', {}, h('tr', {}, [
      h('th', {}, '作家'),
      ...relevantAwardIds.map((id) => {
        const aw = awards.find((x) => x.id === id);
        return h('th', {}, aw ? aw.name_ja : id);
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

  app.appendChild(h('h3', { class: 'page-title', style: 'font-size:1.05rem;' }, '賞どうしの関連'));
  for (const award of awards) {
    if (!award.related_awards || !award.related_awards.length) continue;
    for (const rel of award.related_awards) {
      if (award.id > rel.id) continue; // avoid duplicate pairs
      const relAward = awards.find((x) => x.id === rel.id);
      app.appendChild(h('div', { class: 'related-note' }, [
        h('h4', {}, `${award.name_ja} × ${relAward ? relAward.name_ja : rel.id}`),
        h('p', { style: 'margin:0;' }, rel.note),
      ]));
    }
  }
}

/* ================= STATS (Phase 2) ================= */
async function viewStats(app) {
  const [awards, authors] = await Promise.all([loadAwards(), loadAuthors()]);
  app.innerHTML = '';
  app.appendChild(h('a', { class: 'back-link', href: '#/' }, '← ホームへ戻る'));
  app.appendChild(h('h2', { class: 'page-title' }, '統計'));

  const withData = awards.filter((a) => a.data_file);
  const counts = withData.map((a) => ({
    label: a.name_ja,
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
  app.appendChild(h('p', { class: 'page-subtitle' }, '収録する全8賞の受賞者数を集計。共同受賞は個別に数えています。'));
  app.appendChild(svg);
}

/* ---------- service worker registration ---------- */
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register(`${APP_ROOT}sw.js?v=5-cache-refresh`, { updateViaCache: 'none' })
      .then((registration) => registration.update())
      .catch(() => {});
  });
}
