"use strict";

const tg = window.Telegram?.WebApp;
const API_BASE = window.ARB_API_BASE || "https://144-31-63-38.sslip.io";
const state = { trades: [], current: null, editingId: null, screen: "home" };
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

if (tg) {
  tg.ready();
  tg.expand();
  tg.setHeaderColor?.("#080b12");
  tg.setBackgroundColor?.("#080b12");
}

function requestHeaders(json = false) {
  const result = { Accept: "application/json" };
  if (json) result["Content-Type"] = "application/json";
  if (tg?.initData) result["X-Telegram-Init-Data"] = tg.initData;
  const userId = tg?.initDataUnsafe?.user?.id;
  if (userId) result["X-Telegram-User-Id"] = String(userId);
  return result;
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    ...options,
    headers: { ...requestHeaders(Boolean(options.body) && !(options.body instanceof FormData)), ...(options.headers || {}) },
  });
  const type = response.headers.get("content-type") || "";
  const payload = type.includes("application/json") ? await response.json().catch(() => null) : response;
  if (!response.ok) {
    const detail = payload?.detail;
    const message = Array.isArray(detail) ? detail.map(item => item.msg).join("; ") : detail;
    throw new Error(message || `Ошибка API ${response.status}`);
  }
  return payload;
}

const num = value => Number(value || 0);
const money = value => new Intl.NumberFormat("ru-RU", { style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(num(value));
const percent = value => `${num(value).toFixed(2)}%`;
const esc = value => String(value ?? "").replace(/[&<>'"]/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
const tradeTime = trade => trade.sold_at || trade.created_at || trade.bought_at;
const dateText = value => value ? new Intl.DateTimeFormat("ru-RU", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—";
const isCompleted = trade => String(trade.status).toUpperCase() === "COMPLETED";

function toast(message, error = false) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.toggle("error", error);
  el.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { el.hidden = true; }, 2800);
}

function haptic(kind = "light") { tg?.HapticFeedback?.impactOccurred?.(kind); }

function setApiState(ok, text = ok ? "онлайн" : "ошибка") {
  const badge = $("#api-badge");
  badge.textContent = text;
  badge.classList.toggle("ok", ok);
  $("#api-status").textContent = text;
  $("#api-status").className = ok ? "positive" : "negative";
}

function showScreen(name) {
  state.screen = name;
  $$(".screen").forEach(el => el.classList.toggle("active", el.dataset.screen === name));
  $$("nav [data-go]").forEach(el => el.classList.toggle("active", el.dataset.go === name));
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (name === "analytics") loadAnalytics();
  if (name === "settings") loadSettings();
}

function tradeCard(trade) {
  const profit = num(trade.profit);
  return `<button class="trade-card" data-trade="${Number(trade.id)}">
    <div><strong>${esc(trade.coin)}</strong><small>${esc(trade.buy_exchange)} → ${esc(trade.sell_exchange)}</small>
      <div class="tags"><span class="tag">${esc(trade.status)}</span><span class="tag">${esc(trade.trade_type)}</span><span class="tag">${esc(dateText(tradeTime(trade)))}</span></div>
    </div>
    <div class="result ${profit >= 0 ? "positive" : "negative"}">${money(profit)}<small>ROI ${percent(trade.roi)}</small></div>
  </button>`;
}

function bindTradeCards(root) {
  $$('[data-trade]', root).forEach(el => el.addEventListener("click", () => openTrade(Number(el.dataset.trade))));
}

function renderDashboard() {
  const completed = state.trades.filter(isCompleted);
  const total = completed.reduce((sum, item) => sum + num(item.profit), 0);
  const averageRoi = completed.length ? completed.reduce((sum, item) => sum + num(item.roi), 0) / completed.length : 0;
  const profitable = completed.filter(item => num(item.profit) > 0).length;
  const now = new Date();
  const todayProfit = completed.filter(item => {
    const date = new Date(tradeTime(item));
    return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth() && date.getDate() === now.getDate();
  }).reduce((sum, item) => sum + num(item.profit), 0);
  $("#home-profit").textContent = money(total);
  $("#home-profit").className = total >= 0 ? "positive" : "negative";
  $("#home-roi").textContent = percent(averageRoi);
  $("#home-count").textContent = `${completed.length} сделок`;
  $("#home-today").textContent = money(todayProfit);
  $("#home-winrate").textContent = percent(completed.length ? profitable / completed.length * 100 : 0);
  const recent = [...state.trades].sort((a, b) => new Date(tradeTime(b)) - new Date(tradeTime(a))).slice(0, 5);
  const list = $("#recent-list");
  list.innerHTML = recent.length ? recent.map(tradeCard).join("") : '<div class="empty">Сделок пока нет</div>';
  bindTradeCards(list);
}

function renderTrades() {
  const query = $("#search").value.trim().toLowerCase();
  const status = $("#filter-status").value;
  const type = $("#filter-type").value;
  const sort = $("#sort").value;
  const filtered = state.trades.filter(trade => {
    const haystack = [trade.coin, trade.buy_exchange, trade.sell_exchange, trade.strategy, trade.note].join(" ").toLowerCase();
    return (!status || trade.status === status) && (!type || trade.trade_type === type) && (!query || haystack.includes(query));
  });
  filtered.sort((a, b) => {
    if (sort === "profit-desc") return num(b.profit) - num(a.profit);
    if (sort === "profit-asc") return num(a.profit) - num(b.profit);
    if (sort === "roi-desc") return num(b.roi) - num(a.roi);
    return sort === "date-asc" ? new Date(tradeTime(a)) - new Date(tradeTime(b)) : new Date(tradeTime(b)) - new Date(tradeTime(a));
  });
  $("#trade-count-label").textContent = `${filtered.length} записей`;
  const list = $("#trade-list");
  list.innerHTML = filtered.length ? filtered.map(tradeCard).join("") : '<div class="empty">Ничего не найдено</div>';
  bindTradeCards(list);
}

async function loadTrades() {
  $("#trade-list").innerHTML = '<div class="loading">Загрузка…</div>';
  try {
    state.trades = await request("/trades/");
    setApiState(true);
    renderDashboard();
    renderTrades();
  } catch (error) {
    setApiState(false);
    $("#trade-list").innerHTML = `<div class="empty">${esc(error.message)}</div>`;
    toast(error.message, true);
  }
}

function detail(label, value) { return `<div><span>${esc(label)}</span><b>${esc(value ?? "—")}</b></div>`; }

function openModal(id) {
  $("#backdrop").hidden = false;
  $(id).hidden = false;
  document.body.classList.add("modal-open");
}

function closeModals() {
  $("#backdrop").hidden = true;
  $$(".sheet").forEach(el => { el.hidden = true; });
  document.body.classList.remove("modal-open");
  state.current = null;
}

async function openTrade(id) {
  haptic();
  try {
    const trade = await request(`/trades/${id}`);
    state.current = trade;
    $("#detail-title").textContent = `${trade.coin} #${trade.id}`;
    const profit = num(trade.profit);
    $("#detail-body").innerHTML = `<div class="detail-profit ${profit >= 0 ? "positive" : "negative"}">${money(profit)}</div>
      <div class="tags"><span class="tag">ROI ${percent(trade.roi)}</span><span class="tag">${esc(trade.status)}</span><span class="tag">${esc(trade.trade_type)}</span></div>
      <div class="detail-actions">${trade.status === "PENDING" ? '<button id="complete-trade">✓ Завершить</button>' : ""}<button id="edit-trade">✎ Изменить</button><button id="delete-trade" class="danger">Удалить</button></div>
      <div class="detail-grid">${detail("Монета", trade.coin)}${detail("Объём", trade.amount)}${detail("Покупка", `${trade.buy_exchange} · ${trade.buy_price}`)}${detail("Продажа", `${trade.sell_exchange} · ${trade.sell_price}`)}${detail("Комиссия покупки", trade.buy_fee)}${detail("Комиссия продажи", trade.sell_fee)}${detail("Сеть", `${trade.transfer_network || "—"} · ${trade.network_fee || 0}`)}${detail("Проскальзывание", trade.slippage)}${detail("Куплено", dateText(trade.bought_at))}${detail("Продано", dateText(trade.sold_at))}${detail("Стратегия", trade.strategy)}${detail("Заметка", trade.note)}</div>`;
    openModal("#trade-detail");
    $("#edit-trade")?.addEventListener("click", () => openEditor(trade));
    $("#delete-trade")?.addEventListener("click", deleteCurrentTrade);
    $("#complete-trade")?.addEventListener("click", completeCurrentTrade);
  } catch (error) { toast(error.message, true); }
}

function toLocalDatetime(value) {
  if (!value) return "";
  const date = new Date(value);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function openEditor(trade = null) {
  closeModals();
  state.editingId = trade?.id || null;
  const form = $("#trade-form");
  form.reset();
  $("#editor-kicker").textContent = trade ? "РЕДАКТИРОВАНИЕ" : "НОВАЯ СДЕЛКА";
  $("#editor-title").textContent = trade ? `${trade.coin} #${trade.id}` : "Добавить сделку";
  $("#form-error").hidden = true;
  const values = trade || { status: "COMPLETED", trade_type: "CEX_CEX", buy_fee_percent: 0, sell_fee_percent: 0, network_fee: 0, slippage: 0 };
  for (const field of form.elements) {
    if (!field.name) continue;
    let value = values[field.name];
    if (["bought_at", "sold_at"].includes(field.name)) value = toLocalDatetime(value);
    if (value != null) field.value = value;
  }
  openModal("#trade-editor");
}

function formPayload(form) {
  const data = Object.fromEntries(new FormData(form));
  const iso = value => value ? new Date(value).toISOString() : null;
  return {
    coin: data.coin.trim().toUpperCase(), buy_exchange: data.buy_exchange.trim(), sell_exchange: data.sell_exchange.trim(),
    amount: data.amount, buy_price: data.buy_price, sell_price: data.sell_price,
    buy_fee_percent: data.buy_fee_percent || "0", sell_fee_percent: data.sell_fee_percent || "0", network_fee: data.network_fee || "0", slippage: data.slippage || "0",
    transfer_network: data.transfer_network.trim() || null, bought_at: iso(data.bought_at), sold_at: iso(data.sold_at),
    trade_type: data.trade_type, status: data.status, strategy: data.strategy.trim() || null, note: data.note.trim() || null,
  };
}

async function saveTrade(event) {
  event.preventDefault();
  const button = $("#save-trade");
  const errorBox = $("#form-error");
  button.disabled = true; button.textContent = "Сохранение…"; errorBox.hidden = true;
  try {
    const payload = formPayload(event.currentTarget);
    if (num(payload.amount) <= 0 || num(payload.buy_price) <= 0 || num(payload.sell_price) <= 0) throw new Error("Объём и цены должны быть больше нуля");
    const path = state.editingId ? `/trades/${state.editingId}` : "/trades/";
    await request(path, { method: state.editingId ? "PATCH" : "POST", body: JSON.stringify(payload) });
    tg?.HapticFeedback?.notificationOccurred?.("success");
    closeModals(); await loadTrades(); showScreen("trades"); toast(state.editingId ? "Сделка обновлена" : "Сделка добавлена");
  } catch (error) {
    errorBox.textContent = error.message; errorBox.hidden = false; tg?.HapticFeedback?.notificationOccurred?.("error");
  } finally { button.disabled = false; button.textContent = "Сохранить"; }
}

async function completeCurrentTrade() {
  try { await request(`/trades/${state.current.id}/complete`, { method: "POST" }); closeModals(); await loadTrades(); toast("Сделка завершена"); } catch (error) { toast(error.message, true); }
}

async function deleteCurrentTrade() {
  const id = state.current?.id;
  const execute = async () => {
    try { await request(`/trades/${id}`, { method: "DELETE" }); closeModals(); await loadTrades(); toast("Сделка удалена"); } catch (error) { toast(error.message, true); }
  };
  if (tg?.showConfirm) tg.showConfirm("Удалить эту сделку?", ok => { if (ok) execute(); });
  else if (window.confirm("Удалить эту сделку?")) await execute();
}

function ranking(container, data) {
  const entries = Object.entries(data || {}).sort((a, b) => num(b[1].profit) - num(a[1].profit));
  $(container).innerHTML = entries.length ? entries.map(([name, value]) => `<p><span>${esc(name)} · ${value.trades}</span><b class="${num(value.profit) >= 0 ? "positive" : "negative"}">${money(value.profit)}</b></p>`).join("") : '<div class="empty">Нет данных</div>';
}

function renderEquity(points) {
  const container = $("#equity-chart");
  if (!points.length) { container.innerHTML = '<div class="empty">Нет данных</div>'; $("#equity-total").textContent = money(0); return; }
  const values = points.map(item => num(item.equity));
  const min = Math.min(0, ...values), max = Math.max(0, ...values), span = max - min || 1;
  const coords = values.map((value, index) => `${(index / Math.max(1, values.length - 1) * 100).toFixed(2)},${(100 - (value - min) / span * 88 - 6).toFixed(2)}`).join(" ");
  container.innerHTML = `<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="Кривая доходности"><defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#63a9ff" stop-opacity=".35"/><stop offset="1" stop-color="#63a9ff" stop-opacity="0"/></linearGradient></defs><polygon points="0,100 ${coords} 100,100" fill="url(#fill)"/><polyline points="${coords}" fill="none" stroke="#63a9ff" stroke-width="2" vector-effect="non-scaling-stroke"/></svg>`;
  $("#equity-total").textContent = money(values.at(-1));
}

async function loadAnalytics() {
  try {
    const [stats, equity, coins, exchanges, strategies] = await Promise.all([
      request("/statistics/"), request("/statistics/equity/"), request("/statistics/coins/"), request("/statistics/exchanges/"), request("/statistics/strategies/"),
    ]);
    $("#stat-profit").textContent = money(stats.total_profit); $("#stat-roi").textContent = percent(stats.average_roi);
    $("#stat-winrate").textContent = percent(stats.win_rate); $("#stat-count").textContent = stats.completed_trades;
    renderEquity(equity); ranking("#coin-ranking", coins); ranking("#exchange-ranking", exchanges); ranking("#strategy-ranking", strategies);
  } catch (error) { toast(error.message, true); }
}

function download(path, filename) {
  fetch(`${API_BASE}${path}`, { headers: requestHeaders() }).then(async response => {
    if (!response.ok) throw new Error(`Ошибка API ${response.status}`);
    const blob = await response.blob(); const url = URL.createObjectURL(blob); const link = document.createElement("a");
    link.href = url; link.download = filename; document.body.append(link); link.click(); link.remove(); URL.revokeObjectURL(url);
  }).catch(error => toast(error.message, true));
}

async function importBackup(file) {
  const form = new FormData(); form.append("file", file);
  try {
    const result = await request("/import", { method: "POST", body: form, headers: requestHeaders(false) });
    await loadTrades(); toast(`Импортировано: ${result.inserted}, пропущено: ${result.skipped}`);
  } catch (error) { toast(error.message, true); }
}

function loadSettings() {
  const user = tg?.initDataUnsafe?.user;
  if (!user) return;
  const name = [user.first_name, user.last_name].filter(Boolean).join(" ");
  $("#user-name").textContent = name || "Telegram user"; $("#user-username").textContent = user.username ? `@${user.username}` : "Без username";
  $("#user-id").textContent = `ID: ${user.id}`; $("#avatar").textContent = (user.first_name?.[0] || user.username?.[0] || "?").toUpperCase();
}

async function checkApi() { try { await request("/health"); setApiState(true); toast("API работает"); } catch (error) { setApiState(false); toast(error.message, true); } }

function bindEvents() {
  $$('[data-go]').forEach(el => el.addEventListener("click", () => showScreen(el.dataset.go)));
  $$('[data-add]').forEach(el => el.addEventListener("click", () => openEditor()));
  $$('[data-close]').forEach(el => el.addEventListener("click", closeModals));
  $("#backdrop").addEventListener("click", closeModals); $("#trade-form").addEventListener("submit", saveTrade);
  ["#search", "#filter-status", "#filter-type", "#sort"].forEach(selector => $(selector).addEventListener("input", renderTrades));
  $("#refresh-trades").addEventListener("click", loadTrades); $("#refresh-analytics").addEventListener("click", loadAnalytics); $("#check-api").addEventListener("click", checkApi);
  $("#export-excel").addEventListener("click", () => download("/export/excel", "trades.xlsx"));
  $("#export-backup").addEventListener("click", () => download("/backup", "trades_backup.json"));
  $("#import-backup").addEventListener("click", () => $("#import-file").click());
  $("#import-file").addEventListener("change", event => { const file = event.target.files?.[0]; if (file) importBackup(file); event.target.value = ""; });
  document.addEventListener("keydown", event => { if (event.key === "Escape") closeModals(); });
}

document.addEventListener("DOMContentLoaded", async () => { bindEvents(); loadSettings(); await Promise.all([loadTrades(), checkApi()]); });
