// routes/zones2gis.js
// Прокси к 2GIS Catalog API + Supabase-кэш (обновление вручную)
// Подключить в server.js: app.use('/api/lovi', require('./routes/zones2gis'))

const express = require('express')
const router  = express.Router()
const { createClient } = require('@supabase/supabase-js')

const DGIS_KEY  = process.env.DGIS_API_KEY
const DGIS_BASE = 'https://catalog.api.2gis.com/3.0/items'

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
)

function isAllowed(req) {
  if (process.env.NODE_ENV !== 'production') return true
  const origin = req.headers.origin || req.headers.referer || ''
  return origin.includes('lovi.today') || origin.includes('localhost')
}

// ─── Запрос к 2GIS ─────────────────────────────────────────────────────────
async function fetch2gis({ lat, lon, radius, q = 'массаж' }) {
  const url = new URL(DGIS_BASE)
  url.searchParams.set('q', q)
  url.searchParams.set('point', `${lon},${lat}`)
  url.searchParams.set('radius', radius)
  url.searchParams.set('type', 'branch')
  url.searchParams.set('fields', 'items.point,items.address_name,items.reviews,items.rubrics,items.id')
  url.searchParams.set('page_size', '50')
  url.searchParams.set('key', DGIS_KEY)
  url.searchParams.set('locale', 'ru_RU')

  const r = await fetch(url.toString())
  if (!r.ok) throw new Error(`2GIS HTTP ${r.status}`)
  const data = await r.json()
  const raw = data?.result?.items ?? data?.items ?? []

  return raw.map(it => ({
    dgis_id:       it.id ?? null,
    name:          it.name,
    address:       it.address_name ?? it.address?.name ?? '',
    rating:        it.reviews?.rating_frequency
                     ? Number(it.reviews.rating_frequency).toFixed(1)
                     : null,
    reviews_count: it.reviews?.general_review_count_with_stars ?? null,
    lat:           it.point?.lat ?? null,
    lon:           it.point?.lon ?? null,
    rubrics:       (it.rubrics ?? []).map(r => r.name).slice(0, 3),
  }))
}

// ─── Дедупликация ──────────────────────────────────────────────────────────
// Один объект 2GIS попадает только в одну зону (первую по порядку).
// Ключ: dgis_id если есть, иначе name+address.
function deduplicateAcrossZones(zoneItemsMap) {
  const seen = new Set()
  const result = {}
  for (const [zoneId, items] of Object.entries(zoneItemsMap)) {
    result[zoneId] = items.filter(item => {
      const key = item.dgis_id
        ? `id:${item.dgis_id}`
        : `na:${item.name.toLowerCase()}|${item.address.slice(0, 20).toLowerCase()}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
  }
  return result
}

// ─── GET /api/lovi/zones/search?zone_id=belyaevo-center ────────────────────
// Читает из кэша. Если кэша нет — cache_miss: true.
router.get('/zones/search', async (req, res) => {
  if (!isAllowed(req)) return res.status(403).json({ error: 'Forbidden' })
  const { zone_id } = req.query
  if (!zone_id) return res.status(400).json({ error: 'zone_id обязателен' })

  const { data, error } = await supabase
    .from('zone_2gis_cache')
    .select('items, fetched_at')
    .eq('zone_id', zone_id)
    .maybeSingle()

  if (error) return res.status(500).json({ error: error.message })
  if (!data) return res.json({ zone_id, count: 0, items: [], fetched_at: null, cache_miss: true })

  return res.json({
    zone_id,
    count: data.items.length,
    items: data.items,
    fetched_at: data.fetched_at,
    cache_miss: false,
  })
})

// ─── POST /api/lovi/zones/refresh ──────────────────────────────────────────
// Запрашивает 2GIS, дедуплицирует, сохраняет в Supabase.
// Body: { zones: [{ id, lat, lon, radius }] }
router.post('/zones/refresh', async (req, res) => {
  if (!isAllowed(req)) return res.status(403).json({ error: 'Forbidden' })
  const { zones } = req.body
  if (!Array.isArray(zones) || zones.length === 0) {
    return res.status(400).json({ error: 'zones[] обязателен' })
  }

  const zoneItemsMap = {}
  const errors = []

  await Promise.all(zones.map(async (z) => {
    try {
      zoneItemsMap[z.id] = await fetch2gis({ lat: z.lat, lon: z.lon, radius: z.radius })
    } catch (e) {
      errors.push({ zone_id: z.id, error: e.message })
      zoneItemsMap[z.id] = []
    }
  }))

  const deduped = deduplicateAcrossZones(zoneItemsMap)
  const fetched_at = new Date().toISOString()

  const rows = Object.entries(deduped).map(([zone_id, items]) => ({
    zone_id, items, fetched_at,
  }))

  const { error: upsertError } = await supabase
    .from('zone_2gis_cache')
    .upsert(rows, { onConflict: 'zone_id' })

  if (upsertError) return res.status(500).json({ error: upsertError.message })

  return res.json({
    ok: true,
    fetched_at,
    zones: Object.entries(deduped).map(([zone_id, items]) => ({ zone_id, count: items.length })),
    errors: errors.length ? errors : undefined,
  })
})

module.exports = router
