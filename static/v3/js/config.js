// ============ CONFIG ============
// Базовый URL API (пустая строка = текущий хост)
const API = '';

const TODAY = new Date();
const YEAR  = TODAY.getFullYear();
const MONTH = TODAY.getMonth() + 1;

const MONTHS_RU = [
  'Январь','Февраль','Март','Апрель','Май','Июнь',
  'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'
];

const MONTHS_RU_LC = [
  'январь','февраль','март','апрель','май','июнь',
  'июль','август','сентябрь','октябрь','ноябрь','декабрь'
];

const STAFF_COLORS = {
  'Александра': 'bg-blue text-white',
  'Светлана':   'bg-green text-white',
  'Екатерина':  'bg-purple text-white',
  'Анастасия':  'bg-orange text-white',
  'Марина':     'bg-pink text-white',
  'Мария':      'bg-yellow',
};
