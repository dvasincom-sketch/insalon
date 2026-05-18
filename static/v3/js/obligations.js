// ============ ОБЯЗАТЕЛЬСТВА ============

async function loadObligations() {
  const [summaryData, oblData, paymentsData] = await Promise.all([
    fetchData('/obligations/summary'),
    fetchData('/obligations'),
    fetchData(`/obligations/payments?year=${YEAR}&month=${MONTH}`)
  ]);

  if (!oblData) return;

  const summary   = summaryData || {};
  const payments  = paymentsData?.payments || [];
  const paidIds   = new Set((summary.paid_ids || []).map(Number));
  const paidAmts  = summary.paid_amounts || {};

  const today = TODAY.getDate();

  // ── Сводка ──────────────────────────────────────────────────
  const overdueAmt  = (summary.overdue || []).reduce((s, o) => s + o.amount, 0);
  const weekAmt     = (summary.upcoming_week || []).reduce((s, o) => s + o.amount, 0);
  const totalDebt   = summary.total_debt || 0;

  // Получаем фактическую выручку за текущий месяц
  const plData = await fetchData(`/analytics/pl?project=salon`);
  const currentMonthPL = (plData?.months || []).find(m => m.month === `${YEAR}-${String(MONTH).padStart(2,'0')}`);
  const actualRevenue  = currentMonthPL?.total_revenue || 0;

  // Структура обязательств по категориям
  const oblList  = oblData?.obligations || [];
  const bizCats     = ['salary','rent','marketing','materials','cosmetics','training'];
  const creditCats  = ['credit','credit_card','investor'];

  // Для ЗП используем динамические данные из ФОТ
  const fotSalary   = summary.fot_salary || 0;
  const nonSalaryBiz = oblList.filter(o =>
    bizCats.includes(o.expense_category) &&
    o.expense_category !== 'salary' &&
    o.project === 'salon'
  ).reduce((s,o) => s + parseFloat(o.amount), 0);
  const bizTotal    = nonSalaryBiz + fotSalary;

  const creditTotal   = oblList.filter(o => creditCats.includes(o.expense_category)).reduce((s,o) => s + parseFloat(o.amount), 0);
  const personalTotal = oblList.filter(o => o.project === 'personal').reduce((s,o) => s + parseFloat(o.amount), 0);

  // Для plan: фиксированные + динамическая ЗП вместо статической
  const nonSalaryMonthly = oblList.filter(o =>
    o.day_of_month && o.expense_category !== 'salary'
  ).reduce((s,o) => s + parseFloat(o.amount), 0);
  const totalMonthly = nonSalaryMonthly + fotSalary;
  const deficit      = totalMonthly - actualRevenue;

  // Рендерим карточки
  const cardsEl = document.getElementById('obl-cards');
  if (cardsEl) {
    cardsEl.innerHTML = `
      <div class="col-12 mb-2">
        <div class="row g-2">
          <div class="col-md-4">
            <div class="card">
              <div class="card-body">
                <div class="text-muted small mb-1">Нужная выручка / месяц</div>
                <div class="h2 fw-bold mb-1">${formatMoney(totalMonthly)}</div>
                <div class="d-flex justify-content-between small">
                  <span class="text-muted">Факт: <strong>${formatMoney(actualRevenue)}</strong></span>
                  <span class="${deficit > 0 ? 'text-danger' : 'text-success'} fw-bold">
                    ${deficit > 0 ? '−' : '+'}${formatMoney(Math.abs(deficit))}
                  </span>
                </div>
                <div class="progress mt-2" style="height:4px">
                  <div class="progress-bar ${actualRevenue >= totalMonthly ? 'bg-success' : 'bg-warning'}"
                    style="width:${Math.min(100, Math.round(actualRevenue/totalMonthly*100))}%"></div>
                </div>
                <div class="text-muted small mt-1">${Math.round(actualRevenue/totalMonthly*100)}% выполнено</div>
              </div>
            </div>
          </div>
          <div class="col-md-4">
            <div class="card">
              <div class="card-body">
                <div class="text-muted small mb-1">Бизнес-расходы</div>
                <div class="h2 fw-bold mb-1">${formatMoney(bizTotal)}</div>
                <div class="text-muted small">ЗП (факт ФОТ) · аренда · маркетинг</div>
                <div class="text-muted small mt-1">ЗП: ${formatMoney(fotSalary)} · прочее: ${formatMoney(nonSalaryBiz)}</div>
              </div>
            </div>
          </div>
          <div class="col-md-4">
            <div class="card">
              <div class="card-body">
                <div class="text-muted small mb-1">Кредитная нагрузка</div>
                <div class="h2 fw-bold text-danger mb-1">${formatMoney(creditTotal)}</div>
                <div class="text-muted small">Бизнес: ${formatMoney(oblList.filter(o=>creditCats.includes(o.expense_category)&&o.project==='salon').reduce((s,o)=>s+parseFloat(o.amount),0))}</div>
                <div class="text-muted small mt-1">Личные кредиты: ${formatMoney(oblList.filter(o=>creditCats.includes(o.expense_category)&&o.project==='personal').reduce((s,o)=>s+parseFloat(o.amount),0))}</div>
              </div>
            </div>
          </div>
        </div>
      </div>`;
  }

  document.getElementById('obl-fixed').textContent    = formatMoney(summary.total_fixed || 0);
  document.getElementById('obl-variable').textContent = formatMoney(summary.total_variable || 0);
  document.getElementById('obl-debts').textContent    = formatMoney(totalDebt);

  // Алерты
  const alertsEl = document.getElementById('obl-alerts');
  if (alertsEl) {
    let alertsHtml = '';
    if (overdueAmt > 0) {
      alertsHtml += `
        <div class="col-12 col-md-6">
          <div class="card border-danger" style="border-left:4px solid #d63939">
            <div class="card-body py-2">
              <div class="d-flex align-items-center gap-2 mb-1">
                <span class="text-danger fw-bold">🔴 Просрочено — ${formatMoney(overdueAmt)}</span>
              </div>
              <div class="text-muted small">${(summary.overdue || []).map(o =>
                `<div>· ${o.description} <span class="text-danger fw-bold">${formatMoney(o.amount)}</span></div>`
              ).join('')}</div>
            </div>
          </div>
        </div>`;
    }
    if (weekAmt > 0) {
      alertsHtml += `
        <div class="col-12 col-md-6">
          <div class="card border-warning" style="border-left:4px solid #f76707">
            <div class="card-body py-2">
              <div class="d-flex align-items-center gap-2 mb-1">
                <span class="text-warning fw-bold">⚡ На этой неделе — ${formatMoney(weekAmt)}</span>
              </div>
              <div class="text-muted small">${(summary.upcoming_week || []).map(o =>
                `<div>· ${o.description} (${o.day}) <span class="fw-bold">${formatMoney(o.amount)}</span></div>`
              ).join('')}</div>
            </div>
          </div>
        </div>`;
    }
    alertsHtml = alertsHtml ? `<div class="row g-2">${alertsHtml}</div>` : '';
    alertsEl.innerHTML = alertsHtml;
  }

  // ── Таблица ──────────────────────────────────────────────────
  const obligations = oblData.obligations || [];

  const rows = obligations
    .sort((a, b) => {
      // Обязательства 1-го числа (выплата след. месяца) — в конец периодических
      const dayA = (a.day_of_month === 1) ? 32 : (a.day_of_month || 99);
      const dayB = (b.day_of_month === 1) ? 32 : (b.day_of_month || 99);
      return dayA - dayB;
    })
    .map(o => {
      const isPaid   = paidIds.has(o.id);
      const paidAmt  = paidAmts[o.id] || 0;
      const isPast   = o.day_of_month && o.day_of_month < today;
      const isToday  = o.day_of_month === today;
      const isDebt   = o.type === 'one_time_debt';

      // Динамическая сумма для ЗП
      let displayAmount = parseFloat(o.amount);
      let dynamicNote   = '';
      if (o.expense_category === 'salary' && o.day_of_month) {
        if (o.day_of_month <= 5) {
          // 1-го: выплата за 15-31 текущего месяца (будущая)
          const amt = summary.fot_second_half_total || 0;
          if (amt > 0) { displayAmount = amt; dynamicNote = `<div class="text-blue small">ФОТ 15–31 (план): ${formatMoney(amt)}</div>`; }
        } else if (o.day_of_month >= 14 && o.day_of_month <= 16) {
          // 15-го: выплата за 1-14 текущего месяца
          const amt = summary.fot_first_half_total || 0;
          if (amt > 0) { displayAmount = amt; dynamicNote = `<div class="text-muted small">ФОТ 1–14: ${formatMoney(amt)}</div>`; }
        }
      }

      const statusBadge = isPaid
        ? `<span class="badge bg-green text-white">✓ Оплачен ${paidAmt !== o.amount ? formatMoney(paidAmt) : ''}</span>`
        : isDebt
          ? '<span class="badge bg-red-lt">Долг</span>'
          : isPast
            ? '<span class="badge bg-orange-lt">⚠ Просрочен</span>'
            : isToday
              ? '<span class="badge bg-red text-white">Сегодня!</span>'
              : '<span class="badge bg-blue-lt">Ожидается</span>';

      const projectBadge = o.project === 'salon'
        ? '<span class="badge bg-blue-lt">Салон</span>'
        : o.project === 'personal'
          ? '<span class="badge bg-gray-lt">Личное</span>'
          : `<span class="badge bg-purple-lt">${o.project}</span>`;

      const actionBtn = isPaid
        ? `<button class="btn btn-sm btn-outline-danger" onclick="cancelPayment(${o.id})">↩</button>`
        : `<button class="btn btn-sm btn-outline-success" onclick="openPayModal(${o.id}, '${o.description.replace(/'/g, "\\'")}', ${o.amount})">Оплатить</button>`;

      const rowClass = isPaid ? 'table-success' : isToday ? 'table-danger' : isPast && !isDebt ? 'table-warning' : '';

      return `<tr class="${rowClass}">
        <td>${o.day_of_month ? `<span class="fw-bold">${o.day_of_month}</span>` : '<span class="text-muted">разово</span>'}</td>
        <td>${o.description}${o.notes ? `<div class="text-muted small">${o.notes}</div>` : ''}</td>
        <td>${projectBadge}</td>
        <td><span class="text-muted small">${o.expense_category || ''}</span></td>
        <td class="text-end fw-bold">${formatMoney(displayAmount)}${dynamicNote}</td>
        <td>${statusBadge}</td>
        <td class="text-end">
          <div class="d-flex gap-1 justify-content-end">
            ${actionBtn}
            <button class="btn btn-sm btn-outline-secondary" onclick="openEditModal(${o.id})">✏️</button>
          </div>
        </td>
      </tr>`;
    }).join('');

  document.getElementById('obl-tbody').innerHTML = rows || '<tr><td colspan="7" class="text-center text-muted py-4">Нет обязательств</td></tr>';
}

// ── Модалка оплаты ───────────────────────────────────────────
let _payOblId = null;

function openPayModal(oblId, desc, amount) {
  _payOblId = oblId;
  document.getElementById('pay-modal-title').textContent = desc;
  document.getElementById('pay-modal-amount').value = amount;
  document.getElementById('pay-modal-date').value = TODAY.toISOString().slice(0, 10);
  document.getElementById('pay-modal-notes').value = '';
  showOblModal('obl-pay-modal');
}

async function submitPayment() {
  const amount = parseFloat(document.getElementById('pay-modal-amount').value);
  const date   = document.getElementById('pay-modal-date').value;
  const notes  = document.getElementById('pay-modal-notes').value;
  if (!amount || !date) return;

  await fetch(`${API}/obligations/pay`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ obligation_id: _payOblId, amount, payment_date: date, notes })
  });
  closeOblModal('obl-pay-modal');
  loadObligations();
  showToastObl('Оплата зафиксирована ✓');
}

async function cancelPayment(oblId) {
  // Находим последний платёж за этот месяц
  const data = await fetchData(`/obligations/payments?year=${YEAR}&month=${MONTH}`);
  const payment = (data?.payments || []).find(p => p.obligation_id === oblId);
  if (!payment) return;
  await fetch(`${API}/obligations/payments/${payment.id}`, { method: 'DELETE' });
  loadObligations();
  showToastObl('Оплата отменена');
}

// ── Модалка добавления/редактирования ────────────────────────
let _editOblId = null;

function openAddModal() {
  _editOblId = null;
  document.getElementById('obl-modal-title').textContent = 'Новое обязательство';
  document.getElementById('obl-f-desc').value = '';
  document.getElementById('obl-f-amount').value = '';
  document.getElementById('obl-f-day').value = '';
  document.getElementById('obl-f-type').value = 'fixed';
  document.getElementById('obl-f-project').value = 'salon';
  document.getElementById('obl-f-category').value = '';
  document.getElementById('obl-f-notes').value = '';
  showOblModal('obl-edit-modal');
}

async function openEditModal(oblId) {
  const data = await fetchData('/obligations');
  const o = (data?.obligations || []).find(x => x.id === oblId);
  if (!o) return;
  _editOblId = oblId;
  document.getElementById('obl-modal-title').textContent = 'Редактировать';
  document.getElementById('obl-f-desc').value     = o.description || '';
  document.getElementById('obl-f-amount').value   = o.amount || '';
  document.getElementById('obl-f-day').value      = o.day_of_month || '';
  document.getElementById('obl-f-type').value     = o.type || 'fixed';
  document.getElementById('obl-f-project').value  = o.project || 'salon';
  document.getElementById('obl-f-category').value = o.expense_category || '';
  document.getElementById('obl-f-notes').value    = o.notes || '';
  showOblModal('obl-edit-modal');
}

async function submitObligation() {
  const payload = {
    description:      document.getElementById('obl-f-desc').value.trim(),
    amount:           parseFloat(document.getElementById('obl-f-amount').value),
    day_of_month:     parseInt(document.getElementById('obl-f-day').value) || null,
    type:             document.getElementById('obl-f-type').value,
    project:          document.getElementById('obl-f-project').value,
    expense_category: document.getElementById('obl-f-category').value,
    notes:            document.getElementById('obl-f-notes').value,
  };
  if (!payload.description || !payload.amount) return;

  const method = _editOblId ? 'PUT' : 'POST';
  const url    = _editOblId ? `${API}/obligations/${_editOblId}` : `${API}/obligations`;
  await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  closeOblModal('obl-edit-modal');
  loadObligations();
  showToastObl(_editOblId ? 'Обновлено ✓' : 'Добавлено ✓');
}

async function deleteObligation(oblId) {
  if (!confirm('Удалить обязательство?')) return;
  await fetch(`${API}/obligations/${oblId}`, { method: 'DELETE' });
  loadObligations();
  showToastObl('Удалено');
}

// ── Утилиты ──────────────────────────────────────────────────
function showOblModal(id) {
  const el = document.getElementById(id);
  el.style.display = 'flex';
  el.style.position = 'fixed';
  el.style.top = '0'; el.style.left = '0';
  el.style.width = '100%'; el.style.height = '100%';
  el.style.zIndex = '1060';
  el.style.background = 'rgba(0,0,0,0.45)';
  el.style.alignItems = 'center';
  el.style.justifyContent = 'center';
}

function closeOblModal(id) {
  document.getElementById(id).style.display = 'none';
}

function showToastObl(msg) {
  const t = document.createElement('div');
  t.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;background:#2fb344;color:#fff;padding:12px 20px;border-radius:8px;font-size:14px;box-shadow:0 4px 12px rgba(0,0,0,0.15)';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}
