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

  // Обновляем заголовок таблицы
  const title = document.getElementById('pl-table-title');
  if (title && data.project_label) title.textContent = `P&L — ${data.project_label}`;

  // Для не-салонных проектов показываем другой бейдж
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

  // Выручка
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

  // Расходы
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

  // EBITDA
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

  // Лучший месяц по выручке
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

    // Для не-салонных проектов revenue_other вместо разбивки
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
      // Для других проектов — упрощённая строка: Доходы | Расходы | EBITDA
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
