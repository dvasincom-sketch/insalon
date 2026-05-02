import { useEffect, useState } from "react";
import { getCategories } from "../api/booking";
import { T, s, LoadingScreen, CheckIcon, NextBtn, BackBtn } from "../theme";

const HIDDEN = ["Без группы", "Напитки", "Дополнительные услуги"];

const CATEGORY_ICONS = {
  default: (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
      <circle cx="18" cy="12" r="6.5" stroke={T.gold} strokeWidth="1.2"/>
      <path d="M8 30c0-5.5 4.5-10 10-10s10 4.5 10 10" stroke={T.gold} strokeWidth="1.2" strokeLinecap="round"/>
      <circle cx="18" cy="12" r="3" fill={T.goldGlow}/>
    </svg>
  ),
};

const BG_COLORS = [
  "#1f1c16", "#161d18", "#16171e", "#1e1616",
  "#1a1c18", "#1c1a1e", "#1e1a16", "#161e1c",
];

export default function Categories({ next }) {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [picked, setPicked] = useState(null);

  useEffect(() => {
    getCategories().then((data) => {
      setCategories(data.filter((c) => !HIDDEN.includes(c.title)));
      setLoading(false);
    });
  }, []);

  if (loading) return <LoadingScreen />;

  const handlePick = (cat) => {
    setPicked(cat);
    setTimeout(() => next({ category: cat }), 260);
  };

  return (
    <div style={{ paddingBottom: 24 }}>
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
              }}
            >
              <div style={{
                position: "absolute", inset: 0,
                background: "radial-gradient(ellipse at 50% 0%, rgba(200,169,110,0.09), transparent 65%)",
                opacity: isPicked ? 1 : 0,
                transition: "opacity 0.4s ease",
                pointerEvents: "none",
                borderRadius: 18,
              }} />

              <div style={{
                height: 82,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: BG_COLORS[i % BG_COLORS.length],
                overflow: "hidden",
                position: "relative",
              }}>
                {cat.image_url
                  ? <img src={cat.image_url} alt={cat.title} style={{ width: "100%", height: "100%", objectFit: "cover", opacity: 0.85 }} />
                  : <div style={{ transform: isPicked ? "scale(1.12)" : "scale(1)", transition: "transform 0.4s cubic-bezier(0.34,1.56,0.64,1)" }}>
                      {CATEGORY_ICONS.default}
                    </div>
                }
              </div>

              {isPicked && (
                <div style={{
                  position: "absolute", top: 9, right: 9,
                  width: 20, height: 20,
                  borderRadius: "50%",
                  background: T.gold,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  zIndex: 3,
                  animation: "checkPop 0.3s cubic-bezier(0.34,1.56,0.64,1) both",
                }}>
                  <CheckIcon />
                </div>
              )}

              <div style={{ padding: "10px 12px 13px" }}>
                <div style={{
                  fontFamily: T.font, fontSize: 13, fontWeight: 500,
                  color: isPicked ? T.gold : T.text, marginBottom: 2,
                  transition: "color 0.25s",
                }}>
                  {cat.title}
                </div>
                <div style={{ fontFamily: T.font, fontSize: 11, color: T.textMuted, fontWeight: 300 }}>
                  {cat.services_count ? `${cat.services_count} услуг` : "Нажмите для выбора"}
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <style>{`@keyframes checkPop{from{transform:scale(0)}to{transform:scale(1)}}`}</style>
    </div>
  );
}
