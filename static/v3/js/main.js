// ============ MAIN — точка входа ============

async function init() {
  document.getElementById('last-updated').textContent =
    'Обновлено: ' + TODAY.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });

  await loadPulse();
}

init();
