// ============ ПРОДАЖИ ТОВАРОВ ============

let salesProducts = [];

async function loadProductSales() {
  const month = document.getElementById('sales-filter-month')?.value || '';
  const staff = document.getElementById('sales-filter-staff')?.value || '';

  const tbody = document.getElementById('sales-tbody');
  if (tbody) tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted py-4">Загрузка...</td></tr>';

  const params = new URLSearchParams();
  if (month) params.set('month', month);
  if (staff) params.set('staff', staff);

  const data = await fetchData(`/analytics/product-sales?${params}`);
  if (!data || data.error) {
    if (tbody) tbody.innerHTML = '<tr><td colspan="9" class="text-danger py-3 text-center">Ошибка загрузки</td></tr>';
    return;
  }

  // Итого
  const totalEl = document.getElementById('sales-total');
  if (totalEl) totalEl.textContent = `Итого: ${formatMoney(data.total)}`;

  // Бонусы по мастерам
  const bonusesEl = document.getElementById('sales-bonuses');
  if (bonusesEl && data.bonuses) {
    bonusesEl.innerHTML = Object.entries(data.bonuses).map(([name, bonus]) => `
      <div class="col-auto">
        <div class="card">
          <div class="card-body py-2 px-3">
            <div class="text-muted small">${name}</div>
            <div class="fw-bold text-green">+${formatMoney(bonus)} бонус</div>
            <div class="text-muted small">${formatMoney(data.by_staff[name])} продаж</div>
          </div>
        </div>
      </div>`).join('');
  }

  // Таблица
  if (!data.rows.length) {
    if (tbody) tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted py-4">Нет продаж за выбранный период</td></tr>';
    return;
  }

  const accountLabel = { card: '💳 Карта', cash: '💵 Наличные' };

  tbody.innerHTML = data.rows.map(r => {
    const productName = r.products?.name || '—';
    const bonus = Math.round(r.amount * 0.1);
    return `<tr>
      <td class="text-muted small">${r.date}</td>
      <td>${r.staff_name || '—'}</td>
      <td>${productName}</td>
      <td class="text-center">${r.quantity || 1}</td>
      <td>${accountLabel[r.account] || r.account}</td>
      <td class="text-end fw-bold">${formatMoney(r.amount)}</td>
      <td class="text-end text-green fw-bold">+${formatMoney(bonus)}</td>
      <td class="small text-muted">${r.notes || ''}</td>
      <td>
        <button class="btn btn-sm btn-ghost-danger" onclick="deleteSale(${r.id})">✕</button>
      </td>
    </tr>`;
  }).join('');
}

async function deleteSale(id) {
  if (!confirm('Удалить продажу?')) return;
  const res = await fetch(`/analytics/product-sales/${id}`, { method: 'DELETE' });
  const json = await res.json();
  if (json.ok) loadProductSales();
}

async function openAddSaleModal() {
  // Загружаем справочник товаров
  const data = await fetchData('/analytics/products');
  salesProducts = data?.products || [];

  const productOpts = salesProducts.map(p =>
    `<option value="${p.id}">${p.name}${p.price ? ' — ' + formatMoney(p.price) : ''}</option>`
  ).join('');

  const today = new Date().toISOString().slice(0, 10);

  document.getElementById('pl-detail-title').textContent = 'Добавить продажу товара';
  document.getElementById('pl-detail-body').innerHTML = `
    <div class="row g-3">
      <div class="col-md-6">
        <label class="form-label">Дата</label>
        <input type="date" class="form-control" id="sale-date" value="${today}">
      </div>
      <div class="col-md-6">
        <label class="form-label">Мастер</label>
        <select class="form-select" id="sale-staff">
          <option value="">Выберите мастера</option>
          <option>Александра</option>
          <option>Анастасия</option>
          <option>Анна</option>
          <option>Екатерина</option>
          <option>Марина</option>
          <option>Мария</option>
          <option>Светлана</option>
          <option>София</option>
          <option>Татьяна</option>
        </select>
      </div>
      <div class="col-md-6">
        <label class="form-label">Товар</label>
        <select class="form-select" id="sale-product">
          <option value="">Выберите товар</option>
          ${productOpts}
        </select>
        <div class="mt-1">
          <a href="javascript:void(0)" onclick="showAddProductForm()" class="small text-muted">+ Добавить новый товар</a>
        </div>
      </div>
      <div class="col-md-3">
        <label class="form-label">Кол-во</label>
        <input type="number" class="form-control" id="sale-qty" value="1" min="1">
      </div>
      <div class="col-md-3">
        <label class="form-label">Сумма ₽</label>
        <input type="number" class="form-control" id="sale-amount" placeholder="0">
      </div>
      <div class="col-md-6">
        <label class="form-label">Оплата</label>
        <select class="form-select" id="sale-account">
          <option value="card">💳 Карта</option>
          <option value="cash">💵 Наличные</option>
        </select>
      </div>
      <div class="col-12">
        <label class="form-label">Примечание</label>
        <input type="text" class="form-control" id="sale-notes" placeholder="Опционально">
      </div>
      <div id="add-product-form" style="display:none" class="col-12">
        <div class="card bg-light">
          <div class="card-body py-2">
            <div class="row g-2 align-items-end">
              <div class="col">
                <label class="form-label small">Название товара</label>
                <input type="text" class="form-control form-control-sm" id="new-product-name">
              </div>
              <div class="col-auto">
                <label class="form-label small">Цена ₽</label>
                <input type="number" class="form-control form-control-sm" id="new-product-price" style="width:100px">
              </div>
              <div class="col-auto">
                <button class="btn btn-sm btn-success" onclick="saveNewProduct()">Сохранить</button>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="col-12 d-flex gap-2 justify-content-end">
        <button class="btn btn-secondary" onclick="closePLDetail()">Отмена</button>
        <button class="btn btn-primary" onclick="submitSale()">Сохранить</button>
      </div>
    </div>`;

  document.getElementById('pl-detail-modal').style.display = 'flex';
}

function showAddProductForm() {
  const el = document.getElementById('add-product-form');
  if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

async function saveNewProduct() {
  const name = document.getElementById('new-product-name').value.trim();
  const price = document.getElementById('new-product-price').value;
  if (!name) return alert('Введите название товара');

  const res = await fetch('/analytics/products', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, price: price ? parseFloat(price) : null }),
  });
  const json = await res.json();
  if (json.ok) {
    salesProducts.push(json.product);
    const sel = document.getElementById('sale-product');
    const opt = document.createElement('option');
    opt.value = json.product.id;
    opt.textContent = json.product.name + (json.product.price ? ' — ' + formatMoney(json.product.price) : '');
    opt.selected = true;
    sel.appendChild(opt);
    document.getElementById('add-product-form').style.display = 'none';
    document.getElementById('new-product-name').value = '';
    document.getElementById('new-product-price').value = '';
  }
}

async function submitSale() {
  const date     = document.getElementById('sale-date').value;
  const staff    = document.getElementById('sale-staff').value;
  const product  = document.getElementById('sale-product').value;
  const qty      = document.getElementById('sale-qty').value;
  const amount   = document.getElementById('sale-amount').value;
  const account  = document.getElementById('sale-account').value;
  const notes    = document.getElementById('sale-notes').value;

  if (!date || !staff || !amount) return alert('Заполните дату, мастера и сумму');

  const res = await fetch('/analytics/product-sales', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      date, staff_name: staff,
      product_id: product ? parseInt(product) : null,
      quantity: parseInt(qty) || 1,
      amount: parseFloat(amount),
      account, notes,
    }),
  });
  const json = await res.json();
  if (json.ok) {
    closePLDetail();
    loadProductSales();
  } else {
    alert('Ошибка: ' + json.error);
  }
}
