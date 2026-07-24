# 世界文学賞総覧 (literary-awards)

ノーベル文学賞・ブッカー賞・国際ブッカー賞・芥川龍之介賞など、世界の主要な文学賞の受賞者・受賞作・受賞理由を横断して調べられる静的PWAです。同一作家が複数の賞を受けている例(カズオ・イシグロ、大江健三郎、ハン・ガンなど)を「関連性マップ」で可視化します。

ビルドツール不使用の素のHTML/CSS/JavaScriptで構築されており、GitHub Pagesでそのまま配信できます。

## 動作環境

- iPhone/iPad Safari、Mac Chrome/Safariで動作確認
- オフライン対応PWA(Service Workerによるキャッシュ)
- ダークモード対応(`prefers-color-scheme`に自動追従)

## ディレクトリ構成

```
literary-awards/
├── index.html          SPAシェル
├── app.js               ルーティング・画面描画ロジック(ハッシュルーティング)
├── style.css             スタイル(書斎風の配色、CSS変数でライト/ダーク切替)
├── sw.js                 Service Worker(バージョン管理されたキャッシュ)
├── manifest.json          PWAマニフェスト
├── icons/                 アプリアイコン
└── data/
    ├── awards.json               8賞のマスタデータ(名称・国・創設年・関連賞など)
    ├── authors.json              全受賞者を作家単位で名寄せしたクロスリファレンス(複数受賞の検出に使用、scripts/gen_authors.pyで自動生成)
    ├── major_works.json          ノーベル賞・ブッカー賞・国際ブッカー賞受賞作家(186名)の代表作リスト(受賞作以外の主要著作)
    └── laureates/
        ├── nobel.json            ノーベル文学賞(1901-2025、129件)
        ├── booker.json            ブッカー賞(1969-2025、60件)
        ├── intl-booker.json       国際ブッカー賞(2005-2026、17件)
        └── akutagawa.json         芥川龍之介賞(全175回、222件)
scripts/
└── gen_authors.py         data/laureates/*.jsonとdata/major_works.jsonからdata/authors.jsonを再生成するスクリプト
```

Phase 2(ゴンクール賞・ピュリッツァー賞フィクション部門・全米図書賞フィクション部門・セルバンテス賞)は`awards.json`にマスタ情報のみ登録済みで、`data_file: null`のため一覧には「準備中」と表示されます。

## データ設計の要点

- **`author_id`**: 英語名ベースのスラッグ(例: `kazuo-ishiguro`)。同一人物であれば全ファイルで必ず同じ値を使うこと。これが賞をまたいだ名寄せ(関連性マップ)を支える唯一の仕組みです。新しい賞のデータを追加する際、既存ファイルに同名の作家がいないか`data/authors.json`で必ず確認してください。
- **`data/major_works.json`**: ノーベル賞・ブッカー賞・国際ブッカー賞受賞作家(芥川賞のみの受賞者は対象外)について、受賞作以外の代表作(原題・判明していれば邦題・発表年)を`author_id`をキーに記録したもの。`jp_translation_title`と同様、邦題は確証がある場合のみ記載し、不確かな場合は`null`のままにしています(捏造防止)。新しい対象作家を追加する場合はこのファイルにエントリを足してから`scripts/gen_authors.py`を再実行してください。
- **`theme_summary_ja`**: 各作品(受賞作・major_works双方)につけた3〜4文程度の日本語テーマ・あらすじ要約。既存の紹介文・書評・ジャケット文の言い換えではなく独自の日本語表現で記述したもので、内容を確認できなかった作品は`null`のままにしています(全984作品中933作品に付与、51作品はnull)。受賞作側は`data/laureates/*.json`の各レコードに直接持たせ、`scripts/gen_authors.py`実行時に`representative_works`へ伝播します。major_works側は`data/major_works.json`の各作品エントリに直接持たせます。
- **`jp_translation.status`**: `available` / `unavailable` / `original-ja`(芥川賞は常にこれ) / `n/a`(ノーベル賞や該当作品なしの回など、対象作品が存在しない場合)のいずれか。
- **著作権への配慮**: `citation_ja`は受賞理由の要約であり、末尾に「(要旨)」を付けた意訳・要約のみを収録。ノーベル賞受賞記念講演の本文は一切収録せず、タイトルと公式サイトへのリンクのみ。作品本文の引用も行っていません。
- **不確実な情報の扱い**: 訳者・出版社などの書誌情報が確認できない場合は、`status`のみ記録し`translator`/`publisher`は`null`のまま`note`に「書誌要確認」等を残しています。断定できない情報を推測で埋めていません。

## データ更新手順

### ノーベル文学賞(毎年10月発表)

1. 受賞者発表後、`data/laureates/nobel.json`に新しいレコードを追加。
2. `author_id`は英語名ベースのスラッグを新規作成(既存の受賞歴がある作家の場合は`data/authors.json`で既存IDを確認して再利用)。
3. `citation_ja`はノーベル財団発表の公式citationを要約・意訳し、末尾に「(要旨)」を付す。全文引用・翻訳は行わないこと。
4. `lecture_url`は`https://www.nobelprize.org/prizes/literature/{year}/summary/`のパターンを使用(個別の講演ページURLは年によって構成が異なるため、確実にアクセスできるsummaryページに統一)。
5. 邦訳情報は必ずWebで検索して確認する。受賞直後は邦訳が存在しないことが多いが、数年後に刊行されるケースもあるため「未邦訳」と断定せず`unavailable`+noteで留めるか、確認できた範囲のみ記録する。

### 芥川龍之介賞(1月・7月発表、年2回)

1. 日本文学振興会の発表後、`data/laureates/akutagawa.json`に新しいレコードを追加(`session`は「上期」または「下期」、`round`は通算回数)。
2. `author_id`は原則ローマ字スラッグを新規作成。pykakasi等でヘボン式ローマ字化した上で、ハイフン区切りに整形する運用としていた(生成スクリプトは本リポジトリには含めていないため、新規追加時は手動でスラッグを作成して構わない)。
3. `jp_translation.status`は常に`original-ja`。
4. `citation_ja`は選評の詳細が確認できないため、無理に埋めずnullのままでよい(既存データも大半がnull)。

### ブッカー賞・国際ブッカー賞(隔年5月頃発表)

1. `data/laureates/booker.json` / `intl-booker.json`にレコードを追加。
2. 受賞作家がノーベル賞受賞者(または将来なりうる著名作家)の場合、`data/authors.json`と`data/laureates/nobel.json`を確認し、既存の`author_id`と一致させる。
3. 邦訳刊行までにタイムラグ(1〜3年程度)があるケースが多いため、受賞直後は`unavailable`とし、翌年以降に改めて確認・更新する運用を推奨。

### 新しい賞の追加(Phase 2: ゴンクール賞・ピュリッツァー賞・全米図書賞・セルバンテス賞など)

1. `data/awards.json`の該当エントリの`data_file`を`null`から実際のパス(例: `"laureates/goncourt.json"`)に変更。
2. `data/laureates/goncourt.json`等を新規作成し、他の賞と同じレコード形式で作成。
3. `sw.js`の`PRECACHE_URLS`に新しいJSONファイルのパスを追加し、`CACHE_VERSION`をインクリメントする(バージョンを上げないと既存ユーザーのキャッシュが更新されない)。
4. 新しい賞の`laureates/*.json`を`scripts/gen_authors.py`の`AWARD_FILES`辞書に追加し、`python3 scripts/gen_authors.py`を実行して`data/authors.json`を再生成する。

## ローカルでの動作確認

ビルド不要。任意のHTTPサーバーで配信するだけで動作します。

```bash
cd literary-awards
python3 -m http.server 8000
# http://localhost:8000/index.html を開く
```

Service Workerはoriginごとにスコープされるため、別プロジェクトで同じポートを使い回すと古いキャッシュが残ることがあります。挙動がおかしい場合はブラウザの開発者ツールで対象originのService Workerを解除するか、別のポート番号を使ってください。

## デプロイ(GitHub Pages)

1. リポジトリのSettings → Pages → Branch を `main` / `(root)` に設定。
2. `main`ブランチにpushすると自動的に公開される。
3. 公開URLの例: `https://kimuhixy-ux.github.io/literary-awards/`
4. 相対パス構成のため、サブパス配信でも問題なく動作する。

## 免責事項

受賞理由・選評はすべて要約であり、原文の逐語訳ではありません。ノーベル文学賞受賞記念講演の全文は収録していません。詳細は各賞の公式サイトをご参照ください。
