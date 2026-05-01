// ============ РАСЧЁТ ФОТ ============

let fotData   = {}; // { staffName: { shifts, visitPay, debts, advances, bonuses, ... } }
let fotPeriod = {};

function getFotPeriod() {
  const now   = new Date();
  const day   = now.getDate();
  const year  = now.getFullYear();
  const month = now.getMonth() + 1;

  const isSecondHalf = day >= 15;
  const periodStart  = isSecondHalf
    ? `${year}-${String(month).padStart(2, '0')}-15`
    : `${year}-${String(month).padStart(2, '0')}-01`;
  const lastDay  = new Date(year, month, 0).getDate();
  const periodEnd = isSecondHalf
    ? `${year}-${String(month).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`
    : `${year}-${String(month).padStart(2, '0')}-14`;

  const half = isSecondHalf ? '15–' + new Date(year, month, 0).getDate() : '1–14';
  return { year, month, periodStart, periodEnd, label: `${half} ${MONTHS_RU_LC[month - 1]} ${year}` };
}

async function loadFotData(overridePeriod) {
  fotPeriod = overridePeriod || getFotPeriod();
  const { year, month, day, periodStart, periodEnd, label } = fotPeriod;

  document.getElementById('fot-period-label').textContent = 'Период расчёта: ' + label;
  document.getElementById('fot-period-badge').textContent = label;
  document.getElementById('fot-loading').style.display  = '';
  document.getElementById('fot-content').style.display  = 'none';

  const [shiftsData, visitsData, payrollData, periodData, unclosedData] = await Promise.all([
    fetchData(`/analytics/shifts/${year}/${month}`),
    fetchData(`/analytics/visit-records/${year}/${month}`),
    fetchData('/analytics/payroll?months=6'),
    fetchData(`/payroll/period/${year}/${month}`),
    fetchData('/payroll/unclosed')
  ]);

  // Рендер табов периодов
  const tabsContainer = document.getElementById('fot-period-tabs');
  if (tabsContainer) {
    const unclosed = (unclosedData?.unclosed || []).filter(p => p.period_start !== periodStart);
    let tabsHtml = '';

    // Незакрытые периоды — оранжевые
    unclosed.forEach(p => {
      const d    = new Date(p.period_start + 'T00:00:00');
      const endD = new Date(p.period_end   + 'T00:00:00');
      const lbl  = d.getDate() + '–' + endD.getDate() + ' ' + MONTHS_RU_LC[d.getMonth()];
      const staffCount = p.staff.length;
      tabsHtml += `<button class="btn btn-sm" style="background:#f76707;color:white;border:none;"
        onclick="openPrevPeriod('${p.period_start}')"
        title="${staffCount} сотр. не закрыто">
        ⚠️ ${lbl} · ${staffCount} чел.
      </button>`;
    });

    // Текущий период — голубой активный
    const curD     = new Date(periodStart + 'T00:00:00');
    const curE     = new Date(periodEnd   + 'T00:00:00');
    const curLabel = curD.getDate() + '–' + curE.getDate() + ' ' + MONTHS_RU_LC[curD.getMonth()];
    tabsHtml += `<button class="btn btn-sm btn-primary" style="cursor:default;">${curLabel}</button>`;
    tabsContainer.innerHTML = tabsHtml;
  }

  // Мастера с paid записями за текущий период
  const paidStaff = {};
  (periodData?.records || []).forEach(p => {
    if (p.status === 'paid' && p.period_start === periodStart) paidStaff[p.staff_name] = p;
  });

  // Смены в периоде
  const shiftsByStaff    = {};
  const shiftDaysByStaff = {};
  (shiftsData?.shifts || []).forEach(s => {
    if (s.is_visit_only) return;
    const d  = new Date(s.date + 'T00:00:00');
    const ps = new Date(periodStart + 'T00:00:00');
    const pe = new Date(periodEnd   + 'T23:59:59');
    if (d < ps || d > pe) return;
    if (!shiftsByStaff[s.staff_name]) { shiftsByStaff[s.staff_name] = 0; shiftDaysByStaff[s.staff_name] = []; }
    shiftsByStaff[s.staff_name]++;
    shiftDaysByStaff[s.staff_name].push(parseInt(s.date.split('-')[2]));
  });

  // Выходы под запись в периоде
  const visitPayByStaff    = {};
  const visitDetailByStaff = {};
  Object.entries(visitsData?.visit_days || {}).forEach(([dayNum, recs]) => {
    const d  = new Date(year, month - 1, parseInt(dayNum));
    const ps = new Date(periodStart + 'T00:00:00');
    const pe = new Date(periodEnd   + 'T23:59:59');
    if (d < ps || d > pe) return;
    recs.forEach(r => {
      if (!visitPayByStaff[r.staff_name]) { visitPayByStaff[r.staff_name] = 0; visitDetailByStaff[r.staff_name] = []; }
      visitPayByStaff[r.staff_name] += r.visit_pay || 0;
      visitDetailByStaff[r.staff_name].push(
        `${String(dayNum).padStart(2, '0')}.${String(month).padStart(2, '0')}=${r.visit_pay}₽`
      );
    });
  });

  const debtByStaff = {};

  const allStaff = new Set([
    ...Object.keys(shiftsByStaff),
    ...Object.keys(visitPayByStaff)
  ]);

  fotData = {};
  allStaff.forEach(name => {
    fotData[name] = {
      shifts:      shiftsByStaff[name] || 0,
      shiftDays:   (shiftDaysByStaff[name] || []).sort((a, b) => a - b),
      shiftPay:    (shiftsByStaff[name] || 0) * 5000,
      visitPay:    visitPayByStaff[name] || 0,
      visitDetail: visitDetailByStaff[name] || [],
      debts:       debtByStaff[name] || [],
      advances:    [{ date: '', amount: '' }],
      bonuses:     [],
      isPaid:      !!paidStaff[name],
      paidRecord:  paidStaff[name] || null
    };
  });

  renderFotRows();

  // Подгружаем существующие draft-записи
  const draftData = await fetchData(`/payroll/draft/${year}/${month}`);
  (draftData?.drafts || []).forEach(p => {
    const name = p.staff_name;
    if (!fotData[name]) return;

    // Восстанавливаем авансы из notes
    fotData[name].advances = [];
    const advMatches = [...(p.notes || '').matchAll(/([\d]{4}-[\d]{2}-[\d]{2})=([\d]+)₽/g)];
    advMatches.forEach(m => {
      fotData[name].advances.push({ date: m[1], amount: m[2] });
    });
    if (fotData[name].advances.length === 0) fotData[name].advances.push({ date: '', amount: '' });

    // Восстанавливаем бонусы из notes
    fotData[name].bonuses = [];
    const bonusMatches = [...(p.notes || '').matchAll(/(\d{4}-\d{2}-\d{2})\s+([^=\d]+?)\s*(\d+%?)?\s*=\s*(\d+)₽/g)];
    bonusMatches.forEach(m => {
      fotData[name].bonuses.push({ date: m[1], comment: m[2].trim(), pct: m[3] || '', amount: m[4] });
    });

    fotData[name].savedId      = p.id;
    fotData[name].savedAccrued = p.total_accrued;
    fotData[name].savedAdvance = p.total_paid;
  });

  renderFotRows();

  // Показываем кнопки для уже сохранённых draft
  (draftData?.drafts || []).forEach(p => {
    const payBtn  = document.getElementById(`fot-pay-btn-${p.staff_name}`);
    const savedEl = document.getElementById(`fot-saved-${p.staff_name}`);
    const printBtn = document.getElementById(`fot-print-btn-${p.staff_name}`);
    if (payBtn)   payBtn.style.display   = '';
    if (printBtn) printBtn.style.display = '';
    if (savedEl)  savedEl.style.display  = '';
  });

  document.getElementById('fot-loading').style.display = 'none';
  document.getElementById('fot-content').style.display = '';
  updateFotTotals();
}

function renderFotRows() {
  const container = document.getElementById('fot-rows');
  let html = '';

  Object.entries(fotData).forEach(([name, d]) => {
    // Уже выплачено — закрытый блок
    if (d.isPaid && d.paidRecord) {
      const p     = d.paidRecord;
      const toPay = (p.total_accrued || 0) - (p.total_paid || 0);
      html += `
    <div class="border-bottom p-3 bg-light" id="fot-staff-${name}">
      <div class="row g-3 align-items-center">
        <div class="col-md-9">
          <div class="d-flex align-items-center gap-2 flex-wrap">
            <span class="fw-bold fs-5">${name}</span>
            <span class="badge bg-green text-white">✅ Выплачено</span>
            ${p.shifts > 0 ? `<span class="badge bg-blue text-white">${p.shifts} смен</span><span class="badge bg-blue-lt">${(p.shift_pay || 0).toLocaleString('ru-RU')} ₽</span>` : ''}
            ${p.visit_pay > 0 ? `<span class="badge bg-pink-lt">выходы ${p.visit_pay.toLocaleString('ru-RU')} ₽</span>` : ''}
            ${p.bonus_loyalty > 0 ? `<span class="badge bg-yellow-lt">бонусы ${p.bonus_loyalty.toLocaleString('ru-RU')} ₽</span>` : ''}
          </div>
          <div class="text-muted small mt-1">${p.notes || ''}</div>
        </div>
        <div class="col-md-3 text-end">
          <div class="text-muted small">Начислено: <strong>${(p.total_accrued || 0).toLocaleString('ru-RU')} ₽</strong></div>
          <div class="text-muted small">Выплачено: <strong class="text-red">${(p.total_paid || 0).toLocaleString('ru-RU')} ₽</strong></div>
          <div class="fw-bold ${toPay > 0 ? 'text-green' : toPay < 0 ? 'text-orange' : 'text-muted'}">
            Остаток: ${toPay.toLocaleString('ru-RU')} ₽
          </div>
          <button class="btn btn-sm btn-outline-danger mt-2" onclick="cancelPaidStaff('${name}', ${p.id})">↩ Отменить оплату</button>
        </div>
      </div>
    </div>`;
      return;
    }

    const totalDebt = d.debts.reduce((s, x) => s + x.balance, 0);
    const visitHtml = d.visitPay > 0
      ? `${d.visitPay.toLocaleString('ru-RU')} ₽ <small class="text-muted">(${d.visitDetail.join(', ')})</small>`
      : '<span class="text-muted">—</span>';

    html += `
    <div class="border-bottom p-3" id="fot-staff-${name}">
      <div class="row g-3 align-items-start">

        <div class="col-md-5">
          <div class="d-flex align-items-center gap-2 mb-2 flex-wrap">
            <span class="fw-bold fs-5">${name}</span>
            <span class="badge bg-blue text-white">${d.shifts} смен</span>
            <span class="badge bg-blue-lt">${d.shiftPay.toLocaleString('ru-RU')} ₽</span>
            ${d.visitPay > 0 ? `<span class="badge bg-pink-lt">выходы ${d.visitPay.toLocaleString('ru-RU')} ₽</span>` : ''}
          </div>
          ${d.prevDraft ? `<div class="alert alert-warning py-2 px-3 mb-2" style="font-size:13px;">
            ⚠️ Незакрытый период: <strong>${d.prevDraft.period_start} — ${d.prevDraft.period_end}</strong><br>
            Начислено: ${(d.prevDraft.total_accrued || 0).toLocaleString('ru-RU')} ₽ ·
            Выплачено: ${(d.prevDraft.total_paid || 0).toLocaleString('ru-RU')} ₽ ·
            <strong>Остаток: ${(d.prevDraft.balance || 0).toLocaleString('ru-RU')} ₽</strong>
            <button class="btn btn-sm btn-warning ms-2" onclick="openPrevPeriod('${d.prevDraft.period_start}')">Закрыть</button>
          </div>` : ''}
          <div class="text-muted small mb-2">Дни смен: ${d.shiftDays.join(', ') || '—'}</div>
          ${d.visitPay > 0 ? `<div class="text-muted small mb-2">${visitHtml}</div>` : ''}
          ${totalDebt < 0 ? `<div class="text-muted small mb-2">Переплата зачтена: <span class="text-green">${Math.abs(totalDebt).toLocaleString('ru-RU')} ₽</span></div>` : ''}

          <div class="mb-2">
            <div class="fw-bold small mb-1">💵 Авансы</div>
            <div id="advances-${name}">
              ${d.advances.map((a, i) => advanceRowHtml(name, i, a)).join('')}
            </div>
            <button class="btn btn-sm btn-outline-secondary mt-1" onclick="addAdvance('${name}')">+ Аванс</button>
          </div>

          <div class="mb-3">
            <div class="fw-bold small mb-1">🎁 Бонусы</div>
            <div id="bonuses-${name}">
              ${d.bonuses.map((b, i) => bonusRowHtml(name, i, b)).join('')}
            </div>
            <button class="btn btn-sm btn-outline-success mt-1" onclick="addBonus('${name}')">+ Бонус</button>
          </div>
        </div>

        <div class="col-md-3 ms-auto">
          <div class="card border-0 bg-light p-3 h-100 d-flex flex-column justify-content-between">
            <div>
              <div class="d-flex justify-content-between mb-1 small"><span class="text-muted">Смены</span><span>${d.shiftPay.toLocaleString('ru-RU')} ₽</span></div>
              ${d.visitPay > 0 ? `<div class="d-flex justify-content-between mb-1 small"><span class="text-muted">Выходы</span><span>${d.visitPay.toLocaleString('ru-RU')} ₽</span></div>` : ''}
              <div class="d-flex justify-content-between mb-1 small"><span class="text-muted">Бонусы</span><span id="fot-bonus-sum-${name}">0 ₽</span></div>
              <div class="d-flex justify-content-between mb-1 small"><span class="text-muted">Авансы выданы</span><span class="text-orange" id="fot-adv-sum-${name}">0 ₽</span></div>
              <div class="border-top pt-2 mt-2 d-flex justify-content-between align-items-center">
                <span class="fw-bold">К выплате</span>
                <span class="fw-bold fs-4" id="fot-topay-${name}">—</span>
              </div>
            </div>
            <div class="mt-3">
              <button class="btn btn-primary w-100 mb-1" onclick="confirmFotStaff('${name}')">💾 Сохранить расчёт</button>
              <button class="btn btn-success w-100" id="fot-pay-btn-${name}" onclick="markPaidStaff('${name}')" style="display:none">💸 Оплачено</button>
              <button class="btn btn-outline-secondary w-100 mt-1 no-print" id="fot-print-btn-${name}" onclick="printFotStaff('${name}')" style="display:none">🖨 Печать чека</button>
              <div id="fot-saved-${name}" class="text-success small mt-1 text-center" style="display:none">✅ Сохранено — нажмите «Оплачено» после выплаты</div>
            </div>
          </div>
        </div>

      </div>
    </div>`;
  });

  container.innerHTML = html || '<div class="text-center text-muted py-4">Нет данных за период</div>';

  // Баннер «все закрыты»
  const allStaffList = Object.keys(fotData);
  const allPaid      = allStaffList.length > 0 && allStaffList.every(n => fotData[n].isPaid);

  const existingBanner = document.getElementById('fot-all-paid-banner');
  if (existingBanner) existingBanner.remove();

  if (allPaid) {
    const { label } = fotPeriod;
    const ps       = new Date(fotPeriod.periodStart + 'T00:00:00');
    const pe       = new Date(fotPeriod.periodEnd   + 'T00:00:00');
    const nextDate = new Date(pe);
    nextDate.setDate(nextDate.getDate() + 1);
    const nextYear  = nextDate.getFullYear();
    const nextMonth = nextDate.getMonth() + 1;
    const nextDay   = nextDate.getDate();
    const isNextSecondHalf = nextDay >= 15;
    const nextLastDay = new Date(nextYear, nextMonth, 0).getDate();
    const nextEnd     = isNextSecondHalf ? nextLastDay : 14;
    const nextLabel   = `${nextDay}–${nextEnd} ${MONTHS_RU_LC[nextMonth - 1]} ${nextYear}`;

    const banner = document.createElement('div');
    banner.id        = 'fot-all-paid-banner';
    banner.className = 'p-4 text-center';
    banner.innerHTML = `
      <div style="background:linear-gradient(135deg,#2fb344,#1a7a2e);border-radius:12px;padding:24px;color:white;">
        <div style="font-size:2rem;margin-bottom:8px;">🎉</div>
        <div style="font-size:18px;font-weight:700;margin-bottom:4px;">Все выплаты за ${label} проведены!</div>
        <div style="font-size:14px;opacity:0.9;margin-bottom:16px;">Итого выплачено: ${allStaffList.reduce((s, n) => s + (fotData[n].paidRecord?.total_paid || 0), 0).toLocaleString('ru-RU')} ₽</div>
        <button onclick="openNextPeriod(${nextYear},${nextMonth},${nextDay})"
          style="background:white;color:#2fb344;border:none;padding:10px 24px;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;">
          → Открыть ${nextLabel}
        </button>
      </div>`;
    document.getElementById('fot-rows').appendChild(banner);
  }

  Object.keys(fotData).forEach(name => recalcFot(name));
}

function advanceRowHtml(name, i, a) {
  return `<div class="d-flex gap-1 mb-1 align-items-center" id="adv-row-${name}-${i}">
    <input type="date" class="form-control form-control-sm" style="width:130px"
      value="${a.date}" onchange="updateAdvance('${name}',${i},'date',this.value)">
    <input type="number" class="form-control form-control-sm" style="width:100px"
      placeholder="сумма ₽" value="${a.amount}" min="0"
      oninput="updateAdvance('${name}',${i},'amount',this.value);recalcFot('${name}')">
    <button class="btn btn-sm btn-ghost-danger" onclick="removeAdvance('${name}',${i})">✕</button>
  </div>`;
}

function bonusRowHtml(name, i, b) {
  return `<div class="mb-2 p-1 border rounded" id="bonus-row-${name}-${i}">
    <div class="d-flex gap-1 align-items-center flex-wrap">
      <input type="date" class="form-control form-control-sm" style="width:130px"
        value="${b.date || ''}" onchange="updateBonus('${name}',${i},'date',this.value)">
      <input type="text" class="form-control form-control-sm" style="width:140px"
        placeholder="комментарий" value="${b.comment || ''}"
        oninput="updateBonus('${name}',${i},'comment',this.value)">
      <input type="text" class="form-control form-control-sm" style="width:50px"
        placeholder="%" value="${b.pct || ''}"
        oninput="updateBonus('${name}',${i},'pct',this.value)">
      <input type="number" class="form-control form-control-sm" style="width:85px"
        placeholder="сумма ₽" value="${b.amount || ''}" min="0"
        oninput="updateBonus('${name}',${i},'amount',this.value);recalcFot('${name}')">
      <button class="btn btn-sm btn-ghost-danger p-0" onclick="removeBonus('${name}',${i})">✕</button>
    </div>
  </div>`;
}

function addAdvance(name)           { fotData[name].advances.push({ date: '', amount: '' }); rerenderSection(name); }
function removeAdvance(name, i)     { fotData[name].advances.splice(i, 1); rerenderSection(name); }
function updateAdvance(name, i, field, val) { fotData[name].advances[i][field] = val; }

function addBonus(name)             { fotData[name].bonuses.push({ date: '', comment: '', pct: '', amount: '' }); rerenderSection(name); }
function removeBonus(name, i)       { fotData[name].bonuses.splice(i, 1); rerenderSection(name); }
function updateBonus(name, i, field, val) {
  fotData[name].bonuses[i][field] = val;
  const b   = fotData[name].bonuses[i];
  const pct = b.type === 'cosmetics' ? 0.10 : b.type === 'upsale' ? 0.30 : null;
  if (pct !== null) {
    const el = document.getElementById(`bonus-calc-${name}-${i}`);
    if (el) el.textContent = Math.round((parseFloat(b.sales) || 0) * pct).toLocaleString('ru-RU') + ' ₽';
  }
}

function rerenderSection(name) {
  const d = fotData[name];
  document.getElementById(`advances-${name}`).innerHTML = d.advances.map((a, i) => advanceRowHtml(name, i, a)).join('');
  document.getElementById(`bonuses-${name}`).innerHTML  = d.bonuses.map((b, i) => bonusRowHtml(name, i, b)).join('');
  recalcFot(name);
}

function recalcFot(name) {
  const d = fotData[name];
  if (!d) return;

  const totalAdv   = d.advances.reduce((s, a) => s + (parseFloat(a.amount) || 0), 0);
  let   totalBonus = 0;
  d.bonuses.forEach(b => { totalBonus += parseFloat(b.amount) || 0; });
  const totalDebt = d.debts.reduce((s, x) => s + x.balance, 0);
  const toPay     = d.shiftPay + d.visitPay + totalBonus + totalDebt - totalAdv;

  const advEl   = document.getElementById(`fot-adv-sum-${name}`);
  const bonusEl = document.getElementById(`fot-bonus-sum-${name}`);
  const toPayEl = document.getElementById(`fot-topay-${name}`);
  if (advEl)   advEl.textContent   = totalAdv.toLocaleString('ru-RU') + ' ₽';
  if (bonusEl) bonusEl.textContent = totalBonus.toLocaleString('ru-RU') + ' ₽';
  if (toPayEl) {
    toPayEl.textContent = toPay.toLocaleString('ru-RU') + ' ₽';
    toPayEl.className   = 'fw-bold fs-5 ' + (toPay > 0 ? 'text-green' : toPay < 0 ? 'text-red' : 'text-muted');
  }

  updateFotTotals();
}

function updateFotTotals() {
  let sumShifts = 0, sumShiftPay = 0, sumVisits = 0, sumBonus = 0, sumAdv = 0, sumToPay = 0;
  Object.entries(fotData).forEach(([name, d]) => {
    sumShifts   += d.shifts;
    sumShiftPay += d.shiftPay;
    sumVisits   += d.visitPay;
    let bonus = 0;
    d.bonuses.forEach(b => { bonus += parseFloat(b.amount) || 0; });
    const adv  = d.advances.reduce((s, a) => s + (parseFloat(a.amount) || 0), 0);
    const debt = d.debts.reduce((s, x) => s + x.balance, 0);
    sumBonus  += bonus;
    sumAdv    += adv;
    sumToPay  += d.shiftPay + d.visitPay + bonus + debt - adv;
  });
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  set('fot-sum-shifts',   sumShifts + ' смен');
  set('fot-sum-shiftpay', sumShiftPay.toLocaleString('ru-RU') + ' ₽');
  set('fot-sum-visits',   sumVisits.toLocaleString('ru-RU') + ' ₽');
  set('fot-sum-bonus',    sumBonus.toLocaleString('ru-RU') + ' ₽');
  set('fot-sum-advances', sumAdv.toLocaleString('ru-RU') + ' ₽');
  const toPayEl = document.getElementById('fot-sum-topay');
  if (toPayEl) {
    toPayEl.textContent = sumToPay.toLocaleString('ru-RU') + ' ₽';
    toPayEl.className   = 'text-green fs-3 fw-bold' + (sumToPay < 0 ? ' text-red' : '');
  }
}

async function confirmFotStaff(name) {
  if (!fotData[name])        { alert('fotData пустой для: ' + name); return; }
  if (!fotPeriod.periodStart) { alert('fotPeriod не определён');       return; }
  const d = fotData[name];
  const { periodStart, periodEnd } = fotPeriod;

  let totalBonus = 0;
  const bonusNotes = [];
  d.bonuses.forEach(b => {
    const amt    = parseFloat(b.amount) || 0;
    const pct    = (b.pct || '').replace('%', '');
    const pctStr = pct ? ` ${pct}%` : '';
    bonusNotes.push(`${b.date || '?'} ${b.comment || 'бонус'}${pctStr}=${amt}₽`);
    totalBonus += amt;
  });

  const advNotes = d.advances.filter(a => a.amount).map(a => `${a.date || '?'}=${a.amount}₽`);
  const totalAdv = d.advances.reduce((s, a) => s + (parseFloat(a.amount) || 0), 0);
  const advCash  = totalAdv;

  const visitNotes = d.visitDetail.length > 0 ? `Выходы: ${d.visitDetail.join('+')}. ` : '';
  const notes = `Смены: ${d.shiftDays.join(',')}. ${visitNotes}${bonusNotes.length ? 'Бонусы: ' + bonusNotes.join('+') + '. ' : ''}${advNotes.length ? 'Авансы: ' + advNotes.join('+') + '.' : ''}`;

  const accrued   = d.shiftPay + d.visitPay + totalBonus;
  const totalPaid = totalAdv;
  const balance   = accrued - totalPaid;

  const body = {
    staff_name:              name,
    period_start:            periodStart,
    period_end:              periodEnd,
    shifts:                  d.shifts,
    shift_pay:               d.shiftPay,
    visit_pay:               d.visitPay,
    bonus_loyalty:           totalBonus,
    bonus:                   0,
    advance_cash:            advCash,
    advance_transfer:        0,
    expenses_reimbursement:  0,
    total_accrued:           accrued,
    total_paid:              totalPaid,
    balance:                 balance,
    notes:                   notes,
    status:                  'draft'
  };

  try {
    const resp = await fetch('/payroll/upsert', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body)
    });
    if (resp.ok) {
      const saved = await resp.json();
      fotData[name].savedId      = saved.id;
      fotData[name].savedAccrued = accrued;
      fotData[name].savedAdvance = totalAdv;

      const savedEl  = document.getElementById(`fot-saved-${name}`);
      const payBtn   = document.getElementById(`fot-pay-btn-${name}`);
      const printBtn = document.getElementById(`fot-print-btn-${name}`);
      if (printBtn) printBtn.style.display = '';
      if (savedEl) {
        savedEl.style.display = '';
        savedEl.textContent   = '✅ Сохранено ' + new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) + ' — нажмите «Оплачено» после выплаты';
        savedEl.className     = 'text-success small mt-1 text-center';
      }
      if (payBtn) payBtn.style.display = '';
    } else {
      alert('Ошибка сохранения: ' + resp.status);
    }
  } catch (e) {
    alert('Ошибка: ' + e.message);
  }
}

function printFotStaff(name) {
  const d = fotData[name];
  if (!d) return;

  let totalBonus = 0;
  const bonusLines = d.bonuses.map(b => {
    const amt    = parseFloat(b.amount) || 0;
    totalBonus  += amt;
    const pct    = (b.pct || '').replace('%', '');
    const pctStr = pct ? ` (${pct}%)` : '';
    return `<tr><td>${b.date || '—'}</td><td>${b.comment || 'Бонус'}${pctStr}</td><td style="text-align:right">${amt.toLocaleString('ru-RU')} руб.</td></tr>`;
  }).join('');

  const advLines = d.advances.filter(a => a.amount).map(a =>
    `<tr><td>${a.date || '—'}</td><td>Аванс</td><td style="text-align:right">${parseFloat(a.amount).toLocaleString('ru-RU')} руб.</td></tr>`
  ).join('');

  const totalAdv   = d.advances.reduce((s, a) => s + (parseFloat(a.amount) || 0), 0);
  const accrued    = d.shiftPay + d.visitPay + totalBonus;
  const toPay      = accrued - totalAdv;
  const { periodStart, periodEnd } = fotPeriod;
  const periodLabel = periodStart + ' — ' + periodEnd;

  // Примечание: этот HTML открывается в отдельном окне через window.open()
  // #payment-modal внутри НЕ является дублем основного DOM-элемента — это отдельный документ
  const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { font-family: Arial, sans-serif; font-size: 13px; margin: 20px; color: #111; max-width: 400px; }
  h2 { font-size: 16px; margin-bottom: 4px; }
  .sub { color: #666; font-size: 12px; margin-bottom: 16px; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 12px; }
  th { background: #f0f0f0; padding: 6px 8px; text-align: left; font-size: 11px; text-transform: uppercase; color: #666; }
  td { padding: 5px 8px; border-bottom: 1px solid #eee; }
  .total-row td { font-weight: bold; border-top: 2px solid #111; border-bottom: none; font-size: 14px; }
  .minus { color: #c00; }
  .green { color: #0a0; }
  .footer { margin-top: 20px; font-size: 11px; color: #999; border-top: 1px solid #eee; padding-top: 8px; }
</style>
</head>
<body>
<h2>HeadSPA — Расчёт оплаты</h2>
<div class="sub">${name} · ${periodLabel}</div>

<table>
  <tr><th colspan="3">Начислено</th></tr>
  <tr><td>${d.shiftDays.join(', ')}</td><td>${d.shifts} смен</td><td style="text-align:right">${d.shiftPay.toLocaleString('ru-RU')} руб.</td></tr>
  ${d.visitPay > 0 ? `<tr><td>${d.visitDetail.join(', ')}</td><td>Выходы</td><td style="text-align:right">${d.visitPay.toLocaleString('ru-RU')} руб.</td></tr>` : ''}
  ${bonusLines}
  <tr class="total-row"><td colspan="2">Итого начислено</td><td style="text-align:right">${accrued.toLocaleString('ru-RU')} руб.</td></tr>
</table>

${advLines ? `<table>
  <tr><th colspan="3">Авансы выданы</th></tr>
  ${advLines}
  <tr class="total-row minus"><td colspan="2">Итого авансы</td><td style="text-align:right">− ${totalAdv.toLocaleString('ru-RU')} руб.</td></tr>
</table>` : ''}

<table>
  <tr class="total-row green"><td colspan="2">К выплате</td><td style="text-align:right">${toPay.toLocaleString('ru-RU')} руб.</td></tr>
</table>

<div class="footer">Сформировано: ${new Date().toLocaleDateString('ru-RU')} · Insalon</div>
</body>
</html>`;

  const win = window.open('', '_blank', 'width=480,height=700');
  win.document.write(html);
  win.document.close();
  win.focus();
  setTimeout(() => win.print(), 500);
}

function openPrevPeriod(periodStart) {
  const d     = new Date(periodStart + 'T00:00:00');
  const year  = d.getFullYear();
  const month = d.getMonth() + 1;
  const day   = d.getDate();
  openNextPeriod(year, month, day);
}

function openNextPeriod(year, month, day) {
  const isSecondHalf = day >= 15;
  const lastDay      = new Date(year, month, 0).getDate();
  const periodStart  = year + '-' + String(month).padStart(2, '0') + '-' + String(day).padStart(2, '0');
  const periodEnd    = isSecondHalf
    ? year + '-' + String(month).padStart(2, '0') + '-' + String(lastDay).padStart(2, '0')
    : year + '-' + String(month).padStart(2, '0') + '-14';
  const half        = isSecondHalf ? '15-' + lastDay : '1-14';
  const nextPeriod  = { year, month, day, periodStart, periodEnd, label: half + ' ' + MONTHS_RU_LC[month - 1] + ' ' + year };
  loadFotData(nextPeriod);
}

async function cancelPaidStaff(name, id) {
  if (!confirm('Отменить выплату ' + name + '? Запись вернётся в статус draft.')) return;
  const resp = await fetch('/payroll/mark-paid', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ id: id, status: 'draft' })
  });
  if (resp.ok) {
    await loadFotData();
  } else {
    alert('Ошибка: ' + resp.status);
  }
}

let _currentPaymentName = null;

async function markPaidStaff(name) {
  const d = fotData[name];
  if (!d?.savedId) { alert('Сначала сохраните расчёт'); return; }

  const alreadyPaid = d.savedAdvance || 0;
  const remaining   = (d.savedAccrued || 0) - alreadyPaid;

  _currentPaymentName = name;
  document.getElementById('pm-title').textContent     = name + ' — финальная выплата';
  document.getElementById('pm-accrued').textContent   = (d.savedAccrued || 0).toLocaleString('ru-RU') + ' ₽';
  document.getElementById('pm-advances').textContent  = alreadyPaid.toLocaleString('ru-RU') + ' ₽';
  document.getElementById('pm-remaining').textContent = remaining.toLocaleString('ru-RU') + ' ₽';
  document.getElementById('pm-amount').value = remaining;

  const modal = document.getElementById('payment-modal');
  modal.style.display = 'flex';
  document.getElementById('pm-amount').focus();
}

function closePaymentModal() {
  document.getElementById('payment-modal').style.display = 'none';
  _currentPaymentName = null;
}

async function confirmPaymentModal() {
  const name = _currentPaymentName;
  if (!name) return;
  const d           = fotData[name];
  const finalAmount = parseFloat(document.getElementById('pm-amount').value) || 0;
  const method      = document.getElementById('pm-method').value;
  const alreadyPaid = d.savedAdvance || 0;
  const totalPaid   = alreadyPaid + finalAmount;
  const advCash     = method === 'cash'     ? alreadyPaid + finalAmount : alreadyPaid;
  const advTransfer = method === 'transfer' ? finalAmount : 0;

  closePaymentModal();

  const resp = await fetch('/payroll/mark-paid', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({
      id:               d.savedId,
      total_paid:       totalPaid,
      balance:          (d.savedAccrued || 0) - totalPaid,
      advance_cash:     advCash,
      advance_transfer: advTransfer
    })
  });

  if (resp.ok) {
    const btn     = document.getElementById(`fot-pay-btn-${name}`);
    const savedEl = document.getElementById(`fot-saved-${name}`);
    if (btn)     { btn.textContent = '✅ Выплачено'; btn.disabled = true; btn.className = 'btn btn-outline-success w-100 mt-1'; }
    if (savedEl) savedEl.textContent = '✅ Перенесено в ведомость оплаты труда';
  } else {
    alert('Ошибка: ' + resp.status);
  }
}
