// ============ ОБЯЗАТЕЛЬСТВА ============

async function loadObligations() {
  const data = await fetchData(`/analytics/obligations/${YEAR}/${MONTH}`);
  if (!data) return;

  document.getElementById('obl-fixed').textContent    = formatK(data.summary.fixed);
  document.getElementById('obl-variable').textContent = formatK(data.summary.variable);
  document.getElementById('obl-debts').textContent    = formatK(data.summary.debt);

  const today = TODAY.getDate();

  const isMobile = window.innerWidth < 768;
  const sorted = data.obligations.sort((a, b) => (a.day_of_month || 99) - (b.day_of_month || 99));

  const items = sorted.map(o => {
    const isPast  = o.day_of_month && o.day_of_month < today;
    const isToday = o.day_of_month === today;
    const statusBadge = o.type === 'debt'
      ? '<span class="badge bg-red-lt">Долг</span>'
      : isPast
        ? '<span class="badge bg-green-lt">✓ Оплачен</span>'
        : isToday
          ? '<span class="badge bg-red">Сегодня!</span>'
          : '<span class="badge bg-blue-lt">Ожидается</span>';
    const projectBadge = o.project === 'salon'
      ? '<span class="badge bg-blue-lt">Салон</span>'
      : o.project === 'personal'
        ? '<span class="badge bg-gray-lt">Личное</span>'
        : `<span class="badge bg-purple-lt">${o.project}</span>`;

    if (isMobile) {
      return `
      <div class="px-3 py-2 border-bottom ${isToday ? 'bg-red-lt' : isPast ? 'bg-green-lt' : ''}">
        <div class="d-flex justify-content-between align-items-start mb-1">
          <div class="d-flex align-items-center gap-2">
            <span class="fw-bold">${o.day_of_month || '—'}</span>
            ${projectBadge}
          </div>
          <div class="text-end">
            <div class="fw-bold">${formatK(o.amount)}</div>
            <div>${statusBadge}</div>
          </div>
        </div>
        <div class="small">${o.description}</div>
        ${o.expense_category ? `<div class="text-muted small">${o.expense_category}</div>` : ''}
      </div>`;
    }
    return `
    <tr class="${isToday ? 'table-danger' : isPast ? 'table-success' : ''}">
      <td>${o.day_of_month ? `<span class="fw-bold">${o.day_of_month}</span>` : '<span class="text-muted">разово</span>'}</td>
      <td>${o.description}</td>
      <td>${projectBadge}</td>
      <td><span class="text-muted">${o.expense_category || ''}</span></td>
      <td class="text-end fw-bold">${formatK(o.amount)}</td>
      <td>${statusBadge}</td>
    </tr>`;
  });

  // Рендерим оба — CSS скрывает нужный через media query
  const mobileItems = sorted.map(o => {
    const isPast  = o.day_of_month && o.day_of_month < today;
    const isToday = o.day_of_month === today;
    const statusBadge = o.type === 'debt'
      ? '<span class="badge bg-red-lt">Долг</span>'
      : isPast ? '<span class="badge bg-green-lt">✓ Оплачен</span>'
      : isToday ? '<span class="badge bg-red">Сегодня!</span>'
      : '<span class="badge bg-blue-lt">Ожидается</span>';
    const projectBadge = o.project === 'salon'
      ? '<span class="badge bg-blue-lt">Салон</span>'
      : o.project === 'personal'
        ? '<span class="badge bg-gray-lt">Личное</span>'
        : `<span class="badge bg-purple-lt">${o.project}</span>`;
    return `
    <div class="px-3 py-2 border-bottom ${isToday ? 'bg-red-lt' : isPast ? 'bg-green-lt' : ''}">
      <div class="d-flex justify-content-between align-items-start mb-1">
        <div class="d-flex align-items-center gap-2">
          <span class="fw-bold">${o.day_of_month || '—'}</span>
          ${projectBadge}
        </div>
        <div class="text-end">
          <div class="fw-bold">${formatK(o.amount)}</div>
          <div>${statusBadge}</div>
        </div>
      </div>
      <div class="small">${o.description}</div>
      ${o.expense_category ? `<div class="text-muted small">${o.expense_category}</div>` : ''}
    </div>`;
  });

  document.getElementById('obl-tbody').innerHTML = items.join('');
  const mobile = document.getElementById('obl-mobile');
  if (mobile) mobile.innerHTML = mobileItems.join('');
}
