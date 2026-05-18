// ============ СТАТУС ПРОВЕРОК ============

async function loadSyncStatus() {
  const bar = document.getElementById('sync-status-bar');
  if (!bar) return;
  try {
    const data = await fetchData('/sync/status');
    if (!data) { bar.innerHTML = '<div class="text-muted small">Статус недоступен</div>'; return; }

    const fmt = (iso) => {
      if (!iso) return '—';
      const d = new Date(iso);
      return d.toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
    };

    const recSync  = fmt(data.last_records_sync);
    const recDate  = data.last_records_date ? data.last_records_date.slice(0, 10) : '—';
    const trSync   = fmt(data.last_transactions_sync);
    const trDate   = data.last_transactions_date ? data.last_transactions_date.slice(0, 10) : '—';

    // Проверяем свежесть — если последняя синхронизация > 25 часов назад
    const lastSyncTime = new Date(data.last_records_sync || 0);
    const hoursSince   = (Date.now() - lastSyncTime) / 3600000;
    const statusColor  = hoursSince < 25 ? 'text-green' : 'text-red';
    const statusIcon   = hoursSince < 25 ? '✅' : '⚠️';
    const statusText   = hoursSince < 25 ? 'Синхронизация актуальна' : 'Синхронизация устарела';

    bar.innerHTML = `
      <div class="d-flex align-items-center gap-4 flex-wrap">
        <div>
          <span class="${statusColor} fw-bold">${statusIcon} ${statusText}</span>
        </div>
        <div class="text-muted small">
          📋 Записи: <strong>${recSync}</strong>
          <span class="text-muted">(последняя запись ${recDate})</span>
        </div>
        <div class="text-muted small">
          💰 Транзакции: <strong>${trSync}</strong>
          <span class="text-muted">(последняя ${trDate})</span>
        </div>
        <button class="btn btn-sm btn-outline-secondary ms-auto" onclick="manualSync()">🔄 Синхронизировать</button>
      </div>`;
  } catch(e) {
    bar.innerHTML = '<div class="text-muted small">Ошибка загрузки статуса</div>';
  }
}

async function manualSync() {
  const bar = document.getElementById('sync-status-bar');
  bar.innerHTML = '<div class="text-muted small">⏳ Синхронизация запущена...</div>';
  await fetchData('/sync/recent');
  setTimeout(() => loadSyncStatus(), 5000);
}

async function initChecksFilter() {
  const selC = document.getElementById('checks-filter-month');
  if (!selC || selC.options.length > 1) return;
  const pd = await fetchData('/analytics/payroll?months=12');
  if (!pd?.payroll) return;
  const MONTHS = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];
  const uniqueMonths = [...new Set(pd.payroll.map(p => p.period_start.slice(0, 7)))].sort().reverse();
  selC.innerHTML = '<option value="">Выберите месяц</option>';
  uniqueMonths.forEach(m => {
    const [y, mo] = m.split('-');
    selC.appendChild(new Option(MONTHS[parseInt(mo) - 1] + ' ' + y, m));
  });
}

async function loadChecks() {
  const monthVal = document.getElementById('checks-filter-month')?.value || '';
  if (!monthVal) {
    document.getElementById('checks-body').innerHTML = '<p class="text-muted">Выберите месяц для проверки</p>';
    return;
  }
  document.getElementById('checks-body').innerHTML = '<p class="text-muted">Загрузка...</p>';

  try {
    const [year, month] = monthVal.split('-').map(Number);
    const [shiftsData, visitData, payrollData, coupleData, payrollFull] = await Promise.all([
      fetchData(`/analytics/shifts/${year}/${month}`),
      fetchData(`/analytics/visit-records/${year}/${month}`),
      fetchData(`/analytics/payroll-schedule/${year}/${month}`),
      fetchData(`/analytics/couple-programs/${year}/${month}`),
      fetchData('/analytics/payroll?months=12')
    ]);

    const shifts        = shiftsData?.shifts || [];
    const visitDays     = visitData?.visit_days || {};
    const payrollShifts = payrollData?.shifts_from_payroll || {};
    const payrollVisits = payrollData?.visits_from_payroll || {};
    const coupleDays    = coupleData?.couple_days || {};

    const byDay = {};
    shifts.forEach(s => {
      if (s.is_visit_only) return;
      const day = parseInt(s.date.split('-')[2]);
      if (!byDay[day]) byDay[day] = [];
      byDay[day].push(s.staff_name);
    });

    const errors   = [];
    const warnings = [];

    const daysInMonth = new Date(year, month, 0).getDate();
    for (let day = 1; day <= daysInMonth; day++) {
      const shiftNames        = byDay[day] || [];
      const payrollShiftNames = payrollShifts[day] || [];
      const visitRecords      = visitDays[day] || [];
      const payrollVisitList  = payrollVisits[day] || [];
      const couplePrograms    = coupleDays[day] || [];

      shiftNames.forEach(name => {
        if (payrollShiftNames.length > 0 && !payrollShiftNames.includes(name)) {
          errors.push(`${day}.${String(month).padStart(2, '0')} — ${name}: в расписании, но не в payroll`);
        }
      });
      payrollShiftNames.forEach(name => {
        if (shiftNames.length > 0 && !shiftNames.includes(name)) {
          errors.push(`${day}.${String(month).padStart(2, '0')} — ${name}: в payroll, но не в расписании`);
        }
      });
      visitRecords.forEach(v => {
        if (shiftNames.includes(v.staff_name)) {
          errors.push(`${day}.${String(month).padStart(2, '0')} — ${v.staff_name}: одновременно в смене и под запись`);
        }
      });
      // visit_records — архив, проверка отключена
      if (couplePrograms.length > 0 && shiftNames.length === 1 && visitRecords.length === 0 && payrollVisitList.length === 0) {
        warnings.push(`${day}.${String(month).padStart(2, '0')} — парная программа, но мастер под запись не определён`);
      }
    }

    const payrollRecords = (payrollFull?.payroll || []).filter(p => p.period_start.startsWith(monthVal));
    payrollRecords.forEach(p => {
      const notes = p.notes || '';

      const shiftMatch = notes.match(/Смены?:\s*([\d,\s]+)/);
      if (shiftMatch) {
        const days = shiftMatch[1].split(',').map(d => parseInt(d.trim())).filter(Boolean);
        if (days.length !== p.shifts) {
          errors.push(`${p.staff_name} (${p.period_start.slice(0, 7)}): смен ${p.shifts}, но в примечаниях ${days.length} дней (${days.join(',')})`);
        }
      }

      const visitMatch        = notes.match(/Выходы?[^:]*:(.*?)(?:\.\s+[А-ЯЁ]|$)/);
      const visitInlineMatches = [...notes.matchAll(/Выход[^:\d]*(\d{2})\.(\d{2})=(\d+)/g)];
      let entries = [];
      if (visitMatch) {
        entries = [...visitMatch[1].matchAll(/(\d{2})\.(\d{2})=(\d+)/g)];
      }
      if (visitInlineMatches.length > 0 && entries.length === 0) {
        entries = visitInlineMatches.map(m => [m[0], m[1], m[2], m[3]]);
      }

      if (entries.length > 0) {
        const payrollVisitSum   = entries.reduce((s, m) => s + parseInt(m[3]), 0);
        const payrollVisitCount = entries.length;

        const periodStart = new Date(p.period_start + 'T00:00:00');
        const periodEnd   = new Date(p.period_end   + 'T23:59:59');
        const visitInPeriod = Object.entries(visitDays)
          .filter(([day]) => {
            const d = new Date(year, month - 1, parseInt(day));
            return d >= periodStart && d <= periodEnd;
          })
          .flatMap(([_, recs]) => recs.filter(r => r.staff_name === p.staff_name));

        const visitRecordCount = visitInPeriod.length;
        const visitRecordSum   = visitInPeriod.reduce((s, r) => s + (r.visit_pay || 0), 0);

        // Сравнение с visit_records отключено (архив)
      } else if (p.visit_pay > 0) {
        warnings.push(`${p.staff_name} (${p.period_start.slice(0, 7)}): visit_pay=${p.visit_pay}₽, но в примечаниях нет выходов`);
      }
    });

    const now = new Date().toLocaleString('ru-RU');
    const checksList = [
      'Мастер в расписании (shifts) совпадает с payroll notes',
      'Мастер в payroll notes совпадает с расписанием (shifts)',
      'Мастер не числится одновременно в смене и под запись',
      'Парные программы — мастер под запись определён',
      'Количество смен в payroll совпадает с днями смен в примечаниях'
    ];

    const body = document.getElementById('checks-body');
    let html_out = `<div class="text-muted small mb-3">Проверено: ${now}</div>`;
    html_out += '<div class="mb-3"><strong>Выполненные проверки:</strong><ul class="mt-1 mb-0">';
    html_out += checksList.map(c => `<li class="text-muted small">${c}</li>`).join('');
    html_out += '</ul></div><hr>';

    if (errors.length === 0 && warnings.length === 0) {
      html_out += '<div class="text-center text-green py-2">✅ Ошибок не найдено</div>';
      body.innerHTML = html_out;
      return;
    }

    if (errors.length > 0) {
      html_out += '<h4 class="text-red mb-2">Ошибки (' + errors.length + ')</h4>';
      html_out += errors.map(e =>
        `<div class="badge bg-red-lt d-block mb-2 text-start" style="white-space:normal;font-size:13px">⚠ ${e}</div>`
      ).join('');
    }
    if (warnings.length > 0) {
      html_out += '<h4 class="text-orange mb-2 mt-3">Предупреждения (' + warnings.length + ')</h4>';
      html_out += warnings.map(w =>
        `<div class="badge bg-yellow-lt d-block mb-2 text-start" style="white-space:normal;font-size:13px">⚡ ${w}</div>`
      ).join('');
    }
    body.innerHTML = html_out;

  } catch (e) {
    document.getElementById('checks-body').innerHTML = '<div class="text-red">Ошибка: ' + e.message + '</div>';
    console.error('loadChecks error:', e);
  }
}
