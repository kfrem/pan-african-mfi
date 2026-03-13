import { useState, useEffect, useRef } from "react";
import {
  AreaChart, Area, LineChart, Line, PieChart, Pie, Cell,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, ReferenceArea
} from "recharts";
import { Download, TrendingUp, TrendingDown, ChevronDown, Shield, AlertTriangle, Globe, Moon, Sun, Bell, LogOut } from "lucide-react";

// ─── ANIMATED COUNTER ───
function AnimatedNumber({ value, prefix = "", suffix = "", decimals = 0, duration = 1500 }) {
  const [display, setDisplay] = useState(0);
  const ref = useRef(null);
  useEffect(() => {
    let start = 0;
    const step = (ts) => {
      if (!ref.current) ref.current = ts;
      const progress = Math.min((ts - ref.current) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(eased * value);
      if (progress < 1) requestAnimationFrame(step);
    };
    ref.current = null;
    requestAnimationFrame(step);
  }, [value, duration]);
  const formatted = display.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return <span>{prefix}{formatted}{suffix}</span>;
}

// ─── MOCK DATA ───
const portfolioGrowth = Array.from({ length: 24 }, (_, i) => {
  const d = new Date(2024, i, 1);
  const base = 1800000 + i * 45000 + Math.sin(i * 0.5) * 60000;
  return {
    month: d.toLocaleString("en", { month: "short", year: "2-digit" }),
    portfolio: Math.round(base),
    borrowers: Math.round(280 + i * 12 + Math.random() * 20),
    disbursements: Math.round(120000 + i * 8000 + Math.random() * 30000),
  };
});

const parTrend = Array.from({ length: 12 }, (_, i) => {
  const d = new Date(2025, i + 1, 1);
  return {
    month: d.toLocaleString("en", { month: "short" }),
    par30: +(3.8 + Math.sin(i * 0.6) * 1.2 + Math.random() * 0.5).toFixed(1),
    par90: +(1.2 + Math.sin(i * 0.4) * 0.6 + Math.random() * 0.3).toFixed(1),
  };
});

const countryData = [
  { name: "Ghana", value: 58, color: "#0ea5e9", flag: "🇬🇭" },
  { name: "Zambia", value: 42, color: "#8b5cf6", flag: "🇿🇲" },
];

const covenants = [
  { name: "Capital Adequacy", value: 18.2, threshold: 10, unit: "%", status: "pass" },
  { name: "PAR30 Threshold", value: 4.2, threshold: 8, unit: "%", status: "pass", inverse: true },
  { name: "Liquidity Ratio", value: 22.0, threshold: 15, unit: "%", status: "pass" },
  { name: "Single Obligor", value: 8.0, threshold: 10, unit: "%", status: "watch", inverse: true },
];

const fxRates = { USD: 1, GBP: 0.79, EUR: 0.92 };
const localToUSD = 0.0625;

// ─── STYLES ───
const colors = {
  bg: "#060a14", card: "#0c1222", cardHover: "#111b30",
  border: "#1a2744", borderLight: "#243354",
  text: "#e2e8f0", textMuted: "#7b8ba5", textDim: "#4a5974",
  accent: "#0066ff", accentGlow: "rgba(0,102,255,0.15)",
  green: "#10b981", greenDim: "#065f46",
  amber: "#f59e0b", amberDim: "#78350f",
  red: "#ef4444", redDim: "#7f1d1d",
  purple: "#8b5cf6", cyan: "#06b6d4",
};

const s = {
  page: { background: colors.bg, color: colors.text, fontFamily: "'SF Pro Display', 'Segoe UI', system-ui, -apple-system, sans-serif", minHeight: "100vh", padding: 0, margin: 0 },
  topBar: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 28px", borderBottom: `1px solid ${colors.border}`, background: colors.card },
  logo: { display: "flex", alignItems: "center", gap: "12px" },
  logoIcon: { width: 36, height: 36, borderRadius: 8, background: `linear-gradient(135deg, ${colors.accent}, ${colors.purple})`, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 16, color: "#fff" },
  logoText: { fontSize: 15, fontWeight: 700, letterSpacing: "-0.02em" },
  logoSub: { fontSize: 11, color: colors.textMuted, letterSpacing: "0.06em", textTransform: "uppercase", marginTop: 1 },
  topActions: { display: "flex", alignItems: "center", gap: "16px" },
  currencyBtn: { display: "flex", alignItems: "center", gap: "6px", background: colors.bg, border: `1px solid ${colors.border}`, borderRadius: 8, padding: "6px 14px", color: colors.text, fontSize: 13, fontWeight: 600, cursor: "pointer" },
  iconBtn: { background: "transparent", border: "none", color: colors.textMuted, cursor: "pointer", padding: 6, borderRadius: 6 },
  grid: { display: "grid", gap: "16px", padding: "20px 28px" },
  kpiRow: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "16px" },
  kpi: { background: colors.card, border: `1px solid ${colors.border}`, borderRadius: 12, padding: "20px 22px", transition: "border-color 0.2s", cursor: "default" },
  kpiLabel: { fontSize: 11, fontWeight: 600, color: colors.textMuted, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 },
  kpiValue: { fontSize: 28, fontWeight: 700, letterSpacing: "-0.03em", lineHeight: 1.1 },
  kpiSub: { fontSize: 12, marginTop: 8, display: "flex", alignItems: "center", gap: 4 },
  chartRow: { display: "grid", gridTemplateColumns: "1fr", gap: "16px" },
  chartRow2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" },
  card: { background: colors.card, border: `1px solid ${colors.border}`, borderRadius: 12, padding: "20px 22px" },
  cardTitle: { fontSize: 12, fontWeight: 600, color: colors.textMuted, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 16 },
  downloadBtn: { display: "flex", alignItems: "center", gap: 8, background: `linear-gradient(135deg, ${colors.accent}, #0052cc)`, border: "none", borderRadius: 10, padding: "12px 24px", color: "#fff", fontSize: 14, fontWeight: 700, cursor: "pointer", letterSpacing: "0.01em", boxShadow: `0 4px 20px ${colors.accentGlow}`, transition: "transform 0.15s, box-shadow 0.15s" },
  covenantRow: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 0", borderBottom: `1px solid ${colors.border}` },
  covenantBar: { height: 6, borderRadius: 3, background: colors.bg, flex: 1, marginLeft: 12, marginRight: 12, overflow: "hidden", position: "relative" },
  badge: (color) => ({ fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 20, textTransform: "uppercase", letterSpacing: "0.05em" }),
  investmentRow: { display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: `1px solid ${colors.border}` },
  investmentLabel: { fontSize: 13, color: colors.textMuted },
  investmentValue: { fontSize: 14, fontWeight: 600 },
  tabGroup: { display: "flex", gap: 4, marginBottom: 16 },
  tab: (active) => ({ padding: "6px 16px", fontSize: 12, fontWeight: 600, borderRadius: 6, border: "none", cursor: "pointer", background: active ? colors.accent : "transparent", color: active ? "#fff" : colors.textMuted, transition: "all 0.2s" }),
};

// ─── TOOLTIP ───
function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: colors.card, border: `1px solid ${colors.borderLight}`, borderRadius: 8, padding: "10px 14px", fontSize: 12 }}>
      <div style={{ fontWeight: 600, marginBottom: 6, color: colors.textMuted }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: p.color }} />
          <span style={{ color: colors.textMuted }}>{p.name}:</span>
          <span style={{ fontWeight: 600 }}>{typeof p.value === "number" ? p.value.toLocaleString() : p.value}</span>
        </div>
      ))}
    </div>
  );
}

// ─── MAIN DASHBOARD ───
export default function InvestorDashboard() {
  const [currency, setCurrency] = useState("USD");
  const [chartMode, setChartMode] = useState("portfolio");
  const [showCurrMenu, setShowCurrMenu] = useState(false);

  const rate = fxRates[currency] || 1;
  const fmt = (v) => (v * localToUSD * (1 / rate)).toLocaleString("en-US", { maximumFractionDigits: 0 });
  const sym = currency === "USD" ? "$" : currency === "GBP" ? "£" : "€";

  const invested = 500000;
  const currentVal = 561200;
  const returnAmt = currentVal - invested;
  const returnPct = ((returnAmt / invested) * 100);
  const fxLoss = -2.1;

  return (
    <div style={s.page}>
      {/* TOP BAR */}
      <div style={s.topBar}>
        <div style={s.logo}>
          <div style={s.logoIcon}>M</div>
          <div>
            <div style={s.logoText}>Accra MicroCredit Ltd</div>
            <div style={s.logoSub}>Investor Portal</div>
          </div>
        </div>
        <div style={s.topActions}>
          <div style={{ position: "relative" }}>
            <button style={s.currencyBtn} onClick={() => setShowCurrMenu(!showCurrMenu)}>
              <Globe size={14} /> {currency} <ChevronDown size={12} />
            </button>
            {showCurrMenu && (
              <div style={{ position: "absolute", top: "100%", right: 0, marginTop: 4, background: colors.card, border: `1px solid ${colors.border}`, borderRadius: 8, overflow: "hidden", zIndex: 10, minWidth: 100 }}>
                {["USD", "GBP", "EUR"].map(c => (
                  <div key={c} onClick={() => { setCurrency(c); setShowCurrMenu(false); }}
                    style={{ padding: "8px 16px", fontSize: 13, fontWeight: c === currency ? 700 : 400, cursor: "pointer", background: c === currency ? colors.accentGlow : "transparent", color: c === currency ? colors.accent : colors.text }}>
                    {c}
                  </div>
                ))}
              </div>
            )}
          </div>
          <button style={s.iconBtn}><Bell size={18} /></button>
          <button style={{...s.downloadBtn}} onMouseOver={e => { e.currentTarget.style.transform = "translateY(-1px)"; e.currentTarget.style.boxShadow = `0 8px 30px ${colors.accentGlow}`; }} onMouseOut={e => { e.currentTarget.style.transform = "none"; e.currentTarget.style.boxShadow = `0 4px 20px ${colors.accentGlow}`; }}>
            <Download size={16} /> Download Report
          </button>
          <button style={s.iconBtn}><LogOut size={18} /></button>
        </div>
      </div>

      <div style={s.grid}>
        {/* KPI ROW */}
        <div style={s.kpiRow}>
          <div style={s.kpi}>
            <div style={s.kpiLabel}>Total Portfolio</div>
            <div style={{ ...s.kpiValue, color: colors.text }}>
              <AnimatedNumber value={2450000 * (1/rate)} prefix={sym + " "} decimals={0} />
            </div>
            <div style={{ ...s.kpiSub, color: colors.green }}>
              <TrendingUp size={14} /> +3.2% MoM
            </div>
          </div>
          <div style={s.kpi}>
            <div style={s.kpiLabel}>Portfolio at Risk (PAR30)</div>
            <div style={{ ...s.kpiValue, color: colors.green }}>
              <AnimatedNumber value={4.2} suffix="%" decimals={1} />
            </div>
            <div style={{ ...s.kpiSub, color: colors.green }}>
              <Shield size={14} /> Within threshold
            </div>
          </div>
          <div style={s.kpi}>
            <div style={s.kpiLabel}>Net Return (Annualised)</div>
            <div style={{ ...s.kpiValue, color: colors.green }}>
              <AnimatedNumber value={12.4} prefix="+" suffix="% p.a." decimals={1} />
            </div>
            <div style={{ ...s.kpiSub, color: colors.green }}>
              <TrendingUp size={14} /> YTD {sym} <AnimatedNumber value={returnAmt * (1/rate)} decimals={0} />
            </div>
          </div>
          <div style={s.kpi}>
            <div style={s.kpiLabel}>FX Gain / Loss</div>
            <div style={{ ...s.kpiValue, color: colors.amber }}>
              <AnimatedNumber value={-2.1} suffix="%" decimals={1} />
            </div>
            <div style={{ ...s.kpiSub, color: colors.amber }}>
              <AlertTriangle size={14} /> Monitor ({currency}/GHS)
            </div>
          </div>
        </div>

        {/* PORTFOLIO GROWTH CHART */}
        <div style={s.card}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div style={s.cardTitle}>Portfolio Growth — 24 Months</div>
            <div style={s.tabGroup}>
              {[["portfolio", "Total Book"], ["borrowers", "Borrowers"], ["disbursements", "Disbursements"]].map(([k, label]) => (
                <button key={k} style={s.tab(chartMode === k)} onClick={() => setChartMode(k)}>{label}</button>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={portfolioGrowth}>
              <defs>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={colors.accent} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={colors.accent} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: colors.textDim }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 11, fill: colors.textDim }} tickLine={false} axisLine={false}
                tickFormatter={v => chartMode === "borrowers" ? v : `${(v/1000000).toFixed(1)}M`} />
              <Tooltip content={<ChartTooltip />} />
              <Area type="monotone" dataKey={chartMode} stroke={colors.accent} strokeWidth={2}
                fill="url(#areaGrad)" dot={false} animationDuration={1200} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* TWO-COLUMN: COUNTRY BREAKDOWN + PAR TREND */}
        <div style={s.chartRow2}>
          {/* Country Breakdown Donut */}
          <div style={s.card}>
            <div style={s.cardTitle}>Country Breakdown</div>
            <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
              <ResponsiveContainer width="50%" height={180}>
                <PieChart>
                  <Pie data={countryData} cx="50%" cy="50%" innerRadius={50} outerRadius={75}
                    paddingAngle={3} dataKey="value" animationDuration={1000} stroke="none">
                    {countryData.map((d, i) => <Cell key={i} fill={d.color} />)}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div style={{ flex: 1 }}>
                {countryData.map(d => (
                  <div key={d.name} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
                    <span style={{ width: 10, height: 10, borderRadius: "50%", background: d.color }} />
                    <span style={{ fontSize: 14 }}>{d.flag} {d.name}</span>
                    <span style={{ marginLeft: "auto", fontSize: 20, fontWeight: 700 }}>{d.value}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* PAR Trend */}
          <div style={s.card}>
            <div style={s.cardTitle}>PAR Trend — 12 Months</div>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={parTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: colors.textDim }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 11, fill: colors.textDim }} tickLine={false} axisLine={false} domain={[0, 8]} />
                <Tooltip content={<ChartTooltip />} />
                <ReferenceArea y1={5} y2={8} fill={colors.redDim} fillOpacity={0.25} />
                <ReferenceLine y={5} stroke={colors.red} strokeDasharray="4 4" strokeWidth={1} label={{ value: "Danger", fill: colors.red, fontSize: 10, position: "right" }} />
                <Line type="monotone" dataKey="par30" stroke={colors.amber} strokeWidth={2.5} dot={false} name="PAR 30+" animationDuration={1200} />
                <Line type="monotone" dataKey="par90" stroke={colors.red} strokeWidth={2} dot={false} name="PAR 90+" animationDuration={1400} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* TWO-COLUMN: COVENANTS + INVESTMENT SUMMARY */}
        <div style={s.chartRow2}>
          {/* Covenant Status */}
          <div style={s.card}>
            <div style={s.cardTitle}>Covenant Status</div>
            {covenants.map((c, i) => {
              const pct = c.inverse ? ((c.threshold - c.value) / c.threshold) * 100 : (c.value / c.threshold) * 100;
              const barPct = Math.min(c.inverse ? (c.value / c.threshold) * 100 : pct, 100);
              const barColor = c.status === "pass" ? colors.green : c.status === "watch" ? colors.amber : colors.red;
              const badgeStyle = c.status === "pass"
                ? { ...s.badge(), background: colors.greenDim, color: colors.green }
                : { ...s.badge(), background: colors.amberDim, color: colors.amber };
              return (
                <div key={i} style={s.covenantRow}>
                  <div style={{ fontSize: 13, minWidth: 130 }}>{c.name}</div>
                  <div style={{ fontSize: 15, fontWeight: 700, minWidth: 70, textAlign: "right" }}>{c.value}{c.unit}</div>
                  <div style={s.covenantBar}>
                    <div style={{ height: "100%", width: `${barPct}%`, borderRadius: 3, background: barColor, transition: "width 1.5s ease-out" }} />
                  </div>
                  <span style={badgeStyle}>{c.status}</span>
                </div>
              );
            })}
          </div>

          {/* My Investment Summary */}
          <div style={s.card}>
            <div style={s.cardTitle}>My Investment Summary</div>
            {[
              ["Invested", `${sym} ${(invested * (1/rate)).toLocaleString()}`, "Jan 2024"],
              ["Current Value", `${sym} ${(currentVal * (1/rate)).toLocaleString()}`, null],
              [`Return (${currency})`, `+${sym} ${(returnAmt * (1/rate)).toLocaleString()} (+${returnPct.toFixed(2)}%)`, null],
              ["Return (GHS local)", `+GHS ${(returnAmt / localToUSD).toLocaleString()}`, null],
              ["Dividend Yield", "8.4% p.a.", "Last paid: Q4 2025"],
              ["Investment Status", null, null],
            ].map(([label, val, sub], i) => (
              <div key={i} style={{ ...s.investmentRow, ...(i === 5 ? { borderBottom: "none" } : {}) }}>
                <div>
                  <div style={s.investmentLabel}>{label}</div>
                  {sub && <div style={{ fontSize: 11, color: colors.textDim, marginTop: 2 }}>{sub}</div>}
                </div>
                {i === 5 ? (
                  <span style={{ ...s.badge(), background: colors.greenDim, color: colors.green, alignSelf: "center" }}>Active</span>
                ) : (
                  <div style={{ ...s.investmentValue, color: i === 2 ? colors.green : colors.text }}>{val}</div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* FOOTER */}
        <div style={{ textAlign: "center", padding: "8px 0 20px", fontSize: 11, color: colors.textDim }}>
          Data as of {new Date().toLocaleDateString("en-GB")} · All figures in {currency} unless stated · Confidential
        </div>
      </div>
    </div>
  );
}
