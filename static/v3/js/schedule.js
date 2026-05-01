// ============ РАСПИСАНИЕ + ТАБЫ СОТРУДНИКОВ ============

let scheduleYear  = TODAY.getFullYear();
let scheduleMonth = TODAY.getMonth() + 1;

function changeScheduleMonth(delta) {
  scheduleMonth += delta;
  if (scheduleMonth > 12) { scheduleMonth = 1;  scheduleYear++; }
  if (scheduleMonth < 1)  { scheduleMonth = 12; scheduleYear--; }
  loadSchedule();
}

async function loadSchedule() {
  document.getElementById('schedule-month-title').textContent =
    MONTHS_RU[scheduleMonth - 1] + ' ' + scheduleYear;

  const [data, coupleData, visitData, payrollData] = await Promise.all([
    fetchData(`/analytics/shifts/${scheduleYear}/${scheduleMonth}`),
    fetchData(`/analytics/couple-programs/${scheduleYear}/${scheduleMonth}`),
    fetchData(`/analytics/visit-records/${scheduleYear}/${scheduleMonth}`),
    fetchData(`/analytics/payroll-schedule/${scheduleYear}/${scheduleMonth}`)
  ]);

  if (!data || !data.shifts) return;
  const coupleDays    = coupleData?.couple_days    || {};
  const visitDays     = visitData?.visit_days      || {};
  const payrollShifts = payrollData?.shifts_from_payroll || {};
  const payrollVisits = payrollData?.visits_from_payroll || {};

  // Группируем по дате
  const byDay = {};
  data.shifts.forEach(s => {
    const day = parseInt(s.date.split('-')[2]);
    if (!byDay[day]) byDay[day] = [];
    byDay[day].push(s);
  });

  // Строим календарь
  const firstDay = new Date(scheduleYear, scheduleMonth - 1, 1);
  let startDow   = firstDay.getDay(); // 0=вс
  startDow       = startDow === 0 ? 6 : startDow - 1; // пн=0

  const daysInMonth = new Date(scheduleYear, scheduleMonth, 0).getDate();
  let rows = '';
  let row  = '<tr>';
  let col  = 0;

  // Пустые ячейки до первого дня
  for (let i = 0; i < startDow; i++) {
    row += '<td class="text-muted p-1" style="min-width:100px;height:80px"></td>';
    col++;
  }

  for (let day = 1; day <= daysInMonth; day++) {
    const isWeekend = col >= 5;
    const bgClass   = isWeekend ? 'bg-light' : '';
    const shifts    = byDay[day] || [];
    const shiftsHtml = shifts.map(s =>
      `<span class="badge bg-secondary text-white d-block mb-1">${s.staff_name}</span>`
    ).join('');

    const couplePrograms = coupleDays[day] || [];
    const realShifts     = shifts.filter(s => !s.is_visit_only);
    const shiftNames     = realShifts.map(s => s.staff_name);
    const isSingleShift  = realShifts.length === 1;
    const visitRecords   = visitDays[day] || [];

    const coupleHtml = (couplePrograms.length > 0 && isSingleShift && visitRecords.length === 0)
      ? `<div class="mt-1 border-top pt-1">${couplePrograms.map(c => {
          const payStr = c.visit_pay ? ' — ' + c.visit_pay.toLocaleString('ru-RU') + ' ₽' : '';
          return `<span class="badge bg-pink-lt d-block mb-1" title="${c.service_title} (${c.duration_min} мин)">♥ ? неизвестен${payStr}</span>`;
        }).join('')}</div>`
      : '';

    const conflictInShift = visitRecords.filter(v => shiftNames.includes(v.staff_name));
    const visitHtml = visitRecords.length > 0
      ? `<div class="mt-1 border-top pt-1">${visitRecords.map(v => {
          const payStr      = v.visit_pay ? ' — ' + v.visit_pay.toLocaleString('ru-RU') + ' ₽' : '';
          const isConflict  = shiftNames.includes(v.staff_name);
          const badgeClass  = isConflict ? 'bg-red text-white' : 'bg-pink-lt';
          const conflictTitle = isConflict ? ' ⚠ также в смене!' : '';
          return `<span class="badge ${badgeClass} d-block mb-1" title="${v.service_title}${conflictTitle}">♥ ${v.staff_name}${payStr}${isConflict ? ' ⚠' : ''}</span>`;
        }).join('')}</div>`
      : '';

    const payrollShiftNames = payrollShifts[day] || [];
    const payrollVisitList  = payrollVisits[day] || [];

    const conflicts = [];
    shiftNames.forEach(name => {
      if (payrollShiftNames.length > 0 && !payrollShiftNames.includes(name)) {
        conflicts.push(`⚠ ${name} в shifts, но не в payroll`);
      }
    });
    payrollShiftNames.forEach(name => {
      if (shiftNames.length > 0 && !shiftNames.includes(name)) {
        conflicts.push(`⚠ ${name} в payroll, но не в shifts`);
      }
    });
    visitRecords.forEach(v => {
      if (shiftNames.includes(v.staff_name)) {
        conflicts.push(`⚠ ${v.staff_name} одновременно в смене и под запись`);
      }
    });
    payrollVisitList.forEach(v => {
      const inVisitRecords = visitRecords.some(r => r.staff_name === v.staff_name);
      if (!inVisitRecords) {
        conflicts.push(`⚠ ${v.staff_name} под запись в payroll, но нет в visit_records`);
      }
    });

    const conflictHtml = conflicts.length > 0
      ? `<div class="mt-1">${conflicts.map(c =>
          `<span class="badge bg-red-lt d-block mb-1" style="font-size:10px;white-space:normal">${c}</span>`
        ).join('')}</div>`
      : '';

    row += `<td class="${bgClass} p-1 align-top" style="min-width:100px;height:80px">
      <div class="fw-bold small text-muted mb-1">${day}</div>
      ${shiftsHtml || '<span class="text-muted small">—</span>'}
      ${coupleHtml}
      ${visitHtml}
      ${conflictHtml}
    </td>`;
    col++;

    if (col === 7) {
      row += '</tr>';
      rows += row;
      row = '<tr>';
      col = 0;
    }
  }

  // Добить последнюю строку
  while (col > 0 && col < 7) {
    row += '<td class="text-muted p-1" style="min-width:100px;height:80px"></td>';
    col++;
  }
  if (col === 7) rows += row + '</tr>';

  document.getElementById('schedule-tbody').innerHTML = rows;
}

function showStaffTab(tab, el) {
  ['efficiency', 'payroll', 'schedule', 'checks', 'fot'].forEach(t => {
    document.getElementById('staff-tab-' + t).classList.add('d-none');
  });
  document.getElementById('staff-tab-' + tab).classList.remove('d-none');

  document.querySelectorAll('.nav-tabs .nav-link').forEach(a => a.classList.remove('active'));
  el.classList.add('active');

  if (tab === 'fot')      loadFotData();
  if (tab === 'payroll')  loadPayroll();
  if (tab === 'schedule') loadSchedule();
  if (tab === 'checks') {
    document.getElementById('checks-body').innerHTML = '<p class="text-muted">Выберите месяц для проверки</p>';
  }
}
