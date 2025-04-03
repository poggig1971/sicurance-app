import streamlit as st
from openai import OpenAI
import base64
from fpdf import FPDF
from io import BytesIO
from PIL import Image, ImageOps
import re
import os
from datetime import datetime

# --- UTILITY FUNCTIONS --- #
def sanitize_text(text):
    text = text.replace("’", "'").replace("–", "-").replace("“", '"').replace("”", '"')
    text = re.sub(r'[\u2018\u2019\u201C\u201D]', '', text)
    return text.encode('latin-1', 'ignore').decode('latin-1')

def get_multicell_height(pdf, text, w):
    temp_pdf = FPDF()
    temp_pdf.add_page()
    temp_pdf.set_font(pdf.font_family, size=pdf.font_size_pt)
    start_y = temp_pdf.get_y()
    temp_pdf.multi_cell(w, 6, text)
    return temp_pdf.get_y() - start_y

def evidenzia_criticita(report_text):
    patterns = [
        r"(Criticità:.*)",
        r"(Rischio di .*)",
        r"(Non è presente .*)",
        r"(Assenza di .*)",
        r"(Mancanza di .*)",
        r"(Utilizzo non corretto di .*)",
        r"(DPI.*non.*indossato.*)",
        r"(Non conforme.*)",
        r"(Inadempienza.*)",
        r"(Pericolo di .*)",
    ]
    for pattern in patterns:
        report_text = re.sub(pattern, r"🔴 \1", report_text, flags=re.IGNORECASE)
    return report_text

def conta_criticita(report_text):
    pattern = r"(?i)(Criticità:|Rischio di|Non è presente|Assenza di|Mancanza di|Utilizzo non corretto di|DPI.*non.*indossato|Non conforme|Inadempienza|Pericolo di)"
    return len(re.findall(pattern, report_text))


def semaforo_criticita(n):
    if n == 0:
        return "🟢"
    elif n <= 2:
        return "🟡"
    else:
        return "🔴"

# --- OPENAI CLIENT --- #
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- UI SETUP --- #
st.set_page_config(page_title="TESTING WebApp SicurANCE Piemonte e Valle d'Aosta", layout="centered")

col1, col2 = st.columns([1, 4])
with col1:
    st.image("logo_ance.jpg", width=220)
with col2:
    st.markdown("""
        <h1 style='font-size: 24px; margin-bottom: 5px;'> TESTING WebApp SicurANCE Piemonte e Valle d'Aosta</h1>
        <h4 style='margin-top: 0;'>Analisi AI della sicurezza nei cantieri</h4>
    """, unsafe_allow_html=True)

# --- FILE UPLOAD --- #
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_IMAGES = 5
MAX_WIDTH = 1200

uploaded_files = st.file_uploader(
    f" Carica fino a {MAX_IMAGES} foto del cantiere (max {MAX_FILE_SIZE_MB} MB e {MAX_WIDTH}px per immagine)",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

if uploaded_files:
    if len(uploaded_files) > MAX_IMAGES:
        st.warning(f"⚠️ Hai caricato più di {MAX_IMAGES} immagini. Solo le prime {MAX_IMAGES} verranno analizzate.")
        uploaded_files = uploaded_files[:MAX_IMAGES]

    valid_images = []
    for file in uploaded_files:
        if file.size > MAX_FILE_SIZE:
            st.warning(f"⚠️ Il file '{file.name}' supera il limite di {MAX_FILE_SIZE_MB} MB e verrà ignorato.")
            continue

        try:
            image = Image.open(file)
            if image.width > MAX_WIDTH:
                ratio = MAX_WIDTH / image.width
                new_size = (MAX_WIDTH, int(image.height * ratio))
                image = image.resize(new_size)
                st.info(f"ℹ️ L'immagine '{file.name}' è stata ridimensionata.")

            buffered = BytesIO()
            image = ImageOps.exif_transpose(image)
            image.save(buffered, format="JPEG", quality=85)
            img_bytes = buffered.getvalue()
            valid_images.append(img_bytes)
            st.image(BytesIO(img_bytes), caption=f"{file.name}", use_container_width=True)
        except Exception as e:
            st.error(f"❌ Errore con il file '{file.name}': {e}")

    if valid_images:
        st.session_state["uploaded_images"] = valid_images
        st.session_state["image_ready"] = True
    else:
        st.session_state["image_ready"] = False
        st.error("❌ Nessuna immagine valida caricata.")

# --- PULSANTE AVVIO --- #
if st.button("✅ Avvia l'analisi delle foto"):
    st.session_state["analyze"] = True

if st.session_state.get("analyze") and st.session_state.get("image_ready"):
    with st.spinner(" Analisi in corso..."):
        report_texts = []
        try:
            for i, image_bytes in enumerate(st.session_state["uploaded_images"]):
                base64_image = base64.b64encode(image_bytes).decode("utf-8")
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": (
                            " Sei un esperto in sicurezza nei cantieri edili in Italia. Rispondi sempre in lingua italiana, anche se il contenuto o l’immagine non fosse chiarissima. Non usare mai frasi introduttive in inglese. Analizza le immagini come se fossi un ispettore del lavoro, secondo il D.Lgs. 81/2008.")},
                        {"role": "user", "content": [
                            {"type": "text", "text": (
                                " Analizza questa immagine come esperto di sicurezza nei cantieri secondo il D.Lgs. 81/2008. "
                                    "Non devi identificare le persone, ma puoi valutarne l'equipaggiamento e il comportamento. "
                                    "Verifica nel dettaglio se:\n"
                                    "- vengono indossati correttamente i dispositivi di protezione individuale (casco, guanti, imbracature, occhiali, scarpe antinfortunistiche)\n"
                                    "- i lavoratori operano in sicurezza in quota o in prossimità di carichi sospesi\n"
                                    "- i ponteggi o trabattelli rispettano i requisiti normativi\n"
                                    "- vi siano segnaletiche, recinzioni o delimitazioni di sicurezza adeguate\n"
                                    "- l’ambiente di lavoro presenta rischi elettrici, chimici, meccanici, da scivolamento o inciampo\n\n"
                                    "Fornisci una nota completa con tutte le criticità osservabili nella foto e indica, ove possibile, anche i riferimenti normativi violati."
)},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]}
                    ],
                    max_tokens=1000,
                    temperature=0.2
                )
                report = response.choices[0].message.content
                report = evidenzia_criticita(report)
                criticita_count = conta_criticita(report)
                report_texts.append((image_bytes, f"Immagine {i+1}", report, criticita_count))

            st.success("✅ Analisi completata")
            st.markdown("### Report:")
            for _, label, report, criticita in report_texts:
                st.subheader(f"{label} – {semaforo_criticita(criticita)} {criticita} criticità")
                st.write(report)

        except Exception as e:
            st.error(f"❌ Errore durante l'analisi: {e}")

        finally:
            st.session_state["analyze"] = False

# ————— AVVERTENZA ————— #
with st.expander("ℹ️ Avvertenza sull’utilizzo dell’app", expanded=True):
    st.markdown("""
        <div style='font-size: 14px; line-height: 1.5; color: gray;'>
        <strong>L'app SicurANCE Piemonte e Valle d'Aosta</strong> è uno strumento di supporto all’analisi della sicurezza in cantiere.
        Non sostituisce la valutazione tecnica di figure abilitate (es. CSP, CSE, RSPP) e non esonera dagli obblighi di legge.
        Gli autori declinano ogni responsabilità per usi impropri o conseguenze derivanti da quanto riportato nei report generati.
        </div>
    """, unsafe_allow_html=True)
