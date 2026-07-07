# 自動応募 live 稼働 ＆ アプリ配信 セットアップ手順

このチェックリストを上から順に進めれば、①自動応募のlive稼働 と ②アプリの自動更新 が完了します。
所要 約10分。GitHubリポジトリ `tanishi8/kensho-mvp`（あなたのリポジトリ名に読み替え）で操作します。

---

## パート①　自動応募を live にする

### 手順1. 応募者情報を記入する
1. `profile.記入用.json` をテキストエディタで開く。
2. 15項目をあなたの**実情報**で埋める（虚偽・なりすましは不可）。記入例:

   ```json
   {
     "last_name": "谷",           // 姓
     "first_name": "太郎",         // 名
     "last_kana": "タニ",          // 姓カナ（全角カタカナ）
     "first_kana": "タロウ",        // 名カナ
     "zip": "7300000",            // 郵便番号（ハイフン無し7桁）
     "pref": "広島県",
     "city": "広島市中区",
     "address1": "紙屋町1-1",       // 町名・番地
     "address2": "○○マンション101",  // 建物名・部屋番号（無ければ空でOK）
     "tel": "09000000000",        // 電話（ハイフン無し）
     "email": "あなたの懸賞用メール@example.com",
     "birth_year": "2000",
     "birth_month": "4",
     "birth_day": "1",
     "gender": "男性"             // 「男性」「女性」など
   }
   ```
3. 記入した内容を**すべてコピー**しておく（次の手順で貼り付けます）。

> メモ: このファイルはローカル用です。GitHubには**コミットしません**（Secretで渡します）。

### 手順2. GitHub Secret に登録する（PROFILE_JSON）
1. ブラウザで `https://github.com/tanishi8/kensho-mvp` を開く。
2. 上部タブ **Settings** をクリック。
3. 左メニュー **Secrets and variables** → **Actions** をクリック。
4. 緑の **New repository secret** ボタンをクリック。
5. **Name** に `PROFILE_JSON` と入力。
6. **Secret** 欄に、手順1でコピーしたJSON全文を貼り付け。
7. **Add secret** をクリック。

（メール応募も自動送信したい場合は、同じ画面で `SMTP_HOST` `SMTP_PORT` `SMTP_USER` `SMTP_PASS` も登録。
   未登録ならメール応募は自動スキップされ、CAPTCHA無しフォームのみ自動応募します。）

### 手順3. まず dry-run で安全確認（送信しない）
1. リポジトリ上部タブ **Actions** をクリック。
2. 左の一覧から **「懸賞 自動応募（ツールA）」** を選ぶ。
3. 右の **Run workflow** ボタン → `live` は **false のまま** → **Run workflow**。
4. 数分後、緑チェックになったら実行をクリック →「自動応募 実行」ステップのログで
   「応募候補（送信なし）」を確認（auto/escalate/skip の一覧）。
   → 変な対象が混じっていないか、件数は妥当かをチェック。

### 手順4. 問題なければ live 実行（実送信）
1. 同じ **「懸賞 自動応募（ツールA）」** → **Run workflow**。
2. `live` を **true** に切り替え → **Run workflow**。
3. 以降、この操作をした時だけ実送信されます。
   スケジュール（毎日JST8:20）は**常にdry-run**なので、勝手に応募が飛ぶことはありません。

> 毎日自動でlive応募させたい場合は、`.github/workflows/autoapply.yml` の schedule 実行を
> live化する改修が必要です。希望があれば対応します（暴走防止のため既定はdry-runにしてあります）。

---

## パート②　アプリを自動更新にする（GitHub Pages）

### 手順5. GitHub Pages を /docs で有効化
1. `https://github.com/tanishi8/kensho-mvp` → **Settings**。
2. 左メニュー **Pages**。
3. **Build and deployment** → **Source** を **Deploy from a branch** に。
4. **Branch** を `main`、フォルダを **/docs** に設定 → **Save**。
5. 1〜2分待つと、ページ上部に公開URLが表示される。
   懸賞データのURLは:
   ```
   https://tanishi8.github.io/kensho-mvp/app_feed.json
   ```
   （`tanishi8` はあなたのGitHubユーザー名に置き換え）
6. ブラウザでそのURLを開き、JSONが表示されれば成功。

### 手順6. アプリに URL を設定
1. アプリを開く → 右上の **⚙️（設定）**。
2. **懸賞データ(app_feed.json)のURL** に手順5のURLを貼り付け。
3. （任意）**Gemini APIキー** を入れるとコメント肉付けがLLMになる。
4. **保存**。これでアプリが毎日更新の懸賞データを表示します。

---

## 完了チェック
- [ ] profile.記入用.json を実情報で記入した
- [ ] PROFILE_JSON を Secret に登録した
- [ ] dry-run を実行し候補を確認した
- [ ] live 実行で応募が送信された（Discordに「✅応募」通知）
- [ ] GitHub Pages を /docs で有効化し、app_feed.json が開けた
- [ ] アプリ設定にURLを入れ、最新の懸賞が表示された

困ったら、詰まった手順番号を教えてください。
