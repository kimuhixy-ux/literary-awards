# 文学賞データ向けプログラマティックSEO運用手順

この文書は `literary-awards` の静的受賞記録ページを再生成・検証し、同種のデータサイトへ展開するための手順書です。

## 1. 追加・変更ファイル

- `scripts/generate_pages.py`: 日英詳細ページ、索引、sitemap、robotsの一括生成
- `scripts/validate_generated_pages.py`: 件数、SEO要素、構造化データ、内部リンク、著作物除外の検証
- `templates/detail_ja.html` / `templates/detail_en.html`: 日英詳細ページ
- `templates/index_ja.html` / `templates/index_en.html`: 文学賞別の日英索引
- `items/<slug>/index.html` / `en/items/<slug>/index.html`: 生成ページ
- `sitemap.xml` / `robots.txt`
- `style.css`: 既存テーマに合わせた詳細・索引用スタイル
- `index.html` / `en/index.html`: 静的索引への入口
- `sw.js` / `app.js`: Service Workerの配信バージョン更新

## 2. データとURL

`data/awards.json` の `data_file` が指す8ファイル、合計795レコードを入力とする。URLは次の形式で、slugは賞ID・年・回次・著者IDから安定的に生成する。

- 日本語: `/items/<award-year-author>/`
- 英語: `/en/items/<award-year-author>/`

受賞者名のない「該当作なし」も独立した記録として生成する。著者IDがない受賞者には英語名またはレコード位置を使う。重複slugには連番を付け、生成時に集合全体の一意性を保証する。

## 3. 表示可能な項目

静的ページに出力するのは、賞名、年、回次、受賞者名、国・地域、言語、作品名、翻訳者、邦訳の書誌的情報、出典URLなどの事実情報に限定する。

次の説明的・著作物的フィールドは、本文、title、meta description、OGP、JSON-LD、索引のすべてから除外する。

- `citation_ja` / `citation_en`
- `theme_summary_ja` / `theme_summary_en`
- `notes` / `notes_en`
- `lecture_title` と講演本文
- `jp_translation.note` / `jp_translation.note_en`
- 賞の `description` と関連賞の説明文

検証スクリプトは、これらの原文が生成物へ混入していないことを全ページで検査する。

## 4. 翻訳フォールバック

英語フィールドがない場合は、原綴り、既存の日本語値の順でフォールバックする。未確認の翻訳を推測して追加しない。後日データ翻訳を補完した場合は再生成だけで反映される。

## 5. schema.org

- 受賞者がいる記録: `WebPage.mainEntity` から `Person` を参照し、`Person.award` に賞名と年を記録
- 作品名がある記録: `Book` を追加し、受賞者がいる場合は `author` で参照
- 該当作なし: 人物や作品を作らず `WebPage` のみ
- 全ページ共通: `WebSite` と `BreadcrumbList`

受賞年を作品の刊行年として扱わない。生年月日、ISBN、出版社など、レコードにない値を推測しない。

## 6. AdSenseと英語URL

既存の `config.js` と `ads.js` を各テンプレートから相対パスで読み込む。本番ホストだけで `ca-pub-3562055879455682` を読み込む既存条件は変更しない。英語ページは既存の `/en/` 構造に合わせ、canonicalと `ja` / `en` / `x-default` hreflangを相互設定する。

## 7. sitemapとService Worker

795件×2言語、索引2ページ、既存主要6ページを単一 `sitemap.xml` に収録する。5万URLを超えるデータへ横展開する場合はsitemapを分割する。`robots.txt` にはsitemapの絶対URLを記載する。

生成ページは `PRECACHE_URLS` に追加しない。既存のネットワーク優先処理により、閲覧済みページだけを実行時キャッシュする。

## 8. 更新・検証手順

```sh
python3 scripts/validate_data.py
python3 scripts/generate_pages.py
python3 scripts/validate_generated_pages.py
git diff --check
```

生成物は手編集しない。修正はデータ、テンプレート、生成スクリプトへ行う。再生成を2回実行し、2回目に差分が生じないことも確認する。

## 9. 公開前チェック

- [ ] 日英それぞれ795詳細ページがある
- [ ] 全slugが一意で日英一致している
- [ ] titleとmeta descriptionが各言語内で一意
- [ ] canonicalと相互hreflangが正しい
- [ ] OGPとTwitter Cardがある
- [ ] JSON-LDが構文エラーなく、事実情報だけを含む
- [ ] 除外フィールドが生成物にない
- [ ] 全内部リンクの参照先が存在する
- [ ] 索引に各レコードが1回だけ載る
- [ ] sitemapが1,598 URLで重複なし
- [ ] 生成ページが事前キャッシュ対象外
- [ ] モバイル幅とデスクトップ幅で代表ページを目視確認
- [ ] git push前にオーナー承認を得る
