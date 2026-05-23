import io
import re

import streamlit as st
import streamlit.components.v1 as components
from deep_translator import GoogleTranslator
from gtts import gTTS
from gtts.lang import tts_langs
from langdetect import detect, LangDetectException
from datetime import datetime
from textblob import TextBlob

# ── Optional imports (graceful fallback if not installed) ──────────
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Method 1: EasyOCR (Deep Learning - No Tesseract needed!)
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

# Method 2: PaddleOCR (Alternative Deep Learning OCR)
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False

# Method 3: Tesseract (Traditional OCR - requires installation)
try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# Check if any OCR method is available
OCR_AVAILABLE = EASYOCR_AVAILABLE or PADDLEOCR_AVAILABLE or TESSERACT_AVAILABLE

try:
    import pypdf
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────

LANGUAGES: dict[str, str] = {
    "Afrikaans": "af", "Albanian": "sq", "Amharic": "am", "Arabic": "ar",
    "Armenian": "hy", "Azerbaijani": "az", "Basque": "eu", "Belarusian": "be",
    "Bengali": "bn", "Bosnian": "bs", "Bulgarian": "bg", "Burmese": "my",
    "Catalan": "ca", "Cebuano": "ceb", "Chinese (Simplified)": "zh-CN",
    "Chinese (Traditional)": "zh-TW", "Croatian": "hr", "Czech": "cs",
    "Danish": "da", "Dutch": "nl", "English": "en", "Esperanto": "eo",
    "Estonian": "et", "Filipino": "tl", "Finnish": "fi", "French": "fr",
    "Galician": "gl", "Georgian": "ka", "German": "de", "Greek": "el",
    "Gujarati": "gu", "Haitian Creole": "ht", "Hausa": "ha", "Hawaiian": "haw",
    "Hebrew": "iw", "Hindi": "hi", "Hmong": "hmn", "Hungarian": "hu",
    "Icelandic": "is", "Igbo": "ig", "Indonesian": "id", "Irish": "ga",
    "Italian": "it", "Japanese": "ja", "Javanese": "jw", "Kannada": "kn",
    "Kazakh": "kk", "Khmer": "km", "Korean": "ko", "Kyrgyz": "ky",
    "Lao": "lo", "Latin": "la", "Latvian": "lv", "Lithuanian": "lt",
    "Luxembourgish": "lb", "Macedonian": "mk", "Malagasy": "mg", "Malay": "ms",
    "Malayalam": "ml", "Maltese": "mt", "Maori": "mi", "Marathi": "mr",
    "Mongolian": "mn", "Norwegian": "no", "Nyanja": "ny", "Pashto": "ps",
    "Persian": "fa", "Polish": "pl", "Portuguese": "pt", "Punjabi": "pa",
    "Romanian": "ro", "Russian": "ru", "Samoan": "sm", "Sanskrit": "sa",
    "Scottish Gaelic": "gd", "Serbian": "sr", "Sesotho": "st", "Shona": "sn",
    "Sindhi": "sd", "Sinhala": "si", "Slovak": "sk", "Slovenian": "sl",
    "Somali": "so", "Spanish": "es", "Sundanese": "su", "Swahili": "sw",
    "Swedish": "sv", "Tajik": "tg", "Tamil": "ta", "Telugu": "te",
    "Thai": "th", "Turkish": "tr", "Turkmen": "tk", "Ukrainian": "uk",
    "Urdu": "ur", "Uyghur": "ug", "Uzbek": "uz", "Vietnamese": "vi",
    "Welsh": "cy", "Xhosa": "xh", "Yiddish": "yi", "Yoruba": "yo", "Zulu": "zu",
}

INDIAN_LANGS = {
    "Bengali", "Gujarati", "Hindi", "Kannada", "Malayalam",
    "Marathi", "Punjabi", "Sanskrit", "Sindhi", "Tamil", "Telugu", "Urdu",
}

SUPPORTED_AUDIO_LANGS = set(tts_langs().keys())

FEATURES = [
    ("🔍", "Auto language detection"),
    ("✨", "NLP auto-correct spelling"),
    ("🔁", "Swap source & target language"),
    ("📊", "Live character & word count"),
    ("📋", "Copy translation to clipboard"),
    ("🔊", "Audio playback of translation"),
    ("💾", "Download translation as .txt"),
    ("🕘", "Session translation history"),
    ("🖼️", "OCR image-to-text translation"),
    ("🎙️", "Speech input & voice output"),
    ("♿", "Accessibility mode"),
    ("📄", "PDF & DOCX document translation"),
]

SESSION_DEFAULTS: dict = {
    "translated_text": "",
    "detected_lang":   "",
    "source":          "Auto Detect",
    "target":          "English",
    "history":         [],
    # Accessibility
    "a11y_font_size":    16,
    "a11y_high_contrast": False,
    "a11y_dyslexia":     False,
    # Active tab
    "active_tab":        "text",   # "text" | "image" | "speech" | "document"
}

MAX_CHARS = 15000

# ─────────────────────────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────────────────────────

def build_css(font_size: int, high_contrast: bool, dyslexia: bool) -> str:
    body_font  = "'OpenDyslexic', 'Nunito Sans', sans-serif" if dyslexia else "'Nunito Sans', sans-serif"
    text_color = "#ffffff" if high_contrast else "#e8ecf2"
    bg_color   = "#000000" if high_contrast else "#1a1d24"
    bg2_color  = "#111111" if high_contrast else "#21252e"
    surf_color = "#1a1a1a" if high_contrast else "#272b35"
    border_c   = "rgba(255,255,255,0.35)" if high_contrast else "rgba(255,255,255,0.07)"
    soft_color = "#cccccc" if high_contrast else "#8e97aa"
    
    # ✨ NEW: Vibrant light colors for translations
    if high_contrast:
        # High contrast mode: bright, pure colors
        trans_color = "#00ffff"  # Bright cyan
        trans_glow = "rgba(0,255,255,0.4)"
    else:
        # Normal mode: soft, pastel gradient
        trans_color = "#a5f3fc"  # Light cyan
        trans_glow = "rgba(165,243,252,0.25)"

    dyslexia_import = "@font-face { font-family:'OpenDyslexic'; src:url('https://cdn.jsdelivr.net/npm/opendyslexic@latest/OpenDyslexic-Regular.otf'); }" if dyslexia else ""

    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;500;600;700;800&family=Nunito+Sans:wght@300;400;600&display=swap');
{dyslexia_import}

:root {{
    --bg:          {bg_color};
    --bg2:         {bg2_color};
    --surface:     {surf_color};
    --surface2:    #2e3340;
    --border:      {border_c};
    --border-hi:   rgba(251,100,80,0.35);
    --coral:       #fb6450;
    --coral-dark:  #e04e38;
    --coral-light: #fd8c7a;
    --coral-glow:  rgba(251,100,80,0.18);
    --coral-mist:  rgba(251,100,80,0.08);
    --slate-hi:    #94a3b8;
    --text:        {text_color};
    --soft:        {soft_color};
    --muted:       #535c6e;
    --danger:      #f87171;
    --danger-bg:   rgba(248,113,113,0.09);
    
    /* ✨ NEW: Vibrant translation colors */
    --trans-cyan:     #a5f3fc;
    --trans-blue:     #bfdbfe;
    --trans-green:    #bbf7d0;
    --trans-yellow:   #fef08a;
    --trans-purple:   #e9d5ff;
    --trans-pink:     #fbcfe8;
    --trans-primary:  {trans_color};
    --trans-glow:     {trans_glow};
    
    --r-xs:7px; --r-sm:11px; --r-md:15px; --r-lg:20px;
    --shadow:      0 2px 20px rgba(0,0,0,0.40);
    --shadow-coral:0 4px 24px rgba(251,100,80,0.25);
    --shadow-trans:0 4px 20px {trans_glow};
    --font-size:   {font_size}px;
}}

html, body, .stApp        {{ background: var(--bg) !important; color: var(--text); font-family: {body_font}; font-size: var(--font-size); }}
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container          {{ padding-top: 1.2rem !important; padding-bottom: 2rem !important; max-width: 860px !important; }}

.stApp::before {{
    content:""; position:fixed; inset:0; pointer-events:none; z-index:0;
    background:
        radial-gradient(ellipse 50% 32% at 8%  4%, rgba(251,100,80,.10) 0%, transparent 62%),
        radial-gradient(ellipse 40% 38% at 92% 94%,rgba(251,100,80,.07) 0%, transparent 62%),
        radial-gradient(ellipse 35% 50% at 58% 18%,rgba(148,163,184,.04) 0%,transparent 58%);
}}

.hdr       {{ text-align:center; padding:1.2rem 0 1rem; }}
.hdr-title {{
    font-family:'Nunito',sans-serif; font-size:clamp(2rem,5vw,3rem);
    font-weight:800; letter-spacing:-0.03em; line-height:1; margin-bottom:0.3rem;
    background:linear-gradient(125deg,#e8ecf2 10%,var(--coral-light) 55%,var(--coral) 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}}
.hdr-sub {{ font-size:0.8rem; font-weight:300; color:var(--muted); letter-spacing:0.02em; }}

.card {{
    background:var(--surface); border:1px solid var(--border);
    border-radius:var(--r-lg); padding:1rem 1.2rem;
    margin-bottom:0.6rem; position:relative; overflow:hidden; box-shadow:var(--shadow);
}}
.card::before {{
    content:""; position:absolute; top:0; left:8%; right:8%; height:1px;
    background:linear-gradient(90deg,transparent,rgba(255,255,255,0.07),transparent);
}}

/* ✨ ENHANCED: Result card with gradient glow */
.card-result {{ 
    background:linear-gradient(148deg,var(--surface) 30%,rgba(165,243,252,0.06) 100%); 
    border-color:rgba(165,243,252,0.25);
    box-shadow:var(--shadow), var(--shadow-trans);
}}
.card-result::before {{ 
    background:linear-gradient(90deg,transparent,rgba(165,243,252,0.4),transparent); 
    height:2px;
}}

/* ── TAB BAR ─────────────────────────────────────────────────── */
.tab-bar {{
    display:flex; gap:0.35rem; margin-bottom:0.8rem;
    background:var(--bg2); border:1px solid var(--border);
    border-radius:var(--r-md); padding:0.25rem;
}}
.tab-btn {{
    flex:1; padding:0.45rem 0.5rem; border-radius:var(--r-sm);
    font-size:0.72rem; font-weight:700; letter-spacing:0.04em; text-transform:uppercase;
    cursor:pointer; border:none; background:transparent; color:var(--muted);
    transition:all .18s ease; text-align:center;
}}
.tab-btn:hover {{ color:var(--soft); background:rgba(255,255,255,0.04); }}
.tab-btn.active {{
    background:linear-gradient(130deg,var(--coral-dark),var(--coral));
    color:#fff; box-shadow:var(--shadow-coral);
}}

/* ── ACCESSIBILITY PANEL ─────────────────────────────────────── */
.a11y-panel {{
    background:var(--bg2); border:1px solid var(--border);
    border-radius:var(--r-md); padding:0.8rem 1rem; margin-bottom:0.6rem;
}}
.a11y-title {{
    font-size:0.6rem; font-weight:700; letter-spacing:0.15em; text-transform:uppercase;
    color:var(--coral-light); margin-bottom:0.6rem;
}}
.a11y-row {{ display:flex; align-items:center; gap:0.6rem; margin-bottom:0.3rem; font-size:0.78rem; color:var(--soft); }}

/* ── OCR DROP ZONE ───────────────────────────────────────────── */
.ocr-info {{
    background:var(--coral-mist); border:1px dashed rgba(251,100,80,0.3);
    border-radius:var(--r-md); padding:0.6rem 0.9rem; margin-bottom:0.5rem;
    font-size:0.75rem; color:var(--coral-light); text-align:center;
}}

/* ── SPEECH CARD ─────────────────────────────────────────────── */
.speech-hint {{
    background:var(--coral-mist); border:1px solid rgba(251,100,80,0.2);
    border-radius:var(--r-sm); padding:0.55rem 0.8rem; margin-bottom:0.5rem;
    font-size:0.75rem; color:var(--soft); line-height:1.55;
}}

/* ── DOC STATUS ──────────────────────────────────────────────── */
.doc-badge {{
    display:inline-flex; align-items:center; gap:0.3rem;
    background:var(--coral-mist); border:1px solid rgba(251,100,80,0.22);
    color:var(--coral-light); border-radius:100px;
    padding:0.2rem 0.65rem; font-size:0.62rem; font-weight:700;
    letter-spacing:0.07em; text-transform:uppercase; margin-bottom:0.5rem;
}}

.clabel {{
    display:flex; align-items:center; gap:0.4rem;
    font-size:0.55rem; font-weight:700; letter-spacing:0.18em;
    text-transform:uppercase; color:var(--muted); margin-bottom:0.5rem;
}}
.clabel-dot {{
    width:5px; height:5px; border-radius:50%; flex-shrink:0;
    background:var(--coral); box-shadow:0 0 8px rgba(251,100,80,0.7);
}}
.cdivider {{ border:none; border-top:1px solid var(--border); margin:0.7rem 0 0.6rem; }}

.stTextArea,.stTextArea>div,.stTextArea>div>div {{ background:transparent !important; }}
.stTextArea textarea {{
    background:var(--bg2) !important; border:1px solid rgba(255,255,255,0.08) !important;
    border-radius:var(--r-md) !important; color:var(--text) !important;
    -webkit-text-fill-color:var(--text) !important;
    font-family:{body_font} !important;
    font-size:calc(var(--font-size) * 0.9) !important; font-weight:400 !important; line-height:1.7 !important;
    padding:0.75rem 1rem !important; resize:none !important; caret-color:var(--coral) !important;
    transition:border-color .2s,box-shadow .2s,background .2s;
}}
.stTextArea textarea:focus {{
    border-color:var(--coral) !important; outline:none !important;
    box-shadow:0 0 0 3px var(--coral-glow) !important; background:#242830 !important;
}}
.stTextArea textarea::placeholder {{ color:var(--muted) !important; -webkit-text-fill-color:var(--muted) !important; }}
.stTextArea label {{ display:none !important; }}

.count-bar {{
    display:flex; align-items:center; gap:0.6rem;
    margin-top:0.3rem; margin-bottom:0.1rem; min-height:1.2rem;
}}
.count-chars, .count-words {{ font-size:0.65rem; color:var(--muted); white-space:nowrap; }}
.progress-wrap {{ flex:1; height:2px; border-radius:2px; background:rgba(255,255,255,0.06); overflow:hidden; }}
.progress-fill  {{ height:100%; border-radius:2px; }}

.stSelectbox>label {{
    font-size:0.55rem !important; font-weight:700 !important;
    letter-spacing:0.12em !important; text-transform:uppercase !important;
    color:var(--muted) !important; margin-bottom:0.2rem !important;
}}
.stSelectbox>div>div {{
    background:var(--bg2) !important; border:1px solid rgba(255,255,255,0.08) !important;
    border-radius:var(--r-sm) !important; color:var(--text) !important;
    font-family:{body_font} !important;
    font-size:0.82rem !important; font-weight:400 !important;
    min-height: 2.4rem !important;
}}
.stSelectbox>div>div:focus-within {{ border-color:var(--coral) !important; box-shadow:0 0 0 3px var(--coral-glow) !important; }}

.stButton>button {{
    font-family:{body_font} !important; font-weight:600 !important;
    font-size:0.78rem !important; border-radius:var(--r-sm) !important;
    border:1px solid rgba(255,255,255,0.08) !important;
    background:var(--surface2) !important; color:var(--soft) !important;
    padding:0.35rem 0.6rem !important; min-height:2.4rem !important;
    transition:all .17s ease !important; width:100% !important;
}}
.stButton>button:hover {{
    background:rgba(255,255,255,0.07) !important; color:var(--text) !important;
    border-color:rgba(255,255,255,0.14) !important;
    transform:translateY(-1px) !important; box-shadow:0 3px 10px rgba(0,0,0,0.25) !important;
}}

div[data-testid="element-container"]:has(.marker-primary) + div[data-testid="element-container"] button,
div[data-testid="stElementContainer"]:has(.marker-primary) + div[data-testid="stElementContainer"] button {{
    background:linear-gradient(130deg,var(--coral-dark) 0%,var(--coral) 55%,var(--coral-light) 100%) !important;
    border:none !important; color:#fff !important; font-weight:800 !important;
    font-size:0.82rem !important; letter-spacing:0.04em !important; text-transform:uppercase !important;
    padding:0.4rem 1rem !important; min-height:2.4rem !important;
    border-radius:var(--r-sm) !important; box-shadow:var(--shadow-coral) !important;
}}
div[data-testid="element-container"]:has(.marker-primary) + div[data-testid="element-container"] button:hover,
div[data-testid="stElementContainer"]:has(.marker-primary) + div[data-testid="stElementContainer"] button:hover {{
    filter:brightness(1.08) !important; transform:translateY(-1px) !important;
    box-shadow:0 6px 20px rgba(251,100,80,.35) !important; color: white !important;
}}

div[data-testid="element-container"]:has(.marker-ghost) + div[data-testid="element-container"] button,
div[data-testid="stElementContainer"]:has(.marker-ghost) + div[data-testid="stElementContainer"] button {{
    background:transparent !important; border:1px solid rgba(255,255,255,0.07) !important;
    color:var(--muted) !important; font-size:0.78rem !important;
    padding:0.4rem 0.5rem !important; min-height:2.4rem !important; border-radius:var(--r-sm) !important;
}}
div[data-testid="element-container"]:has(.marker-ghost) + div[data-testid="element-container"] button:hover,
div[data-testid="stElementContainer"]:has(.marker-ghost) + div[data-testid="stElementContainer"] button:hover {{
    border-color:rgba(255,255,255,0.2) !important; color:var(--text) !important;
    background:rgba(255,255,255,0.05) !important; transform:none !important; box-shadow:none !important;
}}

div[data-testid="element-container"]:has(.marker-swap) + div[data-testid="element-container"] button,
div[data-testid="stElementContainer"]:has(.marker-swap) + div[data-testid="stElementContainer"] button {{
    background:transparent !important; border:1px solid rgba(255,255,255,0.08) !important;
    color:var(--soft) !important; padding:0.2rem 0.4rem !important;
    min-height:2.4rem !important; font-size:1rem !important; border-radius:var(--r-xs) !important;
}}
div[data-testid="element-container"]:has(.marker-swap) + div[data-testid="element-container"] button:hover,
div[data-testid="stElementContainer"]:has(.marker-swap) + div[data-testid="stElementContainer"] button:hover {{
    background:var(--surface2) !important; border-color:var(--coral) !important;
    color:var(--coral-light) !important; box-shadow:0 0 10px rgba(251,100,80,0.15) !important;
    transform:none !important;
}}

div[data-testid="element-container"]:has(.marker-teal) + div[data-testid="element-container"] button,
div[data-testid="stElementContainer"]:has(.marker-teal) + div[data-testid="stElementContainer"] button {{
    background:var(--coral-mist) !important;
    border:1px solid rgba(251,100,80,0.25) !important;
    color:var(--coral-light) !important; font-weight:700 !important;
    font-size:0.75rem !important; padding:0.3rem 0.6rem !important;
    min-height:2rem !important; border-radius:var(--r-xs) !important;
}}
div[data-testid="element-container"]:has(.marker-teal) + div[data-testid="element-container"] button:hover,
div[data-testid="stElementContainer"]:has(.marker-teal) + div[data-testid="stElementContainer"] button:hover {{
    background:rgba(251,100,80,0.14) !important; border-color:var(--coral) !important;
    transform:translateY(-1px) !important; color:#fff !important;
    box-shadow:0 3px 12px rgba(251,100,80,0.2) !important;
}}

.stDownloadButton>button {{
    font-family:{body_font} !important; font-weight:700 !important;
    font-size:0.75rem !important; background:var(--coral-mist) !important;
    border:1px solid rgba(251,100,80,0.25) !important; color:var(--coral-light) !important;
    border-radius:var(--r-xs) !important; padding:0.3rem 0.6rem !important;
    min-height:2rem !important; width:100% !important; transition:all .17s ease !important;
}}
.stDownloadButton>button:hover {{
    background:rgba(251,100,80,0.14) !important; border-color:var(--coral) !important;
    transform:translateY(-1px) !important; color:#fff !important;
    box-shadow:0 3px 12px rgba(251,100,80,0.2) !important;
}}

/* ✨ ENHANCED: Vibrant, light-colored translation text with gradient and glow */
.result-text {{
    font-family:'Nunito',sans-serif; 
    font-size:calc(var(--font-size) * 1.08); 
    font-weight:500;
    line-height:1.75; 
    
    /* Beautiful gradient from cyan to blue to purple */
    background: linear-gradient(135deg, var(--trans-cyan) 0%, var(--trans-blue) 50%, var(--trans-purple) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    
    /* Subtle text shadow for depth */
    filter: drop-shadow(0 0 12px {trans_glow}) drop-shadow(0 2px 8px rgba(165,243,252,0.3));
    
    padding:0.8rem 0 0.9rem; 
    border-bottom:1px solid rgba(165,243,252,0.15);
    margin-bottom:0.7rem; 
    word-break:break-word;
    
    /* Smooth animation on appearance */
    animation: fadeInGlow 0.6s ease-out;
}}

@keyframes fadeInGlow {{
    from {{
        opacity: 0;
        filter: drop-shadow(0 0 0px transparent);
        transform: translateY(4px);
    }}
    to {{
        opacity: 1;
        filter: drop-shadow(0 0 12px {trans_glow}) drop-shadow(0 2px 8px rgba(165,243,252,0.3));
        transform: translateY(0);
    }}
}}

.detected {{
    display:inline-flex; align-items:center; gap:0.3rem;
    background:var(--coral-mist); border:1px solid rgba(251,100,80,0.22);
    color:var(--coral-light); border-radius:100px;
    padding:0.15rem 0.6rem 0.15rem 0.45rem;
    font-size:0.62rem; font-weight:700; letter-spacing:0.07em;
    text-transform:uppercase; margin-bottom:0.6rem;
}}
.detected::before {{ content:"◎"; font-size:0.5rem; opacity:0.7; }}

.hist-item {{
    background:var(--bg2); border:1px solid var(--border);
    border-radius:var(--r-md); padding:0.75rem 0.9rem; margin-bottom:0.5rem;
}}
.hist-meta {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:0.35rem; }}
.hist-langs {{ font-size:0.65rem; font-weight:700; letter-spacing:0.05em; color:var(--coral-light); text-transform:uppercase; }}
.hist-time  {{ font-size:0.6rem; color:var(--muted); }}
.hist-original {{ font-size:0.78rem; color:var(--muted); margin-bottom:0.15rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}

/* ✨ ENHANCED: Light-colored history translations with gradient */
.hist-translated {{ 
    font-family:'Nunito',sans-serif; 
    font-size:0.92rem; 
    font-weight:500;
    
    /* Soft gradient for history items */
    background: linear-gradient(120deg, var(--trans-green) 0%, var(--trans-cyan) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    
    filter: drop-shadow(0 0 6px rgba(187,247,208,0.2));
}}

#clipboard-toast {{
    position:fixed; bottom:1.5rem; right:1.5rem; z-index:9999;
    background:var(--surface); border:1px solid var(--border-hi);
    color:var(--coral-light); border-radius:var(--r-sm);
    padding:0.55rem 1rem; font-size:0.8rem; font-weight:600;
    box-shadow:0 4px 20px rgba(0,0,0,0.5);
    opacity:0; transform:translateY(6px);
    transition:opacity .25s,transform .25s; pointer-events:none;
}}
#clipboard-toast.show {{ opacity:1; transform:translateY(0); }}

audio {{ width:100%; border-radius:var(--r-sm); height:32px; margin-top:0.2rem; filter:invert(.9) hue-rotate(140deg) saturate(.8); }}

section[data-testid="stSidebar"]      {{ background:var(--bg2) !important; border-right:1px solid var(--border) !important; }}
section[data-testid="stSidebar"]>div {{ padding:1.2rem 1rem !important; }}
.sb-logo  {{
    font-family:'Nunito',sans-serif; font-size:1.3rem; font-weight:800; letter-spacing:-0.02em;
    background:linear-gradient(125deg,#e8ecf2 20%,var(--coral-light) 70%,var(--coral) 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}}
.sb-sub  {{ font-size:0.65rem; font-weight:300; color:var(--muted); margin-bottom:1rem; }}
.sb-hr   {{ border:none; border-top:1px solid var(--border); margin:0.8rem 0; }}
.sb-head {{ font-size:0.55rem; font-weight:700; letter-spacing:0.15em; text-transform:uppercase; color:var(--muted); margin:0.8rem 0 0.4rem; }}
.sb-body {{ font-size:0.75rem; font-weight:400; line-height:1.6; color:var(--soft); }}
.sb-feat {{ display:flex; align-items:center; gap:0.4rem; padding:0.25rem 0; font-size:0.72rem; color:var(--soft); }}
.sb-icon {{ width:20px; height:20px; border-radius:6px; flex-shrink:0; font-size:0.65rem; display:flex; align-items:center; justify-content:center; background:var(--coral-mist); border:1px solid rgba(251,100,80,0.18); }}
.chip-grid {{ display:flex; flex-wrap:wrap; gap:0.2rem; margin-top:0.15rem; }}
.chip     {{ font-size:0.62rem; padding:0.15rem 0.4rem; border-radius:var(--r-xs); border:1px solid var(--border); color:var(--soft); background:rgba(255,255,255,0.03); }}
.chip.hi  {{ background:var(--coral-mist); border-color:rgba(251,100,80,0.2); color:var(--coral-light); }}

::-webkit-scrollbar           {{ width:4px; }}
::-webkit-scrollbar-track     {{ background:transparent; }}
::-webkit-scrollbar-thumb     {{ background:var(--border); border-radius:4px; }}
</style>
<div id="clipboard-toast">✓ Copied to clipboard</div>
"""

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def card_label(text: str) -> str:
    return f'<div class="clabel"><span class="clabel-dot"></span>{text}</div>'

def chip_list(items: list, highlight: set = None) -> str:
    if highlight is None:
        highlight = set()
    chips = "".join(f'<span class="chip{" hi" if l in highlight else ""}">{l}</span>' for l in items)
    return f'<div class="chip-grid">{chips}</div>'

def lang_name_from_code(code: str) -> str:
    return next((k for k, v in LANGUAGES.items() if v == code), code)

def btn_marker(marker_class: str) -> None:
    st.markdown(f'<div class="{marker_class}" style="display:none"></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# CORE LOGIC
# ─────────────────────────────────────────────────────────────────

def run_translation(text: str, source: str, target: str) -> None:
    if not text.strip():
        st.warning("Please enter some text to translate.")
        return
    if len(text) > MAX_CHARS:
        st.error(f"Input exceeds {MAX_CHARS:,} character limit.")
        return

    with st.spinner("Translating…"):
        try:
            if source == "Auto Detect":
                try:
                    code = detect(text)
                    st.session_state.detected_lang = code
                except LangDetectException:
                    st.error("Language detection failed — select a source language manually.")
                    return
            else:
                code = LANGUAGES[source]
                st.session_state.detected_lang = code

            result = GoogleTranslator(source=code, target=LANGUAGES[target]).translate(text)
            st.session_state.translated_text = result

            entry = {
                "src":    lang_name_from_code(code) if source == "Auto Detect" else source,
                "tgt":    target,
                "input":  text[:120] + ("…" if len(text) > 120 else ""),
                "output": result[:120] + ("…" if len(result) > 120 else ""),
                "time":   datetime.now().strftime("%H:%M"),
            }
            st.session_state.history = [entry] + st.session_state.history[:19]

        except Exception as e:
            st.error(f"Translation error: {e}")

def make_audio(text: str, lang_code: str) -> io.BytesIO | None:
    try:
        buf = io.BytesIO()
        gTTS(text=text, lang=lang_code, slow=False).write_to_fp(buf)
        buf.seek(0)
        return buf
    except Exception as e:
        st.error(f"Audio error: {e}")
        return None

# ─────────────────────────────────────────────────────────────────
# FEATURE: OCR IMAGE TRANSLATION
# ─────────────────────────────────────────────────────────────────

def extract_text_from_image(img: Image.Image, method: str = "auto") -> tuple[str, str]:
    """
    Extract text from image using various OCR methods.
    Returns: (extracted_text, method_used)
    """
    
    # Method 1: EasyOCR (Best - Deep Learning, no external dependencies)
    if method in ["auto", "easyocr"] and EASYOCR_AVAILABLE:
        try:
            # Initialize reader (caches for subsequent uses)
            if 'easyocr_reader' not in st.session_state:
                st.session_state.easyocr_reader = easyocr.Reader(['en'], gpu=False)
            
            reader = st.session_state.easyocr_reader
            
            # Convert PIL to numpy array
            import numpy as np
            img_array = np.array(img)
            
            # Extract text
            results = reader.readtext(img_array)
            text = ' '.join([result[1] for result in results])
            
            return text.strip(), "EasyOCR (Deep Learning)"
        except Exception as e:
            st.warning(f"EasyOCR failed: {e}. Trying next method...")
    
    # Method 2: PaddleOCR (Alternative Deep Learning)
    if method in ["auto", "paddleocr"] and PADDLEOCR_AVAILABLE:
        try:
            # Initialize PaddleOCR
            if 'paddle_reader' not in st.session_state:
                st.session_state.paddle_reader = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
            
            ocr = st.session_state.paddle_reader
            
            # Convert PIL to numpy array
            import numpy as np
            img_array = np.array(img)
            
            # Extract text
            result = ocr.ocr(img_array, cls=True)
            text = ' '.join([line[1][0] for line in result[0]]) if result[0] else ""
            
            return text.strip(), "PaddleOCR (Deep Learning)"
        except Exception as e:
            st.warning(f"PaddleOCR failed: {e}. Trying next method...")
    
    # Method 3: Tesseract (Traditional, requires external installation)
    if method in ["auto", "tesseract"] and TESSERACT_AVAILABLE:
        try:
            text = pytesseract.image_to_string(img).strip()
            return text, "Tesseract OCR"
        except Exception as e:
            st.warning(f"Tesseract failed: {e}")
    
    # No method worked
    return "", "None (All methods failed)"

def render_ocr_tab() -> None:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(card_label("OCR Image Translation"), unsafe_allow_html=True)

    if not OCR_AVAILABLE:
        st.error("""
        **No OCR method available!** Install one of the following:
        
        **Option 1 (Recommended - Easy):**
        ```bash
        pip install easyocr
        ```
        
        **Option 2 (Fast & Accurate):**
        ```bash
        pip install paddlepaddle paddleocr
        ```
        
        **Option 3 (Traditional):**
        ```bash
        pip install pytesseract
        ```
        Then install Tesseract: https://github.com/tesseract-ocr/tesseract
        """)
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    # Show available OCR methods
    available_methods = []
    if EASYOCR_AVAILABLE:
        available_methods.append("✅ EasyOCR (Deep Learning)")
    if PADDLEOCR_AVAILABLE:
        available_methods.append("✅ PaddleOCR (Deep Learning)")
    if TESSERACT_AVAILABLE:
        available_methods.append("✅ Tesseract OCR")
    
    st.markdown(
        f'<div class="ocr-info">📷 Upload a photo of any text — signs, menus, documents, screenshots. Available methods: {", ".join(available_methods)}</div>',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Upload image", type=["png", "jpg", "jpeg", "webp", "bmp", "tiff"],
        label_visibility="collapsed", key="ocr_upload",
    )

    if uploaded:
        img = Image.open(uploaded)
        col_img, col_info = st.columns([1.2, 1])
        
        with col_img:
            st.image(img, use_container_width=True, caption="Uploaded image")
        
        with col_info:
            st.markdown('<hr class="cdivider">', unsafe_allow_html=True)
            
            # OCR Method selector
            ocr_methods = ["Auto (Try all)"]
            if EASYOCR_AVAILABLE:
                ocr_methods.append("EasyOCR")
            if PADDLEOCR_AVAILABLE:
                ocr_methods.append("PaddleOCR")
            if TESSERACT_AVAILABLE:
                ocr_methods.append("Tesseract")
            
            selected_method = st.selectbox(
                "OCR Method", 
                ocr_methods, 
                key="ocr_method_select",
                help="Choose which OCR engine to use"
            )
            
            # Map selection to method parameter
            method_map = {
                "Auto (Try all)": "auto",
                "EasyOCR": "easyocr",
                "PaddleOCR": "paddleocr",
                "Tesseract": "tesseract"
            }
            method_param = method_map.get(selected_method, "auto")
            
            with st.spinner("Extracting text…"):
                raw_text, method_used = extract_text_from_image(img, method_param)

            if raw_text:
                st.markdown(
                    f'<div class="doc-badge">✓ Text extracted · {len(raw_text)} chars · {method_used}</div>', 
                    unsafe_allow_html=True
                )
                st.text_area("Extracted text (editable)", value=raw_text, key="ocr_extracted", height=120)

                source_opts = ["Auto Detect"] + list(LANGUAGES.keys())
                target_opts = list(LANGUAGES.keys())
                ocr_src = st.selectbox("From", source_opts, key="ocr_source")
                ocr_tgt = st.selectbox("To",   target_opts, key="ocr_target", index=target_opts.index("English") if "English" in target_opts else 0)

                btn_marker("marker-primary")
                if st.button("✦ Translate Image Text", use_container_width=True, key="ocr_translate_btn"):
                    text_to_translate = st.session_state.get("ocr_extracted", raw_text)
                    run_translation(text_to_translate, ocr_src, ocr_tgt)
                    # Sync main selectors
                    st.session_state.source = ocr_src
                    st.session_state.target = ocr_tgt
                    st.rerun()
            else:
                st.warning("No text detected in this image. Try a clearer photo with printed text, or try a different OCR method.")

    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# FEATURE: SPEECH INPUT + OUTPUT
# ─────────────────────────────────────────────────────────────────

SPEECH_JS = """
<style>
  #speech-container {
    font-family: 'Nunito Sans', sans-serif;
    display: flex; flex-direction: column; gap: 10px;
    padding: 4px 0;
  }
  #mic-btn {
    display: flex; align-items: center; justify-content: center; gap: 8px;
    padding: 10px 20px; border-radius: 11px; cursor: pointer;
    font-size: 0.8rem; font-weight: 700; letter-spacing: 0.05em;
    border: 1px solid rgba(251,100,80,0.35);
    background: rgba(251,100,80,0.1); color: #fd8c7a;
    transition: all 0.2s ease; width: 100%;
  }
  #mic-btn:hover  { background: rgba(251,100,80,0.18); }
  #mic-btn.active { background: rgba(251,100,80,0.28); border-color: #fb6450; color: #fff; animation: pulse 1.2s infinite; }
  @keyframes pulse { 0%,100%{box-shadow:0 0 0 0 rgba(251,100,80,0.4)} 50%{box-shadow:0 0 0 8px rgba(251,100,80,0)} }
  #mic-status { font-size: 0.68rem; color: #535c6e; text-align: center; min-height: 1.2rem; }
  #mic-result {
    font-size: 0.85rem; color: #e8ecf2; background: #21252e;
    border: 1px solid rgba(255,255,255,0.08); border-radius: 11px;
    padding: 10px 14px; min-height: 60px; word-break: break-word;
    line-height: 1.6;
  }
  #use-text-btn {
    padding: 8px 14px; border-radius: 9px; cursor: pointer;
    font-size: 0.75rem; font-weight: 700; letter-spacing: 0.04em;
    border: 1px solid rgba(251,100,80,0.25);
    background: rgba(251,100,80,0.08); color: #fd8c7a;
    transition: all 0.2s ease; display: none;
  }
  #use-text-btn:hover { background: rgba(251,100,80,0.18); color: #fff; }
</style>
<div id="speech-container">
  <button id="mic-btn" onclick="toggleMic()">🎙️ Start Recording</button>
  <div id="mic-status">Click to begin voice input</div>
  <div id="mic-result">Transcribed speech will appear here…</div>
  <button id="use-text-btn" onclick="useTranscript()">↑ Use This Text →</button>
</div>
<script>
  let recognition, isRecording = false, finalTranscript = "";

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  function toggleMic() {
    if (!SpeechRecognition) {
      document.getElementById('mic-status').textContent = '❌ Speech recognition not supported in this browser (use Chrome/Edge)';
      return;
    }
    if (isRecording) { recognition.stop(); return; }

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      isRecording = true;
      finalTranscript = "";
      document.getElementById('mic-btn').textContent = '⏹ Stop Recording';
      document.getElementById('mic-btn').classList.add('active');
      document.getElementById('mic-status').textContent = '🔴 Listening…';
    };

    recognition.onresult = (e) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) finalTranscript += e.results[i][0].transcript + " ";
        else interim += e.results[i][0].transcript;
      }
      document.getElementById('mic-result').textContent = (finalTranscript + interim) || "…";
    };

    recognition.onend = () => {
      isRecording = false;
      document.getElementById('mic-btn').textContent = '🎙️ Start Recording';
      document.getElementById('mic-btn').classList.remove('active');
      document.getElementById('mic-status').textContent = finalTranscript ? '✓ Done — click "Use This Text" to translate' : 'No speech detected. Try again.';
      if (finalTranscript.trim()) {
        document.getElementById('use-text-btn').style.display = 'block';
      }
    };

    recognition.onerror = (e) => {
      document.getElementById('mic-status').textContent = `Error: ${e.error}`;
    };

    recognition.start();
  }

  function useTranscript() {
    if (!finalTranscript.trim()) return;
    // Send transcript to Streamlit via query param trick
    const encoded = encodeURIComponent(finalTranscript.trim());
    window.parent.postMessage({ type: 'streamlit:setComponentValue', value: finalTranscript.trim() }, '*');
  }
</script>
"""

def render_speech_tab() -> None:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(card_label("Speech Input + Voice Output"), unsafe_allow_html=True)

    st.markdown(
        '<div class="speech-hint">'
        '🎙️ <b>Step 1:</b> Click "Start Recording" and speak — your words are transcribed live.<br>'
        '✏️ <b>Step 2:</b> Edit the transcribed text if needed, then translate.<br>'
        '🔊 <b>Step 3:</b> Play the translated audio back with one click.'
        '</div>',
        unsafe_allow_html=True,
    )

    col_speech, col_manual = st.columns([1, 1])

    with col_speech:
        st.markdown('<div style="font-size:0.6rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:var(--muted);margin-bottom:0.4rem;">Browser Speech Recognition</div>', unsafe_allow_html=True)
        components.html(SPEECH_JS, height=240, scrolling=False)

    with col_manual:
        st.markdown('<div style="font-size:0.6rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:var(--muted);margin-bottom:0.4rem;">Or type / paste speech text</div>', unsafe_allow_html=True)
        speech_text = st.text_area(
            "speech_input", height=120,
            placeholder="Paste or type text here to translate & hear it…",
            key="speech_text_input",
            label_visibility="collapsed",
        )

    st.markdown('<hr class="cdivider">', unsafe_allow_html=True)

    source_opts = ["Auto Detect"] + list(LANGUAGES.keys())
    target_opts = list(LANGUAGES.keys())

    sc1, sc2, sc3 = st.columns([2.5, 2.5, 2])
    with sc1:
        sp_src = st.selectbox("From", source_opts, key="speech_source")
    with sc2:
        sp_tgt = st.selectbox("To", target_opts, key="speech_target",
                              index=target_opts.index("English") if "English" in target_opts else 0)
    with sc3:
        btn_marker("marker-primary")
        if st.button("✦ Translate & Play", use_container_width=True, key="speech_translate_btn"):
            text_to_use = speech_text.strip()
            if text_to_use:
                run_translation(text_to_use, sp_src, sp_tgt)
                st.session_state.source = sp_src
                st.session_state.target = sp_tgt
                # Auto play
                tgt_code = LANGUAGES[sp_tgt]
                if tgt_code in SUPPORTED_AUDIO_LANGS and st.session_state.translated_text:
                    audio = make_audio(st.session_state.translated_text, tgt_code)
                    if audio:
                        st.audio(audio, format="audio/mp3")
            else:
                st.warning("No text to translate. Record or type something first.")

    # Show result if available
    if st.session_state.translated_text:
        st.markdown(f'<div class="result-text" style="margin-top:0.6rem">{st.session_state.translated_text}</div>', unsafe_allow_html=True)
        tgt_code = LANGUAGES.get(st.session_state.target, "en")
        if tgt_code in SUPPORTED_AUDIO_LANGS:
            btn_marker("marker-teal")
            if st.button("🔊 Play Audio Again", key="speech_replay", use_container_width=False):
                audio = make_audio(st.session_state.translated_text, tgt_code)
                if audio:
                    st.audio(audio, format="audio/mp3")

    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# FEATURE: ACCESSIBILITY MODE
# ─────────────────────────────────────────────────────────────────

def render_accessibility_panel() -> None:
    with st.expander("♿  Accessibility Settings", expanded=False):
        st.markdown('<div class="a11y-title">Display & Readability</div>', unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            font_size = st.slider(
                "Font size (px)", min_value=12, max_value=28, step=1,
                value=st.session_state.a11y_font_size, key="a11y_font_size_slider",
            )
            st.session_state.a11y_font_size = font_size

        with col2:
            high_contrast = st.toggle(
                "High contrast mode", value=st.session_state.a11y_high_contrast,
                key="a11y_contrast_toggle",
                help="Maximises contrast for low-vision users (WCAG AAA)"
            )
            st.session_state.a11y_high_contrast = high_contrast

        with col3:
            dyslexia = st.toggle(
                "Dyslexia-friendly font", value=st.session_state.a11y_dyslexia,
                key="a11y_dyslexia_toggle",
                help="Switches to OpenDyslexic typeface"
            )
            st.session_state.a11y_dyslexia = dyslexia

        hints = []
        if high_contrast:
            hints.append("✓ High contrast active")
        if dyslexia:
            hints.append("✓ OpenDyslexic font active")
        if font_size != 16:
            hints.append(f"✓ Font size: {font_size}px")
        if hints:
            st.markdown(
                f'<div style="font-size:0.7rem;color:var(--coral-light);margin-top:0.3rem">{" · ".join(hints)}</div>',
                unsafe_allow_html=True,
            )

# ─────────────────────────────────────────────────────────────────
# FEATURE: PDF / DOCX DOCUMENT TRANSLATION
# ─────────────────────────────────────────────────────────────────

def extract_pdf_text(file_bytes: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        txt = page.extract_text()
        if txt:
            pages.append(txt.strip())
    return "\n\n".join(pages)

def extract_docx_text(file_bytes: bytes) -> str:
    doc = DocxDocument(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

def translate_in_chunks(text: str, source_code: str, target_code: str, chunk_size: int = 4000) -> str:
    """Split long text into chunks and translate each, preserving paragraph breaks."""
    paragraphs = text.split("\n")
    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) + 1 > chunk_size and current:
            chunks.append(current.strip())
            current = para + "\n"
        else:
            current += para + "\n"
    if current.strip():
        chunks.append(current.strip())

    translated_chunks = []
    for chunk in chunks:
        try:
            result = GoogleTranslator(source=source_code, target=target_code).translate(chunk)
            translated_chunks.append(result)
        except Exception:
            translated_chunks.append(chunk)  # fallback: keep original

    return "\n\n".join(translated_chunks)

def render_document_tab() -> None:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(card_label("Document Translation — PDF & DOCX"), unsafe_allow_html=True)

    if not PDF_AVAILABLE and not DOCX_AVAILABLE:
        st.error("Document translation requires:\n```\npip install pypdf python-docx\n```")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    accepted = []
    if PDF_AVAILABLE:  accepted.append("pdf")
    if DOCX_AVAILABLE: accepted.extend(["docx", "doc"])

    st.markdown(
        f'<div class="ocr-info">📄 Upload a <b>.pdf</b> or <b>.docx</b> file — we extract all text, translate it page-by-page, and give you a downloadable result.</div>',
        unsafe_allow_html=True,
    )

    uploaded_doc = st.file_uploader(
        "Upload document", type=accepted,
        label_visibility="collapsed", key="doc_upload",
    )

    if uploaded_doc:
        file_bytes = uploaded_doc.read()
        ext = uploaded_doc.name.rsplit(".", 1)[-1].lower()
        file_name_base = uploaded_doc.name.rsplit(".", 1)[0]

        with st.spinner("Reading document…"):
            try:
                if ext == "pdf":
                    raw_text = extract_pdf_text(file_bytes)
                elif ext in ("docx", "doc"):
                    raw_text = extract_docx_text(file_bytes)
                else:
                    raw_text = ""
            except Exception as e:
                st.error(f"Could not read document: {e}")
                raw_text = ""

        if raw_text.strip():
            words   = len(raw_text.split())
            chars   = len(raw_text)
            preview = raw_text[:400] + ("…" if len(raw_text) > 400 else "")

            st.markdown(
                f'<div class="doc-badge">✓ {ext.upper()} loaded · {words:,} words · {chars:,} chars</div>',
                unsafe_allow_html=True,
            )

            with st.expander("Preview extracted text", expanded=False):
                st.text(preview)

            st.markdown('<hr class="cdivider">', unsafe_allow_html=True)

            source_opts = ["Auto Detect"] + list(LANGUAGES.keys())
            target_opts = list(LANGUAGES.keys())

            dc1, dc2 = st.columns(2)
            with dc1:
                doc_src = st.selectbox("Translate from", source_opts, key="doc_source")
            with dc2:
                doc_tgt = st.selectbox("Translate to",   target_opts, key="doc_target",
                                       index=target_opts.index("English") if "English" in target_opts else 0)

            if words > 2000:
                st.info(f"⏱ Large document ({words:,} words) — translation may take ~{words // 400 + 1} minutes. Please wait.")

            btn_marker("marker-primary")
            if st.button("✦ Translate Document", use_container_width=True, key="doc_translate_btn"):
                with st.spinner(f"Translating document into {doc_tgt}…"):
                    try:
                        if doc_src == "Auto Detect":
                            try:
                                src_code = detect(raw_text[:1000])
                            except LangDetectException:
                                src_code = "auto"
                        else:
                            src_code = LANGUAGES[doc_src]

                        tgt_code = LANGUAGES[doc_tgt]
                        translated_doc = translate_in_chunks(raw_text, src_code, tgt_code)
                        st.session_state["doc_translated"] = translated_doc
                        st.session_state["doc_filename"]   = file_name_base
                        st.session_state["doc_target_name"] = doc_tgt
                        st.success(f"✓ Document translated into {doc_tgt}!")
                    except Exception as e:
                        st.error(f"Translation error: {e}")

        else:
            st.warning("Could not extract text from this document. It may be a scanned image — try the OCR tab instead.")

    # Show download if translation ready
    if st.session_state.get("doc_translated"):
        translated = st.session_state["doc_translated"]
        fname      = st.session_state.get("doc_filename", "document")
        tgt_name   = st.session_state.get("doc_target_name", "translated")

        st.markdown('<hr class="cdivider">', unsafe_allow_html=True)
        st.markdown(f'<div class="doc-badge">📥 Ready to download · {len(translated.split()):,} words</div>', unsafe_allow_html=True)

        with st.expander("Preview translated document", expanded=True):
            st.text(translated[:600] + ("…" if len(translated) > 600 else ""))

        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            st.download_button(
                "↓ Download as .txt",
                data=translated,
                file_name=f"{fname}_{tgt_name}.txt",
                mime="text/plain",
                use_container_width=True,
                key="doc_dl_txt",
            )
        with dl_col2:
            if DOCX_AVAILABLE:
                # Build a proper .docx output
                out_doc = DocxDocument()
                out_doc.add_heading(f"Translated to {tgt_name}", level=1)
                for para in translated.split("\n"):
                    if para.strip():
                        out_doc.add_paragraph(para)
                docx_buf = io.BytesIO()
                out_doc.save(docx_buf)
                docx_buf.seek(0)
                st.download_button(
                    "↓ Download as .docx",
                    data=docx_buf,
                    file_name=f"{fname}_{tgt_name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key="doc_dl_docx",
                )

        if st.button("✕ Clear Document", key="doc_clear"):
            st.session_state.pop("doc_translated", None)
            st.session_state.pop("doc_filename", None)
            st.session_state.pop("doc_target_name", None)
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# ORIGINAL UI SECTIONS
# ─────────────────────────────────────────────────────────────────

def render_sidebar() -> None:
    indian_list = sorted(INDIAN_LANGS)
    world_list  = [l for l in LANGUAGES if l not in INDIAN_LANGS]

    html = f"""
        <div class="sb-logo">Translature</div>
        <div class="sb-sub">AI-powered language translation</div>
        <hr class="sb-hr">
        <div class="sb-head">About</div>
        <div class="sb-body">
            Translature is an AI-powered translator that handles text, images, voice, and documents
            across 100+ languages with smart auto-detection and full accessibility support.
        </div>
        <div style="margin-top:.5rem">
            {"".join(f'<div class="sb-feat"><span class="sb-icon">{i}</span><span>{l}</span></div>' for i,l in FEATURES)}
        </div>
        <hr class="sb-hr">
        <div class="sb-head">🇮🇳 Indian Languages</div>
        {chip_list(indian_list, INDIAN_LANGS)}
        <div class="sb-head" style="margin-top:.7rem">🌍 All Languages ({len(world_list)} more)</div>
        {chip_list(world_list)}
    """
    with st.sidebar:
        st.markdown(html, unsafe_allow_html=True)

def _render_count_bar(text: str) -> None:
    chars = len(text)
    words = len(text.split()) if text.strip() else 0
    pct   = min(chars / MAX_CHARS * 100, 100)

    if chars > MAX_CHARS:
        bar_color = "var(--danger)"
        char_cls  = ' style="color:var(--danger);font-weight:600"'
    elif chars > MAX_CHARS * 0.9:
        bar_color = "#fbbf24"
        char_cls  = ' style="color:#fbbf24;font-weight:600"'
    else:
        bar_color = "var(--coral)"
        char_cls  = ' style="color:var(--soft);font-weight:600"'

    st.markdown(
        f'''<div class="count-bar">
            <span class="count-chars"><b{char_cls}>{chars:,}</b> / {MAX_CHARS:,} chars</span>
            <div class="progress-wrap"><div class="progress-fill" style="width:{pct:.1f}%;background:{bar_color}"></div></div>
            <span class="count-words"><b style="color:var(--soft);font-weight:600">{words:,}</b> words</span>
        </div>''',
        unsafe_allow_html=True,
    )

def render_input_card() -> bool:
    def fix_text_callback():
        current_text = st.session_state.get("_text_buf", "")
        if current_text.strip():
            st.session_state["_text_buf"] = str(TextBlob(current_text).correct())

    def clear_text_callback():
        st.session_state["_text_buf"] = ""
        st.session_state["translated_text"] = ""
        st.session_state["detected_lang"] = ""

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(card_label("Source text"), unsafe_allow_html=True)

    text = st.text_area(
        "input", height=120,
        placeholder="Type or paste text here…",
        key="_text_buf",
        label_visibility="collapsed",
    )
    _render_count_bar(text)

    st.markdown('<hr class="cdivider">', unsafe_allow_html=True)

    source_opts = ["Auto Detect"] + list(LANGUAGES.keys())
    target_opts = list(LANGUAGES.keys())

    c1, c2, c3, c4, c5, c6 = st.columns([2.6, 0.6, 2.6, 1.2, 1.2, 2.2], vertical_alignment="bottom")
    with c1:
        st.selectbox("From", source_opts, key="source")
    with c2:
        btn_marker("marker-swap")
        if st.button("⇄", help="Swap languages", use_container_width=True):
            if st.session_state.source != "Auto Detect":
                st.session_state.source, st.session_state.target = st.session_state.target, st.session_state.source
                st.rerun()
    with c3:
        st.selectbox("To", target_opts, key="target")
    with c4:
        btn_marker("marker-ghost")
        st.button("✨ Fix", help="Auto-correct spelling", on_click=fix_text_callback, use_container_width=True)
    with c5:
        btn_marker("marker-ghost")
        st.button("✕ Clear", on_click=clear_text_callback, use_container_width=True)
    with c6:
        btn_marker("marker-primary")
        clicked = st.button("✦ Translate", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)
    return clicked

def render_result_card() -> None:
    t = st.session_state.translated_text
    if not t:
        return

    st.markdown('<div class="card card-result">', unsafe_allow_html=True)
    st.markdown(card_label("Translation"), unsafe_allow_html=True)

    if st.session_state.source == "Auto Detect" and st.session_state.detected_lang:
        name = lang_name_from_code(st.session_state.detected_lang)
        st.markdown(f'<div class="detected">Detected · {name}</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="result-text">{t}</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.5, 5])
    with c1:
        btn_marker("marker-teal")
        if st.button("📋 Copy", use_container_width=True, help="Copy translation"):
            escaped = t.replace("\\", "\\\\").replace("`", "\\`").replace("'", "\\'")
            js_code = f"""
            <script>
                window.parent.navigator.clipboard.writeText(`{escaped}`).then(() => {{
                    const t = window.parent.document.getElementById('clipboard-toast');
                    if (t) {{ t.classList.add('show'); setTimeout(() => t.classList.remove('show'), 2200); }}
                }});
            </script>
            """
            components.html(js_code, height=0, width=0)
    with c2:
        btn_marker("marker-teal")
        st.download_button("↓ Save", t, "translation.txt", "text/plain", use_container_width=True)
    with c3:
        target_code = LANGUAGES[st.session_state.target]
        if target_code in SUPPORTED_AUDIO_LANGS:
            btn_marker("marker-teal")
            if st.button("🔊 Play", use_container_width=True):
                audio = make_audio(t, target_code)
                if audio:
                    st.audio(audio, format="audio/mp3")
        else:
            btn_marker("marker-ghost")
            st.button("🔇 N/A", disabled=True, use_container_width=True, help="Audio not supported")

    st.markdown('</div>', unsafe_allow_html=True)

def render_history() -> None:
    history = st.session_state.history
    if not history:
        return

    st.markdown('<div class="card">', unsafe_allow_html=True)
    hcol1, hcol2 = st.columns([6, 1], vertical_alignment="bottom")
    with hcol1:
        st.markdown(card_label(f"History · {len(history)}"), unsafe_allow_html=True)
    with hcol2:
        btn_marker("marker-ghost")
        if st.button("Clear", key="clear_hist", use_container_width=True):
            st.session_state.history = []
            st.rerun()

    for entry in history:
        st.markdown(
            f'<div class="hist-item">'
            f'  <div class="hist-meta">'
            f'    <span class="hist-langs">{entry["src"]} → {entry["tgt"]}</span>'
            f'    <span class="hist-time">{entry["time"]}</span>'
            f'  </div>'
            f'  <div class="hist-original">{entry["input"]}</div>'
            f'  <div class="hist-translated">{entry["output"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# TAB BAR
# ─────────────────────────────────────────────────────────────────

def render_tab_bar() -> str:
    active = st.session_state.active_tab
    tabs = [
        ("text",     "✦ Text"),
        ("image",    "🖼️ Image OCR"),
        ("speech",   "🎙️ Speech"),
        ("document", "📄 Document"),
    ]

    # Render styled tab bar (visual only)
    tab_html = '<div class="tab-bar">'
    for key, label in tabs:
        cls = "tab-btn active" if key == active else "tab-btn"
        tab_html += f'<div class="{cls}" style="pointer-events:none">{label}</div>'
    tab_html += '</div>'
    st.markdown(tab_html, unsafe_allow_html=True)

    # Actual selector (hidden via CSS override won't work cleanly, use columns instead)
    tcols = st.columns(len(tabs))
    for i, (key, label) in enumerate(tabs):
        with tcols[i]:
            if active != key:
                if st.button(label, key=f"tab_{key}", use_container_width=True):
                    st.session_state.active_tab = key
                    st.rerun()

    return active

# ─────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(page_title="Translature — AI Translator", page_icon="✦", layout="centered")

    for k, v in SESSION_DEFAULTS.items():
        st.session_state.setdefault(k, v)

    # Inject CSS (dynamic based on accessibility settings)
    st.markdown(
        build_css(
            st.session_state.a11y_font_size,
            st.session_state.a11y_high_contrast,
            st.session_state.a11y_dyslexia,
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="hdr">'
        '<div class="hdr-title">Translature</div>'
        '<div class="hdr-sub" color="white">Translate text, images, voice & documents across 100+ languages</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    render_sidebar()

    # Accessibility panel (always visible, collapsible)
    render_accessibility_panel()

    # Tab navigation
    active_tab = render_tab_bar()

    # Tab content
    if active_tab == "text":
        if render_input_card():
            run_translation(
                st.session_state.get("_text_buf", ""),
                st.session_state.source,
                st.session_state.target,
            )
        render_result_card()
        render_history()

    elif active_tab == "image":
        render_ocr_tab()
        render_result_card()
        render_history()

    elif active_tab == "speech":
        render_speech_tab()
        render_history()

    elif active_tab == "document":
        render_document_tab()


if __name__ == "__main__":
    main()
