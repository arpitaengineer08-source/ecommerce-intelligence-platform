"""Visual identity for the Streamlit app: midnight-ink canvas, aurora hero, glass KPI cards, Plotly template."""
import plotly.graph_objects as go
import plotly.io as pio

C = dict(bg="#0C0E1F", surface="#161A35", edge="#2A2F5C", iris="#7C5CFF", cyan="#22D3EE", amber="#FFB547",
         mint="#34E5A1", rose="#FF5C8A", text="#E9EBFF", muted="#9AA0CC")
COLORWAY = [C["iris"], C["cyan"], C["amber"], C["mint"], C["rose"], "#B39DFF", "#7BE0F2", "#FFD28A", "#8FF0C8", "#FF9CB8"]

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700;800&family=DM+Sans:wght@400;500;600&display=swap');
html, body, [class*="css"], .stApp {{ font-family: 'DM Sans', system-ui, sans-serif; }}
.stApp {{ background: radial-gradient(1200px 600px at 85% -10%, #231a5a 0%, transparent 60%),
                     radial-gradient(900px 500px at -10% 10%, #0b3a4a 0%, transparent 55%), {C['bg']}; }}
#MainMenu, footer, header[data-testid="stHeader"] {{ visibility: hidden; height: 0; }}
.block-container {{ padding-top: 1.4rem; max-width: 1400px; }}
h1, h2, h3, h4 {{ font-family: 'Sora','Segoe UI',system-ui,sans-serif, sans-serif !important; letter-spacing: -0.02em; color: {C['text']}; }}
section[data-testid="stSidebar"] {{ background: linear-gradient(180deg, #11142b 0%, #0c0e1f 100%); border-right: 1px solid {C['edge']}55; }}
section[data-testid="stSidebar"] .stRadio > label {{ display:none; }}
section[data-testid="stSidebar"] [role="radiogroup"] {{ gap: 2px; }}
section[data-testid="stSidebar"] [role="radiogroup"] label {{ padding: 9px 12px; border-radius: 10px; border: 1px solid transparent; transition: background .15s, border-color .15s; }}
section[data-testid="stSidebar"] [role="radiogroup"] label:hover {{ background: {C['surface']}; }}
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{ background: linear-gradient(90deg, {C['iris']}33, transparent); border-color: {C['iris']}88; }}
section[data-testid="stSidebar"] [role="radiogroup"] label [data-baseweb="radio"] > div:first-child,
section[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child:not(:only-child) {{ display:none !important; }}
section[data-testid="stSidebar"] [role="radiogroup"] label p {{ font-weight:500; font-size:.95rem; }}
.brand {{ font-family:'Sora','Segoe UI',system-ui,sans-serif; font-weight:800; font-size: 1.25rem; line-height:1.15; margin-bottom:2px; }}
.brand span {{ background: linear-gradient(90deg,{C['cyan']},{C['iris']},{C['rose']}); -webkit-background-clip:text; background-clip:text; color:transparent; }}
.brand-sub {{ color:{C['muted']}; font-size:.78rem; margin-bottom:14px; }}

/* hero : the one memorable moment */
.hero {{ position:relative; overflow:hidden; border-radius:22px; padding:30px 34px 26px; margin-bottom:22px;
        border:1px solid {C['edge']}; background: linear-gradient(135deg, #14173a 0%, #0f1230 100%); }}
.hero::before {{ content:""; position:absolute; inset:-40%; background:
        conic-gradient(from 90deg at 50% 50%, {C['iris']}55, {C['cyan']}33, {C['mint']}22, {C['rose']}44, {C['iris']}55);
        filter: blur(70px); opacity:.55; animation: drift 24s linear infinite; }}
.hero > * {{ position:relative; z-index:1; }}
.hero h1 {{ font-size: clamp(1.6rem, 3.1vw, 2.5rem); margin:0 0 6px; font-weight:800; line-height:1.12; }}
.hero p {{ color:#C9CDF5; margin:0 0 4px; max-width: 760px; }}
.chip {{ display:inline-block; font-size:.72rem; padding:3px 10px; border-radius:99px; border:1px solid {C['edge']}; color:{C['muted']}; margin-right:6px; background:#0c0e1f88; }}
.story {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap:14px; margin-top:18px; }}
.story > div {{ background:#0c0e1fb3; border:1px solid {C['edge']}; border-radius:14px; padding:14px 16px; }}
.story b {{ font-family:'Sora','Segoe UI',system-ui,sans-serif; font-size:.9rem; display:block; margin-bottom:5px; }}
.story .s1 b {{ color:{C['cyan']}; }} .story .s2 b {{ color:{C['amber']}; }} .story .s3 b {{ color:{C['mint']}; }}
.story span {{ color:#D5D8FF; font-size:.9rem; line-height:1.45; }}
@keyframes drift {{ to {{ transform: rotate(360deg); }} }}

/* KPI cards */
.kpi-grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap:12px; margin: 4px 0 18px; }}
.kpi {{ background: linear-gradient(180deg, {C['surface']} 0%, #121530 100%); border:1px solid {C['edge']}88; border-radius:16px; padding:14px 16px 12px; position:relative; }}
.kpi::before {{ content:""; position:absolute; left:16px; right:16px; top:0; height:3px; border-radius:0 0 4px 4px; background: var(--accent); }}
.kpi-label {{ color:{C['muted']}; font-size:.8rem; margin-top:4px; }}
.kpi-value {{ font-family:'Sora','Segoe UI',system-ui,sans-serif; font-weight:700; font-size:1.65rem; margin:2px 0; letter-spacing:-0.02em; }}
.kpi-sub {{ font-size:.78rem; color:{C['muted']}; }} .kpi-sub.up {{ color:{C['mint']}; }} .kpi-sub.down {{ color:{C['rose']}; }}

/* callouts & cards */
.callout {{ border-left:4px solid var(--accent, {C['iris']}); background:{C['surface']}; border-radius:0 12px 12px 0; padding:12px 16px; margin:8px 0 16px; color:#D9DCFF; font-size:.93rem; line-height:1.5; }}
.callout b {{ color:#fff; }}
.panel-title {{ font-family:'Sora','Segoe UI',system-ui,sans-serif; font-weight:600; font-size:1rem; margin: 6px 0 0; }}
.panel-sub {{ color:{C['muted']}; font-size:.82rem; margin-bottom:2px; }}
.rec {{ background:{C['surface']}; border:1px solid {C['edge']}88; border-radius:16px; padding:16px 18px; margin-bottom:14px; border-left:5px solid var(--accent); }}
.rec h4 {{ margin:0 0 6px; font-size:1.02rem; }} .rec p {{ margin:4px 0; color:#CFD2F7; font-size:.9rem; line-height:1.5; }}
.rec .tag {{ float:right; font-size:.72rem; padding:2px 9px; border-radius:99px; background:var(--accent)22; color:var(--accent); border:1px solid var(--accent)66; }}
.flow {{ display:flex; flex-wrap:wrap; align-items:stretch; gap:10px; margin:10px 0 18px; }}
.flow .node {{ flex:1 1 170px; background:{C['surface']}; border:1px solid {C['edge']}; border-radius:14px; padding:12px 14px; }}
.flow .node b {{ display:block; font-family:'Sora','Segoe UI',system-ui,sans-serif; font-size:.9rem; margin-bottom:4px; }}
.flow .node span {{ color:{C['muted']}; font-size:.8rem; }}
.flow .arrow {{ align-self:center; color:{C['iris']}; font-size:1.4rem; }}
div[data-testid="stDataFrame"] {{ border:1px solid {C['edge']}88; border-radius:12px; overflow:hidden; }}
.stTabs [data-baseweb="tab-list"] {{ gap:6px; }}
.stTabs [data-baseweb="tab"] {{ background:{C['surface']}; border-radius:10px 10px 0 0; padding:8px 16px; }}
@media (prefers-reduced-motion: reduce) {{ .hero::before {{ animation:none; }} }}
</style>
"""


def register_template():
    pio.templates["ecom"] = go.layout.Template(layout=go.Layout(
        font=dict(family="DM Sans, sans-serif", color=C["text"], size=13),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", colorway=COLORWAY,
        xaxis=dict(gridcolor="rgba(255,255,255,0.07)", zerolinecolor="rgba(255,255,255,0.10)", linecolor="rgba(255,255,255,0.13)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.07)", zerolinecolor="rgba(255,255,255,0.10)", linecolor="rgba(255,255,255,0.13)"),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=1.12, x=0),
        hoverlabel=dict(bgcolor=C["surface"], bordercolor=C["edge"], font=dict(color=C["text"])),
        margin=dict(l=10, r=10, t=30, b=10)))
    pio.templates.default = "ecom"


def style(fig, h=360):
    fig.update_layout(height=h, template="ecom")
    return fig


def money(x: float) -> str:
    a = abs(x)
    if a >= 1e6: return f"R${x / 1e6:.2f}M"
    if a >= 1e3: return f"R${x / 1e3:.1f}K"
    return f"R${x:,.0f}"


def kpi(label, value, sub="", accent=None, tone=""):
    return (f'<div class="kpi" style="--accent:{accent or C["iris"]}"><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div><div class="kpi-sub {tone}">{sub}&nbsp;</div></div>')


def kpi_row(items):
    return '<div class="kpi-grid">' + "".join(kpi(*i) if isinstance(i, tuple) else i for i in items) + "</div>"


def callout(text, accent=None):
    return f'<div class="callout" style="--accent:{accent or C["iris"]}">{text}</div>'
