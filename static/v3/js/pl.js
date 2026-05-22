// ============ P&L ============

// Текущий проект — по умолчанию салон
let currentPLProject = 'salon';

function onPLProjectChange() {
  const sel = document.getElementById('pl-project-select');
  if (!sel) return;
  currentPLProject = sel.value;
  loadPL();
}

async function loadPL() {
  const tbody = document.getElementById('pl-tbody');
  if (tbody) tbody.innerHTML = '<tr><td colspan="14" class="text-center text-muted py-4">Загрузка...</td></tr>';

  const data = await fetchData(`/analytics/pl?project=${currentPLProject}`);
  if (!data || !data.months) return;

  const months = [...data.months]
    .filter(m => m.total_revenue > 0)
    .reverse();

  const title = document.getElementById('pl-table-title');
  if (title && data.project_label) title.textContent = `P&L — ${data.project_label}`;

  const badge = document.getElementById('pl-clean-badge');
  if (badge) {
    if (currentPLProject === 'salon') {
      badge.textContent = 'Очищено от личных расходов';
      badge.className = 'badge bg-green-lt';
    } else if (currentPLProject === 'consolidated') {
      badge.textContent = 'Все проекты';
      badge.className = 'badge bg-blue-lt';
    } else {
      badge.textContent = data.project_label || currentPLProject;
      badge.className = 'badge bg-purple-lt';
    }
  }

  renderPLSnapshot(months);
  renderPLTable(months);
}

function renderPLSnapshot(months) {
  if (!months.length) return;

  const last = months[0];
  const prev = months[1];

  const revEl = document.getElementById('pl-snap-revenue');
  const revDelta = document.getElementById('pl-snap-revenue-delta');
  if (revEl) revEl.textContent = formatK(last.total_revenue);
  if (revDelta && prev) {
    const diff = last.total_revenue - prev.total_revenue;
    const pct = prev.total_revenue ? Math.round(diff / prev.total_revenue * 100) : 0;
    const sign = diff >= 0 ? '▲' : '▼';
    revDelta.textContent = `${sign} ${pct > 0 ? '+' : ''}${pct}% к ${prev.month}`;
    revDelta.className = 'text-' + (diff >= 0 ? 'green' : 'red') + ' small mt-1';
  } else if (revDelta) {
    revDelta.textContent = '';
  }

  const expEl = document.getElementById('pl-snap-expenses');
  const expDelta = document.getElementById('pl-snap-expenses-delta');
  if (expEl) expEl.textContent = formatK(last.total_expenses);
  if (expDelta && prev) {
    const diff = last.total_expenses - prev.total_expenses;
    const pct = prev.total_expenses ? Math.round(diff / prev.total_expenses * 100) : 0;
    const sign = diff >= 0 ? '▲' : '▼';
    expDelta.textContent = `${sign} ${pct > 0 ? '+' : ''}${pct}% к ${prev.month}`;
    expDelta.className = 'text-' + (diff >= 0 ? 'red' : 'green') + ' small mt-1';
  } else if (expDelta) {
    expDelta.textContent = '';
  }

  const ebitdaEl = document.getElementById('pl-snap-ebitda');
  const marginEl = document.getElementById('pl-snap-margin');
  if (ebitdaEl) {
    const profit = last.profit ?? (last.total_revenue - last.total_expenses);
    ebitdaEl.textContent = (profit >= 0 ? '+' : '') + formatK(profit);
    ebitdaEl.className = 'h2 mb-0 ' + (profit >= 0 ? 'text-green' : 'text-red');
    if (marginEl && last.total_revenue > 0) {
      const margin = Math.round(profit / last.total_revenue * 100);
      marginEl.textContent = `маржа ${margin}%`;
    } else if (marginEl) {
      marginEl.textContent = '';
    }
  }

  const bestEl = document.getElementById('pl-snap-best-val');
  const bestMonth = document.getElementById('pl-snap-best-month');
  if (bestEl && months.length) {
    const best = months.reduce((a, b) => b.total_revenue > a.total_revenue ? b : a, months[0]);
    bestEl.textContent = formatK(best.total_revenue);
    if (bestMonth) bestMonth.textContent = best.month;
  }
}

function renderPLTable(months) {
  const tbody = document.getElementById('pl-tbody');
  if (!months.length) {
    tbody.innerHTML = '<tr><td colspan="14" class="text-center text-muted py-4">Нет данных за выбранный проект</td></tr>';
    return;
  }

  tbody.innerHTML = months.map(m => {
    const profit = m.profit ?? (m.total_revenue - m.total_expenses);
    const profitClass = profit >= 0 ? 'fw-bold text-green' : 'fw-bold text-red';
    const profitBg = profit >= 0 ? 'background:#f0fdf4' : 'background:#fff0f0';
    const isSalon = currentPLProject === 'salon';

    if (isSalon) {
      return `
      <tr>
        <td><span class="fw-bold">${m.month}</span></td>
        <td class="text-end" style="color:#2f9e44">${formatK(m.revenue_services)}</td>
        <td class="text-end" style="color:#2f9e44">${formatK(m.revenue_certificates)}</td>
        <td class="text-end" style="color:#2f9e44">${formatK(m.revenue_abonements)}</td>
        <td class="text-end" style="color:#2f9e44">${formatK(m.revenue_fitmost)}</td>
        <td class="text-end fw-bold" style="background:#d3f9d8;color:#1e7e34">${formatK(m.total_revenue)}</td>
        <td class="text-end" style="color:#c92a2a;cursor:pointer" onclick="showPLDetail('${m.month}','salary','ФОТ')" title="Детализация">${formatK(m.salary)}</td>
        <td class="text-end" style="color:#c92a2a;cursor:pointer" onclick="showPLDetail('${m.month}','salon_rent','Аренда')" title="Детализация">${formatK(m.rent)}</td>
        <td class="text-end" style="color:#c92a2a;cursor:pointer" onclick="showPLDetail('${m.month}','cosmetics','Косметика')" title="Детализация">${formatK(m.cosmetics)}</td>
        <td class="text-end" style="color:#c92a2a">${formatK(m.materials)}</td>
        <td class="text-end" style="color:#c92a2a;cursor:pointer" onclick="showPLDetail('${m.month}','marketing','Маркетинг')" title="Детализация">${formatK(m.marketing)}</td>
        <td class="text-end" style="color:#c92a2a;cursor:pointer" onclick="showPLDetail('${m.month}','bank_fees','Банк')" title="Детализация">${formatK(m.bank_fees)}</td>
        <td class="text-end fw-bold" style="background:#ffe0e0;color:#c92a2a">${formatK(m.total_expenses)}</td>
        <td class="text-end ${profitClass}" style="${profitBg}">${profit >= 0 ? '+' : ''}${formatK(profit)}</td>
      </tr>`;
    } else {
      return `
      <tr>
        <td><span class="fw-bold">${m.month}</span></td>
        <td class="text-end" style="color:#2f9e44" colspan="4">${formatK(m.revenue_other || m.total_revenue)}</td>
        <td class="text-end fw-bold" style="background:#d3f9d8;color:#1e7e34">${formatK(m.total_revenue)}</td>
        <td class="text-end" style="color:#c92a2a;cursor:pointer" onclick="showPLDetail('${m.month}','salary','ФОТ')" title="Детализация">${formatK(m.salary)}</td>
        <td class="text-end" style="color:#c92a2a;cursor:pointer" onclick="showPLDetail('${m.month}','salon_rent','Аренда')" title="Детализация">${formatK(m.rent)}</td>
        <td class="text-end" style="color:#c92a2a;cursor:pointer" onclick="showPLDetail('${m.month}','cosmetics','Косметика')" title="Детализация">${formatK(m.cosmetics)}</td>
        <td class="text-end" style="color:#c92a2a">${formatK(m.materials)}</td>
        <td class="text-end" style="color:#c92a2a;cursor:pointer" onclick="showPLDetail('${m.month}','marketing','Маркетинг')" title="Детализация">${formatK(m.marketing)}</td>
        <td class="text-end" style="color:#c92a2a;cursor:pointer" onclick="showPLDetail('${m.month}','bank_fees','Банк')" title="Детализация">${formatK(m.bank_fees)}</td>
        <td class="text-end fw-bold" style="background:#ffe0e0;color:#c92a2a">${formatK(m.total_expenses)}</td>
        <td class="text-end ${profitClass}" style="${profitBg}">${profit >= 0 ? '+' : ''}${formatK(profit)}</td>
      </tr>`;
    }
  }).join('');
}


// ── P&L Drill-down ──────────────────────────────────────────
async function showPLDetail(month, category, label) {
  const modalEl = document.getElementById('pl-detail-modal');
  if (!modalEl) return;

  document.getElementById('pl-detail-title').textContent = `${label} — ${month}`;
  document.getElementById('pl-detail-body').innerHTML = '<div class="text-center text-muted py-3">Загрузка...</div>';

  modalEl.style.display = 'flex';

  const data = await fetchData(`/analytics/pl-detail?month=${month}&category=${category}`);
  if (!data || data.error) {
    document.getElementById('pl-detail-body').innerHTML = '<div class="text-danger py-3">Ошибка загрузки</div>';
    return;
  }

  const rows = (data.rows || []).map(r => `
    <tr>
      <td class="small">${r.date || ''}</td>
      <td class="small">${r.label}</td>
      <td class="text-muted small">${r.detail || ''}</td>
      <td class="text-end fw-bold">${formatMoney(r.amount)}</td>
      ${r.status ? `<td><span class="badge ${r.status === 'paid' ? 'bg-green-lt' : 'bg-yellow-lt'}">${r.status}</span></td>` : '<td></td>'}
    </tr>`).join('');

  document.getElementById('pl-detail-body').innerHTML = `
    <table class="table table-vcenter table-sm">
      <thead>
        <tr>
          <th style="width:90px">Дата</th>
          <th>Описание</th>
          <th>Детали</th>
          <th class="text-end">Сумма</th>
          <th style="width:80px">Статус</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
      <tfoot>
        <tr class="fw-bold">
          <td colspan="3" class="text-end">Итого:</td>
          <td class="text-end">${formatMoney(data.total)}</td>
          <td></td>
        </tr>
      </tfoot>
    </table>`;
}

function closePLDetail() {
  const el = document.getElementById('pl-detail-modal');
  if (el) el.style.display = 'none';
}


// ============ TRANSACTIONS TAB ============

const TX_CATEGORIES = [
  'bank_fee', 'cosmetics', 'salon_rent', 'credit', 'internal',
  'salary', 'marketing', 'materials', 'food', 'transport', 'other',
  'transfer_in', 'production', 'credit_card', 'investor'
];

const TX_PROJECTS = [
  'salon', 'personal', 'podcast', 'book', 'consulting', 'internal'
];

let txState = {
  page: 1,
  month: '',
  source: '',
  category: '',
  project: '',
  total: 0,
  perPage: 50,
};

// Переключение под-вкладок P&L (P&L / Транзакции)
function showPLTab(tab) {
  document.querySelectorAll('[data-pl-tab-content]').forEach(el => el.classList.add('d-none'));
  document.querySelectorAll('[data-pl-tab]').forEach(el => el.classList.remove('active'));

  const content = document.getElementById(`pl-tab-${tab}`);
  if (content) content.classList.remove('d-none');

  const link = document.querySelector(`[data-pl-tab="${tab}"]`);
  if (link) link.classList.add('active');

  if (tab === 'transactions') {
    loadTransactions();
  }
  if (tab === 'personal') {
    loadPersonalExpenses();
    loadSelfTransfers();
  }
  if (tab === 'reconciliation') {
    loadReconciliation();
  }
}

async function loadTransactions(resetPage = true) {
  if (resetPage) txState.page = 1;

  txState.month    = document.getElementById('tx-filter-month')?.value    || '';
  txState.source   = document.getElementById('tx-filter-source')?.value   || '';
  txState.category = document.getElementById('tx-filter-category')?.value || '';
  txState.project  = document.getElementById('tx-filter-project')?.value  || '';

  const tbody = document.getElementById('tx-tbody');
  if (tbody) tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">Загрузка...</td></tr>';

  const params = new URLSearchParams({
    page:     txState.page,
    per_page: txState.perPage,
  });
  if (txState.month)    params.set('month',    txState.month);
  if (txState.source)   params.set('source',   txState.source);
  if (txState.category) params.set('category', txState.category);
  if (txState.project)  params.set('project',  txState.project);

  const data = await fetchData(`/analytics/transactions?${params}`);

  if (!data || data.error) {
    if (tbody) tbody.innerHTML = '<tr><td colspan="8" class="text-danger py-3 text-center">Ошибка загрузки</td></tr>';
    return;
  }

  txState.total = data.total || 0;
  renderTransactionsTable(data.rows || []);
  renderTxPagination();

  const summaryEl = document.getElementById('tx-summary');
  if (summaryEl) summaryEl.textContent = `${data.total} транзакций`;
}

function renderTransactionsTable(rows) {
  const tbody = document.getElementById('tx-tbody');
  if (!tbody) return;

  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">Нет транзакций по выбранным фильтрам</td></tr>';
    return;
  }

  tbody.innerHTML = rows.map(r => {
    const amountClass = r.amount >= 0 ? 'text-green' : 'text-red';
    const amountStr   = (r.amount >= 0 ? '+' : '') + formatMoney(r.amount);

    const catSelect  = buildTxSelect(TX_CATEGORIES, r.category,
      `saveTxField(${r.id}, '${r.source}', 'category', this.value)`);
    const projSelect = buildTxSelect(TX_PROJECTS, r.project,
      `saveTxField(${r.id}, '${r.source}', 'project', this.value)`);

    const sourceBadge = ({
      bank:     '<span class="badge bg-blue-lt">🏦 Банк</span>',
      personal: '<span class="badge bg-purple-lt">👤 Личные</span>',
      cash:     '<span class="badge bg-yellow-lt">💵 Наличные</span>',
    })[r.source] || `<span class="badge bg-secondary-lt">${escHtml(r.source)}</span>`;

    return `
    <tr id="tx-row-${r.id}-${r.source}">
      <td class="text-muted small" style="white-space:nowrap">${r.date || ''}</td>
      <td>${sourceBadge}</td>
      <td class="small" style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
          title="${escHtml(r.description || '')}">${escHtml(r.description || '')}</td>
      <td class="small text-muted" style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
          title="${escHtml(r.counterparty || '')}">${escHtml(r.counterparty || '')}</td>
      <td>${catSelect}</td>
      <td>${projSelect}</td>
      <td class="text-end fw-bold ${amountClass}" style="white-space:nowrap">${amountStr}</td>
      <td id="tx-status-${r.id}-${r.source}" style="width:28px;text-align:center"></td>
    </tr>`;
  }).join('');
}

function buildTxSelect(options, current, onchange) {
  const opts = options.map(o =>
    `<option value="${o}"${o === current ? ' selected' : ''}>${o}</option>`
  ).join('');
  return `<select class="form-select form-select-sm" style="min-width:110px;font-size:12px" onchange="${onchange}">${opts}</select>`;
}

function escHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

async function saveTxField(id, source, field, value) {
  const statusEl = document.getElementById(`tx-status-${id}-${source}`);
  if (statusEl) statusEl.innerHTML = '<span class="spinner-border spinner-border-sm text-muted" style="width:14px;height:14px"></span>';

  try {
    const res = await fetch(`/analytics/transactions/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source, [field]: value }),
    });
    const json = await res.json();

    if (statusEl) {
      if (json.ok) {
        statusEl.innerHTML = '<span class="text-green" style="font-size:16px">✓</span>';
        setTimeout(() => { if (statusEl) statusEl.innerHTML = ''; }, 1500);
      } else {
        statusEl.innerHTML = '<span class="text-red" title="Ошибка сохранения" style="font-size:16px">✗</span>';
      }
    }
  } catch (e) {
    if (statusEl) statusEl.innerHTML = '<span class="text-red" style="font-size:16px">✗</span>';
  }
}

function renderTxPagination() {
  const el = document.getElementById('tx-pagination');
  if (!el) return;

  const totalPages = Math.ceil(txState.total / txState.perPage);
  if (totalPages <= 1) { el.innerHTML = ''; return; }

  const page = txState.page;
  const pages = [];
  pages.push(1);
  if (page > 3) pages.push('…');
  for (let p = Math.max(2, page - 1); p <= Math.min(totalPages - 1, page + 1); p++) pages.push(p);
  if (page < totalPages - 2) pages.push('…');
  if (totalPages > 1) pages.push(totalPages);

  el.innerHTML = `
    <div class="d-flex align-items-center gap-2 flex-wrap">
      <nav>
        <ul class="pagination pagination-sm mb-0">
          <li class="page-item${page === 1 ? ' disabled' : ''}">
            <a class="page-link" href="javascript:void(0)" onclick="txGoPage(${page - 1})">←</a>
          </li>
          ${pages.map(p => p === '…'
            ? `<li class="page-item disabled"><span class="page-link">…</span></li>`
            : `<li class="page-item${p === page ? ' active' : ''}">
                 <a class="page-link" href="javascript:void(0)" onclick="txGoPage(${p})">${p}</a>
               </li>`
          ).join('')}
          <li class="page-item${page === totalPages ? ' disabled' : ''}">
            <a class="page-link" href="javascript:void(0)" onclick="txGoPage(${page + 1})">→</a>
          </li>
        </ul>
      </nav>
      <span class="text-muted small">Стр. ${page} из ${totalPages} · ${txState.total} строк</span>
    </div>`;
}

function txGoPage(p) {
  const totalPages = Math.ceil(txState.total / txState.perPage);
  if (p < 1 || p > totalPages) return;
  txState.page = p;
  loadTransactions(false);
}

function resetTxFilters() {
  ['tx-filter-month', 'tx-filter-source', 'tx-filter-category', 'tx-filter-project']
    .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  loadTransactions();
}


// ══ Личные расходы ══════════════════════════════════════════
async function loadSelfTransfers() {
  const tbody = document.getElementById('self-transfers-tbody');
  if (!tbody) return;

  const data = await fetchData('/analytics/self-transfers?date_from=2026-01-01');
  if (!data || data.error) {
    tbody.innerHTML = '<tr><td colspan="3" class="text-danger text-center py-3">Ошибка загрузки</td></tr>';
    return;
  }
  if (!data.months || !data.months.length) {
    tbody.innerHTML = '<tr><td colspan="3" class="text-muted text-center py-3">Нет данных</td></tr>';
    return;
  }

  // Показываем только месяцы где есть неразмеченные переводы
  const pending = data.months.filter(m => !m.done);
  const done    = data.months.filter(m => m.done);

  if (!pending.length && !done.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-3">Нет данных</td></tr>';
    return;
  }

  tbody.innerHTML = [
    ...pending.map(m => {
      const txData = JSON.stringify(m.transactions).replace(/"/g, '&quot;');
      const bdData = JSON.stringify(m.breakdown || []).replace(/"/g, '&quot;');
      return `<tr style="cursor:pointer" onclick="showSelfTransferDetail(${txData}, '${m.month}', ${m.total}, ${m.marked || 0}, ${bdData})">
        <td class="fw-bold">${m.month}</td>
        <td class="text-end text-muted">${m.count}</td>
        <td class="text-end">${formatK(m.total)}</td>
        <td class="text-end">
          ${m.marked ? `<span class="text-green small">✓ ${formatK(m.marked)}</span> ` : ''}
          <span class="badge bg-orange-lt">⚠️ ${formatK(m.remaining)}</span>
        </td>
      </tr>`;
    }),
    ...done.map(m => {
      const txData = JSON.stringify(m.transactions).replace(/"/g, '&quot;');
      const bdData2 = JSON.stringify(m.breakdown || []).replace(/"/g, '&quot;');
      return `<tr class="text-muted" style="cursor:pointer" onclick="showSelfTransferDetail(${txData}, '${m.month}', ${m.total}, ${m.marked || 0}, ${bdData2})">
        <td>${m.month}</td>
        <td class="text-end">${m.count}</td>
        <td class="text-end">${formatK(m.total)}</td>
        <td class="text-end"><span class="badge bg-green-lt">✅ размечено</span></td>
      </tr>`;
    }),
  ].join('');
}

function showSelfTransferDetail(txs, month, monthTotal, alreadyMarked, breakdown) {
  const total    = monthTotal || txs.reduce((s, t) => s + t.amount, 0);
  const marked   = alreadyMarked || 0;
  const bdItems  = breakdown || [];
  const modalEl = document.getElementById('pl-detail-modal');
  if (!modalEl) return;
  document.getElementById('pl-detail-title').textContent = `Переводы себе — ${month}`;

  const rows = txs.map(t => `
    <tr>
      <td class="small text-muted">${t.date}</td>
      <td class="text-end fw-bold">${formatMoney(t.amount)}</td>
      <td><select class="form-select form-select-sm" style="min-width:150px;font-size:12px"
            onchange="saveSelfTransferPurpose(${t.id}, this.value)">
        <option value="">— не размечено —</option>
        <option value="credit_sber"${t.purpose==='credit_sber'?' selected':''}>💳 Кредит Сбер</option>
        <option value="rent"${t.purpose==='rent'?' selected':''}>🏠 Аренда</option>
        <option value="subscriptions"${t.purpose==='subscriptions'?' selected':''}>📱 Подписки</option>
        <option value="transfers"${t.purpose==='transfers'?' selected':''}>👤 Перевод другому</option>
        <option value="internal"${t.purpose==='internal'?' selected':''}>🔄 Внутренний</option>
        <option value="other"${t.purpose==='other'?' selected':''}>📦 Прочее</option>
      </select></td>
    </tr>`).join('');

  const totalAmt = txs.reduce((s, t) => s + t.amount, 0);
  document.getElementById('pl-detail-body').innerHTML = `
    <table class="table table-vcenter table-sm">
      <thead><tr><th>Дата</th><th class="text-end">Сумма</th><th>Назначение</th></tr></thead>
      <tbody>${rows}</tbody>
      <tfoot><tr class="fw-bold">
        <td class="text-end">Итого:</td>
        <td class="text-end">${formatMoney(total)}</td><td></td>
      </tr></tfoot>
    </table>
    <div class="card mt-3">
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <span class="fw-bold text-muted small">Разбивка за месяц — итого: <b>${formatMoney(total)}</b></span>
          <span class="small" id="st-remainder">Не размечено: <b class="${marked >= total ? 'text-green' : 'text-orange'}">${formatMoney(Math.max(0, total - marked))}</b>${marked > 0 ? ' <span class=\"text-green small\">(✓ ' + formatMoney(marked) + ' размечено)</span>' : ''}</span>
        </div>
        ${bdItems.length ? `
        <div class="mb-3 p-2 bg-light rounded">
          <div class="small fw-bold text-muted mb-1">Уже размечено:</div>
          ${bdItems.map(b => `
            <div class="d-flex justify-content-between small py-1 border-bottom align-items-center">
              <span>${b.desc} <span class="badge bg-secondary-lt">${b.cat}</span></span>
              <div class="d-flex align-items-center gap-2">
                <span class="fw-bold">${formatMoney(b.amount)}</span>
                <button class="btn btn-sm btn-outline-danger py-0 px-1" style="font-size:11px"
                  onclick="deleteBreakdownItem(${b.id}, '${month}')">✕</button>
              </div>
            </div>`).join('')}
        </div>` : ''}
        <div id="st-rows"></div>
        <button class="btn btn-sm btn-outline-secondary mt-2" onclick="stAddRow(${total})">+ Добавить строку</button>
        <div class="mt-3">
          <button class="btn btn-sm btn-primary" onclick="saveSelfTransferMonth('${month}', ${total})">
            Сохранить разбивку
          </button>
          <span class="small text-muted ms-2" id="st-save-status"></span>
        </div>
      </div>
    </div>`;
  modalEl.style.display = 'flex';
}

let stTotal = 0;

function stAddRow(total) {
  stTotal = total;
  const container = document.getElementById('st-rows');
  const idx = container.children.length;
  const row = document.createElement('div');
  row.className = 'row g-2 align-items-center mb-2';
  row.innerHTML = `
    <div class="col-auto">
      <input type="number" class="form-control form-control-sm st-amount" 
             placeholder="Сумма" style="width:120px" oninput="stUpdateRemainder(${total})">
    </div>
    <div class="col">
      <input type="text" class="form-control form-control-sm st-desc" 
             placeholder="Описание (напр. Кредит Сбер, Claude Pro...)">
    </div>
    <div class="col-auto">
      <select class="form-select form-select-sm st-cat" style="min-width:130px;font-size:12px">
        <option value="credit">💳 Кредит</option>
        <option value="rent">🏠 Аренда</option>
        <option value="subscriptions">📱 Подписки</option>
        <option value="shopping">🛍️ Покупки</option>
        <option value="food">🍽️ Еда</option>
        <option value="sport">🏃 Спорт</option>
        <option value="government">🏛️ Госуслуги</option>
        <option value="transfers">👤 Перевод</option>
        <option value="other">📦 Прочее</option>
      </select>
    </div>
    <div class="col-auto">
      <button class="btn btn-sm btn-outline-danger" onclick="this.closest('.row').remove(); stUpdateRemainder(${total})">✕</button>
    </div>`;
  container.appendChild(row);
  stUpdateRemainder(total);
}

function stUpdateRemainder(total) {
  const amounts = [...document.querySelectorAll('.st-amount')]
    .map(el => parseFloat(el.value || 0));
  const used = amounts.reduce((s, a) => s + a, 0);
  const rem  = total - used;
  const el   = document.getElementById('st-remainder');
  if (el) el.innerHTML = `Не размечено: <b class="${rem > 0.01 ? 'text-orange' : 'text-green'}">${formatMoney(rem)}</b>`;
}

async function deleteBreakdownItem(id, month) {
  const res  = await fetch(`/analytics/transactions/${id}`, { method: 'DELETE' });
  const data = await res.json();
  if (data.ok) {
    loadSelfTransfers();
    loadPersonalExpenses();
    closePLDetail();
  } else {
    console.error('Ошибка удаления:', data.error);
  }
}

async function saveSelfTransferMonth(month, total) {
  const status = document.getElementById('st-save-status');
  const rows   = [...document.querySelectorAll('#st-rows .row')];

  if (!rows.length) {
    if (status) status.innerHTML = '<span class="text-orange">Добавьте хотя бы одну строку</span>';
    return;
  }

  const items = rows.map(row => ({
    amount: parseFloat(row.querySelector('.st-amount').value || 0),
    desc:   row.querySelector('.st-desc').value.trim(),
    cat:    row.querySelector('.st-cat').value,
  })).filter(r => r.amount > 0);

  if (!items.length) {
    if (status) status.innerHTML = '<span class="text-orange">Укажите суммы</span>';
    return;
  }

  if (status) status.innerHTML = '<span class="text-muted">Сохраняю...</span>';

  const res = await fetch('/analytics/self-transfer-breakdown', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ month, items }),
  });
  const data = await res.json();

  if (data.ok) {
    if (status) status.innerHTML = `<span class="text-green">✓ Сохранено ${items.length} строк</span>`;
    loadPersonalExpenses();
    loadSelfTransfers();
  } else {
    if (status) status.innerHTML = `<span class="text-danger">Ошибка: ${data.error}</span>`;
  }
}

async function saveSelfTransferPurpose(id, value) {
  await fetch(`/analytics/transactions/${id}`, {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({source: 'personal', expense_category: value}),
  });
}

async function loadPersonalExpenses() {
  const tbodyEl = document.getElementById('personal-tbody');
  const theadEl = document.getElementById('personal-thead');
  const totalEl = document.getElementById('personal-grand-total');
  if (!tbodyEl) return;

  tbodyEl.innerHTML = '<tr><td colspan="20" class="text-center text-muted py-4">Загрузка...</td></tr>';

  const data = await fetchData('/analytics/personal-expenses?date_from=2026-01-01');
  if (!data || data.error) {
    tbodyEl.innerHTML = '<tr><td class="text-danger py-3 text-center">Ошибка загрузки</td></tr>';
    return;
  }

  const cats   = data.categories || [];
  const labels = data.cat_labels || {};
  const months = data.months || [];

  // Thead
  theadEl.innerHTML = '<tr>'
    + '<th>Месяц</th>'
    + cats.map(c => `<th class="text-end" style="white-space:nowrap">${labels[c] || c}</th>`).join('')
    + '<th class="text-end fw-bold">Итого</th>'
    + '</tr>';

  // Tbody — ячейки кликабельны
  tbodyEl.innerHTML = months.map(m => {
    const cells = cats.map(c => {
      const amt = m.categories[c] || 0;
      if (!amt) return `<td class="text-end text-muted">—</td>`;
      return `<td class="text-end" style="cursor:pointer;text-decoration:underline dotted"
                title="Детализация" onclick="showPersonalDetail('${m.month}','${c}')">${formatK(amt)}</td>`;
    }).join('');
    return `<tr>
      <td class="fw-bold">${m.month}</td>
      ${cells}
      <td class="text-end fw-bold" style="cursor:pointer;text-decoration:underline dotted"
          onclick="showPersonalDetail('${m.month}','__all__')">${formatK(m.total)}</td>
    </tr>`;
  }).join('');

  if (totalEl) {
    totalEl.textContent = 'Итого за период: ' + formatK(data.grand_total);
  }
}


async function showPersonalDetail(month, category) {
  const modalEl = document.getElementById('pl-detail-modal');
  if (!modalEl) return;
  const label = category === '__all__' ? 'Все категории' : category;
  document.getElementById('pl-detail-title').textContent = `Личные расходы — ${month} — ${label}`;
  document.getElementById('pl-detail-body').innerHTML = '<div class="text-center text-muted py-3">Загрузка...</div>';
  modalEl.style.display = 'flex';

  const data = await fetchData(`/analytics/personal-expenses-detail?month=${month}&category=${category}`);
  if (!data || data.error) {
    document.getElementById('pl-detail-body').innerHTML = '<div class="text-danger py-3">Ошибка загрузки</div>';
    return;
  }
  if (!data.rows || !data.rows.length) {
    document.getElementById('pl-detail-body').innerHTML = '<div class="text-muted py-3 text-center">Нет транзакций</div>';
    return;
  }
  const rows = data.rows.map(r => `
    <tr>
      <td class="small text-muted" style="white-space:nowrap">${r.date}</td>
      <td class="small text-muted">${r.category}</td>
      <td class="small">${r.description || '—'}</td>
      <td class="text-end fw-bold">${formatMoney(r.amount)}</td>
    </tr>`).join('');
  document.getElementById('pl-detail-body').innerHTML = `
    <table class="table table-vcenter table-sm">
      <thead><tr>
        <th style="width:90px">Дата</th>
        <th style="width:100px">Категория</th>
        <th>Описание</th>
        <th class="text-end">Сумма</th>
      </tr></thead>
      <tbody>${rows}</tbody>
      <tfoot><tr class="fw-bold">
        <td colspan="3" class="text-end">Итого:</td>
        <td class="text-end">${formatMoney(data.total)}</td>
      </tr></tfoot>
    </table>`;
}

// ============ RECONCILIATION TAB ============

async function loadReconciliation() {
  const data = await fetchData('/analytics/reconciliation');
  if (!data || data.error) {
    ['recon-terminal-tbody', 'recon-online-tbody'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = '<tr><td colspan="6" class="text-danger py-3 text-center">Ошибка загрузки</td></tr>';
    });
    return;
  }

  const terminalTbody = document.getElementById('recon-terminal-tbody');
  const onlineTbody   = document.getElementById('recon-online-tbody');
  if (!terminalTbody || !onlineTbody) return;

  // Fitmost — отдельный запрос
  loadFitmostReconciliation();

  terminalTbody.innerHTML = data.months.map(m => {
    const diffClass = m.terminal_ok ? 'text-green' : 'text-red';
    const icon      = m.terminal_ok ? '✅' : '⚠️';
    const mo = m.month;
    return `<tr>
      <td class="fw-bold">${mo}</td>
      <td class="text-end" style="cursor:pointer" onclick="showReconDetail('${mo}','ycl_terminal','YCL Карта')" title="Детализация">${formatK(m.terminal_ycl)}</td>
      <td class="text-end text-muted" style="cursor:pointer" onclick="showReconDetail('${mo}','ycl_cash','YCL Касса')" title="Детализация">${formatK(m.terminal_ycl_cash)}</td>
      <td class="text-end" style="cursor:pointer" onclick="showReconDetail('${mo}','bank_terminal','Банк ТБанк')" title="Детализация">${formatK(m.terminal_bank_gross)}</td>
      <td class="text-end text-muted">${formatK(m.terminal_fee)}</td>
      <td class="text-end fw-bold ${diffClass}" style="cursor:pointer" onclick="showReconDays('${mo}')" title="Расхождения по дням">${m.terminal_diff >= 0 ? '+' : ''}${formatK(m.terminal_diff)}</td>
      <td class="text-center" style="cursor:pointer" onclick="showReconDays('${mo}')">${icon}</td>
    </tr>`;
  }).join('');

  onlineTbody.innerHTML = data.months.map(m => {
    const diffClass = m.online_ok ? 'text-green' : 'text-orange';
    const icon      = m.online_ok ? '✅' : '⚠️';
    const mo = m.month;
    return `<tr>
      <td class="fw-bold">${mo}</td>
      <td class="text-end" style="cursor:pointer" onclick="showReconDetail('${mo}','ycl_online','YCL ЮKassa')" title="Детализация">${formatK(m.online_ycl)}</td>
      <td class="text-end" style="cursor:pointer" onclick="showReconDetail('${mo}','bank_online','Аванпост')" title="Детализация">${formatK(m.online_bank_gross)}</td>
      <td class="text-end text-muted">${m.online_fee_pct}%</td>
      <td class="text-end fw-bold ${diffClass}">${m.online_diff >= 0 ? '+' : ''}${formatK(m.online_diff)}</td>
      <td class="text-center">${icon}</td>
    </tr>`;
  }).join('');
}


// ── Reconciliation drill-down ────────────────────────────────
async function showReconDays(month, tableDiff) {
  const modalEl = document.getElementById('pl-detail-modal');
  if (!modalEl) return;

  document.getElementById('pl-detail-title').textContent = `Расхождения по дням — ${month}`;
  document.getElementById('pl-detail-body').innerHTML = '<div class="text-center text-muted py-3">Загрузка...</div>';
  modalEl.style.display = 'flex';

  const data = await fetchData(`/analytics/reconciliation-days?month=${month}`);
  if (!data || data.error) {
    document.getElementById('pl-detail-body').innerHTML = '<div class="text-danger py-3">Ошибка загрузки</div>';
    return;
  }

  const problems  = data.rows.filter(r => r.suspicious || r.real_missing);
  const allWithDiff = data.rows.filter(r => Math.abs(r.diff) > 100);
  const tableDiffTotal = allWithDiff.reduce((s, r) => s + r.diff, 0);

  const allRows = allWithDiff.map(r => {
    let icon = '', hint = '';
    if (r.suspicious)        { icon = '🔴'; hint = 'Возможно карта записана как касса'; }
    else if (r.real_missing) { icon = '❌'; hint = 'Нет записи в YCL'; }
    else if (r.boundary)     { icon = '📅'; hint = 'Последний день месяца — карта зачислится в следующем месяце'; }
    else if (r.diff > 0)     { icon = '⚠️'; hint = 'YCL > Банк (ошибка записи)'; }
    else                     { icon = '⚠️'; hint = 'Банк > YCL (продажа товара или пропущена запись)'; }
    const dClass = r.diff < 0 ? 'text-red' : 'text-green';
    const dSign  = r.diff >= 0 ? '+' : '';
    return '<tr>'
      + '<td style="white-space:nowrap">' + icon + ' ' + r.day + '</td>'
      + '<td class="text-end">' + formatMoney(r.ycl_card) + '</td>'
      + '<td class="text-end text-muted">' + formatMoney(r.ycl_cash) + '</td>'
      + '<td class="text-end">' + formatMoney(r.bank) + '</td>'
      + '<td class="text-end fw-bold ' + dClass + '">' + dSign + formatMoney(r.diff) + '</td>'
      + '<td class="small text-muted">' + hint + '</td>'
      + '</tr>';
  }).join('');

  const tdColorTotal = tableDiffTotal < 0 ? 'text-red' : 'text-green';
  const tableHtml = allWithDiff.length
    ? '<table class="table table-vcenter table-sm">'
      + '<thead><tr><th>День</th><th class="text-end">YCL карта</th><th class="text-end">YCL касса</th><th class="text-end">Банк</th><th class="text-end">Разница</th><th>Подсказка</th></tr></thead>'
      + '<tbody>' + allRows + '</tbody>'
      + '</table>'
    : '<div class="text-success py-3 text-center">✅ Явных расхождений не найдено</div>';

  const suspCount = problems.filter(r=>r.suspicious).length;
  const missCount = problems.filter(r=>r.real_missing).length;
  const boundaryCount = allWithDiff.filter(r=>r.boundary).length;
  const badgesHtml = '<div class="mb-3 d-flex gap-3 flex-wrap">'
    + (suspCount ? '<span class="badge bg-red-lt">🔴 Касса вместо карты: ' + suspCount + '</span>' : '')
    + (missCount ? '<span class="badge bg-orange-lt">❌ Нет в YCL: ' + missCount + '</span>' : '')
    + (boundaryCount ? '<span class="badge bg-blue-lt">📅 Пограничных дней: ' + boundaryCount + '</span>' : '')
    + (!suspCount && !missCount && !boundaryCount ? '<span class="badge bg-green-lt">✅ Проблем не найдено</span>' : '')
    + '</div>';

  document.getElementById('pl-detail-body').innerHTML = badgesHtml + tableHtml;
}

async function showReconDetail(month, side, label) {
  const modalEl = document.getElementById('pl-detail-modal');
  if (!modalEl) return;

  document.getElementById('pl-detail-title').textContent = `${label} — ${month}`;
  document.getElementById('pl-detail-body').innerHTML = '<div class="text-center text-muted py-3">Загрузка...</div>';
  modalEl.style.display = 'flex';

  const data = await fetchData(`/analytics/reconciliation-detail?month=${month}&side=${side}`);
  if (!data || data.error) {
    document.getElementById('pl-detail-body').innerHTML = '<div class="text-danger py-3">Ошибка загрузки</div>';
    return;
  }

  const rows = (data.rows || []).map(r => `
    <tr>
      <td class="small text-muted" style="white-space:nowrap">${r.date}</td>
      <td class="small">${r.label}</td>
      <td class="small text-muted">${r.detail || ''}</td>
      <td class="text-end fw-bold">${formatMoney(r.amount)}</td>
    </tr>`).join('');

  document.getElementById('pl-detail-body').innerHTML = `
    <table class="table table-vcenter table-sm">
      <thead>
        <tr>
          <th style="width:90px">Дата</th>
          <th>Описание</th>
          <th>Детали</th>
          <th class="text-end">Сумма</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
      <tfoot>
        <tr class="fw-bold">
          <td colspan="3" class="text-end">Итого:</td>
          <td class="text-end">${formatMoney(data.total)}</td>
        </tr>
      </tfoot>
    </table>`;
}

async function loadFitmostReconciliation() {
  const tbody  = document.getElementById('recon-fitmost-tbody');
  const debtEl = document.getElementById('fitmost-total-debt');
  if (!tbody) return;

  const data = await fetchData('/analytics/fitmost-reconciliation');
  if (!data || data.error) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Ошибка загрузки</td></tr>';
    return;
  }

  tbody.innerHTML = data.months.map(m => {
    const diff      = m.month_diff || 0;
    const diffClass = diff >= 0 ? 'text-green' : 'text-orange';
    const diffStr   = (diff >= 0 ? '+' : '') + formatK(diff);
    const debtClass = m.debt > 0 ? 'text-orange' : 'text-green';
    let badge = '';
    if (m.count > 0 && m.month_received === 0)
      badge = ' <span class="badge bg-red-lt">ожидается</span>';
    else if (m.count > 0 && diff >= -500)
      badge = ' <span class="badge bg-green-lt">✓</span>';
    else if (m.count > 0)
      badge = ' <span class="badge bg-orange-lt">!</span>';

    // Ячейки «Записей/Ожидаем» и «Получено» кликабельны
    const tdRecords  = m.count > 0
      ? `<td class="text-end" style="cursor:pointer;text-decoration:underline dotted" title="Показать записи" onclick="showFitmostRecords('${m.month}')">${m.count}</td>`
      + `<td class="text-end text-muted">${formatK(m.full_cost)}</td>`
      + `<td class="text-end" style="cursor:pointer;text-decoration:underline dotted" title="Показать записи" onclick="showFitmostRecords('${m.month}')">${formatK(m.month_expect)}</td>`
      : `<td class="text-end">0</td><td class="text-end text-muted">—</td><td class="text-end">—</td>`;
    const tdPayments = m.month_received > 0
      ? `<td class="text-end" style="cursor:pointer;text-decoration:underline dotted" title="Показать платежи" onclick="showFitmostPayments('${m.month}')">${formatK(m.month_received)}</td>`
      : `<td class="text-end text-muted">—</td>`;

    return '<tr>'
      + '<td class="fw-bold">' + m.month + badge + '</td>'
      + tdRecords
      + tdPayments
      + '<td class="text-end fw-bold ' + diffClass + '">' + diffStr + '</td>'
      + '<td class="text-end small ' + debtClass + '">' + formatK(m.debt) + '</td>'
      + '</tr>';
  }).join('');

  if (debtEl) {
    const cls = (data.total_debt || 0) > 0 ? 'text-orange' : 'text-green';
    debtEl.innerHTML = 'Оказано услуг: <b>' + formatK(data.total_expect) + '</b>'
      + ' &nbsp;|&nbsp; Получено: <b>' + formatK(data.total_received) + '</b>'
      + ' &nbsp;|&nbsp; Долг Fitmost: <b class="' + cls + '">' + formatK(data.total_debt) + '</b>';
  }
}

// Клик на «Записей / Ожидаем» — список визитов Fitmost за месяц
async function showFitmostRecords(month) {
  const modalEl = document.getElementById('pl-detail-modal');
  if (!modalEl) return;
  document.getElementById('pl-detail-title').textContent = `Fitmost записи — ${month}`;
  document.getElementById('pl-detail-body').innerHTML = '<div class="text-center text-muted py-3">Загрузка...</div>';
  modalEl.style.display = 'flex';

  const data = await fetchData(`/analytics/fitmost-detail?month=${month}`);
  if (!data || data.error) {
    document.getElementById('pl-detail-body').innerHTML = '<div class="text-danger py-3">Ошибка загрузки</div>';
    return;
  }
  if (!data.rows || !data.rows.length) {
    document.getElementById('pl-detail-body').innerHTML = '<div class="text-muted py-3 text-center">Нет записей за период</div>';
    return;
  }
  const rows = data.rows.map(r =>
    `<tr>
      <td class="small text-muted" style="white-space:nowrap">${r.date}</td>
      <td class="small">${r.client}</td>
      <td class="small text-muted">${r.service}</td>
      <td class="text-end">${formatMoney(r.cost)}</td>
      <td class="text-end fw-bold">${formatMoney(r.expect)}</td>
    </tr>`
  ).join('');
  document.getElementById('pl-detail-body').innerHTML = `
    <table class="table table-vcenter table-sm">
      <thead><tr>
        <th style="width:90px">Дата</th><th>Клиент</th><th>Услуга</th>
        <th class="text-end">Полная</th><th class="text-end">65%</th>
      </tr></thead>
      <tbody>${rows}</tbody>
      <tfoot><tr class="fw-bold">
        <td colspan="3" class="text-end">Итого ожидается:</td>
        <td class="text-end">${formatMoney(data.total_cost)}</td>
        <td class="text-end">${formatMoney(data.total_expect)}</td>
      </tr></tfoot>
    </table>`;
}

// Клик на «Получено» — список банковских платежей за месяц
async function showFitmostPayments(month) {
  const modalEl = document.getElementById('pl-detail-modal');
  if (!modalEl) return;
  document.getElementById('pl-detail-title').textContent = `Fitmost платежи из банка — ${month}`;
  document.getElementById('pl-detail-body').innerHTML = '<div class="text-center text-muted py-3">Загрузка...</div>';
  modalEl.style.display = 'flex';

  const data = await fetchData(`/analytics/fitmost-payments?month=${month}`);
  if (!data || data.error) {
    document.getElementById('pl-detail-body').innerHTML = '<div class="text-danger py-3">Ошибка загрузки</div>';
    return;
  }
  if (!data.rows || !data.rows.length) {
    document.getElementById('pl-detail-body').innerHTML = '<div class="text-muted py-3 text-center">Платежей за этот месяц нет</div>';
    return;
  }
  const rows = data.rows.map(r =>
    `<tr>
      <td class="small text-muted" style="white-space:nowrap">${r.date}</td>
      <td class="small">${r.description || r.counterparty}</td>
      <td class="text-end fw-bold">${formatMoney(r.amount)}</td>
    </tr>`
  ).join('');
  document.getElementById('pl-detail-body').innerHTML = `
    <table class="table table-vcenter table-sm">
      <thead><tr>
        <th style="width:90px">Дата</th><th>Описание</th><th class="text-end">Сумма</th>
      </tr></thead>
      <tbody>${rows}</tbody>
      <tfoot><tr class="fw-bold">
        <td colspan="2" class="text-end">Итого получено:</td>
        <td class="text-end">${formatMoney(data.total)}</td>
      </tr></tfoot>
    </table>`;
}