// ============ ИДЕИ / ПРОЕКТЫ ============

let _ideasCache = [];

async function loadIdeas() {
  const data = await fetchData('/analytics/hypotheses');
  _ideasCache = data?.hypotheses || [];
  renderIdeas(_ideasCache);
}

function renderIdeas(list) {
  const total      = list.length;
  const inProgress = list.filter(h => h.status === 'В работе').length;
  const totalCapex = list.reduce((s, h) => s + (h.capex_total || 0), 0);

  document.getElementById('ideas-content').innerHTML = `
    <div class="row row-deck row-cards mb-3">
      <div class="col-md-3">
        <div class="card"><div class="card-body text-center">
          <div class="text-muted mb-1" style="font-size:13px">Всего проектов</div>
          <div class="display-6 fw-bold">${total}</div>
        </div></div>
      </div>
      <div class="col-md-3">
        <div class="card"><div class="card-body text-center">
          <div class="text-muted mb-1" style="font-size:13px">В работе</div>
          <div class="display-6 fw-bold text-green">${inProgress}</div>
        </div></div>
      </div>
      <div class="col-md-3">
        <div class="card"><div class="card-body text-center">
          <div class="text-muted mb-1" style="font-size:13px">Суммарный CapEx</div>
          <div class="display-6 fw-bold">${formatMoney(totalCapex)}</div>
        </div></div>
      </div>
      <div class="col-md-3">
        <div class="card"><div class="card-body d-flex align-items-center justify-content-center">
          <button class="btn btn-primary w-100" onclick="openAddHypModal()">+ Добавить проект</button>
        </div></div>
      </div>
    </div>

    <div class="card">
      <div class="card-body p-0">
        <div class="table-responsive">
          <table class="table table-vcenter card-table" style="font-size:13.5px">
            <thead>
              <tr>
                <th style="width:20%">Проект</th>
                <th>Тип</th>
                <th>Сроки</th>
                <th>Фокус</th>
                <th class="text-end">CapEx (план)</th>
                <th class="text-end">Прибыль (план)</th>
                <th>Статус</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              ${list.length === 0
                ? '<tr><td colspan="8" class="text-center text-muted py-4">Проектов пока нет. Добавьте первый!</td></tr>'
                : list.map(h => ideaRow(h)).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    ${ideaModalHtml()}
    ${addHypModalHtml()}
  `;
}

function focusBadge(level) {
  if (level === 'Высокий') return 'bg-red-lt text-red';
  if (level === 'Средний') return 'bg-yellow-lt text-yellow';
  return 'bg-green-lt text-green';
}

function statusBadge(status) {
  if (status === 'В работе') return 'bg-green text-white';
  if (status === 'Запущен')  return 'bg-blue text-white';
  if (status === 'Отклонён') return 'bg-red-lt text-red';
  return 'bg-secondary-lt text-secondary';
}

function profitLabel(h) {
  if (h.profit_type === 'monthly' && h.expected_profit_monthly)
    return formatMoney(h.expected_profit_monthly) + '/мес';
  if (h.profit_type === 'onetime' && h.expected_profit_onetime)
    return formatMoney(h.expected_profit_onetime) + ' разово';
  return '—';
}

function dateRange(h) {
  if (!h.date_start && !h.date_end) return '—';
  const fmt = s => s ? s.slice(0,7).split('-').reverse().join('.') : '…';
  return fmt(h.date_start) + ' — ' + fmt(h.date_end);
}

function ideaRow(h) {
  return `<tr style="cursor:pointer" onclick="openIdeaModal(${h.id})">
    <td>
      <div class="fw-bold">${h.name}</div>
      <div class="text-muted" style="font-size:12px">${h.tag || ''}</div>
    </td>
    <td class="text-muted">${h.project_type || '—'}</td>
    <td class="text-muted" style="font-size:12px">${dateRange(h)}</td>
    <td><span class="badge ${focusBadge(h.focus_level)}">${h.focus_level || '—'}</span></td>
    <td class="text-end">${h.capex_total ? formatMoney(h.capex_total) : '—'}</td>
    <td class="text-end text-green fw-bold">${profitLabel(h)}</td>
    <td><span class="badge ${statusBadge(h.status)}">${h.status}</span></td>
    <td class="text-end">
      <button class="btn btn-sm btn-ghost-danger" onclick="event.stopPropagation(); deleteHypothesis(${h.id})">✕</button>
    </td>
  </tr>`;
}

// ── Модал просмотра ────────────────────────────────────────────
function ideaModalHtml() {
  return `
  <div id="ideaModal" style="display:none; position:fixed; inset:0; z-index:1055; overflow-y:auto; background:rgba(0,0,0,0.5)">
    <div style="max-width:760px; margin:40px auto; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 8px 40px rgba(0,0,0,0.18)">
      <div class="d-flex align-items-center justify-content-between p-3 border-bottom">
        <div>
          <div class="fw-bold fs-4" id="im-name"></div>
          <div class="text-muted small" id="im-tag"></div>
        </div>
        <button class="btn btn-ghost-secondary" onclick="closeIdeaModal()">✕</button>
      </div>
      <div class="p-4" id="im-body"></div>
      <div class="d-flex gap-2 p-3 border-top justify-content-end">
        <a id="im-doclink" href="#" target="_blank" class="btn btn-outline-primary d-none">📄 Открыть документ</a>
        <button class="btn btn-ghost-secondary" onclick="closeIdeaModal()">Закрыть</button>
      </div>
    </div>
  </div>`;
}

async function openIdeaModal(id) {
  const h = _ideasCache.find(x => x.id === id);
  if (!h) return;

  document.getElementById('im-name').textContent = h.name;
  document.getElementById('im-tag').textContent  = h.tag || '';

  // Фактические расходы если проект в работе
  let factHtml = '';
  if (h.status === 'В работе' && h.project_key) {
    const txData = await fetchData(`/analytics/pl?project=${h.project_key}`);
    const periods = txData?.periods || [];
    const factExpenses = periods.reduce((s, p) => s + Math.abs(p.expenses || 0), 0);
    const factRevenue  = periods.reduce((s, p) => s + (p.revenue || 0), 0);
    factHtml = `
      <div class="row g-2 mb-3 p-3 rounded" style="background:#f8f9fa">
        <div class="col-12 fw-bold text-muted small mb-1">📊 Факт из P&L (${h.project_key})</div>
        <div class="col-6">
          <div class="text-muted small">Фактические расходы</div>
          <div class="fw-bold text-red">${formatMoney(factExpenses)}</div>
        </div>
        <div class="col-6">
          <div class="text-muted small">Фактические доходы</div>
          <div class="fw-bold text-green">${formatMoney(factRevenue)}</div>
        </div>
      </div>`;
  }

  // CapEx строки
  const capexItems = h.capex_items || [];
  const capexHtml = capexItems.length > 0
    ? `<table class="table table-sm mb-0">
        ${capexItems.map(i => `<tr>
          <td class="text-muted" style="font-size:13px">${i.label}</td>
          <td class="text-end fw-bold" style="font-size:13px">${formatMoney(i.amount)}</td>
        </tr>`).join('')}
        <tr class="border-top">
          <td class="fw-bold">Итого CapEx</td>
          <td class="text-end fw-bold text-red">${formatMoney(h.capex_total || 0)}</td>
        </tr>
      </table>`
    : '<div class="text-muted small">Статьи расходов не указаны</div>';

  const prdFields = [
    ['🎯 Проблема',              h.prd_problem],
    ['🏁 Результат для клиента', h.prd_outcome],
    ['📊 Ключевые результаты',   h.prd_kr],
    ['🚀 MVP',                   h.prd_mvp],
    ['💎 Отличие',               h.prd_diff],
    ['⚠️ Главный риск',          h.prd_risk],
    ['🗄️ Данные',                h.prd_data],
  ].filter(([,v]) => v);

  document.getElementById('im-body').innerHTML = `
    <div class="row g-3 mb-3">
      <div class="col-3"><div class="text-muted small">Тип</div><div class="fw-bold">${h.project_type || '—'}</div></div>
      <div class="col-3"><div class="text-muted small">Сроки</div><div class="fw-bold" style="font-size:13px">${dateRange(h)}</div></div>
      <div class="col-3"><div class="text-muted small">Фокус</div><span class="badge ${focusBadge(h.focus_level)}">${h.focus_level || '—'}</span></div>
      <div class="col-3"><div class="text-muted small">Ожид. прибыль</div><div class="fw-bold text-green">${profitLabel(h)}</div></div>
    </div>

    ${factHtml}

    <div class="mb-3">
      <div class="fw-bold text-muted small mb-2">💰 CapEx (план)</div>
      ${capexHtml}
    </div>

    ${prdFields.length > 0 ? `
    <div class="fw-bold text-muted small mb-2 mt-3">📋 PRD</div>
    <div class="row g-3">
      ${prdFields.map(([label, val]) => `
        <div class="col-md-6">
          <div class="text-muted small mb-1">${label}</div>
          <div style="font-size:13px; line-height:1.6">${val}</div>
        </div>`).join('')}
    </div>` : ''}
  `;

  const docLink = document.getElementById('im-doclink');
  if (h.doc_url) { docLink.href = h.doc_url; docLink.classList.remove('d-none'); }
  else docLink.classList.add('d-none');

  document.getElementById('ideaModal').style.display = 'block';
}

function closeIdeaModal() {
  document.getElementById('ideaModal').style.display = 'none';
}

// ── Модал добавления ──────────────────────────────────────────
let _capexRows = [];

function addHypModalHtml() {
  return `
  <div id="addHypModal" style="display:none; position:fixed; inset:0; z-index:1060; overflow-y:auto; background:rgba(0,0,0,0.5)">
    <div style="max-width:660px; margin:40px auto; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 8px 40px rgba(0,0,0,0.18)">
      <div class="d-flex align-items-center justify-content-between p-3 border-bottom">
        <div class="fw-bold fs-5">Новый проект / гипотеза</div>
        <button class="btn btn-ghost-secondary" onclick="closeAddHypModal()">✕</button>
      </div>
      <div class="p-4" style="max-height:78vh; overflow-y:auto">
        <div class="row g-3">

          <div class="col-12">
            <label class="form-label">Название *</label>
            <input class="form-control" id="hyp-name" placeholder="Например: Книга о менеджменте">
          </div>
          <div class="col-12">
            <label class="form-label">Тег / подзаголовок</label>
            <input class="form-control" id="hyp-tag" placeholder="творческий актив, монетизация через продажи">
          </div>
          <div class="col-md-6">
            <label class="form-label">Тип проекта</label>
            <input class="form-control" id="hyp-type" placeholder="IT-гипотеза / Творческий актив / ...">
          </div>
          <div class="col-md-6">
            <label class="form-label">Статус</label>
            <select class="form-select" id="hyp-status">
              <option>Идея</option><option>В работе</option><option>Запущен</option><option>Отклонён</option>
            </select>
          </div>
          <div class="col-md-6">
            <label class="form-label">Дата начала</label>
            <input class="form-control" id="hyp-date-start" type="month">
          </div>
          <div class="col-md-6">
            <label class="form-label">Дата окончания</label>
            <input class="form-control" id="hyp-date-end" type="month">
          </div>
          <div class="col-md-6">
            <label class="form-label">Личный фокус</label>
            <select class="form-select" id="hyp-focus">
              <option>Высокий</option><option selected>Средний</option><option>Низкий</option>
            </select>
          </div>
          <div class="col-md-6">
            <label class="form-label">Проект в P&L</label>
            <select class="form-select" id="hyp-project-key">
              <option value="">— не привязан —</option>
              <option value="salon">salon</option>
              <option value="personal">personal</option>
              <option value="podcast">podcast</option>
              <option value="book">book</option>
              <option value="consulting">consulting</option>
              <option value="internal">internal</option>
            </select>
          </div>

          <div class="col-12 mt-2">
            <div class="d-flex justify-content-between align-items-center mb-2">
              <div class="fw-bold small">💰 CapEx — статьи расходов</div>
              <button class="btn btn-sm btn-outline-secondary" onclick="addCapexRow()">+ Добавить статью</button>
            </div>
            <div id="capex-rows"></div>
            <div class="text-end text-muted small mt-1">Итого: <span class="fw-bold" id="capex-total-label">0 ₽</span></div>
          </div>

          <div class="col-12 mt-1">
            <div class="fw-bold small mb-2">📈 Ожидаемая прибыль</div>
            <div class="d-flex gap-2 align-items-center mb-2">
              <select class="form-select form-select-sm w-auto" id="hyp-profit-type">
                <option value="monthly">Ежемесячно</option>
                <option value="onetime">Разово</option>
              </select>
              <input class="form-control form-control-sm" id="hyp-profit-val" type="number" placeholder="сумма в ₽">
            </div>
          </div>

          <div class="col-12 mt-1">
            <div class="fw-bold small mb-2">📋 PRD (опционально)</div>
          </div>
          <div class="col-12">
            <label class="form-label">Проблема</label>
            <textarea class="form-control" id="hyp-problem" rows="2"></textarea>
          </div>
          <div class="col-12">
            <label class="form-label">Результат для клиента</label>
            <textarea class="form-control" id="hyp-outcome" rows="2"></textarea>
          </div>
          <div class="col-12">
            <label class="form-label">MVP</label>
            <textarea class="form-control" id="hyp-mvp" rows="2"></textarea>
          </div>
          <div class="col-12">
            <label class="form-label">Главный риск</label>
            <textarea class="form-control" id="hyp-prd-risk" rows="2"></textarea>
          </div>
          <div class="col-12">
            <label class="form-label">Ссылка на документ (Google Doc / PDF)</label>
            <input class="form-control" id="hyp-doc-url" placeholder="https://docs.google.com/...">
          </div>
        </div>
      </div>
      <div class="d-flex gap-2 p-3 border-top justify-content-end">
        <button class="btn btn-ghost-secondary" onclick="closeAddHypModal()">Отмена</button>
        <button class="btn btn-primary" onclick="saveHypothesis()">Сохранить</button>
      </div>
    </div>
  </div>`;
}

function openAddHypModal() {
  _capexRows = [];
  renderCapexRows();
  document.getElementById('addHypModal').style.display = 'block';
}

function closeAddHypModal() {
  document.getElementById('addHypModal').style.display = 'none';
}

function addCapexRow() {
  _capexRows.push({ label: '', amount: 0 });
  renderCapexRows();
}

function renderCapexRows() {
  const container = document.getElementById('capex-rows');
  if (!container) return;
  container.innerHTML = _capexRows.map((r, i) => `
    <div class="d-flex gap-2 mb-2 align-items-center">
      <input class="form-control form-control-sm" placeholder="Статья расхода"
        value="${r.label}" oninput="_capexRows[${i}].label=this.value">
      <input class="form-control form-control-sm" type="number" placeholder="₽" style="max-width:120px"
        value="${r.amount || ''}" oninput="_capexRows[${i}].amount=parseInt(this.value)||0; updateCapexTotal()">
      <button class="btn btn-sm btn-ghost-danger" onclick="_capexRows.splice(${i},1); renderCapexRows()">✕</button>
    </div>`).join('');
  updateCapexTotal();
}

function updateCapexTotal() {
  const total = _capexRows.reduce((s, r) => s + (r.amount || 0), 0);
  const el = document.getElementById('capex-total-label');
  if (el) el.textContent = formatMoney(total);
}

async function saveHypothesis() {
  const name = document.getElementById('hyp-name').value.trim();
  if (!name) { alert('Введите название'); return; }

  const profitType = document.getElementById('hyp-profit-type').value;
  const profitVal  = parseInt(document.getElementById('hyp-profit-val').value) || 0;
  const capexTotal = _capexRows.reduce((s, r) => s + (r.amount || 0), 0);

  const dateStart = document.getElementById('hyp-date-start').value;
  const dateEnd   = document.getElementById('hyp-date-end').value;

  const body = {
    name,
    tag:          document.getElementById('hyp-tag').value.trim(),
    project_type: document.getElementById('hyp-type').value.trim(),
    status:       document.getElementById('hyp-status').value,
    date_start:   dateStart ? dateStart + '-01' : null,
    date_end:     dateEnd   ? dateEnd   + '-01' : null,
    focus_level:  document.getElementById('hyp-focus').value,
    project_key:  document.getElementById('hyp-project-key').value,
    capex_items:  _capexRows.filter(r => r.label),
    capex_total:  capexTotal,
    profit_type:  profitType,
    expected_profit_monthly: profitType === 'monthly' ? profitVal : 0,
    expected_profit_onetime: profitType === 'onetime' ? profitVal : 0,
    prd_problem:  document.getElementById('hyp-problem').value.trim(),
    prd_outcome:  document.getElementById('hyp-outcome').value.trim(),
    prd_mvp:      document.getElementById('hyp-mvp').value.trim(),
    prd_risk:     document.getElementById('hyp-prd-risk').value.trim(),
    doc_url:      document.getElementById('hyp-doc-url').value.trim(),
  };

  const resp = await fetch(`${API}/analytics/hypotheses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  const data = await resp.json();
  if (data.ok) {
    closeAddHypModal();
    loadIdeas();
  } else {
    alert('Ошибка: ' + data.error);
  }
}

async function deleteHypothesis(id) {
  if (!confirm('Удалить проект?')) return;
  await fetch(`${API}/analytics/hypotheses/${id}`, { method: 'DELETE' });
  loadIdeas();
}
