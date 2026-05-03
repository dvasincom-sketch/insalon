// ============ DEV LOG ============
// js/devlog.js

const DL_API = 'https://insalon.onrender.com/dev-sessions';

const DL_CAT_COLOR = { analytics: 'bg-azure', dev: 'bg-indigo', design: 'bg-pink' };
const DL_CAT_ICON  = { analytics: '📊', dev: '⌨️', design: '✦' };
const DL_CAT_LABEL = { analytics: 'Analytics', dev: 'Dev', design: 'Design' };

function dlFmt(n, d=1)  { return Number(n||0).toFixed(d); }
function dlFmtK(n)      { n=Number(n||0); return n>=1000?(n/1000).toFixed(1)+'k':String(n); }
function dlEsc(s)       { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function dlToday()      { return new Date().toISOString().slice(0,10); }
function dlBadge(cat)   { return `<span class="badge ${DL_CAT_COLOR[cat]||'bg-secondary'} text-white">${DL_CAT_LABEL[cat]||cat}</span>`; }

// ─── Modal — монтируем один раз в body ───────────────────────
function dlEnsureModal() {
  if (document.getElementById('dl-modal')) return;
  const el = document.createElement('div');
  el.innerHTML = `
<div class="modal fade" id="dl-modal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-sm modal-dialog-centered">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Новая dev-сессия</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <div class="mb-2">
          <label class="form-label">Дата</label>
          <input type="date" id="dl-f-date" class="form-control form-control-sm">
        </div>
        <div class="mb-2">
          <label class="form-label">Фича / Задача</label>
          <input type="text" id="dl-f-feature" class="form-control form-control-sm" placeholder="Booking widget UI">
        </div>
        <div class="mb-2">
          <label class="form-label">Категория</label>
          <select id="dl-f-category" class="form-select form-select-sm">
            <option value="dev">Dev</option>
            <option value="design">Design</option>
            <option value="analytics">Analytics</option>
          </select>
        </div>
        <div class="row g-2 mb-2">
          <div class="col">
            <label class="form-label">Минуты</label>
            <input type="number" id="dl-f-duration" class="form-control form-control-sm" value="60" min="0">
          </div>
          <div class="col">
            <label class="form-label">Токены</label>
            <input type="number" id="dl-f-tokens" class="form-control form-control-sm" value="0" min="0">
          </div>
        </div>
        <div class="mb-2">
          <label class="form-label">Заметки</label>
          <textarea id="dl-f-notes" class="form-control form-control-sm" rows="2" placeholder="Опционально…"></textarea>
        </div>
        <div id="dl-form-err" class="text-danger small d-none"></div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-link link-secondary me-auto" data-bs-dismiss="modal">Отмена</button>
        <button class="btn btn-indigo btn-sm" id="dl-save-btn" onclick="dlSaveSession()">Сохранить</button>
      </div>
    </div>
  </div>
</div>`;
  document.body.appendChild(el.firstElementChild);
}

// ─── Main entry ───────────────────────────────────────────────
function loadDevLog() {
  const screen = document.getElementById('screen-devlog');
  if (!screen) return;

  dlEnsureModal();

  screen.innerHTML = `
  <!-- Stat cards -->
  <div class="row row-cards g-3 mb-3" id="dl-stats">
    ${dlEmptyStatCards()}
  </div>

  <!-- Table card -->
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">Сессии</h3>
      <div class="card-options d-flex gap-2">
        <select id="dl-filter" class="form-select form-select-sm" style="width:150px">
          <option value="">Все категории</option>
          <option value="analytics">Analytics</option>
          <option value="dev">Dev</option>
          <option value="design">Design</option>
        </select>
        <button class="btn btn-indigo btn-sm" onclick="dlOpenModal()">+ Добавить</button>
      </div>
    </div>
    <div class="card-body p-0">
      <div id="dl-table-wrap">
        <div class="text-center text-muted py-4 small">Загрузка…</div>
      </div>
    </div>
  </div>

  <!-- Backlog -->
  <div class="card mt-3">
    <div class="card-header">
      <h3 class="card-title">Бэклог задач</h3>
      <div class="card-options d-flex gap-2">
        <select id="dl-bl-priority" class="form-select form-select-sm" style="width:100px">
          <option value="">Все</option>
          <option value="P0">P0</option>
          <option value="P1">P1</option>
          <option value="P2">P2</option>
        </select>
      </div>
    </div>
    <div class="card-body p-0">
      <div id="dl-backlog-wrap">
        <div class="text-center text-muted py-4 small">Загрузка…</div>
      </div>
    </div>
  </div>

`;

  document.getElementById('dl-filter').addEventListener('change', dlLoadSessions);
  document.getElementById('dl-bl-priority').addEventListener('change', dlLoadBacklog);
  dlLoadStats();
  dlLoadSessions();
  dlLoadBacklog();
}

// ─── Пустые карточки-скелетоны пока данных нет ───────────────
function dlEmptyStatCards() {
  return `
    <div class="col-6 col-lg-3">
      <div class="card card-sm">
        <div class="card-body">
          <div class="row align-items-center">
            <div class="col-auto"><span class="avatar bg-blue text-white">⏱</span></div>
            <div class="col"><div class="fw-semibold">Всего времени</div><div class="text-muted small">— ч</div></div>
          </div>
        </div>
      </div>
    </div>
    <div class="col-6 col-lg-3">
      <div class="card card-sm">
        <div class="card-body">
          <div class="row align-items-center">
            <div class="col-auto"><span class="avatar bg-yellow text-white">🪙</span></div>
            <div class="col"><div class="fw-semibold">Токены</div><div class="text-muted small">—</div></div>
          </div>
        </div>
      </div>
    </div>
    <div class="col-6 col-lg-3">
      <div class="card card-sm">
        <div class="card-body">
          <div class="row align-items-center">
            <div class="col-auto"><span class="avatar bg-indigo text-white">⌨️</span></div>
            <div class="col"><div class="fw-semibold">Dev</div><div class="text-muted small">— ч</div></div>
          </div>
        </div>
      </div>
    </div>
    <div class="col-6 col-lg-3">
      <div class="card card-sm">
        <div class="card-body">
          <div class="row align-items-center">
            <div class="col-auto"><span class="avatar bg-pink text-white">✦</span></div>
            <div class="col"><div class="fw-semibold">Design</div><div class="text-muted small">— ч</div></div>
          </div>
        </div>
      </div>
    </div>`;
}

// ─── Stats ────────────────────────────────────────────────────
async function dlLoadStats() {
  const wrap = document.getElementById('dl-stats');
  if (!wrap) return;
  try {
    const res = await fetch(DL_API + '/stats');
    if (!res.ok) return; // тихо — скелетон остаётся
    const s = await res.json();
    const cats = Object.entries(s.by_category || {});
    const catCards = cats.map(([cat, d]) => `
      <div class="col-6 col-lg-3">
        <div class="card card-sm">
          <div class="card-body">
            <div class="row align-items-center">
              <div class="col-auto">
                <span class="avatar ${DL_CAT_COLOR[cat]||'bg-secondary'} text-white">${DL_CAT_ICON[cat]||'•'}</span>
              </div>
              <div class="col">
                <div class="fw-semibold">${DL_CAT_LABEL[cat]||cat}</div>
                <div class="text-muted small">${dlFmt(d.hours)} ч · ${dlFmtK(d.tokens)} tok</div>
              </div>
            </div>
          </div>
        </div>
      </div>`).join('');
    wrap.innerHTML = `
      <div class="col-6 col-lg-3">
        <div class="card card-sm"><div class="card-body">
          <div class="row align-items-center">
            <div class="col-auto"><span class="avatar bg-blue text-white">⏱</span></div>
            <div class="col"><div class="fw-semibold">Всего времени</div><div class="text-muted small">${dlFmt(s.total_hours)} ч</div></div>
          </div>
        </div></div>
      </div>
      <div class="col-6 col-lg-3">
        <div class="card card-sm"><div class="card-body">
          <div class="row align-items-center">
            <div class="col-auto"><span class="avatar bg-yellow text-white">🪙</span></div>
            <div class="col"><div class="fw-semibold">Токены</div><div class="text-muted small">${dlFmtK(s.total_tokens)}</div></div>
          </div>
        </div></div>
      </div>
      ${catCards}`;
  } catch(e) {
    // тихо — скелетон остаётся до деплоя
  }
}

// ─── Sessions table ───────────────────────────────────────────
async function dlLoadSessions() {
  const wrap = document.getElementById('dl-table-wrap');
  if (!wrap) return;
  const cat = document.getElementById('dl-filter')?.value || '';
  const url = cat ? `${DL_API}?category=${cat}` : DL_API;
  try {
    const res = await fetch(url);
    if (!res.ok) {
      wrap.innerHTML = `<div class="text-center text-muted py-5">
        <div style="font-size:2rem" class="mb-2">📋</div>
        Нет сессий. Нажми <strong>+ Добавить</strong>.
      </div>`;
      return;
    }
    const data = await res.json();
    if (!data.length) {
      wrap.innerHTML = `<div class="text-center text-muted py-5">
        <div style="font-size:2rem" class="mb-2">📋</div>
        Нет сессий. Нажми <strong>+ Добавить</strong>.
      </div>`;
      return;
    }
    const rows = data.map(s => `
      <tr>
        <td class="text-muted text-nowrap small">${s.date}</td>
        <td>${dlEsc(s.feature)}</td>
        <td>${dlBadge(s.category)}</td>
        <td class="text-end">${dlFmt(s.duration_min/60)} ч</td>
        <td class="text-end">${dlFmtK(s.tokens_approx)}</td>
        <td class="text-center" style="width:36px">${s.notes?`<span title="${dlEsc(s.notes)}" style="cursor:help">📝</span>`:''}</td>
      </tr>`).join('');
    wrap.innerHTML = `
      <div class="table-responsive">
        <table class="table table-vcenter table-hover card-table">
          <thead><tr>
            <th>Дата</th><th>Задача</th><th>Категория</th>
            <th class="text-end">Часы</th><th class="text-end">Токены</th><th></th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  } catch(e) {
    wrap.innerHTML = `<div class="text-center text-muted py-5">
      <div style="font-size:2rem" class="mb-2">📋</div>
      Нет сессий. Нажми <strong>+ Добавить</strong>.
    </div>`;
  }
}

// ─── Modal ────────────────────────────────────────────────────
function dlOpenModal() {
  document.getElementById('dl-f-date').value     = dlToday();
  document.getElementById('dl-f-feature').value  = '';
  document.getElementById('dl-f-tokens').value   = '0';
  document.getElementById('dl-f-duration').value = '60';
  document.getElementById('dl-f-notes').value    = '';
  document.getElementById('dl-form-err').classList.add('d-none');
  new bootstrap.Modal(document.getElementById('dl-modal')).show();
}

async function dlSaveSession() {
  const errEl   = document.getElementById('dl-form-err');
  const feature = document.getElementById('dl-f-feature').value.trim();
  errEl.classList.add('d-none');
  if (!feature) { errEl.textContent = 'Укажите название задачи.'; errEl.classList.remove('d-none'); return; }

  const payload = {
    date:          document.getElementById('dl-f-date').value,
    feature,
    category:      document.getElementById('dl-f-category').value,
    duration_min:  parseInt(document.getElementById('dl-f-duration').value, 10) || 0,
    tokens_approx: parseInt(document.getElementById('dl-f-tokens').value, 10)   || 0,
    notes:         document.getElementById('dl-f-notes').value.trim() || null,
  };

  const btn = document.getElementById('dl-save-btn');
  btn.disabled = true; btn.textContent = 'Сохраняю…';
  try {
    const res = await fetch(DL_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || res.statusText); }
    bootstrap.Modal.getInstance(document.getElementById('dl-modal')).hide();
    dlLoadStats();
    dlLoadSessions();
  } catch(e) {
    errEl.textContent = `Ошибка: ${e.message}`; errEl.classList.remove('d-none');
  } finally {
    btn.disabled = false; btn.textContent = 'Сохранить';
  }
}

// ─── Backlog ──────────────────────────────────────────────────
const PRIORITY_COLOR = { P0: 'bg-red', P1: 'bg-orange', P2: 'bg-secondary' };

async function dlLoadBacklog() {
  const wrap = document.getElementById('dl-backlog-wrap');
  if (!wrap) return;
  const priority = document.getElementById('dl-bl-priority')?.value || '';
  let url = 'https://insalon.onrender.com/dev-sessions/backlog?status=open';
  if (priority) url += `&priority=${priority}`;  // фильтр на фронте
  try {
    const res = await fetch('https://insalon.onrender.com/dev-sessions/backlog');
    if (!res.ok) return;
    let data = await res.json();
    if (priority) data = data.filter(r => r.priority === priority);
    if (!data.length) {
      wrap.innerHTML = '<div class="text-center text-muted py-4 small">Бэклог пуст.</div>';
      return;
    }
    const totalH   = data.reduce((s, r) => s + (r.planned_hours || 0), 0);
    const totalTok = data.reduce((s, r) => s + (r.planned_tokens || 0), 0);
    const rows = data.map(r => `
      <tr>
        <td><span class="badge ${PRIORITY_COLOR[r.priority]||'bg-secondary'} text-white">${r.priority}</span></td>
        <td>${dlBadge(r.category)}</td>
        <td>${dlEsc(r.feature)}</td>
        <td class="text-end">${r.planned_hours ? r.planned_hours + ' ч' : '—'}</td>
        <td class="text-end">${r.planned_tokens ? dlFmtK(r.planned_tokens) : '—'}</td>
        <td class="text-muted small text-nowrap">${r.planned_date || '—'}</td>
      </tr>`).join('');
    wrap.innerHTML = `
      <div class="table-responsive">
        <table class="table table-vcenter card-table">
          <thead><tr>
            <th style="width:60px">Prior.</th>
            <th style="width:100px">Категория</th>
            <th>Задача</th>
            <th class="text-end" style="width:80px">Часы</th>
            <th class="text-end" style="width:80px">Токены</th>
            <th style="width:100px">Дата</th>
          </tr></thead>
          <tbody>${rows}</tbody>
          <tfoot>
            <tr class="fw-semibold">
              <td colspan="3" class="text-muted small">Итого задач: ${data.length}</td>
              <td class="text-end">${dlFmt(totalH)} ч</td>
              <td class="text-end">${dlFmtK(totalTok)}</td>
              <td></td>
            </tr>
          </tfoot>
        </table>
      </div>`;
  } catch(e) {
    wrap.innerHTML = '<div class="text-center text-muted py-4 small">Нет данных.</div>';
  }
}
