// ============ ПУЛЬС СИСТЕМЫ ============

async function loadKPI() {
  const [summary, revenue, clients] = await Promise.all([
    fetchData('/analytics/summary'),
    fetchData('/analytics/revenue?weeks=12'),
    fetchData('/analytics/clients?weeks=12')
  ]);

  if (summary) {
    document.getElementById('kpi-revenue').textContent      = formatK(summary.current_month_revenue);
    document.getElementById('kpi-prev-revenue').textContent = formatK(summary.prev_month_revenue);
    document.getElementById('kpi-visits').textContent       = summary.current_month_visits;
    document.getElementById('kpi-prev-visits').textContent  = summary.prev_month_visits;

    const vGrowth = summary.visits_growth;
    const vClass  = vGrowth >= 0 ? 'text-green' : 'text-red';
    document.getElementById('kpi-visits-trend').innerHTML =
      `<span class="${vClass} small fw-bold">${vGrowth >= 0 ? '+' : ''}${vGrowth}%</span>`;

    document.getElementById('kpi-clients').textContent      = summary.unique_clients;
    document.getElementById('kpi-prev-clients').textContent = summary.prev_unique_clients;
    const cGrowth = summary.clients_growth;
    const cClass  = cGrowth >= 0 ? 'text-green' : 'text-red';
    document.getElementById('kpi-clients-trend').innerHTML =
      `<span class="${cClass} small fw-bold">${cGrowth >= 0 ? '+' : ''}${cGrowth}%</span>`;

    const growth      = summary.revenue_growth;
    const growthClass = growth >= 0 ? 'text-green' : 'text-red';
    const growthSign  = growth >= 0 ? '+' : '';
    document.getElementById('kpi-revenue-trend').innerHTML =
      `<span class="${growthClass} small fw-bold">${growthSign}${growth}%</span>`;
  }

  if (revenue && revenue.labels) {
    new ApexCharts(document.getElementById('revenue-chart'), {
      series: [{ name: 'Выручка', data: revenue.revenue }],
      chart:  { type: 'area', height: 160, toolbar: { show: false }, sparkline: { enabled: false } },
      labels: revenue.labels.map(d => new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })),
      colors: ['#206bc4'],
      fill:   { opacity: 0.1 },
      stroke: { width: 2 },
      xaxis:  { labels: { rotate: -45, style: { fontSize: '10px' } } },
      yaxis:  { labels: { formatter: v => formatK(v) } },
      tooltip: { y: { formatter: v => formatK(v) } }
    }).render();

    // Таблица недель — кликабельная
    const weeksBody = document.getElementById('revenue-weeks-body');
    const weeks  = [...revenue.labels].reverse();
    const amounts = [...revenue.revenue].reverse();

    weeksBody.innerHTML = weeks.map((label, i) => {
      const amount    = amounts[i];
      const prevAmount = amounts[i + 1];
      const diff      = prevAmount ? amount - prevAmount : null;
      const diffPct   = prevAmount ? Math.round(diff / prevAmount * 100) : null;
      const diffClass = diff >= 0 ? 'text-green' : 'text-red';
      const diffStr   = diff !== null
        ? `<span class="${diffClass}">${diff >= 0 ? '+' : ''}${diffPct}%</span>`
        : '<span class="text-muted">—</span>';

      const labelDate  = new Date(label);
      const nextDate   = new Date(labelDate);
      nextDate.setDate(nextDate.getDate() + 7);
      const fmt        = d => d.toISOString().split('T')[0];
      const weekLabel  = labelDate.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
      const weekEnd    = new Date(nextDate);
      weekEnd.setDate(weekEnd.getDate() - 1);
      const weekEndLabel = weekEnd.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });

      return `<tr style="cursor:pointer" onclick="showDetail('${fmt(labelDate)}','${fmt(nextDate)}','Неделя ${weekLabel} — ${weekEndLabel}')">
        <td><span class="fw-bold">${weekLabel}</span> <span class="text-muted small">— ${weekEndLabel}</span></td>
        <td class="text-end fw-bold">${formatMoney(amount)}</td>
        <td class="text-end">${diffStr}</td>
        <td class="text-center"><span class="badge bg-blue-lt">→ детали</span></td>
      </tr>`;
    }).join('');
  }

  if (clients && clients.labels) {
    new ApexCharts(document.getElementById('clients-chart'), {
      series: [
        { name: 'Новые',     data: clients.new },
        { name: 'Повторные', data: clients.returning }
      ],
      chart:  { type: 'bar', height: 200, toolbar: { show: false }, stacked: true },
      labels: clients.labels.map(d => new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })),
      colors: ['#206bc4', '#2fb344'],
      xaxis:  { labels: { rotate: -45, style: { fontSize: '10px' } } },
      legend: { position: 'top' }
    }).render();
  }
}

async function loadPulse() {
  await loadKPI();
  const [summary, churn, obligations] = await Promise.all([
    fetchData('/analytics/summary'),
    fetchData('/analytics/churn?days=45'),
    fetchData(`/analytics/obligations/${YEAR}/${MONTH}`)
  ]);

  if (summary) {
    document.getElementById('rev-month').textContent = formatK(summary.current_month_revenue);
  }

  if (obligations) {
    const salon   = obligations.summary.salon;
    const revenue = summary?.current_month_revenue || 0;
    document.getElementById('obl-month').textContent = formatK(salon);

    const pct = Math.min(revenue / salon * 100, 100);
    document.getElementById('obl-bar').style.width = pct + '%';
    document.getElementById('obl-bar').className =
      'obligation-fill ' + (pct >= 100 ? 'bg-green' : pct >= 70 ? 'bg-yellow' : 'bg-red');

    const diff = revenue - salon;
    document.getElementById('obl-comment').textContent =
      diff >= 0
        ? `✅ Доход покрывает обязательства. Остаток: ${formatK(diff)}`
        : `⚠️ Не хватает: ${formatK(Math.abs(diff))}`;

    // Ближайшие платежи
    const today    = TODAY.getDate();
    const upcoming = obligations.obligations
      .filter(o => o.day_of_month && o.day_of_month >= today && o.type !== 'debt')
      .sort((a, b) => a.day_of_month - b.day_of_month)
      .slice(0, 4);

    document.getElementById('obl-list').innerHTML = upcoming.map(o => `
      <div class="d-flex align-items-center mb-2">
        <span class="badge bg-blue-lt me-2">${o.day_of_month}</span>
        <span class="flex-grow-1 text-truncate small">${o.description}</span>
        <span class="ms-2 fw-bold small">${formatK(o.amount)}</span>
      </div>
    `).join('');
  }

  await loadNorthStar();
  await loadHeatmap();
  await loadUtilization();
}

async function loadNorthStar() {
  const data = await fetchData('/analytics/cmph');
  if (!data || data.error) return;

  document.getElementById('ns-cmph').textContent = formatMoney(data.cmph);
  const trend = data.cmph > 3000 ? '🟢 Отлично' : data.cmph > 1500 ? '🟡 Норма' : '🔴 Низко';
  document.getElementById('ns-trend').textContent  = trend;
  document.getElementById('ns-detail').textContent = data.labor_hours + 'ч · CM ' + formatK(data.cm);
}

async function loadHeatmap() {
  const container = document.getElementById('heatmap-container');

  const days = [];
  for (let i = 27; i >= 0; i--) {
    const d = new Date(TODAY);
    d.setDate(d.getDate() - i);
    days.push(d);
  }

  const weeks    = [];
  for (let w = 0; w < 4; w++) {
    weeks.push(days.slice(w * 7, w * 7 + 7));
  }

  const dayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

  container.innerHTML = weeks.map((week, wi) => `
    <div>
      <div class="text-muted small mb-1 text-center">Нед ${wi + 1}</div>
      <div class="d-flex gap-1 flex-column">
        ${week.map((day, di) => {
          const util      = Math.random() * 100; // TODO: заменить реальными данными
          const heatClass = util === 0  ? 'heat-0' :
                            util < 25   ? 'heat-1' :
                            util < 50   ? 'heat-2' :
                            util < 75   ? 'heat-3' :
                            util < 90   ? 'heat-4' : 'heat-5';
          return `<div class="heatmap-cell ${heatClass}" title="${day.toLocaleDateString('ru')} — ${Math.round(util)}%">
            ${dayNames[di]}
          </div>`;
        }).join('')}
      </div>
    </div>
  `).join('');
}

async function loadUtilization() {
  // Заглушка — заменим на реальные данные после добавления расписания
  document.getElementById('util-rate').textContent = '68%';

  new ApexCharts(document.getElementById('util-chart'), {
    series: [68],
    chart:  { type: 'radialBar', height: 80, width: 80, sparkline: { enabled: true } },
    plotOptions: { radialBar: {
      hollow:      { size: '50%' },
      dataLabels:  { show: false }
    }},
    colors: ['#206bc4'],
  }).render();
}
