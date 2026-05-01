// ============ DRILL DOWN MODAL ============

async function showDetail(dateFrom, dateTo, title) {
  document.getElementById('modal-title').textContent  = title;
  document.getElementById('modal-period').textContent = `${dateFrom} — ${dateTo}`;
  document.getElementById('modal-count').textContent  = '...';
  document.getElementById('modal-total').textContent  = '...';
  document.getElementById('modal-tbody').innerHTML    = '<tr><td colspan="5" class="text-center py-3">Загрузка...</td></tr>';

  const modalEl = document.getElementById('detail-modal');
  const modal   = window.tabler ? new tabler.Modal(modalEl) : new bootstrap.Modal(modalEl);
  modal.show();

  const data = await fetchData(`/analytics/revenue/detail?date_from=${dateFrom}&date_to=${dateTo}`);
  if (!data || data.error) {
    document.getElementById('modal-tbody').innerHTML =
      '<tr><td colspan="5" class="text-center text-red py-3">Ошибка загрузки</td></tr>';
    return;
  }

  document.getElementById('modal-count').textContent = data.count;
  document.getElementById('modal-total').textContent = formatMoney(data.total);

  document.getElementById('modal-tbody').innerHTML = data.transactions.map(t => {
    const dt      = new Date(t.date);
    const dateStr = dt.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
    const timeStr = dt.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });

    const typeBadge = t.type_title.includes('сертификат')
      ? 'bg-purple-lt'
      : t.type_title.includes('абонемент')
        ? 'bg-orange-lt'
        : 'bg-green-lt';

    const accountIcon = t.account?.includes('Эквайринг')  ? '💳'
      : t.account?.includes('Расчетный') ? '🏦'
      : '💵';

    return `<tr>
      <td><span class="fw-bold">${dateStr}</span> <span class="text-muted">${timeStr}</span></td>
      <td>${t.client_name || '<span class="text-muted">—</span>'}</td>
      <td><span class="badge ${typeBadge}">${t.type_title}</span></td>
      <td>${accountIcon} <span class="text-muted small">${t.account || '—'}</span></td>
      <td class="text-end fw-bold">${formatMoney(t.amount)}</td>
    </tr>`;
  }).join('');
}
