// ============ P&L ============

async function loadPL() {
  const data = await fetchData('/analytics/pl');
  if (!data || !data.months) return;

  const tbody = document.getElementById('pl-tbody');
  tbody.innerHTML = [...data.months]
    .filter(m => m.total_revenue > 0 || m.total_expenses > 0)
    .reverse()
    .map(m => {
      const profitClass = m.profit >= 0 ? 'text-green fw-bold' : 'text-red fw-bold';
      return `
      <tr>
        <td><span class="fw-bold">${m.month}</span></td>
        <td class="text-end">${formatK(m.revenue_services)}</td>
        <td class="text-end">${formatK(m.revenue_certificates)}</td>
        <td class="text-end">${formatK(m.revenue_abonements)}</td>
        <td class="text-end">${formatK(m.revenue_fitmost)}</td>
        <td class="text-end fw-bold">${formatK(m.total_revenue)}</td>
        <td class="text-end text-red">${formatK(m.salary)}</td>
        <td class="text-end text-red">${formatK(m.rent)}</td>
        <td class="text-end text-red">${formatK(m.cosmetics)}</td>
        <td class="text-end text-red">${formatK(m.materials)}</td>
        <td class="text-end text-red">${formatK(m.marketing)}</td>
        <td class="text-end text-red">${formatK(m.bank_fees)}</td>
        <td class="text-end text-red">${formatK(m.taxes)}</td>
        <td class="text-end fw-bold text-red">${formatK(m.total_expenses)}</td>
        <td class="text-end ${profitClass}">${formatK(m.profit)}</td>
      </tr>`;
    }).join('');
}
