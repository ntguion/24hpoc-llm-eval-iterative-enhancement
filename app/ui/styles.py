"""
Custom CSS styling for the Streamlit UI (dark theme)
"""

CUSTOM_CSS = """
<style>
/* ============================================
   CALL SUMMARY COPILOT - DARK THEME
   Sleek, focused, and easy on the eyes
   ============================================ */

:root {
    color-scheme: dark;
    --bg-primary: #0b1220;
    --bg-secondary: #111827;
    --bg-elevated: #131c2b;
    --border-color: #1f2937;
    --text-primary: #e5e7eb;
    --text-muted: #94a3b8;
    --accent-teal: #22d3ee;
    --accent-blue: #6366f1;
    --accent-gradient: linear-gradient(135deg, #22d3ee 0%, #6366f1 100%);
}

html, body {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: "Inter", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

[data-testid="stAppViewContainer"] {
    background: linear-gradient(160deg, rgba(11,18,32,0.95) 0%, rgba(15,23,42,0.97) 55%, rgba(17,24,39,1) 100%) !important;
}

.main {
    padding: 1.5rem 2.5rem 3rem 2.5rem;
}

.block-container {
    max-width: 1380px;
}

/* -------- TYPOGRAPHY -------- */
h1, h2, h3 {
    color: #f8fafc !important;
    font-weight: 700;
    letter-spacing: -0.01em;
}

h2 {
    margin-top: 1.5rem !important;
    padding-bottom: 0.5rem !important;
    border-bottom: 1px solid rgba(99, 102, 241, 0.25) !important;
}

p, label, span, div {
    color: var(--text-primary);
}

small, .stCaption, .st-markdown p em {
    color: var(--text-muted) !important;
}

/* -------- METRICS -------- */
div[data-testid="stMetric"] {
    background: var(--bg-secondary);
    border-radius: 0.85rem;
    border: 1px solid var(--border-color);
    padding: 1rem;
    box-shadow: 0 8px 20px rgba(2, 6, 23, 0.45);
}

div[data-testid="stMetricValue"] {
    font-size: 2rem;
    font-weight: 700;
    color: var(--accent-teal);
}

div[data-testid="stMetricLabel"] {
    color: var(--text-muted);
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

/* -------- CARDS / EXPANDERS -------- */
div[data-testid="stExpander"] {
    background: var(--bg-secondary) !important;
    border-radius: 1rem !important;
    border: 1px solid var(--border-color) !important;
    box-shadow: 0 16px 30px rgba(2, 6, 23, 0.55) !important;
    margin-bottom: 1.25rem !important;
}

div[data-testid="stExpander"] > details > summary {
    color: var(--text-primary) !important;
    font-weight: 600;
}

div[data-testid="stExpander"] > details[open] {
    background: var(--bg-secondary) !important;
    border-radius: 1rem !important;
}

/* -------- BUTTONS -------- */
.stButton button {
    background: var(--accent-gradient) !important;
    color: #f8fafc !important;
    border: none !important;
    border-radius: 0.6rem;
    padding: 0.7rem 1.8rem;
    font-weight: 600;
    font-size: 0.98rem;
    letter-spacing: 0.02em;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    box-shadow: 0 12px 24px rgba(34, 211, 238, 0.35);
}

.stButton button:hover {
    transform: translateY(-2px);
    box-shadow: 0 16px 32px rgba(99, 102, 241, 0.35);
}

.stButton button:active {
    transform: translateY(0);
    box-shadow: 0 8px 16px rgba(99, 102, 241, 0.3);
}

.stButton button:focus-visible {
    outline: 2px solid rgba(34, 211, 238, 0.7);
    outline-offset: 2px;
}

/* -------- TABS -------- */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.6rem;
    background: transparent;
    border-bottom: 1px solid rgba(148, 163, 184, 0.25);
}

.stTabs [data-baseweb="tab"] {
    height: 3.2rem;
    background: rgba(17, 24, 39, 0.85) !important;
    border-radius: 0.9rem 0.9rem 0 0;
    padding: 0 1.75rem;
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--text-muted) !important;
    border: 1px solid transparent !important;
    transition: all 0.2s ease;
}

.stTabs [data-baseweb="tab"]:hover {
    color: #f8fafc !important;
    border-color: rgba(99, 102, 241, 0.35) !important;
}

.stTabs [aria-selected="true"] {
    background: rgba(30, 41, 59, 0.95) !important;
    color: #f8fafc !important;
    border-color: rgba(34, 211, 238, 0.55) !important;
    border-bottom: 2px solid var(--bg-secondary) !important;
    margin-bottom: -1px !important;
    box-shadow: 0 8px 20px rgba(34, 211, 238, 0.15);
}

/* -------- SIDEBAR -------- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(8, 15, 27, 0.98) 100%) !important;
    border-right: 1px solid rgba(148, 163, 184, 0.12) !important;
    box-shadow: 6px 0 18px rgba(2, 6, 23, 0.65);
}

section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] label {
    color: #f8fafc !important;
}

section[data-testid="stSidebar"] .stTextInput input {
    background: rgba(15, 23, 42, 0.9) !important;
    border: 1px solid rgba(148, 163, 184, 0.25) !important;
    border-radius: 0.55rem;
    color: #f8fafc !important;
}

section[data-testid="stSidebar"] .stTextInput input::placeholder {
    color: rgba(148, 163, 184, 0.6) !important;
}

section[data-testid="stSidebar"] .stTextInput input:focus {
    border-color: rgba(34, 211, 238, 0.7) !important;
    box-shadow: 0 0 0 3px rgba(34, 211, 238, 0.25) !important;
}

section[data-testid="stSidebar"] div[data-testid="stMetric"] {
    background: rgba(17, 24, 39, 0.9) !important;
    border: 1px solid rgba(148, 163, 184, 0.25) !important;
}

section[data-testid="stSidebar"] div[data-testid="stMetricValue"] {
    color: var(--accent-teal) !important;
}

section[data-testid="stSidebar"] div[data-testid="stMetricLabel"] {
    color: rgba(148, 163, 184, 0.75) !important;
}

section[data-testid="stSidebar"] hr {
    border-color: rgba(71, 85, 105, 0.35) !important;
}

/* Sidebar alerts */
section[data-testid="stSidebar"] .stAlert {
    background: rgba(34, 211, 238, 0.12) !important;
    border-left: 3px solid var(--accent-teal) !important;
    color: #f8fafc !important;
}

/* -------- PROGRESS & INDICATORS -------- */
.stProgress > div > div {
    background: var(--accent-gradient);
    border-radius: 1rem;
}

.stSpinner > div {
    border-color: var(--accent-teal) !important;
}

/* -------- CODE & JSON -------- */
.stCodeBlock, pre, code {
    background: rgba(15, 23, 42, 0.9) !important;
    color: #f8fafc !important;
    border-radius: 0.9rem !important;
    border: 1px solid rgba(99, 102, 241, 0.35) !important;
    box-shadow: inset 0 0 12px rgba(2, 6, 23, 0.55) !important;
}

/* -------- INPUTS & CONTROLS -------- */
.stSelectbox select,
.stTextArea textarea,
.stNumberInput input {
    background: rgba(15, 23, 42, 0.95) !important;
    border: 1px solid rgba(148, 163, 184, 0.2) !important;
    color: #f8fafc !important;
    border-radius: 0.55rem !important;
}

.stSelectbox div[data-baseweb="select"] {
    border-radius: 0.65rem !important;
    border: 1px solid rgba(148, 163, 184, 0.35) !important;
    background: rgba(17, 24, 39, 0.85) !important;
    box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.9);
}

.stSelectbox div[data-baseweb="select"]:hover {
    border-color: rgba(99, 102, 241, 0.45) !important;
}

.stSelectbox div[data-baseweb="select"] div[role="button"] {
    background: transparent !important;
    color: #f8fafc !important;
}

.stSelectbox div[data-baseweb="select"] svg {
    color: rgba(226, 232, 240, 0.85) !important;
}

.stSelectbox select:focus,
.stTextArea textarea:focus,
.stNumberInput input:focus {
    border-color: rgba(99, 102, 241, 0.6) !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.25) !important;
}

.stSlider > div > div > div > div {
    background: var(--accent-teal) !important;
}

.stSlider [role="slider"] {
    background: var(--accent-teal) !important;
    box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.25);
}

.stRadio > div {
    background: rgba(17, 24, 39, 0.9) !important;
    border: 1px solid rgba(148, 163, 184, 0.2) !important;
    border-radius: 0.55rem;
}

/* -------- TABLES -------- */
.dataframe {
    background: rgba(15, 23, 42, 0.9);
    border-radius: 0.9rem;
    border: 1px solid rgba(148, 163, 184, 0.25);
    color: #f8fafc;
}

/* -------- ANIMATIONS -------- */
.element-container {
    animation: fadeIn 0.35s ease;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
}

/* -------- FOOTER -------- */
.stMarkdown footer, footer {
    color: var(--text-muted) !important;
}
</style>
"""
