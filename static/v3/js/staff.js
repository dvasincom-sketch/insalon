// ============ СОТРУДНИКИ ============

async function loadStaff() {
  const daily = await fetchData('/analytics/staff/daily?days=30');
  if (!daily || !daily.days) return;

  const byStaff = {};
  daily.days.forEach(d => {
    if (!byStaff[d.staff]) byStaff[d.staff] = { shifts: 0, revenue: 0, profitable: 0, unprofitable: 0 };
    byStaff[d.staff].shifts++;
    byStaff[d.staff].revenue += d.revenue;
    if (d.is_profitable) byStaff[d.staff].profitable++;
    else byStaff[d.staff].unprofitable++;
  });

  const staffSummary = Object.entries(byStaff).map(([name, s]) => ({
    name,
    shifts:        s.shifts,
    revenue:       s.revenue,
    avg_revenue:   Math.round(s.revenue / s.shifts),
    coefficient:   Math.round(s.revenue / s.shifts / 5000 * 10) / 10,
    profitable:    s.profitable,
    unprofitable:  s.unprofitable
  })).sort((a, b) => b.revenue - a.revenue);

  const totalShifts     = daily.days.length;
  const profitableShifts = daily.days.filter(d => d.is_profitable).length;
  const totalRevenue    = daily.days.reduce((s, d) => s + d.revenue, 0);
  const avgRevenue      = Math.round(totalRevenue / totalShifts);
  const avgCoef         = Math.round(totalRevenue / totalShifts / 5000 * 10) / 10;
  const salaryPct       = Math.round(5000 / avgRevenue * 100);
  const profitablePct   = Math.round(profitableShifts / totalShifts * 100);

  document.getElementById('staff-cards').innerHTML = `
    <div class="col-12">
      <div class="row row-deck row-cards mb-3">
        <div class="col-md-3">
          <div class="card">
            <div class="card-body text-center">
              <div class="text-muted mb-1">Средний коэффициент</div>
              <div class="display-6 fw-bold ${avgCoef >= 4 ? 'text-green' : avgCoef >= 2 ? 'text-blue' : 'text-red'}">${avgCoef}x</div>
              <div class="text-muted small">норма ≥ 2x</div>
            </div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card">
            <div class="card-body text-center">
              <div class="text-muted mb-1">ЗП от выручки</div>
              <div class="display-6 fw-bold ${salaryPct <= 35 ? 'text-green' : salaryPct <= 50 ? 'text-yellow' : 'text-red'}">${salaryPct}%</div>
              <div class="text-muted small">норма 25-35%</div>
            </div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card">
            <div class="card-body text-center">
              <div class="text-muted mb-1">Прибыльных смен</div>
              <div class="display-6 fw-bold ${profitablePct >= 70 ? 'text-green' : profitablePct >= 50 ? 'text-yellow' : 'text-red'}">${profitablePct}%</div>
              <div class="text-muted small">${profitableShifts} из ${totalShifts}</div>
            </div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card">
            <div class="card-body text-center">
              <div class="text-muted mb-1">Ср. выручка/смена</div>
              <div class="display-6 fw-bold">${formatK(avgRevenue)}</div>
              <div class="text-muted small">при ЗП 5 000 ₽</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="col-12">
      <div class="card mb-3">
        <div class="card-header">
          <h3 class="card-title">Эффективность мастеров — последние 30 дней</h3>
        </div>
        <div class="table-responsive">
          <table class="table table-vcenter card-table">
            <thead>
              <tr>
                <th>Мастер</th>
                <th class="text-center">Смен</th>
                <th class="text-end">Выручка</th>
                <th class="text-end">Ср./смена</th>
                <th class="text-center">Коэфф.</th>
                <th class="text-center">✅ Прибыльных</th>
                <th class="text-center">❌ Убыточных</th>
              </tr>
            </thead>
            <tbody>
              ${staffSummary.map(s => `
              <tr>
                <td class="fw-bold">${s.name}</td>
                <td class="text-center">${s.shifts}</td>
                <td class="text-end">${formatMoney(s.revenue)}</td>
                <td class="text-end">${formatMoney(s.avg_revenue)}</td>
                <td class="text-center">
                  <span class="badge ${s.coefficient >= 4 ? 'bg-green' : s.coefficient >= 2 ? 'bg-yellow' : 'bg-red'}">${s.coefficient}x</span>
                </td>
                <td class="text-center text-green fw-bold">${s.profitable}</td>
                <td class="text-center text-red fw-bold">${s.unprofitable}</td>
              </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    <div class="col-12">
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Детализация по дням</h3>
          <div class="card-options">
            <span class="badge bg-green-lt">≥2x прибыльно</span>
            <span class="badge bg-red-lt ms-1">&lt;2x убыточно</span>
          </div>
        </div>
        <div class="table-responsive">
          <table class="table table-vcenter table-sm card-table">
            <thead>
              <tr>
                <th>День</th>
                <th>Мастер</th>
                <th class="text-center">Записей</th>
                <th class="text-center">Часов</th>
                <th class="text-end">Выручка</th>
                <th class="text-end text-purple">+ Або.</th>
                <th class="text-end fw-bold">Итого</th>
                <th class="text-end">Смена</th>
                <th class="text-center">Коэфф.</th>
                <th class="text-end">% ЗП</th>
              </tr>
            </thead>
            <tbody>
              ${daily.days.map(d => {
                const rowClass  = d.revenue === 0 && d.abonement_revenue === 0 ? 'table-secondary' : !d.is_profitable ? 'table-danger' : '';
                const coefClass = d.coefficient >= 4 ? 'text-green fw-bold' : d.coefficient >= 2 ? 'text-blue' : 'text-red fw-bold';
                return `<tr class="${rowClass}">
                  <td>${new Date(d.day).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', weekday: 'short' })}</td>
                  <td class="fw-bold">${d.staff}</td>
                  <td class="text-center">
                    ${d.records}
                    ${d.zero_cost_records > 0 ? '<span class="badge bg-purple-lt ms-1">+' + d.zero_cost_records + ' або.</span>' : ''}
                  </td>
                  <td class="text-center text-muted">${d.duration_hours > 0 ? d.duration_hours + 'ч' : '—'}</td>
                  <td class="text-end">${d.revenue > 0 ? formatMoney(d.revenue) : '<span class="text-muted">—</span>'}</td>
                  <td class="text-end text-purple">${d.abonement_revenue > 0 ? '+' + formatK(d.abonement_revenue) : '—'}</td>
                  <td class="text-end fw-bold">${formatMoney(d.total_revenue)}</td>
                  <td class="text-end">${formatMoney(d.shift_pay)}</td>
                  <td class="text-center"><span class="${coefClass}">${d.coefficient}x</span></td>
                  <td class="text-end ${d.salary_pct > 50 ? 'text-red' : 'text-muted'}">${d.salary_pct > 0 ? d.salary_pct + '%' : '—'}</td>
                </tr>`;
              }).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>`;
}
