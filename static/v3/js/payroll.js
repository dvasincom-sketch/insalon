// ============ ВЕДОМОСТЬ ОПЛАТЫ ТРУДА ============

async function applyPayrollFilter() {
  await loadPayroll();
}

function validatePayrollNotes(p) {
  const notes    = p.notes || '';
  const warnings = [];
  const periodStart = new Date(p.period_start);

  const dateRegex = /(\d{2})\.(\d{2})=\d+/g;
  let m;
  while ((m = dateRegex.exec(notes)) !== null) {
    const day   = parseInt(m[1]);
    const month = parseInt(m[2]) - 1;
    const year  = periodStart.getFullYear();
    const d     = new Date(year, month, day);
    if (d.getMonth() !== month) {
      warnings.push('⚠ ' + m[1] + '.' + (month + 1).toString().padStart(2, '0') + ' не существует');
    }
  }

  const shiftMatch = notes.match(/Смены?:\s*([\d,\s]+)/);
  if (shiftMatch) {
    const days = shiftMatch[1].split(',').map(d => parseInt(d.trim())).filter(Boolean);
    days.forEach(day => {
      const d = new Date(periodStart.getFullYear(), periodStart.getMonth(), day);
      if (d.getMonth() !== periodStart.getMonth()) {
        warnings.push('⚠ смена ' + day + ' числа не существует');
      }
    });
  }

  if (warnings.length === 0) return '';
  return '<div class="mt-1">' + warnings.map(w =>
    '<span class="badge bg-red-lt d-block mb-1" style="white-space:normal">' + w + '</span>'
  ).join('') + '</div>';
}

function initPayrollMonthFilter() {
  const sel = document.getElementById('payroll-filter-month');
  if (!sel || sel.options.length > 1) return;
  sel.innerHTML = '<option value="">Все месяцы</option>';
  const now = new Date();
  const months = [
    'Январь','Февраль','Март','Апрель','Май','Июнь',
    'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'
  ];
  for (let i = 0; i < 7; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const val = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
    const label = months[d.getMonth()] + ' ' + d.getFullYear();
    sel.appendChild(new Option(label, val));
  }
}

async function loadPayroll() {
  initPayrollMonthFilter();
  const staff   = document.getElementById('payroll-filter-staff')?.value  || '';
  const monthVal = document.getElementById('payroll-filter-month')?.value || '';
  const period  = document.getElementById('payroll-filter-period')?.value || '';
  const data    = await fetchData('/analytics/payroll?months=6');
  if (!data || !data.payroll) return;

  let filtered = data.payroll;
  if (staff)    filtered = filtered.filter(p => p.staff_name === staff);
  if (monthVal) filtered = filtered.filter(p => p.period_start.startsWith(monthVal));
  if (period === '1') filtered = filtered.filter(p => parseInt(p.period_start.split('-')[2]) <= 14);
  if (period === '2') filtered = filtered.filter(p => parseInt(p.period_start.split('-')[2]) >= 15);

  const labels = [];
  if (staff)          labels.push(staff);
  if (monthVal)       labels.push(monthVal);
  if (period === '1') labels.push('1–14');
  if (period === '2') labels.push('15–31');

  const lbl = document.getElementById('payroll-filter-label');
  if (lbl) lbl.textContent = labels.join(' · ') || 'Все записи';

  const summary = document.getElementById('payroll-summary');
  if (filtered.length > 0) {
    const totalAccrued = filtered.reduce((s, p) => s + (p.total_accrued || 0), 0);
    const totalVisit   = filtered.reduce((s, p) => s + (p.visit_pay || 0), 0);
    const totalBonus   = filtered.reduce((s, p) => s + (p.bonus_loyalty || 0), 0);
    const totalPaid    = filtered.reduce((s, p) => s + (p.total_paid || 0), 0);
    const totalBalance = filtered.reduce((s, p) => s + (p.balance || 0) + (p.offset_amount || 0), 0);

    document.getElementById('ps-accrued').textContent = formatMoney(totalAccrued);
    document.getElementById('ps-visit').textContent   = totalVisit > 0 ? formatMoney(totalVisit) : '—';
    document.getElementById('ps-bonus').textContent   = totalBonus > 0 ? formatMoney(totalBonus) : '—';
    document.getElementById('ps-paid').textContent    = formatMoney(totalPaid);

    const balEl = document.getElementById('ps-balance');
    balEl.textContent = formatMoney(totalBalance);
    balEl.className   = 'fw-bold ' + (totalBalance > 0 ? 'text-red' : totalBalance < 0 ? 'text-orange' : 'text-green');
    summary.style.display = '';
  } else {
    summary.style.display = 'none';
  }

  const totalBalance = filtered.reduce((s, p) => s + (p.balance || 0) + (p.offset_amount || 0), 0);

  document.getElementById('payroll-tbody').innerHTML = filtered.map(p => {
    const periodStart = new Date(p.period_start).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
    const periodEnd   = new Date(p.period_end).toLocaleDateString('ru-RU',   { day: 'numeric', month: 'short' });
    const balanceClass = p.balance > 0 ? 'text-red fw-bold' : p.balance < 0 ? 'text-orange fw-bold' : 'text-green';

    return `<tr>
      <td class="text-muted small">${periodStart} — ${periodEnd}</td>
      <td class="fw-bold">${p.staff_name}</td>
      <td class="text-center">${p.shifts}</td>
      <td class="text-muted small">${(() => {
        const m = (p.notes || '').match(/Смены?:\s*([\d,\s]+)/);
        return m ? m[1].trim() : '—';
      })()}</td>
      <td class="text-muted small">${(() => {
        const notes = p.notes || '';
        const days  = [];
        const visitBlock = notes.match(/Выходы?[^:]*:(.*?)(?:\.\s+[А-ЯЁ]|$)/);
        if (visitBlock) {
          const re = /(\d{2})\.(\d{2})=\d+/g;
          let m;
          while ((m = re.exec(visitBlock[1])) !== null) {
            days.push(parseInt(m[1]) + '.' + m[2]);
          }
        }
        return days.length > 0 ? days.join(', ') : '—';
      })()}</td>
      <td class="text-end">${formatMoney(p.total_accrued)}</td>
      <td class="text-end text-muted">${p.advance_cash > 0 ? formatMoney(p.advance_cash) : '—'}</td>
      <td class="text-end text-muted">${p.bonus_loyalty > 0 ? formatMoney(p.bonus_loyalty) : '—'}</td>
      <td class="text-end text-muted">${p.visit_pay > 0 ? formatMoney(p.visit_pay) : '—'}</td>
      <td class="text-end text-muted">${p.expenses_reimbursement > 0 ? '+' + formatMoney(p.expenses_reimbursement) : '—'}</td>
      <td class="text-end text-orange">${p.offset_amount > 0 ? formatMoney(p.offset_amount) : '—'}</td>
      <td class="text-end text-red">${formatMoney(p.total_paid)}</td>
      <td class="text-end ${balanceClass}">${formatMoney(p.balance)}</td>
      <td class="text-muted small">${p.notes || ''} ${validatePayrollNotes(p)}</td>
    </tr>`;
  }).join('') + `<tr class="table-light fw-bold">
    <td colspan="10" class="text-end">Итого к выплате:</td>
    <td></td>
    <td class="text-end text-red">${formatMoney(totalBalance)}</td>
    <td></td>
  </tr>`;
}
