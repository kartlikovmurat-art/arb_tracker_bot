
const tg = window.Telegram?.WebApp;
const API_BASE = "/api";

let allTrades = [];
let editingTradeId = null;
let currentTrade = null;
let filters = {
    status: "",
    trade_type: "",
    coin: "",
    exchange: ""
};

if (tg) {
    tg.ready();
    tg.expand();
    tg.setHeaderColor("#080b0a");
    tg.setBackgroundColor("#080b0a");
}

function headers() {
    const userId = tg?.initDataUnsafe?.user?.id;

    return userId
        ? { "X-Telegram-User-Id": String(userId) }
        : {};
}

async function apiGet(path) {
    const response = await fetch(`${API_BASE}${path}`, {
        headers: headers(),
        cache: "no-store"
    });

    if (!response.ok) {
        throw new Error(`API ${response.status}`);
    }

    return response.json();
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function money(value) {
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(Number(value || 0));
}

function percent(value) {
    return `${Number(value || 0).toFixed(2)}%`;
}

function tradeDate(trade) {
    return trade.created_at || trade.sold_at || trade.bought_at || null;
}

function dateText(value) {
    if (!value) {
        return "—";
    }

    return new Intl.DateTimeFormat("ru-RU", {
        dateStyle: "medium",
        timeStyle: "short"
    }).format(new Date(value));
}

function isCompleted(trade) {
    return String(trade.status || "").toUpperCase() === "COMPLETED";
}

function statusClass(status) {
    const value = String(status || "").toLowerCase();

    if (value === "completed") return "completed";
    if (value === "pending") return "pending";
    if (value === "cancelled") return "cancelled";

    return "";
}

function renderDashboard(trades) {
    const completed = trades.filter(isCompleted);

    const totalProfit = completed.reduce(
        (sum, trade) => sum + Number(trade.profit || 0),
        0
    );

    const averageRoi = completed.length
        ? completed.reduce(
            (sum, trade) => sum + Number(trade.roi || 0),
            0
        ) / completed.length
        : 0;

    const today = new Date();

    const todayProfit = completed
        .filter(trade => {
            const value = tradeDate(trade);

            if (!value) {
                return false;
            }

            const date = new Date(value);

            return (
                date.getFullYear() === today.getFullYear() &&
                date.getMonth() === today.getMonth() &&
                date.getDate() === today.getDate()
            );
        })
        .reduce(
            (sum, trade) => sum + Number(trade.profit || 0),
            0
        );

    const totalProfitElement =
        document.getElementById("total-profit");

    const totalRoiElement =
        document.getElementById("total-roi");

    const countElement =
        document.getElementById("trade-count");

    const todayElement =
        document.getElementById("today-profit");

    if (totalProfitElement) {
        totalProfitElement.textContent = money(totalProfit);
    }

    if (totalRoiElement) {
        totalRoiElement.textContent = percent(averageRoi);
    }

    if (countElement) {
        countElement.textContent = String(completed.length);
    }

    if (todayElement) {
        todayElement.textContent = money(todayProfit);
    }

    const recent = [...completed]
        .sort(
            (a, b) =>
                new Date(tradeDate(b) || 0) -
                new Date(tradeDate(a) || 0)
        )
        .slice(0, 5);

    const container =
        document.getElementById("trades-list");

    if (!container) {
        return;
    }

    container.innerHTML = recent.length
        ? recent.map(buildTradeCard).join("")
        : `
            <div class="empty-state">
                <div class="empty-icon">◇</div>
                <div>Завершённых сделок пока нет</div>
            </div>
        `;

    bindTradeCards(container);
}

function buildTradeCard(trade) {
    const profit = Number(trade.profit || 0);

    return `
        <button
            class="trade-card"
            data-trade-id="${Number(trade.id)}"
        >
            <div class="trade-main">

                <div class="trade-coin">
                    ${escapeHtml(trade.coin || "—")}
                </div>

                <div class="trade-route">
                    ${escapeHtml(trade.buy_exchange || "—")}
                    →
                    ${escapeHtml(trade.sell_exchange || "—")}
                </div>

                <div class="trade-extra">

                    <span class="tag ${statusClass(trade.status)}">
                        ${escapeHtml(trade.status || "—")}
                    </span>

                    <span class="tag">
                        ${escapeHtml(trade.trade_type || "—")}
                    </span>

                    <span class="tag">
                        ${dateText(tradeDate(trade))}
                    </span>

                </div>

            </div>

            <div class="trade-result ${
                profit >= 0
                    ? "profit-positive"
                    : "profit-negative"
            }">

                ${money(profit)}

                <small>
                    ROI ${percent(trade.roi)}
                </small>

            </div>

        </button>
    `;
}

function bindTradeCards(container) {
    container
        .querySelectorAll("[data-trade-id]")
        .forEach(element => {

            element.addEventListener("click", () => {
                openTrade(
                    Number(element.dataset.tradeId)
                );
            });

        });
}

function populateFilters() {
    const coins = [
        ...new Set(
            allTrades
                .map(trade => trade.coin)
                .filter(Boolean)
        )
    ].sort();

    const exchanges = [
        ...new Set(
            allTrades.flatMap(trade => [
                trade.buy_exchange,
                trade.sell_exchange
            ]).filter(Boolean)
        )
    ].sort();

    const coinSelect =
        document.getElementById("filter-coin");

    const exchangeSelect =
        document.getElementById("filter-exchange");

    if (coinSelect) {
        coinSelect.innerHTML =
            `<option value="">Все монеты</option>` +
            coins.map(
                coin =>
                    `<option value="${escapeHtml(coin)}">${escapeHtml(coin)}</option>`
            ).join("");
    }

    if (exchangeSelect) {
        exchangeSelect.innerHTML =
            `<option value="">Все биржи</option>` +
            exchanges.map(
                exchange =>
                    `<option value="${escapeHtml(exchange)}">${escapeHtml(exchange)}</option>`
            ).join("");
    }
}

function renderTradeList() {
    const search =
        document.getElementById("trade-search")
            ?.value
            .trim()
            .toLowerCase() || "";

    const sort =
        document.getElementById("filter-sort")
            ?.value || "date-desc";

    let trades = allTrades.filter(trade => {

        const searchText = [
            trade.coin,
            trade.buy_exchange,
            trade.sell_exchange,
            trade.strategy,
            trade.note,
            trade.trade_type,
            trade.status
        ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();

        return (
            (!filters.status ||
                String(trade.status).toUpperCase() === filters.status) &&

            (!filters.trade_type ||
                String(trade.trade_type).toUpperCase() === filters.trade_type) &&

            (!filters.coin ||
                trade.coin === filters.coin) &&

            (!filters.exchange ||
                trade.buy_exchange === filters.exchange ||
                trade.sell_exchange === filters.exchange) &&

            (!search ||
                searchText.includes(search))
        );
    });

    trades.sort((a, b) => {

        if (sort === "profit-desc") {
            return Number(b.profit || 0) -
                Number(a.profit || 0);
        }

        if (sort === "profit-asc") {
            return Number(a.profit || 0) -
                Number(b.profit || 0);
        }

        if (sort === "roi-desc") {
            return Number(b.roi || 0) -
                Number(a.roi || 0);
        }

        const dateA =
            new Date(tradeDate(a) || 0).getTime();

        const dateB =
            new Date(tradeDate(b) || 0).getTime();

        return sort === "date-asc"
            ? dateA - dateB
            : dateB - dateA;
    });

    const list =
        document.getElementById("full-trades-list");

    const count =
        document.getElementById("trades-count-label");

    const summary =
        document.getElementById("filter-summary");

    if (!list) {
        return;
    }

    if (count) {
        count.textContent =
            `${trades.length} ${
                trades.length === 1
                    ? "запись"
                    : "записей"
            }`;
    }

    if (summary) {
        summary.textContent =
            trades.length === allTrades.length
                ? "Все сделки"
                : `Показано ${trades.length} из ${allTrades.length}`;
    }

    list.innerHTML = trades.length
        ? trades.map(buildTradeCard).join("")
        : `
            <div class="empty-state">
                <div class="empty-icon">◇</div>
                <div>По заданным фильтрам сделок нет</div>
            </div>
        `;

    bindTradeCards(list);
}

async function loadTrades() {

    const list =
        document.getElementById("full-trades-list");

    if (list) {
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">◇</div>
                <div>Загрузка сделок...</div>
            </div>
        `;
    }

    try {

        allTrades =
            await apiGet("/trades/");

        renderDashboard(allTrades);
        populateFilters();
        renderTradeList();

    } catch (error) {

        console.error(error);

        if (list) {
            list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">⚠</div>
                    <div>Не удалось загрузить сделки</div>
                </div>
            `;
        }
    }
}

async function openTrade(id) {

    tg?.HapticFeedback?.impactOccurred?.("light");

    try {

        const trade =
            await apiGet(`/trades/${id}`);

        currentTrade = trade;

        const profit =
            Number(trade.profit || 0);

        const title =
            document.getElementById("modal-title");

        const body =
            document.getElementById("modal-body");

        if (title) {
            title.textContent =
                `${trade.coin || "Сделка"} #${trade.id}`;
        }

        if (body) {

            body.innerHTML = `

                <div class="detail-hero">

                    <div>

                        <div class="detail-profit ${
                            profit >= 0
                                ? "profit-positive"
                                : "profit-negative"
                        }">
                            ${money(profit)}
                        </div>

                        <div class="detail-roi">
                            ROI ${percent(trade.roi)}
                            · ${escapeHtml(trade.status || "—")}
                        </div>

                    </div>

                    <span class="tag ${statusClass(trade.status)}">
                        ${escapeHtml(trade.trade_type || "—")}
                    </span>

                </div>

                <div class="detail-actions">

                    <button
                        type="button"
                        class="detail-action"
                        id="edit-current-trade"
                    >
                        ✎ РЕДАКТИРОВАТЬ
                    </button>

                    <button
                        type="button"
                        class="detail-action danger"
                        id="delete-current-trade"
                    >
                        УДАЛИТЬ
                    </button>

                </div>

                <div class="detail-grid">

                    ${detail("Монета", trade.coin)}
                    ${detail("Объём", trade.amount)}

                    ${detail(
                        "Покупка",
                        `${trade.buy_exchange || "—"} · ${trade.buy_price || "—"}`
                    )}

                    ${detail(
                        "Продажа",
                        `${trade.sell_exchange || "—"} · ${trade.sell_price || "—"}`
                    )}

                    ${detail("Buy fee", trade.buy_fee)}
                    ${detail("Sell fee", trade.sell_fee)}
                    ${detail("Withdrawal", trade.withdrawal_fee)}
                    ${detail("Gas", trade.gas_fee)}
                    ${detail("Slippage", trade.slippage)}
                    ${detail("Сеть", trade.transfer_network)}

                    ${detail("Куплено", dateText(trade.bought_at))}
                    ${detail("Продано", dateText(trade.sold_at))}

                    ${detail("Стратегия", trade.strategy)}
                    ${detail("Примечание", trade.note)}

                </div>
            `;
        }

        const backdrop =
            document.getElementById(
                "trade-modal-backdrop"
            );

        const modal =
            document.getElementById(
                "trade-modal"
            );

        if (backdrop) {
            backdrop.hidden = false;
            backdrop.style.display = "block";
            backdrop.style.pointerEvents = "auto";
        }

        if (modal) {
            modal.hidden = false;
            modal.style.display = "block";
            modal.style.pointerEvents = "auto";
        }

    } catch (error) {

        console.error(error);

        tg?.showAlert?.(
            "Не удалось загрузить сделку."
        );
    }
}

function detail(label, value) {

    return `
        <div class="detail-cell">

            <div class="detail-label">
                ${escapeHtml(label)}
            </div>

            <div class="detail-value">
                ${escapeHtml(value || "—")}
            </div>

        </div>
    `;
}



function closeTrade() {
    const modal = document.getElementById("trade-modal");
    const backdrop = document.getElementById("trade-modal-backdrop");

    if (modal) {
        modal.hidden = true;
        modal.style.display = "none";
    }

    if (backdrop) {
        backdrop.hidden = true;
        backdrop.style.display = "none";
    }

    currentTrade = null;
}

function openAddTrade(trade = null) {
    tg?.HapticFeedback?.impactOccurred?.("light");

    editingTradeId = trade ? Number(trade.id) : null;

    const modal = document.getElementById("add-trade-modal");
    const backdrop = document.getElementById("add-trade-backdrop");
    const form = document.getElementById("trade-form");

    if (!modal || !backdrop || !form) {
        return;
    }

    form.reset();

    form.querySelector('[name="status"]').value =
        trade?.status || "COMPLETED";

    if (trade) {
        const values = {
            coin: trade.coin,
            amount: trade.amount,
            buy_exchange: trade.buy_exchange,
            sell_exchange: trade.sell_exchange,
            buy_price: trade.buy_price,
            sell_price: trade.sell_price,
            buy_fee_percent: trade.buy_fee_percent,
            sell_fee_percent: trade.sell_fee_percent,
            network_fee: trade.network_fee,
            transfer_network: trade.transfer_network,
            trade_type: trade.trade_type,
            status: trade.status,
            strategy: trade.strategy,
            note: trade.note,
        };

        for (const [name, value] of Object.entries(values)) {
            const field = form.querySelector(`[name="${name}"]`);

            if (field && value != null) {
                field.value = value;
            }
        }

        const bought = form.querySelector('[name="bought_at"]');
        const sold = form.querySelector('[name="sold_at"]');

        if (bought && trade.bought_at) {
            bought.value = new Date(trade.bought_at)
                .toISOString()
                .slice(0, 16);
        }

        if (sold && trade.sold_at) {
            sold.value = new Date(trade.sold_at)
                .toISOString()
                .slice(0, 16);
        }
    }

    const title = modal.querySelector(".modal-title");

    if (title) {
        title.textContent =
            trade
                ? `Редактировать #${trade.id}`
                : "Добавить сделку";
    }

    const submit = document.getElementById("trade-form-submit");

    if (submit) {
        submit.textContent =
            trade
                ? "СОХРАНИТЬ ИЗМЕНЕНИЯ"
                : "СОХРАНИТЬ СДЕЛКУ";
    }

    modal.hidden = false;
    backdrop.hidden = false;
}

function closeAddTrade() {
    const modal = document.getElementById("add-trade-modal");
    const backdrop = document.getElementById("add-trade-backdrop");

    if (modal && backdrop) {
        modal.hidden = true;
        backdrop.hidden = true;
    }
}

function localDatetimeToIso(value) {
    if (!value) {
        return null;
    }

    const date = new Date(value);

    return Number.isNaN(date.getTime())
        ? null
        : date.toISOString();
}

async function createTrade(payload) {
    const response = await fetch(`${API_BASE}/trades/`, {
        method: "POST",
        headers: {
            ...headers(),
            "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
        throw new Error(
            data?.detail || `API ${response.status}`
        );
    }

    return data;
}


async function updateTrade(id, payload) {
    const response = await fetch(
        `${API_BASE}/trades/${id}`,
        {
            method: "PATCH",
            headers: {
                ...headers(),
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
        }
    );

    const data = await response.json().catch(() => null);

    if (!response.ok) {
        throw new Error(
            data?.detail || `API ${response.status}`
        );
    }

    return data;
}

async function deleteTrade(id) {
    const response = await fetch(
        `${API_BASE}/trades/${id}`,
        {
            method: "DELETE",
            headers: headers(),
        }
    );

    const data = await response.json().catch(() => null);

    if (!response.ok) {
        throw new Error(
            data?.detail || `API ${response.status}`
        );
    }

    return data;
}


function buildTradePayload(form) {
    const data = Object.fromEntries(new FormData(form).entries());

    return {
        coin: data.coin.trim().toUpperCase(),
        buy_exchange: data.buy_exchange.trim(),
        sell_exchange: data.sell_exchange.trim(),

        amount: data.amount,
        buy_price: data.buy_price,
        sell_price: data.sell_price,

        buy_fee_percent: data.buy_fee_percent || "0",
        sell_fee_percent: data.sell_fee_percent || "0",
        network_fee: data.network_fee || "0",

        transfer_network:
            data.transfer_network?.trim() || null,

        bought_at:
            localDatetimeToIso(data.bought_at),

        sold_at:
            localDatetimeToIso(data.sold_at),

        trade_type:
            data.trade_type || "CEX_CEX",

        status:
            data.status || "COMPLETED",

        strategy:
            data.strategy?.trim() || null,

        note:
            data.note?.trim() || null,
    };
}

async function submitTradeForm(event) {
    event.preventDefault();

    const form = event.currentTarget;
    const button = document.getElementById("trade-form-submit");
    const error = document.getElementById("trade-form-error");

    if (error) {
        error.hidden = true;
        error.textContent = "";
    }

    if (button) {
        button.disabled = true;
        button.textContent =
            editingTradeId
                ? "СОХРАНЕНИЕ..."
                : "СОХРАНЕНИЕ...";
    }

    try {
        const payload = buildTradePayload(form);

        if (
            Number(payload.amount) <= 0 ||
            Number(payload.buy_price) <= 0 ||
            Number(payload.sell_price) <= 0
        ) {
            throw new Error(
                "Объём и цены должны быть больше нуля."
            );
        }

        if (editingTradeId) {
            await updateTrade(editingTradeId, payload);
        } else {
            await createTrade(payload);
        }

        tg?.HapticFeedback?.notificationOccurred?.("success");

        closeAddTrade();

        editingTradeId = null;

        allTrades = await apiGet("/trades/");
        renderDashboard(allTrades);
        populateFilters();

        if (
            document
                .getElementById("view-trades")
                ?.classList.contains("active")
        ) {
            renderTradeList();
        }

        showView("trades");

    } catch (err) {
        console.error(
            "Trade save failed:",
            err
        );

        if (error) {
            error.textContent =
                err?.message ||
                "Не удалось сохранить сделку.";

            error.hidden = false;
        }

        tg?.HapticFeedback?.notificationOccurred?.("error");

    } finally {
        if (button) {
            button.disabled = false;
            button.textContent =
                editingTradeId
                    ? "СОХРАНИТЬ ИЗМЕНЕНИЯ"
                    : "СОХРАНИТЬ СДЕЛКУ";
        }
    }
}



async function confirmDeleteTrade() {

    if (!currentTrade) {
        return;
    }

    const executeDelete = async () => {

        try {

            await deleteTrade(
                Number(currentTrade.id)
            );

            tg?.HapticFeedback?.notificationOccurred?.(
                "success"
            );

            closeTrade();

            currentTrade = null;

            allTrades =
                await apiGet("/trades/");

            renderDashboard(allTrades);
            populateFilters();

            if (
                document
                    .getElementById("view-trades")
                    ?.classList.contains("active")
            ) {
                renderTradeList();
            }

        } catch (error) {

            console.error(
                "Delete trade failed:",
                error
            );

            tg?.showAlert?.(
                error?.message ||
                "Не удалось удалить сделку."
            );
        }
    };

    if (tg?.showConfirm) {
        tg.showConfirm(
            "Удалить эту сделку?",
            ok => {
                if (ok) {
                    executeDelete();
                }
            }
        );
    } else if (window.confirm("Удалить эту сделку?")) {
        await executeDelete();
    }
}

function openCurrentTradeEdit() {

    if (!currentTrade) {
        return;
    }

    closeTrade();
    openAddTrade(currentTrade);
}


/* ============================================================
   APP CONTROL LAYER
   ============================================================ */



document.addEventListener("DOMContentLoaded", () => { loadTrades(); });
document.addEventListener("DOMContentLoaded", () => { loadTrades(); });

document.querySelectorAll(".nav-item[data-view]").forEach(button => {
    button.addEventListener("click", () => {
        const view = button.dataset.view;

        document.querySelectorAll(".view").forEach(v => {
            v.classList.remove("active");
        });

        document.getElementById(`view-${view}`)?.classList.add("active");

        document.querySelectorAll(".nav-item[data-view]").forEach(b => {
            b.classList.toggle("active", b === button);
        });

        if (view === "home" || view === "trades") {
            loadTrades();
        }

        if (view === "stats") {
            loadAnalytics();
        }

        if (view === "settings") {
            loadSettings();
        }
    });
});

document.getElementById("open-trades")?.addEventListener("click", () => {
    document.getElementById("nav-trades")?.click();
});

document.getElementById("add-trade")?.addEventListener("click", () => {
    openAddTrade();
});

document.getElementById("nav-add")?.addEventListener("click", () => {
    openAddTrade();
});

document.getElementById("modal-close")?.addEventListener("click", () => {
    closeTrade();
});

document.getElementById("trade-modal-backdrop")?.addEventListener("click", () => {
    closeTrade();
});

document.getElementById("add-trade-close")?.addEventListener("click", () => {
    closeAddTrade();
});

document.getElementById("add-trade-backdrop")?.addEventListener("click", () => {
    closeAddTrade();
});

document.getElementById("trades-refresh")?.addEventListener("click", () => {
    loadTrades();
});

document.getElementById("stats-refresh")?.addEventListener("click", () => {
    loadAnalytics();
});

document.getElementById("settings-api-check")?.addEventListener("click", () => {
    checkApiStatus();
});

setTimeout(() => {
    loadTrades();
}, 500);

document.querySelectorAll(".nav-item[data-view]").forEach(button => {
    button.addEventListener("click", () => {
        const view = button.dataset.view;

        document.querySelectorAll(".view").forEach(v => {
            v.classList.remove("active");
        });

        document.getElementById(`view-${view}`)?.classList.add("active");

        document.querySelectorAll(".nav-item[data-view]").forEach(b => {
            b.classList.toggle("active", b === button);
        });

        if (view === "home" || view === "trades") {
            loadTrades();
        }

        if (view === "stats") {
            loadAnalytics();
        }

        if (view === "settings") {
            loadSettings();
        }
    });
});

document.getElementById("open-trades")?.addEventListener("click", () => {
    document.getElementById("nav-trades")?.click();
});

document.getElementById("add-trade")?.addEventListener("click", () => {
    openAddTrade();
});

document.getElementById("nav-add")?.addEventListener("click", () => {
    openAddTrade();
});

document.getElementById("modal-close")?.addEventListener("click", () => {
    closeTrade();
});

document.getElementById("trade-modal-backdrop")?.addEventListener("click", () => {
    closeTrade();
});

document.getElementById("add-trade-close")?.addEventListener("click", () => {
    closeAddTrade();
});

document.getElementById("add-trade-backdrop")?.addEventListener("click", () => {
    closeAddTrade();
});

document.getElementById("trades-refresh")?.addEventListener("click", () => {
    loadTrades();
});

document.getElementById("stats-refresh")?.addEventListener("click", () => {
    loadAnalytics();
});

document.getElementById("settings-api-check")?.addEventListener("click", () => {
    checkApiStatus();
});

setTimeout(() => {
    loadTrades();
}, 500);
