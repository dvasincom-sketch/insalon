// ============ ОБЯЗАТЕЛЬСТВА ============

async function loadObligations() {
  const data = await fetchData(`/analytics/obligations/${YEAR}/${MONTH}`);
  if (!data) return;

  document.getElementById('obl-fixed').textContent    = formatK(data.summary.fixed);
  document.getElementById('obl-variable').textContent = formatK(data.summary.variable);
  document.getElementById('obl-debts').textContent    = formatK(data.summary.debt);

  const today = TODAY.getDate();

  document.getElementById('obl-tbody').innerHTML = data.obligations
    .sort((a, b) => (a.day_of_month || 99) - (b.day_of_month || 99))
    .map(o => {
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

      return `
      <tr class="${isToday ? 'table-danger' : isPast ? 'table-success' : ''}">
        <td>${o.day_of_month ? `<span class="fw-bold">${o.day_of_month}</span>` : '<span class="text-muted">разово</span>'}</td>
        <td>${o.description}</td>
        <td>${projectBadge}</td>
        <td><span class="text-muted">${o.expense_category || ''}</span></td>
        <td class="text-end fw-bold">${formatK(o.amount)}</td>
        <td>${statusBadge}</td>
      </tr>`;
    }).join('');
}
