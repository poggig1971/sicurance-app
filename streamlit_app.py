import streamlit as st
from openai import OpenAI
import base64
from fpdf import FPDF
from io import BytesIO
from PIL import Image
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
uploaded_files = st.file_uploader(
    "📷 Carica una o più foto del cantiere (max 5) Le immagini caricate non vengono archiviate né associate a metadati personali. L’intero processo di analisi avviene esclusivamente in sessione, nel rispetto delle best practice del Regolamento Generale sulla Protezione dei Dati (GDPR), garantendo la tutela della privacy degli utenti e dei soggetti eventualmente presenti.",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

if uploaded_files:
    st.session_state["uploaded_images"] = [file.read() for file in uploaded_files]
    st.session_state["image_ready"] = True
    for i, img_bytes in enumerate(st.session_state["uploaded_images"]):
        st.image(BytesIO(img_bytes), caption=f"📍 Immagine {i+1}", use_container_width=True)

# ————— PULSANTE SEMPLICE ————— #
if st.button("✅ Avvia l'analisi delle foto"):
    st.session_state["note"] = ""
    st.session_state["analyze"] = True

# ————— ANALISI + PDF ————— #
if st.session_state.get("analyze") and st.session_state.get("image_ready"):
    with st.spinner("🧠 Analisi in corso..."):
        report_texts = []
        try:
            for i, image_bytes in enumerate(st.session_state["uploaded_images"]):
                base64_image = base64.b64encode(image_bytes).decode("utf-8")
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                    {   
                        "role": "system",
                        "content": (
                            "Sei un esperto in sicurezza nei cantieri edili in Italia. Rispondi sempre in lingua italiana. Analizza le immagini esclusivamente per verificare la presenza e il corretto utilizzo dei dispositivi di protezione individuale (DPI), la conformità di ponteggi e attrezzature, e l’idoneità delle misure di prevenzione dei rischi secondo il D.Lgs. 81/2008. Ignora qualsiasi aspetto relativo all’identificazione di persone. Considera solo gli elementi tecnici visibili (caschi, scarpe, imbracature, cartelli, delimitazioni, etc.)."
                        )
                    },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                    "Analizza questa immagine come esperto di sicurezza nei cantieri secondo il D.Lgs. 81/2008. Non devi in alcun modo identificare persone, volti o soggetti specifici. Verifica solamente se:- sono presenti e correttamente utilizzati i dispositivi di protezione individuale (caschi, guanti, occhiali, scarpe antinfortunistiche, imbracature) - l’ambiente è conforme alle norme di sicurezza (ponteggi, parapetti, segnaletica, recinzioni, carichi sospesi, rischio elettrico o meccanico, rischio di scivolamento o caduta) - i comportamenti operativi osservabili sono compatibili con la normativa sulla sicurezza Fornisci una valutazione dettagliata delle eventuali criticità tecniche osservabili, con riferimento agli articoli del D.Lgs. 81/2008, evitando qualsiasi commento su chi o cosa appare nell’immagine."
                                )                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=1000,
                    temperature=0.2
                )
                report = response.choices[0].message.content
                report_texts.append((image_bytes, f"Immagine {i+1}", report))

            st.success("✅ Analisi completata")
            st.markdown("### Report:")
            for _, label, report in report_texts:
                st.subheader(label)
                st.write(report)

            # ——— PDF GENERATION ——— #
            pdf = FPDF(orientation='P', unit='mm', format='A4')
            pdf.set_auto_page_break(auto=False, margin=15)
            pdf.set_font("Helvetica", size=11)

            def add_header():
                pdf.set_font("Helvetica", style='B', size=13)
                pdf.cell(0, 10, sanitize_text("Report "), ln=True, align="C")
                pdf.set_font("Helvetica", style='', size=11)
                pdf.cell(0, 10, sanitize_text("Analisi Automatica della sicurezza nei cantieri"), ln=True, align="C")
                pdf.ln(5)

            def add_footer():
                pdf.set_y(-15)
                pdf.set_font("Helvetica", size=8)
                pdf.set_text_color(128)
                pdf.cell(0, 10, sanitize_text(f"Generato il {datetime.today().strftime('%d/%m/%Y')} - Pagina {pdf.page_no()}"), align='C')

            pdf.add_page()
            add_header()
            current_y = 40

            for idx, (img_bytes, img_label, report) in enumerate(report_texts):
                cleaned_label = sanitize_text(img_label)
                cleaned_report = sanitize_text(report)
                img = Image.open(BytesIO(img_bytes)).convert("RGB")
                img_w, img_h = img.size
                ratio = 180 / img_w
                img_h_resized = img_h * ratio
                img_path = f"/tmp/temp_{cleaned_label.replace(' ', '_')}.jpg"
                img.save(img_path)

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

           # if note:
           #     pdf.add_page()
           #     add_header()
           #     pdf.set_font("Helvetica", style='B', size=12)
           #     pdf.cell(0, 10, "Note aggiuntive:", ln=True)
           #     pdf.set_font("Helvetica", size=11)
        #    pdf.multi_cell(0, 6, sanitize_text(note))

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

        except Exception as e:
            st.error("❌ Errore durante la generazione del report.")
            st.exception(e)

# ————— AVVERTENZA ————— #
with st.expander("ℹ️ Avvertenza sull’utilizzo dell’app", expanded=True):
    st.markdown("""
        <div style='font-size: 14px; line-height: 1.5; color: gray;'>
        <strong>L'app SicurANCE Piemonte e Valle d'Aosta</strong> è uno strumento di supporto all’analisi della sicurezza in cantiere.
        Non sostituisce la valutazione tecnica di figure abilitate (es. CSP, CSE, RSPP) e non esonera dagli obblighi di legge.
        Gli autori declinano ogni responsabilità per usi impropri o conseguenze derivanti da quanto riportato nei report generati.
        </div>
    """, unsafe_allow_html=True)
