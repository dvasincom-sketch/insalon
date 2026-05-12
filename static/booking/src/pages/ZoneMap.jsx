import { useState, useCallback } from 'react'
import { MapPin, Search, ChevronLeft, AlertCircle, CheckCircle, Star } from 'lucide-react'

// ─── Иконка-helper ──────────────────────────────────────────────────────────
const Icon = ({ i: I, size = 16, color = 'currentColor', stroke = 1.5, style = {} }) => (
  <I size={size} color={color} strokeWidth={stroke} style={{ flexShrink: 0, ...style }} />
)

// ─── Доменная модель v0 ──────────────────────────────────────────────────────
// Временно в коде — потом вынесем в БД вместе с DISTRICTS из Home.jsx
// Все координаты — центроид зоны, радиус — пешеходный охват в метрах
const DISTRICTS = [
  {
    id: 'konkovo',
    name: 'Коньково',
    zones: [
      {
        id: 'yabloneviy-sad',
        name: 'Яблоневый сад',
        anchor: 'м. Беляево, выходы 1–2',
        lat: 55.6445, lon: 37.5297, radius: 600,
        barrier: 'Профсоюзная (восток), Миклухо-Маклая (юг)',
        slots: 2, taken: [],
      },
      {
        id: 'konkovskie-prudy',
        name: 'Коньковские пруды',
        anchor: 'м. Беляево вых. 3–4 / м. Коньково',
        lat: 55.6370, lon: 37.5210, radius: 650,
        barrier: 'Профсоюзная (запад), Битцевский лес (юг)',
        slots: 2, taken: [],
      },
      {
        id: 'derevlyovskiy-prud',
        name: 'Деревлёвский пруд',
        anchor: 'м. Беляево, выходы 7–8',
        lat: 55.6500, lon: 37.5450, radius: 600,
        barrier: 'Миклухо-Маклая (север), Севастопольский пр. (восток)',
        slots: 2, taken: [],
      },
      {
        id: 'belyaevo-center',
        name: 'Беляево центр',
        anchor: 'м. Беляево, выход 6',
        lat: 55.6480, lon: 37.5350, radius: 550,
        barrier: 'Миклухо-Маклая (ось), Профсоюзная (запад)',
        slots: 2,
        taken: [{ index: 0, salon: 'Head Spa Beauty', address: 'ул. Миклухо-Маклая 37' }],
      },
      {
        id: 'obrucheva',
        name: 'Обручева',
        anchor: 'ул. Обручева (авт. от Беляево)',
        lat: 55.6570, lon: 37.5280, radius: 600,
        barrier: 'Профсоюзная (барьер на юге)',
        slots: 2, taken: [],
      },
      {
        id: 'kaluzhskaya-border',
        name: 'Калужская (граница)',
        anchor: 'м. Калужская',
        lat: 55.6630, lon: 37.5175, radius: 550,
        barrier: 'Профсоюзная (барьер с севера)',
        slots: 2, taken: [],
      },
    ],
  },
  // Обручевский, Ломоносовский, Черёмушки — добавить после описания районов
]

// ─── Утилиты ────────────────────────────────────────────────────────────────
const API_BASE = 'https://insalon.onrender.com/api/lovi'

async function searchZone(zone) {
  const params = new URLSearchParams({
    lat: zone.lat,
    lon: zone.lon,
    radius: zone.radius,
    q: 'массаж',
  })
  const r = await fetch(`${API_BASE}/zones/search?${params}`)
  if (!r.ok) {
    const err = await r.json().catch(() => ({}))
    throw new Error(err.error || `HTTP ${r.status}`)
  }
  return r.json()
}

function competitionLabel(count) {
  if (count === 0) return { text: 'нет конкурентов', level: 'success' }
  if (count <= 2) return { text: `${count} конкурента`, level: 'success' }
  if (count <= 5) return { text: `${count} конкурентов`, level: 'warning' }
  return { text: `${count} конкурентов`, level: 'danger' }
}

const LEVEL_COLORS = {
  success: { bg: 'rgba(16,185,129,0.1)', color: '#065f46' },
  warning: { bg: 'rgba(245,158,11,0.1)', color: '#78350f' },
  danger:  { bg: 'rgba(239,68,68,0.1)',  color: '#7f1d1d' },
}

// ═══════════════════════════════════════════════════════════════════════════
// КОМПОНЕНТЫ
// ═══════════════════════════════════════════════════════════════════════════

function Badge({ level, text }) {
  const c = LEVEL_COLORS[level]
  return (
    <span style={{
      background: c.bg, color: c.color,
      fontSize: 11, fontWeight: 600,
      padding: '3px 8px', borderRadius: 6,
      whiteSpace: 'nowrap',
    }}>
      {text}
    </span>
  )
}

function SlotDots({ zone }) {
  return (
    <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
      {Array.from({ length: zone.slots }).map((_, i) => {
        const isTaken = i < zone.taken.length
        return (
          <div key={i} style={{
            width: 9, height: 9, borderRadius: '50%',
            background: isTaken ? '#F97316' : 'rgba(18,26,18,0.15)',
            border: isTaken ? 'none' : '1px solid rgba(18,26,18,0.2)',
          }} />
        )
      })}
      <span style={{ fontSize: 11, color: '#8F8475', marginLeft: 4 }}>
        {zone.slots - zone.taken.length} из {zone.slots}
      </span>
    </div>
  )
}

// Карточка зоны в списке
function ZoneCard({ zone, data, loading, onClick, active }) {
  const label = data ? competitionLabel(data.count) : null

  return (
    <div
      onClick={onClick}
      style={{
        background: active ? '#fff' : 'rgba(255,255,255,0.6)',
        border: active ? '1.5px solid #F97316' : '1px solid rgba(18,26,18,0.08)',
        borderRadius: 16,
        padding: '14px 16px',
        cursor: 'pointer',
        transition: 'all 0.2s',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: '#121A12', lineHeight: 1.2 }}>
          {zone.name}
        </div>
        {loading && (
          <span style={{ fontSize: 11, color: '#8F8475' }}>загрузка…</span>
        )}
        {label && !loading && <Badge level={label.level} text={label.text} />}
      </div>
      <div style={{ fontSize: 12, color: '#8F8475', marginBottom: 10 }}>
        {zone.anchor}
      </div>
      <SlotDots zone={zone} />
    </div>
  )
}

// Панель деталей зоны
function ZoneDetail({ zone, data, loading, onClose }) {
  if (!zone) return null

  return (
    <div style={{
      background: '#fff',
      border: '1px solid rgba(18,26,18,0.08)',
      borderRadius: 20,
      padding: '24px',
      height: '100%',
      boxSizing: 'border-box',
      overflowY: 'auto',
    }}>
      <button
        onClick={onClose}
        style={{
          background: 'transparent', border: 'none', cursor: 'pointer',
          color: '#8F8475', fontSize: 12, fontWeight: 600,
          padding: 0, marginBottom: 16,
          display: 'flex', alignItems: 'center', gap: 6,
          fontFamily: 'inherit',
        }}
      >
        <Icon i={ChevronLeft} size={14} /> все зоны
      </button>

      <div style={{ fontSize: 22, fontFamily: 'Playfair Display,serif', color: '#121A12', marginBottom: 4 }}>
        {zone.name}
      </div>
      <div style={{ fontSize: 13, color: '#8F8475', marginBottom: 20 }}>
        {zone.anchor}
      </div>

      {/* Мета-строки */}
      {[
        ['Барьеры', zone.barrier],
        ['Радиус поиска', `${zone.radius} м`],
        ['Слотов', `${zone.slots - zone.taken.length} свободно из ${zone.slots}`],
      ].map(([label, val]) => (
        <div key={label} style={{
          display: 'flex', gap: 12, fontSize: 13,
          padding: '8px 0', borderBottom: '1px solid rgba(18,26,18,0.06)',
        }}>
          <span style={{ color: '#8F8475', minWidth: 110 }}>{label}</span>
          <span style={{ color: '#121A12' }}>{val}</span>
        </div>
      ))}

      {/* Наши партнёры */}
      {zone.taken.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#8F8475', marginBottom: 8 }}>
            Наш партнёр
          </div>
          {zone.taken.map(t => (
            <div key={t.salon} style={{
              display: 'flex', gap: 10, alignItems: 'flex-start',
              background: 'rgba(249,115,22,0.06)',
              border: '1px solid rgba(249,115,22,0.2)',
              borderRadius: 10, padding: '10px 12px',
            }}>
              <Icon i={CheckCircle} size={16} color="#F97316" style={{ marginTop: 2 }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#121A12' }}>{t.salon}</div>
                <div style={{ fontSize: 12, color: '#8F8475', marginTop: 2 }}>{t.address}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Конкуренты из 2GIS */}
      <div style={{ marginTop: 20 }}>
        <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#8F8475', marginBottom: 10 }}>
          Конкуренты в зоне
        </div>

        {loading && (
          <div style={{ fontSize: 13, color: '#8F8475' }}>Загружаем данные 2GIS…</div>
        )}

        {!loading && data && data.count === 0 && (
          <div style={{ fontSize: 13, color: '#065f46', background: 'rgba(16,185,129,0.08)', borderRadius: 10, padding: '10px 12px' }}>
            Конкурентов в зоне не найдено — хорошая возможность.
          </div>
        )}

        {!loading && data && data.items.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {data.items.map((item, i) => (
              <div key={i} style={{
                background: 'rgba(18,26,18,0.03)',
                border: '1px solid rgba(18,26,18,0.06)',
                borderRadius: 10, padding: '10px 12px',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ fontSize: 13, fontWeight: 500, color: '#121A12', flex: 1, marginRight: 8 }}>
                    {item.name}
                  </div>
                  {item.rating && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
                      <Icon i={Star} size={12} color="#F97316" />
                      <span style={{ fontSize: 12, color: '#121A12', fontWeight: 500 }}>{item.rating}</span>
                      {item.reviews_count && (
                        <span style={{ fontSize: 11, color: '#8F8475' }}>({item.reviews_count})</span>
                      )}
                    </div>
                  )}
                </div>
                {item.address && (
                  <div style={{ fontSize: 12, color: '#8F8475', marginTop: 3 }}>{item.address}</div>
                )}
                {item.rubrics && item.rubrics.length > 0 && (
                  <div style={{ fontSize: 11, color: '#8F8475', marginTop: 4 }}>
                    {item.rubrics.join(' · ')}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {!loading && !data && (
          <div style={{ fontSize: 13, color: '#8F8475' }}>
            Нажмите «Загрузить все» чтобы получить данные.
          </div>
        )}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// ГЛАВНАЯ СТРАНИЦА
// ═══════════════════════════════════════════════════════════════════════════
export default function ZoneMap() {
  const [activeDistrictId, setActiveDistrictId] = useState(DISTRICTS[0].id)
  const [activeZoneId, setActiveZoneId] = useState(null)
  const [zoneData, setZoneData] = useState({})
  const [loading, setLoading] = useState({})
  const [globalLoading, setGlobalLoading] = useState(false)
  const [error, setError] = useState(null)
  const [lastFetched, setLastFetched] = useState(null)

  const activeDistrict = DISTRICTS.find(d => d.id === activeDistrictId)
  const activeZone = activeDistrict?.zones.find(z => z.id === activeZoneId)

  const fetchAll = useCallback(async () => {
    setGlobalLoading(true)
    setError(null)
    const allZones = DISTRICTS.flatMap(d => d.zones)
    for (const z of allZones) {
      setLoading(prev => ({ ...prev, [z.id]: true }))
      try {
        const data = await searchZone(z)
        setZoneData(prev => ({ ...prev, [z.id]: data }))
      } catch (e) {
        setZoneData(prev => ({ ...prev, [z.id]: { count: 0, items: [], error: e.message } }))
      } finally {
        setLoading(prev => ({ ...prev, [z.id]: false }))
      }
      await new Promise(r => setTimeout(r, 350))
    }
    setGlobalLoading(false)
    setLastFetched(new Date())
  }, [])

  const fetchOne = useCallback(async (zone) => {
    setLoading(prev => ({ ...prev, [zone.id]: true }))
    setError(null)
    try {
      const data = await searchZone(zone)
      setZoneData(prev => ({ ...prev, [zone.id]: data }))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(prev => ({ ...prev, [zone.id]: false }))
    }
  }, [])

  const totalZones = DISTRICTS.flatMap(d => d.zones).length
  const loadedCount = Object.keys(zoneData).length

  return (
    <div style={{
      background: '#FDFCF9', minHeight: '100vh',
      fontFamily: 'Inter, system-ui, sans-serif',
      color: '#121A12',
    }}>
      {/* Шапка */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 50,
        background: 'rgba(253,252,249,0.9)', backdropFilter: 'blur(12px)',
        borderBottom: '1px solid rgba(18,26,18,0.08)',
        padding: '14px 32px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16,
        flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <img src="/logo.svg" alt="Лови" style={{ height: 20 }} />
          <span style={{
            fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase',
            color: '#8F8475', fontWeight: 600,
          }}>
            Аналитика зон спроса
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          {lastFetched && (
            <span style={{ fontSize: 12, color: '#8F8475' }}>
              Обновлено: {lastFetched.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
          {loadedCount > 0 && (
            <span style={{ fontSize: 12, color: '#8F8475' }}>
              {loadedCount} из {totalZones} зон
            </span>
          )}
          <button
            onClick={fetchAll}
            disabled={globalLoading}
            style={{
              background: globalLoading ? 'rgba(18,26,18,0.4)' : '#121A12',
              color: '#fff', border: 'none',
              padding: '8px 16px', borderRadius: 12,
              fontSize: 13, fontWeight: 600,
              cursor: globalLoading ? 'not-allowed' : 'pointer',
              fontFamily: 'inherit',
              display: 'flex', alignItems: 'center', gap: 8,
            }}
          >
            <Icon i={Search} size={14} color="#fff" />
            {globalLoading ? 'Загружаем…' : 'Загрузить все зоны'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          margin: '16px 32px 0',
          background: 'rgba(239,68,68,0.08)',
          border: '1px solid rgba(239,68,68,0.2)',
          borderRadius: 10, padding: '10px 14px',
          display: 'flex', gap: 10, alignItems: 'center',
          fontSize: 13, color: '#7f1d1d',
        }}>
          <Icon i={AlertCircle} size={16} color="#dc2626" />
          {error}
        </div>
      )}

      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '32px 32px' }}>
        {/* Табы районов */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 24, flexWrap: 'wrap' }}>
          {DISTRICTS.map(d => {
            const zones = d.zones
            const loaded = zones.filter(z => zoneData[z.id]).length
            const isActive = d.id === activeDistrictId
            return (
              <button
                key={d.id}
                onClick={() => { setActiveDistrictId(d.id); setActiveZoneId(null) }}
                style={{
                  background: isActive ? '#121A12' : 'transparent',
                  color: isActive ? '#fff' : '#121A12',
                  border: isActive ? 'none' : '1px solid rgba(18,26,18,0.15)',
                  padding: '8px 16px', borderRadius: 12,
                  fontSize: 13, fontWeight: isActive ? 600 : 400,
                  cursor: 'pointer', fontFamily: 'inherit',
                  display: 'flex', alignItems: 'center', gap: 8,
                }}
              >
                {d.name}
                {loaded > 0 && (
                  <span style={{
                    background: isActive ? 'rgba(255,255,255,0.2)' : 'rgba(18,26,18,0.08)',
                    fontSize: 10, padding: '2px 6px', borderRadius: 6,
                  }}>
                    {loaded}/{zones.length}
                  </span>
                )}
              </button>
            )
          })}
        </div>

        {/* Двухколоночный лейаут */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: activeZone ? '1fr 1.4fr' : '1fr',
          gap: 16,
          alignItems: 'flex-start',
        }}>
          {/* Список зон */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {activeDistrict?.zones.map(zone => (
              <ZoneCard
                key={zone.id}
                zone={zone}
                data={zoneData[zone.id]}
                loading={!!loading[zone.id]}
                active={activeZoneId === zone.id}
                onClick={() => {
                  setActiveZoneId(prev => prev === zone.id ? null : zone.id)
                  if (!zoneData[zone.id] && !loading[zone.id]) {
                    fetchOne(zone)
                  }
                }}
              />
            ))}
          </div>

          {/* Деталь */}
          {activeZone && (
            <div style={{ position: 'sticky', top: 80 }}>
              <ZoneDetail
                zone={activeZone}
                data={zoneData[activeZone.id]}
                loading={!!loading[activeZone.id]}
                onClose={() => setActiveZoneId(null)}
              />
            </div>
          )}
        </div>

        {/* Сводная статистика */}
        {loadedCount > 0 && (
          <div style={{
            marginTop: 40, paddingTop: 32,
            borderTop: '1px solid rgba(18,26,18,0.08)',
          }}>
            <div style={{
              fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase',
              color: '#8F8475', marginBottom: 16, fontWeight: 600,
            }}>
              Сводка по всем загруженным зонам
            </div>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
              gap: 12,
            }}>
              {[
                {
                  label: 'Всего конкурентов',
                  value: Object.values(zoneData).reduce((s, d) => s + (d?.count || 0), 0),
                },
                {
                  label: 'Зон без конкурентов',
                  value: Object.values(zoneData).filter(d => d?.count === 0).length,
                },
                {
                  label: 'Высокая плотность (6+)',
                  value: Object.values(zoneData).filter(d => d?.count >= 6).length,
                },
                {
                  label: 'Зон загружено',
                  value: `${loadedCount} / ${totalZones}`,
                },
              ].map(({ label, value }) => (
                <div key={label} style={{
                  background: 'rgba(18,26,18,0.03)',
                  border: '1px solid rgba(18,26,18,0.06)',
                  borderRadius: 14, padding: '14px 16px',
                }}>
                  <div style={{ fontSize: 24, fontWeight: 600, color: '#121A12', fontFamily: 'Playfair Display,serif' }}>
                    {value}
                  </div>
                  <div style={{ fontSize: 12, color: '#8F8475', marginTop: 4 }}>{label}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
