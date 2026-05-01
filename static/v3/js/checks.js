// ============ СТАТУС ПРОВЕРОК ============

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
      payrollVisitList.forEach(v => {
        const inVisitRecords = visitRecords.some(r => r.staff_name === v.staff_name);
        if (!inVisitRecords) {
          warnings.push(`${day}.${String(month).padStart(2, '0')} — ${v.staff_name}: выход в payroll, но нет в visit_records`);
        }
      });
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

        if (payrollVisitCount !== visitRecordCount && payrollVisitSum === visitRecordSum) {
          warnings.push(`${p.staff_name} (${p.period_start.slice(0, 7)}): записей в payroll ${payrollVisitCount}, в visit_records ${visitRecordCount} — но суммы совпадают (${payrollVisitSum}₽)`);
        } else if (payrollVisitCount !== visitRecordCount && payrollVisitSum !== visitRecordSum) {
          errors.push(`${p.staff_name} (${p.period_start.slice(0, 7)}): записей в payroll ${payrollVisitCount}, в visit_records ${visitRecordCount}; сумма в payroll ${payrollVisitSum}₽, в visit_records ${visitRecordSum}₽`);
        } else if (payrollVisitCount === visitRecordCount && payrollVisitSum !== visitRecordSum) {
          errors.push(`${p.staff_name} (${p.period_start.slice(0, 7)}): количество совпадает (${payrollVisitCount}), но сумма в payroll ${payrollVisitSum}₽, в visit_records ${visitRecordSum}₽`);
        }
      } else if (p.visit_pay > 0) {
        warnings.push(`${p.staff_name} (${p.period_start.slice(0, 7)}): visit_pay=${p.visit_pay}₽, но в примечаниях нет выходов`);
      }
    });

    const now = new Date().toLocaleString('ru-RU');
    const checksList = [
      'Мастер в расписании (shifts) совпадает с payroll notes',
      'Мастер в payroll notes совпадает с расписанием (shifts)',
      'Мастер не числится одновременно в смене и под запись',
      'Выход под запись из payroll есть в visit_records',
      'Парные программы — мастер под запись определён',
      'Количество смен в payroll совпадает с днями смен в примечаниях',
      'Дни выходов в payroll совпадают с visit_records по количеству и сумме'
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
