// ============ ROUTER ============
let plLoaded      = false;
let staffLoaded   = false;
let oblLoaded     = false;
let devlogLoaded  = false;

const TITLES = {
  pulse:       'Пульс системы',
  ideas:       'Идеи',
  pl:          'P&L отчёт',
  sales:       'Продажи товаров',
  staff:       'Сотрудники',
  obligations: 'Обязательства',
  devlog:      'Dev Log'
};

const STAFF_TABS = ['efficiency', 'schedule', 'payroll', 'checks', 'fot'];

function _hideAllStaffTabs() {
  STAFF_TABS.forEach(t => {
    const el = document.getElementById('staff-tab-' + t);
    if (el) el.classList.add('d-none');
  });
}

function showScreen(name, tab) {
  // Скрываем все экраны
  ['pulse', 'ideas', 'pl', 'sales', 'staff', 'obligations', 'devlog'].forEach(s => {
    const el = document.getElementById('screen-' + s);
    if (el) el.classList.add('d-none');
  });

  // Всегда скрываем табы staff при смене экрана
  _hideAllStaffTabs();

  const screen = document.getElementById('screen-' + name);
  if (screen) screen.classList.remove('d-none');
  document.getElementById('page-title').textContent = TITLES[name] || name;

  // Активный пункт меню
  document.querySelectorAll('.navbar-nav .nav-link').forEach(el => el.classList.remove('active'));
  const activeLink = document.querySelector(`.navbar-nav .nav-link[data-screen="${name}"]`);
  if (activeLink) activeLink.classList.add('active');

  // Lazy-load
  if (name === 'ideas') { loadIdeas(); }
  if (name === 'pl'          && !plLoaded)     { loadPL();          plLoaded     = true; }
  if (name === 'sales') { loadProductSales(); }
  if (name === 'staff') { loadStaffMonthly(); staffLoaded = true; }
  if (name === 'obligations' && !oblLoaded)    { loadObligations(); oblLoaded    = true; }
  if (name === 'devlog'      && !devlogLoaded) { loadDevLog();      devlogLoaded = true; }

  // Переключаем таб если передан, иначе показываем первый
  if (name === 'staff') {
    _activateStaffTab(tab || 'efficiency');
  }

  // Пишем в URL
  const hash = (name === 'staff')
    ? `staff/${tab || 'efficiency'}`
    : name;
  if (location.hash !== '#' + hash) {
    history.pushState({ screen: name, tab: tab || null }, '', '#' + hash);
  }
}

function _activateStaffTab(tab) {
  _hideAllStaffTabs();

  const target = document.getElementById('staff-tab-' + tab);
  if (target) target.classList.remove('d-none');

  // Активная вкладка в nav
  document.querySelectorAll('.card-header-tabs .nav-link').forEach(l => l.classList.remove('active'));
  const tabLink = document.querySelector(`.card-header-tabs .nav-link[data-tab="${tab}"]`);
  if (tabLink) tabLink.classList.add('active');
}

function showStaffTab(tab, el) {
  _activateStaffTab(tab);
  history.pushState({ screen: 'staff', tab }, '', '#staff/' + tab);
}

function routeFromHash() {
  const hash = location.hash.replace('#', '') || 'pulse';
  const [screen, tab] = hash.split('/');
  const validScreens = ['pulse', 'ideas', 'pl', 'sales', 'staff', 'obligations', 'devlog'];
  const target = validScreens.includes(screen) ? screen : 'pulse';
  showScreen(target, tab || null);
}

window.addEventListener('popstate', routeFromHash);
document.addEventListener('DOMContentLoaded', routeFromHash);
