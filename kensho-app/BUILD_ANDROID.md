# 懸賞アシスタント アプリ — ビルド手順（Android / PWA）

このアプリは Web技術（HTML/JS/CSS）で作られ、**Capacitor** でネイティブAndroidアプリ(APK)に
ラップできます。同じコードが **PWA**（ホーム画面に追加して使うWebアプリ）としても動きます。

- 中身: `www/`（index.html / app.js / styles.css / app_feed.json ほか）
- 設定: `capacitor.config.json`, `package.json`

---

## 0. アプリが表示するデータ（前提）

アプリは `app_feed.json`（懸賞ランキング）を読み込みます。取得先は3通り:

1. **GitHub Pages（推奨・自動更新）**
   バックエンド `kensho-mvp` の GitHub Actions が毎日 `docs/app_feed.json` を更新します。
   リポジトリの Settings → Pages → Source を「Deploy from a branch」→ `main` / `/docs` にすると、
   `https://<ユーザー名>.github.io/kensho-mvp/app_feed.json` で配信されます。
   → アプリの「⚙️設定」でこのURLを入力。
2. **同梱データ**（オフライン）: `www/app_feed.json`（初期サンプル）。設定URLが空/失敗時に使用。
3. 手動で `www/app_feed.json` を差し替えてもOK。

---

## 手順A: まず PWA として今すぐ使う（最短・ビルド不要）

### ローカルで確認
```bash
cd kensho-app
npm run serve        # http://localhost:8080 を開く
```

### スマホで使う（ホーム画面に追加）
`www/` を GitHub Pages などにそのまま公開し、スマホのChromeで開く →
メニュー →「ホーム画面に追加」。アプリのように全画面で起動します。

---

## 手順B: Android APK を作る（Capacitor → Android Studio）

### 必要なもの
- Node.js 18+ / npm
- Android Studio（SDK・Gradle同梱）

### 1) 依存をインストールし Android プロジェクトを生成
```bash
cd kensho-app
npm install
npx cap add android      # android/ フォルダが生成される
npx cap sync             # www/ と設定を android/ に反映
```

### 2) Android Studio で開く
```bash
npx cap open android
```
Android Studio が起動し `android/` プロジェクトが開きます。初回は Gradle 同期を待ちます。

### 3) 実機・エミュレータで実行
- 上部の ▶（Run）で、接続したスマホ or エミュレータにインストールして起動。
- スマホ側は「開発者向けオプション → USBデバッグ」をON。

### 4) 配布用 APK / AAB を書き出す
- メニュー **Build → Build Bundle(s)/APK(s) → Build APK(s)**
  → `android/app/build/outputs/apk/debug/app-debug.apk`
- 自分だけで使うなら debug APK をそのまま端末に入れればOK（署名は自動のデバッグ鍵）。
- 手元でずっと使うなら **Build → Generate Signed Bundle/APK** で署名鍵を作って release ビルドにすると、
  Android の警告が減り長期運用に向きます。

### 中身を更新したとき
`www/` を編集したら:
```bash
npx cap copy android     # もしくは npx cap sync
```
その後 Android Studio で再ビルド。

---

## 権限・設定メモ
- 外部リンク（応募ページ・X・Instagram）は既定のブラウザ/アプリで開きます
  （`@capacitor/browser` があればアプリ内ブラウザ、無ければ外部ブラウザ）。
- Gemini APIキー・GitHubトークンは**端末ローカル**(localStorage)にのみ保存され、
  Google/GitHub の公式API以外へは送信しません。
- ネットワーク: `capacitor.config.json` の `androidScheme: https` 済み。

---

## トラブルシュート
- **Gradle同期エラー**: Android Studio の「SDK Manager」で最新の Android SDK / Build-Tools を入れる。
- **白い画面**: `npx cap copy` を忘れていないか。`www/index.html` が存在するか確認。
- **データが出ない**: 設定のフィードURLが正しいか、GitHub Pages が有効かを確認。空にすると同梱データを表示。
