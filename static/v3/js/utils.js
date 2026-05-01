// ============ UTILS ============

function formatMoney(n) {
  if (!n && n !== 0) return '—';
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency', currency: 'RUB', maximumFractionDigits: 0
  }).format(n);
}

function formatK(n) {
  if (!n && n !== 0) return '—';
  if (Math.abs(n) >= 1000000) return (n / 1000000).toFixed(1) + 'М ₽';
  if (Math.abs(n) >= 1000)    return Math.round(n / 1000) + 'К ₽';
  return n + ' ₽';
}
