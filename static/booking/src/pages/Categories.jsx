import { useEffect, useState, useRef } from "react";
import { getCategories } from "../api/booking";
import { T, s, LoadingScreen, CheckIcon } from "../theme";

const HIDDEN = ["Без группы", "Напитки", "Дополнительные услуги"];

function getCategoryIcon(title) {
  const t = title.toLowerCase();

  if (t.includes("head") || t.includes("голов")) return (
    <svg width="34" height="34" viewBox="0 0 34 34" fill="none">
      <circle cx="17" cy="13" r="7" stroke={T.gold} strokeWidth="1.2"/>
      <path d="M10 28c0-3.9 3.1-7 7-7s7 3.1 7 7" stroke={T.gold} strokeWidth="1.2" strokeLinecap="round"/>
      <path d="M14 11c0-1.7 1.3-3 3-3" stroke={T.gold} strokeWidth="1" strokeLinecap="round" opacity="0.5"/>
    </svg>
  );

  if (t.includes("масс")) return (
    <svg width="34" height="34" viewBox="0 0 34 34" fill="none">
      <path d="M8 17c0-5 4-9 9-9s9 4 9 9" stroke={T.gold} strokeWidth="1.2" strokeLinecap="round"/>
      <path d="M11 20c1-2 3-3 6-3s5 1 6 3" stroke={T.gold} strokeWidth="1.2" strokeLinecap="round"/>
      <circle cx="17" cy="24" r="2.5" stroke={T.gold} strokeWidth="1.2"/>
    </svg>
  );

  if (t.includes("spa") || t.includes("спа") || t.includes("ритуал")) return (
    <svg width="34" height="34" viewBox="0 0 34 34" fill="none">
      <path d="M17 8L20 14L27 15L22 20L23 27L17 24L11 27L12 20L7 15L14 14Z" stroke={T.gold} strokeWidth="1.1" strokeLinejoin="round"/>
    </svg>
  );

  if (t.includes("обёрт") || t.includes("обертыв")) return (
    <svg width="34" height="34" viewBox="0 0 34 34" fill="none">
      <ellipse cx="17" cy="17" rx="9" ry="6" stroke={T.gold} strokeWidth="1.2"/>
      <path d="M8 17c0 5 4 9 9 9s9-4 9-9" stroke={T.gold} strokeWidth="1.2" strokeLinecap="round"/>
      <path d="M13 14c1-1.5 2.5-2 4-2" stroke={T.gold} strokeWidth="1" strokeLinecap="round" opacity="0.5"/>
    </svg>
  );

  if (t.includes("фито") || t.includes("трав")) return (
    <svg width="34" height="34" viewBox="0 0 34 34" fill="none">
      <path d="M17 26V14" stroke={T.gold} strokeWidth="1.2" strokeLinecap="round"/>
      <path d="M17 18c0 0-4-3-4-7 0 0 4 1 4 7z" stroke={T.gold} strokeWidth="1.1" strokeLinejoin="round"/>
      <path d="M17 21c0 0 4-2 5-6 0 0-4 0-5 6z" stroke={T.gold} strokeWidth="1.1" strokeLinejoin="round"/>
    </svg>
  );

  if (t.includes("комб") || t.includes("выгод")) return (
    <svg width="34" height="34" viewBox="0 0 34 34" fill="none">
      <rect x="8" y="8" width="8" height="8" rx="2" stroke={T.gold} strokeWidth="1.2"/>
      <rect x="18" y="8" width="8" height="8" rx="2" stroke={T.gold} strokeWidth="1.2"/>
      <rect x="8" y="18" width="8" height="8" rx="2" stroke={T.gold} strokeWidth="1.2"/>
      <rect x="18" y="18" width="8" height="8" rx="2" stroke={T.gold} strokeWidth="1.2"/>
    </svg>
  );

  if (t.includes("дет") || t.includes("child")) return (
    <svg width="34" height="34" viewBox="0 0 34 34" fill="none">
      <circle cx="17" cy="13" r="5" stroke={T.gold} strokeWidth="1.2"/>
      <path d="M10 26c0-3.9 3.1-7 7-7s7 3.1 7 7" stroke={T.gold} strokeWidth="1.2" strokeLinecap="round"/>
      <path d="M14 11l1.5 1.5L19 10" stroke={T.gold} strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );

  if (t.includes("двоих") || t.includes("пар") || t.includes("double")) return (
    <svg width="34" height="34" viewBox="0 0 34 34" fill="none">
      <circle cx="13" cy="13" r="4.5" stroke={T.gold} strokeWidth="1.2"/>
      <circle cx="21" cy="13" r="4.5" stroke={T.gold} strokeWidth="1.2"/>
      <path d="M7 27c0-3.3 2.7-6 6-6h8c3.3 0 6 2.7 6 6" stroke={T.gold} strokeWidth="1.2" strokeLinecap="round"/>
    </svg>
  );

  // дефолт
  return (
    <svg width="34" height="34" viewBox="0 0 34 34" fill="none">
      <circle cx="17" cy="12" r="6" stroke={T.gold} strokeWidth="1.2"/>
      <path d="M9 28c0-4.4 3.6-8 8-8s8 3.6 8 8" stroke={T.gold} strokeWidth="1.2" strokeLinecap="round"/>
    </svg>
  );
}

const BG_COLORS = [
  "#1f1c16", "#161d18", "#16171e", "#1e1616",
  "#1a1c18", "#1c1a1e", "#1e1a16", "#161e1c",
];

export default function Categories({ next }) {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [picked, setPicked] = useState(null);
  // рандомные задержки shimmer — генерируются один раз
  const delays = useRef([]);

  useEffect(() => {
    getCategories().then((data) => {
      const filtered = data.filter((c) => !HIDDEN.includes(c.title));
      setCategories(filtered);
      delays.current = filtered.map(() =>
        `${(Math.random() * 5).toFixed(2)}s`
      );
      setLoading(false);
    });
  }, []);

  if (loading) return <LoadingScreen />;

  const handlePick = (cat) => {
    if (picked) return; // блокируем повторный клик пока идёт анимация
    setPicked(cat);
    setTimeout(() => next({ category: cat }), 300);
  };

  return (
    <div style={{ paddingBottom: 24 }}>
      <style>{`
        @keyframes checkPop {
          from { transform: scale(0); opacity: 0; }
          to   { transform: scale(1); opacity: 1; }
        }
        @keyframes shimmer {
          0%   { transform: translateX(-120%) rotate(20deg); opacity: 0; }
          15%  { opacity: 1; }
          85%  { opacity: 1; }
          100% { transform: translateX(220%) rotate(20deg); opacity: 0; }
        }
      `}</style>

      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 10,
        marginBottom: 14,
      }}>
        {categories.map((cat, i) => {
          const isPicked = picked?.id === cat.id;

          return (
            <div
              key={cat.id}
              onClick={() => handlePick(cat)}
              className="cat-card"
              style={{
                ...s.card,
                ...(isPicked ? s.cardPicked : {}),
                transform: isPicked ? "scale(0.97)" : "scale(1)",
                cursor: picked ? "default" : "pointer",
              }}
            >
              {/* Gold glow при выборе */}
              <div style={{
                position: "absolute", inset: 0, borderRadius: 18,
                background: "radial-gradient(ellipse at 50% 0%, rgba(200,169,110,0.11), transparent 65%)",
                opacity: isPicked ? 1 : 0,
                transition: "opacity 0.4s ease",
                pointerEvents: "none",
                zIndex: 1,
              }} />

              {/* Shimmer — переливание градиентом */}
              <div style={{
                position: "absolute", inset: 0, borderRadius: 18,
                overflow: "hidden", pointerEvents: "none", zIndex: 1,
                opacity: isPicked ? 0 : 1,
                transition: "opacity 0.3s ease",
              }}>
                <div style={{
                  position: "absolute",
                  top: "-30%", bottom: "-30%",
                  width: "50%",
                  background: "linear-gradient(90deg, transparent 0%, rgba(200,169,110,0.08) 50%, transparent 100%)",
                  animation: `shimmer 5s ease-in-out infinite`,
                  animationDelay: delays.current[i] || "0s",
                }} />
              </div>

              {/* Медиа — фото или иконка */}
              <div style={{
                height: 82,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: BG_COLORS[i % BG_COLORS.length],
                overflow: "hidden",
                position: "relative",
                flexShrink: 0,
              }}>
                {cat.image_url
                  ? <img
                      src={cat.image_url}
                      alt={cat.title}
                      style={{
                        width: "100%", height: "100%", objectFit: "cover",
                        opacity: isPicked ? 1 : 0.85,
                        transition: "opacity 0.3s ease",
                      }}
                    />
                  : <div style={{
                      transform: isPicked ? "scale(1.1)" : "scale(1)",
                      transition: "transform 0.4s cubic-bezier(0.34,1.56,0.64,1)",
                    }}>
                      {getCategoryIcon(cat.title)}
                    </div>
                }
              </div>

              {/* Чекбокс при выборе */}
              {isPicked && (
                <div style={{
                  position: "absolute", top: 9, right: 9,
                  width: 20, height: 20, borderRadius: "50%",
                  background: T.gold,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  zIndex: 3,
                  animation: "checkPop 0.28s cubic-bezier(0.34,1.56,0.64,1) both",
                }}>
                  <CheckIcon />
                </div>
              )}

              {/* Название + количество */}
              <div style={{ padding: "10px 12px 13px", position: "relative", zIndex: 2 }}>
                <div style={{
                  fontFamily: T.font, fontSize: 13, fontWeight: 500,
                  color: isPicked ? T.gold : T.text,
                  transition: "color 0.25s",
                  lineHeight: 1.3,
                }}>
                  {cat.title}
                </div>
                {cat.services_count > 0 && (
                  <div style={{
                    fontFamily: T.font, fontSize: 11,
                    color: T.textMuted, fontWeight: 300, marginTop: 2,
                  }}>
                    {cat.services_count} услуг
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
