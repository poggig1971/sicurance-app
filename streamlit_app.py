import streamlit as st
from openai import OpenAI
import base64
from fpdf import FPDF
from io import BytesIO
from PIL import Image, ImageOps
import re
import os
from datetime import datetime

# ————— UTILITY FUNCTIONS ————— #
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
        r"(Criticità rilevata:)",
        r"(Rischio di )",
        r"(Non è presente )",
        r"(Assenza di )",
        r"(Mancanza di )",
        r"(Utilizzo non corretto di )",
        r"(DPI.*non.*indossato)",
        r"(Non conforme)",
        r"(Inadempienza)",
        r"(Pericolo di )",
    ]
    for pattern in patterns:
        report_text = re.sub(pattern, r"🔴 \1", report_text, flags=re.IGNORECASE)
    return report_text

def conta_criticita(report_text):
    return report_text.count("🔴")

def semaforo_criticita(n):
    if n == 0:
        return "🟢"
    elif n <= 2:
        return "🟡"
    else:
        return "🔴"

# ————— OPENAI CLIENT ————— #
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ————— UI SETUP ————— #
st.set_page_config(page_title="TESTING WebApp SicurANCE Piemonte e Valle d'Aosta", layout="centered")

col1, col2 = st.columns([1, 4])
with col1:
    st.image("logo_ance.jpg", width=220)
with col2:
    st.markdown("""
        <h1 style='font-size: 24px; margin-bottom: 5px;'> TESTING WebApp SicurANCE Piemonte e Valle d'Aosta</h1>
        <h4 style='margin-top: 0;'>Analisi AI della sicurezza nei cantieri</h4>
    """, unsafe_allow_html=True)

# ————— FILE UPLOAD ————— #
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_IMAGES = 5
MAX_WIDTH = 1200

uploaded_files = st.file_uploader(
    f"📷 Carica fino a {MAX_IMAGES} foto del cantiere (max {MAX_FILE_SIZE_MB} MB e {MAX_WIDTH}px per immagine)",
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


# ————— PULSANTE AVVIO ————— #
if st.button("✅ Avvia l'analisi delle foto"):
    st.session_state["analyze"] = True

if st.session_state.get("analyze") and st.session_state.get("image_ready"):
    with st.spinner("🧠 Analisi in corso..."):
        report_texts = []
        try:
            for i, image_bytes in enumerate(st.session_state["uploaded_images"]):
                base64_image = base64.b64encode(image_bytes).decode("utf-8")
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": (
                            "Sei un esperto di sicurezza nei cantieri. Rispondi solo sugli aspetti tecnici "
                            "e normativi secondo il D.Lgs. 81/2008. Non identificare persone. Usa uno stile tecnico, "
                            "suddiviso per punti. Evidenzia eventuali criticità e suggerisci azioni correttive.")},
                        {"role": "user", "content": [
                            {"type": "text", "text": (
                                "Analizza la sicurezza dell'immagine allegata secondo il D.Lgs. 81/2008. "
                                "Verifica DPI, ambiente, comportamenti. Specifica criticità e articoli di riferimento.")},
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


            # ——— PDF GENERATION ——— #
            pdf = FPDF(orientation='P', unit='mm', format='A4')
            pdf.set_auto_page_break(auto=False, margin=15)
            pdf.set_font("Helvetica", size=11)

            def add_header():
                pdf.set_font("Helvetica", style='B', size=13)
                pdf.cell(0, 10, sanitize_text("Report"), ln=True, align="C")
                pdf.set_font("Helvetica", style='', size=11)
                pdf.cell(0, 10, sanitize_text("Analisi automatica della sicurezza nei cantieri"), ln=True, align="C")
                pdf.ln(5)

            def add_footer():
                pdf.set_y(-15)
                pdf.set_font("Helvetica", size=8)
                pdf.set_text_color(128)
                pdf.cell(0, 10, sanitize_text(f"Generato il {datetime.today().strftime('%d/%m/%Y')} - Pagina {pdf.page_no()}"), align='C')

            pdf.add_page()
            add_header()
            current_y = 40

            for idx, (img_bytes, img_label, report, _) in enumerate(report_texts):
                cleaned_label = sanitize_text(img_label)
                cleaned_report = sanitize_text(report)

                img = Image.open(BytesIO(img_bytes)).convert("RGB")
                img_w, img_h = img.size
                ratio = 180 / img_w
                img_h_resized = img_h * ratio
                img_path = f"/tmp/temp_{cleaned_label.replace(' ', '_')}.jpg"
                img.resize((180, int(img_h_resized))).save(img_path)

                if current_y + img_h_resized > pdf.h - 30:
                    pdf.add_page()
                    add_header()
                    current_y = 40

                pdf.image(img_path, x=15, y=current_y, w=180)
                current_y += img_h_resized + 5
                os.remove(img_path)

                pdf.set_font("Helvetica", style='B', size=11)
                label_text = f"{cleaned_label} - Risultato dell'analisi:"
                text_label_height = get_multicell_height(pdf, label_text, pdf.w - 30)
                if current_y + text_label_height > pdf.h - 30:
                    pdf.add_page()
                    add_header()
                    current_y = 40
                pdf.set_y(current_y)
                pdf.multi_cell(0, 6, label_text)
                current_y += text_label_height

                pdf.set_font("Helvetica", size=10)
                text_report_height = get_multicell_height(pdf, cleaned_report, pdf.w - 30)
                if current_y + text_report_height > pdf.h - 30:
                    pdf.add_page()
                    add_header()
                    current_y = 40
                pdf.set_y(current_y)
                pdf.multi_cell(0, 6, cleaned_report)
                current_y += text_report_height + 10

            # ——— INDICE DELLE CRITICITÀ CON SEMAFORO ——— #
            pdf.add_page()
            add_header()
            pdf.set_font("Helvetica", style='B', size=12)
            pdf.cell(0, 10, "Indice delle criticità rilevate per immagine:", ln=True)
            pdf.ln(5)
            pdf.set_font("Helvetica", size=10)
            for _, label, _, criticita in report_texts:
                bollino = semaforo_criticita(criticita)
                testo = f"{bollino} {sanitize_text(label)}: {criticita} criticità rilevate"
                pdf.cell(0, 8, testo, ln=True)

            # ——— DISCLAIMER ——— #
            disclaimer = (
                "L'app SicurANCE Piemonte e Valle d'Aosta è uno strumento di supporto all’analisi della sicurezza in cantiere. "
                "Non sostituisce la valutazione tecnica di figure abilitate (es. CSP, CSE, RSPP) e non esonera dagli obblighi di legge. "
                "Gli autori declinano ogni responsabilità per usi impropri o conseguenze derivanti da quanto riportato nei report generati."
            )

            pdf.add_page()
            add_header()
            pdf.set_font("Helvetica", style='B', size=12)
            pdf.cell(0, 10, "Disclaimer sull'utilizzo dell'applicativo:", ln=True)
            pdf.set_font("Helvetica", size=10)
            pdf.multi_cell(0, 6, sanitize_text(disclaimer))

            for i in range(1, pdf.page_no() + 1):
                pdf.page = i
                add_footer()

            pdf_output = BytesIO()
            pdf_bytes = pdf.output(dest='S').encode('latin-1', 'ignore')
            pdf_output.write(pdf_bytes)
            pdf_output.seek(0)

            st.download_button(
                label="📄 Scarica il report in PDF",
                data=pdf_output,
                file_name="report.pdf",
                mime="application/pdf"
            )

            st.session_state["analyze"] = False
