// routes/zones2gis.js
// Прокси к 2GIS Catalog API — решает CORS, прячет ключ на сервере
// Подключить в server.js: app.use('/api/lovi', require('./routes/zones2gis'))

const express = require('express')
const router = express.Router()

const DGIS_KEY = process.env.DGIS_API_KEY || 'a0c99e2a-de74-4d58-9ed4-2b33d269050e'
const DGIS_BASE = 'https://catalog.api.2gis.com/3.0/items'

// Простая защита: принимаем запросы только с нашего домена
// (Render автоматически добавляет заголовки, поэтому в dev убираем проверку)
function isAllowed(req) {
  if (process.env.NODE_ENV !== 'production') return true
  const origin = req.headers.origin || req.headers.referer || ''
  return origin.includes('lovi.today') || origin.includes('localhost')
}

// GET /api/lovi/zones/search?lat=55.648&lon=37.535&radius=550&q=массаж
router.get('/zones/search', async (req, res) => {
  if (!isAllowed(req)) {
    return res.status(403).json({ error: 'Forbidden' })
  }

  const { lat, lon, radius = 600, q = 'массаж' } = req.query
  if (!lat || !lon) {
    return res.status(400).json({ error: 'lat и lon обязательны' })
  }

  const url = new URL(DGIS_BASE)
  url.searchParams.set('q', q)
  url.searchParams.set('point', `${lon},${lat}`)
  url.searchParams.set('radius', radius)
  url.searchParams.set('type', 'branch')
  url.searchParams.set('fields', 'items.point,items.address_name,items.reviews,items.rubrics')
  url.searchParams.set('page_size', '50')
  url.searchParams.set('key', DGIS_KEY)
  url.searchParams.set('locale', 'ru_RU')

  try {
    const upstream = await fetch(url.toString())
    if (!upstream.ok) {
      const text = await upstream.text()
      return res.status(upstream.status).json({ error: text })
    }

    const data = await upstream.json()
    // Нормализуем структуру — 2GIS возвращает result.items или items
    const raw = data?.result?.items ?? data?.items ?? []

    const items = raw.map(it => ({
      name: it.name,
      address: it.address_name ?? it.address?.name ?? '',
      rating: it.reviews?.rating_frequency
        ? Number(it.reviews.rating_frequency).toFixed(1)
        : null,
      reviews_count: it.reviews?.general_review_count_with_stars ?? null,
      lat: it.point?.lat ?? null,
      lon: it.point?.lon ?? null,
      rubrics: (it.rubrics ?? []).map(r => r.name).slice(0, 3),
    }))

    res.json({
      count: items.length,
      items,
      meta: {
        query: q,
        lat: Number(lat),
        lon: Number(lon),
        radius: Number(radius),
        fetched_at: new Date().toISOString(),
      },
    })
  } catch (err) {
    console.error('[zones2gis] upstream error:', err)
    res.status(502).json({ error: 'Upstream error', detail: err.message })
  }
})

module.exports = router
