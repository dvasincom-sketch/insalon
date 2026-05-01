// ============ ROUTER ============
// Флаги lazy-load экранов (были window.* в оригинале)
let plLoaded       = false;
let staffLoaded    = false;
let oblLoaded      = false;

function showScreen(name) {
  ['pulse', 'pl', 'staff', 'obligations'].forEach(s => {
    document.getElementById('screen-' + s).classList.add('d-none');
  });
  document.getElementById('screen-' + name).classList.remove('d-none');

  const titles = {
    pulse:       'Пульс системы',
    pl:          'P&L отчёт',
    staff:       'Сотрудники',
    obligations: 'Обязательства'
  };
  document.getElementById('page-title').textContent = titles[name];

  if (name === 'pl'          && !plLoaded)    { loadPL();          plLoaded    = true; }
  if (name === 'staff'       && !staffLoaded) { loadStaff();       staffLoaded = true; }
  if (name === 'obligations' && !oblLoaded)   { loadObligations(); oblLoaded   = true; }
}
