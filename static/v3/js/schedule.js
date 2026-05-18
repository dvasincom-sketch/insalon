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

  const [data, coupleData, visitData, payrollData, dayoffResp] = await Promise.all([
    fetchData(`/analytics/shifts/${scheduleYear}/${scheduleMonth}`),
    fetchData(`/analytics/couple-programs/${scheduleYear}/${scheduleMonth}`),
    fetchData(`/analytics/visit-records/${scheduleYear}/${scheduleMonth}`),
    fetchData(`/analytics/payroll-schedule/${scheduleYear}/${scheduleMonth}`),
    fetch(`https://isdayoff.ru/api/getdata?year=${scheduleYear}&month=${scheduleMonth}&cc=ru`).then(r => r.text()).catch(() => '')
  ]);
  const dayoffStr = typeof dayoffResp === 'string' ? dayoffResp : '';

  if (!data || !data.shifts) return;
  const coupleDays    = coupleData?.couple_days    || {};
  const visitDays     = visitData?.visit_days      || {};
  const payrollShifts = payrollData?.shifts_from_payroll || {};
  const payrollVisits = payrollData?.visits_from_payroll || {};

  // Группируем по дате
  const byDay = {};
  [...(data.shifts || []), ...(data.visits || [])].forEach(s => {
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
    const isWeekend  = col >= 5;
    const isHoliday  = dayoffStr[day - 1] === '1';
    const bgClass    = isHoliday ? 'bg-red-lt' : isWeekend ? 'bg-light' : '';
    const today2     = new Date();
    const isToday    = day === today2.getDate() && scheduleMonth === today2.getMonth() + 1 && scheduleYear === today2.getFullYear();
    const dayNumColor = (isWeekend || isHoliday) ? 'color:#c92a2a;font-weight:600' : 'color:#868e96';
    const shifts    = byDay[day] || [];
    const shiftsHtml = shifts.filter(s => !s.is_visit_only).map(s =>
      `<span class="badge bg-secondary text-white d-block mb-1">${s.staff_name}</span>`
    ).join('');

    const couplePrograms    = coupleDays[day] || [];
    const realShifts        = shifts.filter(s => !s.is_visit_only);
    const shiftNames        = realShifts.map(s => s.staff_name);
    const isSingleShift     = realShifts.length === 1;
    const visitRecords      = visitDays[day] || [];
    const payrollShiftNames = payrollShifts[day] || [];
    const payrollVisitList  = payrollVisits[day] || [];

    const conflictInShift = visitRecords.filter(v => shiftNames.includes(v.staff_name));

    // Выходы из таблицы shifts (is_visit_only=true)
    const shiftsVisits = (byDay[day] || []).filter(s => s.is_visit_only);

    // Индикатор неназначенных парных программ
    // Не показываем если: два мастера в смене ИЛИ все парные уже назначены
    const assignedCount = shiftsVisits.length + visitRecords.length;
    const needsAssignment = couplePrograms.length > 0
      && realShifts.length < 2
      && assignedCount < couplePrograms.length;

    const coupleHtml = needsAssignment
      ? `<div class="mt-1 border-top pt-1">
          <span class="badge bg-yellow-lt d-block mb-1" style="white-space:normal">
            ⚡ ${couplePrograms.length - assignedCount} парн. — нужен мастер
          </span>
         </div>`
      : '';

    // Приоритет: visit_records → shifts (is_visit_only) → payroll.notes
    const visitSource = visitRecords.length > 0
      ? visitRecords.map(v => ({ staff_name: v.staff_name, visit_pay: v.visit_pay, source: 'visit' }))
      : shiftsVisits.length > 0
        ? shiftsVisits.map(s => ({ staff_name: s.staff_name, visit_pay: s.shift_pay, source: 'shifts' }))
        : payrollVisitList.map(v => ({ staff_name: v.staff_name, visit_pay: v.pay, source: 'payroll' }));

    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const cellDate = new Date(scheduleYear, scheduleMonth - 1, day);
    const isFuture = cellDate > today;

    const visitHtml = visitSource.length > 0
      ? `<div class="mt-1 border-top pt-1">${visitSource.map(v => {
          const payStr     = v.visit_pay ? ' — ' + v.visit_pay.toLocaleString('ru-RU') + ' ₽' : '';
          const isConflict = shiftNames.includes(v.staff_name);
          const badgeClass = isConflict
            ? 'bg-red text-white'
            : isFuture ? 'bg-blue-lt' : 'bg-pink-lt';
          const prefix = isFuture ? '🔵' : '♥';
          return `<span class="badge ${badgeClass} d-block mb-1">${prefix} ${v.staff_name}${payStr}${isConflict ? ' ⚠' : ''}</span>`;
        }).join('')}</div>`
      : '';

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
    // visit_records оставлен как архив, проверка отключена

    const conflictHtml = conflicts.length > 0
      ? `<div class="mt-1">${conflicts.map(c =>
          `<span class="badge bg-red-lt d-block mb-1" style="font-size:10px;white-space:normal">${c}</span>`
        ).join('')}</div>`
      : '';

    row += `<td class="${bgClass} p-1 align-top" style="min-width:130px;height:90px;cursor:pointer;${isToday ? 'outline:2px solid #206bc4;outline-offset:-2px;' : ''}"
      onclick="openScheduleModal(${scheduleYear}, ${scheduleMonth}, ${day})">
      <div class="small mb-1" style="${dayNumColor}">${day}</div>
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
    initChecksFilter();
    loadSyncStatus();
  }
}


async function openScheduleModal(year, month, day) {
  console.log('openScheduleModal called', year, month, day);
  const dateStr = `${year}-${String(month).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
  const dayLabel = `${day} ${MONTHS_RU_LC[month-1]} ${year}`;

  document.getElementById('scheduleModalTitle').textContent = dayLabel;
  console.log('modal element:', document.getElementById('scheduleModal'));

  // Загружаем данные параллельно
  const [shiftsResp, coupleResp, staffResp] = await Promise.all([
    fetch(`${API}/analytics/shifts/${year}/${month}`).then(r => r.json()),
    fetch(`${API}/analytics/couple-programs/${year}/${month}`).then(r => r.json()),
    fetch(`${API}/payroll/staff/list`).then(r => r.json())
  ]);

  const dayShifts   = [...(shiftsResp?.shifts || []), ...(shiftsResp?.visits || [])].filter(s => s.date === dateStr);
  const coupleProgs = (coupleResp?.couple_days || {})[day] || [];
  const staffList   = staffResp?.staff || [];
  const realShifts  = dayShifts.filter(s => !s.is_visit_only);

  // Список опций сотрудников
  const staffOptions = staffList.map(n => `<option value="${n}">${n}</option>`).join('');

  // Текущие смены
  const shiftsHtml = dayShifts.length > 0
    ? dayShifts.map(s => `
      <div class="d-flex align-items-center justify-content-between mb-1">
        <span class="badge ${s.is_visit_only ? 'bg-pink-lt' : 'bg-secondary text-white'}">
          ${s.is_visit_only ? '♥' : '👤'} ${s.staff_name} ${s.is_visit_only ? '(выход)' : '(смена)'}
        </span>
        <button class="btn btn-sm btn-outline-danger ms-2" onclick="deleteShift(${s.id}, ${year}, ${month}, ${day})">✕</button>
      </div>`).join('')
    : '<div class="text-muted small mb-2">Нет смен</div>';

  // Парные программы — показываем только если один мастер в смене
  const coupleHtml = coupleProgs.length > 0 && realShifts.length < 2
    ? `<div class="mt-3">
        <div class="fw-bold small mb-2">♥ Парные программы</div>
        ${coupleProgs.map((c, i) => `
          <div class="border rounded p-2 mb-2">
            <div class="small text-muted mb-1">${c.service_title} · ${c.time} · ${c.duration_min} мин · <strong>${c.visit_pay} ₽</strong></div>
            <div class="small mb-1">Клиент: ${c.client_name}</div>
            <div class="small text-muted mb-1">Мастер из YCLIENTS: <strong>${c.staff_name || '?'}</strong></div>
            <select class="form-select form-select-sm mt-1" id="couple-staff-${i}">
              <option value="">Назначить мастера на выход...</option>
              ${staffOptions}
            </select>
            <button class="btn btn-sm btn-outline-primary mt-1 w-100"
              onclick="assignCoupleStaff('${dateStr}', ${i}, ${c.visit_pay}, ${year}, ${month}, ${day})">
              Назначить выход под запись
            </button>
          </div>`).join('')}
      </div>`
    : '';

  // Форма добавления смены
  const addHtml = `
    <div class="mt-3 border-top pt-3">
      <div class="fw-bold small mb-2">+ Добавить в расписание</div>
      <div class="d-flex gap-2 align-items-center flex-wrap">
        <select class="form-select form-select-sm w-auto" id="modal-staff-select">
          <option value="">Мастер...</option>
          ${staffOptions}
        </select>
        <select class="form-select form-select-sm w-auto" id="modal-shift-type">
          <option value="shift">Смена (5 000 ₽)</option>
          <option value="visit">Выход под запись</option>
        </select>
        <button class="btn btn-sm btn-primary" onclick="addShiftFromModal('${dateStr}', ${year}, ${month}, ${day})">
          Добавить
        </button>
      </div>
    </div>`;

  document.getElementById('scheduleModalBody').innerHTML = shiftsHtml + coupleHtml + addHtml;

  const modalEl = document.getElementById('scheduleModal');
  modalEl.classList.add('show');
  modalEl.style.display = 'block';
  document.body.classList.add('modal-open');
  let backdrop = document.getElementById('schedule-backdrop');
  if (!backdrop) {
    backdrop = document.createElement('div');
    backdrop.id = 'schedule-backdrop';
    backdrop.className = 'modal-backdrop fade show';
    document.body.appendChild(backdrop);
  }
}

async function addShiftFromModal(dateStr, year, month, day) {
  const staffName = document.getElementById('modal-staff-select').value;
  const shiftType = document.getElementById('modal-shift-type').value;
  if (!staffName) { alert('Выберите мастера'); return; }

  const isVisit   = shiftType === 'visit';
  const shiftPay  = isVisit ? 0 : 5000;

  const resp = await fetch(`${API}/payroll/shifts/add`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ date: dateStr, staff_name: staffName, shift_pay: shiftPay, is_visit_only: isVisit })
  });
  const data = await resp.json();
  if (data.status === 'exists') {
    alert(`${staffName} уже есть в расписании на этот день`);
    return;
  }
  closeScheduleModal();
  loadSchedule();
}

async function deleteShift(shiftId, year, month, day) {
  if (!confirm('Удалить запись из расписания?')) return;
  await fetch(`${API}/payroll/shifts/${shiftId}`, { method: 'DELETE' });
  closeScheduleModal();
  loadSchedule();
}

async function assignCoupleStaff(dateStr, idx, visitPay, year, month, day) {
  const staffName = document.getElementById(`couple-staff-${idx}`)?.value;
  if (!staffName) { showToast('Выберите мастера'); return; }
  const resp = await fetch(`${API}/payroll/shifts/add`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ date: dateStr, staff_name: staffName, shift_pay: visitPay, is_visit_only: true })
  });
  const data = await resp.json();
  if (data.status === 'exists') {
    showToast(staffName + ' уже есть в расписании на этот день');
  } else {
    showToast(staffName + ' назначен на выход');
    closeScheduleModal();
    loadSchedule();
  }
}


function closeScheduleModal() {
  const modalEl = document.getElementById('scheduleModal');
  modalEl.classList.remove('show');
  modalEl.style.display = 'none';
  document.body.classList.remove('modal-open');
  const backdrop = document.getElementById('schedule-backdrop');
  if (backdrop) backdrop.remove();
}


async function openFillMonthModal() {
  const staffResp = await fetch(`${API}/payroll/staff/list`).then(r => r.json());
  const staffList = staffResp?.staff || [];
  const sel = document.getElementById('fill-staff-select');
  sel.innerHTML = '<option value="">Выберите мастера...</option>' +
    staffList.map(n => `<option value="${n}">${n}</option>`).join('');
  document.getElementById('fillMonthModal').style.display = 'block';
}

function closeFillMonthModal() {
  document.getElementById('fillMonthModal').style.display = 'none';
}

async function executeFillMonth() {
  const staffName = document.getElementById('fill-staff-select').value;
  if (!staffName) { alert('Выберите мастера'); return; }

  const checkboxes = document.querySelectorAll('#fill-weekdays input[type=checkbox]:checked');
  const weekdays = Array.from(checkboxes).map(c => parseInt(c.value));
  if (weekdays.length === 0) { alert('Выберите хотя бы один день недели'); return; }

  const isVisit  = document.getElementById('fill-shift-type').value === 'visit';
  const shiftPay = isVisit ? 0 : 5000;

  // Генерируем даты для текущего месяца
  const daysInMonth = new Date(scheduleYear, scheduleMonth, 0).getDate();
  const dates = [];
  for (let day = 1; day <= daysInMonth; day++) {
    const d = new Date(scheduleYear, scheduleMonth - 1, day);
    const dow = d.getDay() === 0 ? 6 : d.getDay() - 1; // пн=0
    if (weekdays.includes(dow)) {
      dates.push(`${scheduleYear}-${String(scheduleMonth).padStart(2,'0')}-${String(day).padStart(2,'0')}`);
    }
  }

  // Добавляем смены
  let added = 0;
  let skipped = 0;
  for (const date of dates) {
    const resp = await fetch(`${API}/payroll/shifts/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date, staff_name: staffName, shift_pay: shiftPay, is_visit_only: isVisit })
    });
    const data = await resp.json();
    if (data.status === 'created') added++;
    else skipped++;
  }

  closeFillMonthModal();
  loadSchedule();
  showToast(`Добавлено: ${added} смен. Пропущено: ${skipped}`);
}


async function clearMonth() {
  if (!confirm(`Удалить все смены за ${MONTHS_RU[scheduleMonth-1]} ${scheduleYear}?`)) return;

  const resp = await fetch(`${API}/analytics/shifts/${scheduleYear}/${scheduleMonth}`).then(r => r.json());
  const shifts = resp?.shifts || [];

  let deleted = 0;
  for (const s of shifts) {
    await fetch(`${API}/payroll/shifts/${s.id}`, { method: 'DELETE' });
    deleted++;
  }
  loadSchedule();
  showToast(`Удалено смен: ${deleted}`);
}

function showToast(msg) {
  const existing = document.getElementById('schedule-toast');
  if (existing) existing.remove();
  const toast = document.createElement('div');
  toast.id = 'schedule-toast';
  toast.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;background:#2fb344;color:#fff;padding:12px 20px;border-radius:8px;font-size:14px;box-shadow:0 4px 12px rgba(0,0,0,0.15)';
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}
