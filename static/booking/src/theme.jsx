export const T = {
  bg: "#111110",
  s1: "#181816",
  s2: "#1e1e1b",
  s3: "#252520",
  border: "#2a2a26",
  borderHi: "rgba(200,169,110,0.28)",
  gold: "#c8a96e",
  goldDim: "#8a6e42",
  goldGlow: "rgba(200,169,110,0.14)",
  green: "#5a9467",
  greenDim: "#3d6b4a",
  text: "#f2ede4",
  textMid: "#c0bcb6",
  textMuted: "#8a8480",
  font: "'Outfit', sans-serif",
  serif: "'Playfair Display', serif",
};

export const fonts = `
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,300;0,400;1,300&family=Outfit:wght@300;400;500&display=swap');
`;

export const globalReset = `
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
  body { background: ${T.bg}; }
`;

export const s = {
  phone: {
    background: T.bg,
    minHeight: "100dvh",
    maxWidth: 430,
    margin: "0 auto",
    display: "flex",
    flexDirection: "column",
    fontFamily: T.font,
    color: T.text,
    position: "relative",
    overflow: "hidden",
  },
  header: {
    padding: "20px 24px 0",
    flexShrink: 0,
    position: "relative",
    zIndex: 2,
  },
  wordmark: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 18,
  },
  wordmarkLine: {
    width: 20,
    height: 1,
    background: T.goldDim,
  },
  wordmarkText: {
    fontFamily: T.font,
    fontSize: 10,
    fontWeight: 300,
    letterSpacing: "0.25em",
    color: T.goldDim,
    textTransform: "none",
  },
  progressTrack: {
    height: 2,
    background: T.s3,
    borderRadius: 1,
    marginBottom: 14,
    overflow: "hidden",
    position: "relative",
  },
  stepMeta: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 18,
  },
  stepNum: {
    fontFamily: T.font,
    fontSize: 11,
    fontWeight: 300,
    color: T.textMuted,
    letterSpacing: "0.12em",
  },
  screenTitle: {
    fontFamily: T.serif,
    fontWeight: 300,
    fontSize: 30,
    lineHeight: 1.1,
    color: T.text,
    marginBottom: 4,
    letterSpacing: "-0.01em",
  },
  screenHint: {
    fontFamily: T.font,
    fontSize: 12,
    color: T.textMuted,
    marginBottom: 16,
    fontWeight: 300,
  },
  body: {
    flex: 1,
    overflowY: "auto",
    padding: "0 24px",
    position: "relative",
    zIndex: 2,
    scrollbarWidth: "none",
  },
  footer: {
    padding: "14px 24px 32px",
    flexShrink: 0,
    position: "relative",
    zIndex: 2,
    borderTop: `1px solid ${T.border}`,
  },
  footerInner: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  card: {
    background: T.s2,
    border: `1px solid ${T.border}`,
    borderRadius: 18,
    overflow: "hidden",
    cursor: "pointer",
    transition: "all 0.28s cubic-bezier(0.34,1.56,0.64,1)",
    position: "relative",
    WebkitUserSelect: "none",
    userSelect: "none",
  },
  cardPicked: {
    borderColor: T.gold,
    background: T.s1,
  },
  row: {
    display: "flex",
    alignItems: "center",
    gap: 13,
    padding: "13px 14px",
    background: T.s2,
    border: `1px solid ${T.border}`,
    borderRadius: 16,
    cursor: "pointer",
    transition: "all 0.25s",
    position: "relative",
    overflow: "hidden",
  },
  rowPicked: {
    borderColor: T.gold,
  },
  label: {
    fontFamily: T.font,
    fontSize: 10,
    letterSpacing: "0.12em",
    textTransform: "none",
    color: T.textMuted,
    marginBottom: 8,
    fontWeight: 300,
  },
  timeSlot: {
    height: 40,
    borderRadius: 10,
    border: `1px solid ${T.border}`,
    background: "transparent",
    fontFamily: "'Outfit',sans-serif",
    fontSize: 13,
    color: T.textMid,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    transition: "all 0.22s",
    fontWeight: 300,
  },
  timeSlotPicked: {
    background: T.s1,
    borderColor: T.gold,
    color: T.gold,
    fontWeight: 500,
  },
  timeSlotBusy: {
    opacity: 0.22,
    pointerEvents: "none",
    textDecoration: "line-through",
  },
  input: {
    width: "100%",
    height: 52,
    borderRadius: 13,
    border: `1px solid ${T.border}`,
    background: T.s2,
    color: T.text,
    fontFamily: "'Outfit',sans-serif",
    fontSize: 14,
    fontWeight: 300,
    padding: "16px 16px 0",
    outline: "none",
    transition: "border-color 0.2s",
    display: "block",
  },
  inputError: {
    borderColor: "#8a3030",
  },
};

export function BackBtn({ onClick }) {
  return (
    <button
      onClick={onClick}
      className="btn-back"
      style={{
        width: 48,
        height: 48,
        borderRadius: "50%",
        border: `1px solid ${T.border}`,
        background: "transparent",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        cursor: "pointer",
        flexShrink: 0,
        color: T.textMuted,
      }}
    >
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    </button>
  );
}

export function NextBtn({ onClick, disabled, label = "Далее", confirm = false }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={confirm ? "btn-pay" : "btn-next"}
      style={{
        flex: 1,
        height: 52,
        borderRadius: 26,
        background: disabled ? T.s3 : confirm ? T.green : T.gold,
        border: "none",
        color: disabled ? T.textMuted : confirm ? "#e8f5ea" : T.bg,
        fontFamily: T.font,
        fontSize: 14,
        fontWeight: 500,
        letterSpacing: "0.04em",
        cursor: disabled ? "default" : "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 7,
        transition: "all 0.28s cubic-bezier(0.34,1.56,0.64,1)",
      }}
    >
      {label}
      {!disabled && (
        <svg className="btn-arrow" width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M3 7h8M8 4l3 3-3 3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      )}
    </button>
  );
}

export function ProgressBar({ step, total }) {
  const pct = Math.round((step / total) * 100);
  return (
    <div style={s.progressTrack}>
      <div style={{
        height: "100%",
        width: `${pct}%`,
        background: `linear-gradient(90deg, ${T.goldDim}, ${T.gold})`,
        borderRadius: 1,
        transition: "width 0.6s cubic-bezier(0.34,1.56,0.64,1)",
      }} />
    </div>
  );
}

export function Wordmark() {
  return (
    <div style={s.wordmark}>
      <div style={s.wordmarkLine} />
      <div style={s.wordmarkText}>Insalon · Head Spa</div>
    </div>
  );
}

export function Ambient() {
  return (
    <div style={{
      position: "absolute",
      top: -120,
      left: "50%",
      transform: "translateX(-50%)",
      width: 280,
      height: 220,
      background: "radial-gradient(ellipse, rgba(200,169,110,0.055) 0%, transparent 70%)",
      pointerEvents: "none",
      zIndex: 0,
    }} />
  );
}

export function LoadingScreen() {
  return (
    <div style={{
      ...s.phone,
      alignItems: "center",
      justifyContent: "center",
      gap: 12,
    }}>
      <div style={{
        width: 36,
        height: 36,
        border: `1px solid ${T.border}`,
        borderTop: `1px solid ${T.gold}`,
        borderRadius: "50%",
        animation: "spin 0.9s linear infinite",
      }} />
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
      <div style={{ fontFamily: T.font, fontSize: 12, color: T.textMuted, fontWeight: 300 }}>
        Загрузка...
      </div>
    </div>
  );
}

export function CheckIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
      <path d="M2 5l2 2.5L8 2.5" stroke="#111110" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}
