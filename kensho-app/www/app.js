/* 懸賞アシスタント — アプリ本体ロジック
   - app_feed.json を取得して懸賞カードを表示
   - ワンタップSNS導線（RT/フォローは人間が最終操作＝規約遵守）
   - Gemini で感想を肉付け
   - 応募記録（ローカル＋任意でGitHubへ同期）
   すべての鍵・トークンは端末ローカル(localStorage)にのみ保存。 */

const LS = {
  get: (k, d = "") => localStorage.getItem(k) ?? d,
  set: (k, v) => localStorage.setItem(k, v),
  del: (k) => localStorage.removeItem(k),
};
const CFG = {
  feedUrl:  () => LS.get("feedUrl", "app_feed.json"),
  gemini:   () => LS.get("geminiKey", ""),
  model:    () => LS.get("geminiModel", "gemini-2.5-flash-lite"),
  repo:     () => LS.get("ghRepo", ""),
  token:    () => LS.get("ghToken", ""),
};

let FEED = { items: [], watch: [], generated_at: null };
let appliedLocal = new Set(JSON.parse(LS.get("appliedLocal", "[]")));
let activeGenre = "all";
let curItem = null;
let currentView = "picks";

const $ = (s) => document.querySelector(s);
const el = (t, c) => { const e = document.createElement(t); if (c) e.className = c; return e; };

/* ---------- 外部リンク（Capacitorがあればネイティブで開く） ---------- */
function openExternal(url) {
  if (!url) return;
  try {
    if (window.Capacitor?.Plugins?.Browser) {
      window.Capacitor.Plugins.Browser.open({ url });
      return;
    }
  } catch (e) {}
  window.open(url, "_blank", "noopener");
}

/* ---------- トースト ---------- */
let toastTimer = null;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg; t.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add("hidden"), 2200);
}

/* ---------- フィード取得 ----------
   3段フォールバック（F）: ①GitHub Contents API（repo+token時・private非公開取得）
                          ②設定した公開URL（GitHub Pages 等）
                          ③同梱の app_feed.json（オフライン） */
async function fetchFromUrl(url) {
  const u = url + (url.includes("?") ? "&" : "?") + "t=" + Date.now();
  const res = await fetch(u, { cache: "no-store" });
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.json();
}

async function fetchViaGitHub() {
  const repo = CFG.repo(), token = CFG.token();
  if (!repo || !token) return null;
  const api = `https://api.github.com/repos/${repo}/contents/docs/app_feed.json?ref=main&t=${Date.now()}`;
  const res = await fetch(api, {
    headers: { Authorization: `Bearer ${token}`, Accept: "application/vnd.github.raw+json" },
    cache: "no-store",
  });
  if (!res.ok) throw new Error("GitHub API " + res.status);
  const txt = await res.text();
  const j = JSON.parse(txt);
  // Accept:raw ならフィードJSON（contentを持たない）。無視された場合はメタJSON(content=base64)（E）
  return j.content
    ? JSON.parse(decodeURIComponent(escape(atob(j.content.replace(/\n/g, "")))))
    : j;
}

async function loadFeed() {
  $("#feedMeta").textContent = "読み込み中…";
  // 取得元を優先順に並べる（設定に応じて）
  const sources = [];
  if (CFG.repo() && CFG.token()) sources.push({ fn: fetchViaGitHub, fallback: false });
  const url = CFG.feedUrl();
  if (url && url !== "app_feed.json") sources.push({ fn: () => fetchFromUrl(url), fallback: false });
  sources.push({ fn: () => fetchFromUrl("app_feed.json"), fallback: true });

  let loaded = false, usedFallback = false;
  for (const src of sources) {
    try {
      const data = await src.fn();
      if (data) { FEED = data; loaded = true; usedFallback = src.fallback; break; }
    } catch (e) { /* 次の取得元へ */ }
  }
  if (!loaded) {
    $("#feedMeta").textContent = "データ取得に失敗しました。設定を確認してください。";
    FEED = { items: [], watch: [] };
  } else if (usedFallback && sources.length > 1) {
    toast("オンライン取得に失敗→同梱データを表示");
  }

  const dt = FEED.generated_at ? new Date(FEED.generated_at) : null;
  $("#feedMeta").textContent =
    `全${(FEED.items || []).length}件` + (dt ? ` ・ 更新 ${dt.toLocaleString("ja-JP", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" })}` : "");
  renderStats();
  buildGenreChips();
  render();
  renderWatch();
}

/* ---------- 統計バー ---------- */
function renderStats() {
  const st = FEED.stats || {};
  const bar = $("#statsBar");
  if (!st || st.total == null) { bar.innerHTML = ""; return; }
  const wr = st.win_rate != null ? Math.round(st.win_rate * 100) + "%" : "-";
  bar.innerHTML = `
    <div class="st"><b>${st.applied_total ?? 0}</b><span>応募</span></div>
    <div class="st"><b>${st.won ?? 0}</b><span>当選</span></div>
    <div class="st"><b>${wr}</b><span>当選率</span></div>
    <div class="st"><b>${(FEED.items || []).length}</b><span>候補</span></div>`;
}

/* ---------- ビュー切替（狙い目 / 常設懸賞） ---------- */
function setView(v) {
  currentView = v;
  document.querySelectorAll(".vtab").forEach((b) =>
    b.classList.toggle("active", b.dataset.view === v));
  const picks = v === "picks";
  $("#list").classList.toggle("hidden", !picks);
  $("#filters").classList.toggle("hidden", !picks);
  $("#watchList").classList.toggle("hidden", picks);
}

/* ---------- 常設懸賞（watch）描画 ---------- */
function renderWatch() {
  const box = $("#watchList");
  box.innerHTML = "";
  const watch = FEED.watch || [];
  if (!watch.length) {
    const e = el("div", "empty");
    e.textContent = "常設懸賞は未登録です（watchlist.yaml に追加できます）。";
    box.appendChild(e);
    return;
  }
  const label = { monthly: "毎月応募可", weekly: "毎週", anytime: "随時" };
  watch.forEach((w) => {
    const c = el("div", "watch-card");
    const cad = w.cadence || "anytime";
    c.innerHTML = `
      <h2>${escapeHtml(w.name || "")}</h2>
      <span class="cadence ${cad}">${label[cad] || "随時"}${w.genre ? " ・ " + escapeHtml(w.genre) : ""}</span>
      ${w.note ? `<div class="watch-note">${escapeHtml(w.note)}</div>` : ""}
      <div class="actions">
        <button class="open" data-open>応募ページを開く</button>
      </div>`;
    c.querySelector("[data-open]").onclick = () => openExternal(w.url);
    box.appendChild(c);
  });
}

/* ---------- ジャンルチップ ---------- */
function buildGenreChips() {
  const row = $("#chipRow");
  row.innerHTML = "";
  const genres = ["all", ...new Set(FEED.items.map((i) => i.genre).filter(Boolean))];
  const labels = { all: "すべて" };
  genres.forEach((g) => {
    const c = el("div", "chip" + (g === activeGenre ? " active" : ""));
    c.textContent = labels[g] || g;
    c.onclick = () => { activeGenre = g; buildGenreChips(); render(); };
    row.appendChild(c);
  });
}

/* ---------- 応募状態 ---------- */
function statusOf(item) {
  if (appliedLocal.has(item.id)) return "applied";
  return item.status || "candidate";
}

/* ---------- 描画 ---------- */
function render() {
  const list = $("#list");
  list.innerHTML = "";
  const q = $("#q").value.trim().toLowerCase();
  const sortKey = $("#sortSel").value;
  const hideApplied = $("#hideApplied").checked;

  let items = FEED.items.slice();
  if (activeGenre !== "all") items = items.filter((i) => i.genre === activeGenre);
  if (q) items = items.filter((i) => (i.title || "").toLowerCase().includes(q));
  if (hideApplied) items = items.filter((i) => statusOf(i) !== "applied");
  items.sort((a, b) => (b[sortKey] ?? 0) - (a[sortKey] ?? 0));

  if (!items.length) {
    const e = el("div", "empty");
    e.textContent = "該当する懸賞がありません。";
    list.appendChild(e);
    return;
  }
  items.forEach((it, idx) => list.appendChild(card(it, idx + 1)));
}

function card(it, rank) {
  const c = el("div", "card" + (statusOf(it) === "applied" ? " applied" : ""));

  const st = statusOf(it);
  const stTag = st === "applied" ? `<span class="status-tag status-applied">応募済み</span>`
    : st === "won" ? `<span class="status-tag status-won">当選🎉</span>` : "";

  const wc = it.win_count ? `${Number(it.win_count).toLocaleString()}名` : "本数不明";
  const badges = [
    `<span class="badge">${it.method || "不明"}</span>`,
    `<span class="badge">${it.genre || "その他"}</span>`,
    `<span class="badge win">${wc}</span>`,
    it.roi != null ? `<span class="badge roi">roi ${it.roi}</span>` : "",
    it.manual_lottery ? `<span class="badge manual">手動抽選</span>` : "",
    it.local ? `<span class="badge local">地域限定</span>` : "",
    it.preference_hit ? `<span class="badge pref">★好み</span>` : "",
  ].join("");

  const sns = it.sns || {};
  const openCls = sns.platform === "x" ? "open x" : sns.platform === "instagram" ? "open instagram" : "open";
  const openLabel = sns.label || "応募ページを開く";

  c.innerHTML = `
    <div class="rank">#${rank} ${stTag}</div>
    <h2>${escapeHtml(it.title || "")}</h2>
    <div class="badges">${badges}</div>
    ${it.comment_advice ? `<div class="advice">💬 ${escapeHtml(it.comment_advice)}</div>` : ""}
    <div class="actions">
      <button class="${openCls}" data-open>${escapeHtml(openLabel)}</button>
      <button class="cmt" data-comment>コメント肉付け</button>
      <button class="applied-btn ${st === "applied" ? "done" : ""}" data-applied>${st === "applied" ? "✓ 応募済み" : "応募した"}</button>
    </div>`;

  c.querySelector("[data-open]").onclick = () => {
    openExternal(sns.open_url || it.link);
    if (sns.action) toast(sns.action);
  };
  c.querySelector("[data-comment]").onclick = () => openCommentModal(it);
  c.querySelector("[data-applied]").onclick = () => toggleApplied(it, c);
  return c;
}

/* ---------- 応募記録 ---------- */
async function toggleApplied(it, cardEl) {
  if (appliedLocal.has(it.id)) {
    appliedLocal.delete(it.id);
    toast("応募記録を取り消しました");
  } else {
    appliedLocal.add(it.id);
    toast("応募済みに記録しました");
    syncApplied(it).catch(() => {});
  }
  LS.set("appliedLocal", JSON.stringify([...appliedLocal]));
  render();
}

// 任意: GitHub に応募記録を同期（docs/app_applications.json を更新）
async function syncApplied(it) {
  const repo = CFG.repo(), token = CFG.token();
  if (!repo || !token) return;
  const api = `https://api.github.com/repos/${repo}/contents/docs/app_applications.json`;
  const headers = { Authorization: `Bearer ${token}`, Accept: "application/vnd.github+json" };
  let sha = null, current = {};
  try {
    const g = await fetch(api, { headers });
    if (g.ok) {
      const j = await g.json();
      sha = j.sha;
      current = JSON.parse(decodeURIComponent(escape(atob(j.content.replace(/\n/g, "")))));
    }
  } catch (e) {}
  current[it.id] = { id: it.id, title: it.title, link: it.link, applied_at: new Date().toISOString() };
  const body = {
    message: `app: record application ${it.id}`,
    content: btoa(unescape(encodeURIComponent(JSON.stringify(current, null, 2)))),
  };
  if (sha) body.sha = sha;
  const p = await fetch(api, { method: "PUT", headers, body: JSON.stringify(body) });
  if (p.ok) toast("GitHubにも記録しました");
  else toast(`GitHub記録に失敗（${p.status}）。時間をおいて再試行を`);
}

/* ---------- コメント肉付け ---------- */
function openCommentModal(it) {
  curItem = it;
  $("#cmTitle").textContent = it.title || "";
  $("#cmOpinion").value = "";
  $("#cmEngine").textContent = "";
  $("#cmResults").innerHTML = "";
  // 同梱の候補を初期表示
  if (it.comment_suggestions?.length) renderComments(it.comment_suggestions, "同梱テンプレート");
  $("#commentModal").classList.remove("hidden");
}

function renderComments(comments, engineLabel) {
  $("#cmEngine").textContent = engineLabel ? `生成: ${engineLabel}` : "";
  const box = $("#cmResults");
  box.innerHTML = "";
  comments.forEach((txt) => {
    const r = el("div", "result");
    r.innerHTML = `<div>${escapeHtml(txt)}</div>`;
    const b = el("button", "copy");
    b.textContent = "コピー";
    b.onclick = async () => { await copyText(txt); toast("コピーしました"); };
    r.appendChild(b);
    box.appendChild(r);
  });
}

async function generateComment() {
  const opinion = $("#cmOpinion").value.trim();
  const it = curItem;
  const key = CFG.gemini();
  if (!key) {
    // キー無し：ルールベース（感想を冒頭に添える）
    let base = it.comment_suggestions || [];
    if (opinion) base = base.map((b) => `${opinion}。${b}`);
    renderComments(base, "ルールベース（Geminiキー未設定）");
    return;
  }
  if (!opinion) { toast("感想・意見を入力してください"); return; }
  $("#cmGenerate").disabled = true;
  $("#cmEngine").textContent = "生成中…";
  try {
    const prompt = buildPrompt(it, opinion, 2);
    const model = CFG.model() || "gemini-2.5-flash-lite";
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-goog-api-key": key },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { temperature: 0.7, responseMimeType: "application/json" },
      }),
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    const text = data.candidates[0].content.parts[0].text;
    const parsed = JSON.parse(text);
    const comments = (parsed.comments || []).filter((x) => x && x.trim());
    if (!comments.length) throw new Error("空の応答");
    renderComments(comments, "Gemini");
  } catch (e) {
    let base = it.comment_suggestions || [];
    if (opinion) base = base.map((b) => `${opinion}。${b}`);
    renderComments(base, "ルールベース（LLM失敗）");
    toast("Gemini呼び出しに失敗→ルールベースで生成");
  } finally {
    $("#cmGenerate").disabled = false;
  }
}

function buildPrompt(it, opinion, n) {
  return `あなたは日本の懸賞応募コメントの作成を手伝うアシスタントです。
応募者が書いた「短い感想・意見」を、当選しやすい丁寧な応募コメントに肉付けしてください。

厳守ルール:
- 応募者が書いていない事実（家族構成・居住地・体験など）を勝手に創作しない。書かれた範囲だけを自然に整える。
- 「①その賞品への関心・応募理由」＋「②当選後の具体的な使い道」を2〜3文で。
- 定型句だけ（「当たりますように」等）にしない。誇張・過剰な媚びは避け、誠実で具体的に。
- 丁寧語。1案あたり120〜200字程度。
- 出力はJSONのみ。{"comments":["案1","案2"]} の形式。

懸賞情報:
- タイトル: ${it.title || ""}
- ジャンル: ${it.genre || "その他"}
- 応募方式: ${it.method || "不明"}

応募者の短い感想・意見:
${opinion}

案を${n}個、JSONで:`;
}

async function copyText(t) {
  try { await navigator.clipboard.writeText(t); }
  catch (e) {
    const ta = document.createElement("textarea");
    ta.value = t; document.body.appendChild(ta); ta.select();
    document.execCommand("copy"); ta.remove();
  }
}

/* ---------- 設定 ---------- */
function openSettings() {
  $("#setFeedUrl").value = LS.get("feedUrl", "");
  $("#setGemini").value = CFG.gemini();
  $("#setModel").value = CFG.model();
  $("#setRepo").value = CFG.repo();
  $("#setToken").value = CFG.token();
  $("#settingsModal").classList.remove("hidden");
}
function saveSettings() {
  LS.set("feedUrl", $("#setFeedUrl").value.trim() || "app_feed.json");
  LS.set("geminiKey", $("#setGemini").value.trim());
  LS.set("geminiModel", $("#setModel").value.trim() || "gemini-2.5-flash-lite");
  LS.set("ghRepo", $("#setRepo").value.trim());
  LS.set("ghToken", $("#setToken").value.trim());
  $("#settingsModal").classList.add("hidden");
  toast("設定を保存しました");
  loadFeed();
}
function clearSettings() {
  ["feedUrl", "geminiKey", "geminiModel", "ghRepo", "ghToken"].forEach(LS.del);
  toast("保存データを消去しました");
  openSettings();
}

/* ---------- ユーティリティ ---------- */
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (m) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
}

/* ---------- イベント配線 ---------- */