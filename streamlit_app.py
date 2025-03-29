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
st.set_page_config(page_title="TEST SicurANCE Piemonte e Valle d'Aosta", layout="centered")

col1, col2 = st.columns([1, 4])
with col1:
    st.image("logo_ance.jpg", width=220)
with col2:
    st.markdown("""
        <h1 style='font-size: 24px; margin-bottom: 5px;'> TEST SicurANCE Piemonte e Valle d'Aosta</h1>
        <h4 style='margin-top: 0;'>Analisi AI della sicurezza nei cantieri</h4>
    """, unsafe_allow_html=True)

# ————— FILE UPLOAD ————— #
uploaded_files = st.file_uploader(
    "📷 Carica una o più foto del cantiere (max 5)",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

if uploaded_files:
    st.session_state["uploaded_images"] = [file.read() for file in uploaded_files]
    st.session_state["image_ready"] = True
    for i, img_bytes in enumerate(st.session_state["uploaded_images"]):
        st.image(BytesIO(img_bytes), caption=f"📍 Immagine {i+1}", use_container_width=True)

# ————— FORM ————— #
with st.form("note_form"):
    note = st.text_area("Località o Note aggiuntive per i report (facoltative)", height=100)
    submitted = st.form_submit_button("✅ Conferma per procedere all'analisi delle foto")
    if submitted:
        st.session_state["note"] = note
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
                                "Sei un esperto in sicurezza nei cantieri edili in Italia. "
                                "Rispondi sempre in lingua italiana. Analizza le immagini come se fossi un ispettore del lavoro, secondo il D.Lgs. 81/2008."
                            )
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        "Sei un esperto di sicurezza nei cantieri edili in Italia. Rispondi sempre in lingua italiana. Analizza le immagini come se fossi un ispettore del lavoro, secondo il D.Lgs. 81/2008.\n\n"
                                        "Analizza questa immagine come esperto di sicurezza nei cantieri secondo il D.Lgs. 81/2008. Non devi identificare le persone, ma puoi valutarne l'equipaggiamento e il comportamento.\n\n"
                                        "Verifica nel dettaglio i seguenti aspetti, indicando chiaramente se sono rispettati o meno, e fornendo il riferimento normativo specifico del D.Lgs. 81/2008:\n\n"
                                        "- **Dispositivi di Protezione Individuale (DPI):**\n"
                                        "    - Elmetto: è presente? È indossato correttamente (allacciato, della taglia giusta)? (Riferimento normativo: Art. 75-77)\n"
                                        "    - Imbracatura: è presente? È indossata e allacciata correttamente? (Riferimento normativo: Art. 115-116)\n"
                                        "    - Scarpe antinfortunistiche: sono presenti e indossate? (Riferimento normativo: Art. 75-77)\n"
                                        "    - Guanti: sono presenti e indossati? (Riferimento normativo: Art. 75-77)\n"
                                        "    - Occhiali protettivi: sono presenti e indossati, se necessario? (Riferimento normativo: Art. 75-77)\n"
                                        "- **Lavori in quota:**\n"
                                        "    - Sono presenti sistemi di protezione contro le cadute (parapetti, linee vita)? (Riferimento normativo: Art. 115-116)\n"
                                        "    - I lavoratori utilizzano correttamente i sistemi di protezione? (Riferimento normativo: Art. 115-116)\n"
                                        "- **Ponteggi e trabattelli:**\n"
                                        "    - Sono montati correttamente? Sono stabili? Sono presenti parapetti? (Riferimento normativo: Allegato XVIII)\n"
                                        "    - Sono presenti tavole del ponteggio integre? (Riferimento normativo: Allegato XVIII)\n"
                                        "- **Segnaletica e delimitazioni:**\n"
                                        "    - È presente segnaletica di sicurezza per indicare pericoli o obblighi? (Riferimento normativo: Titolo V)\n"
                                        "    - Le aree pericolose sono delimitate per impedire l'accesso non autorizzato? (Riferimento normativo: Titolo V)\n"
                                        "- **Rischi ambientali:**\n"
                                        "    - Sono presenti rischi di caduta o inciampo (materiali disordinati, pavimenti scivolosi)?\n"
                                        "    - Sono presenti rischi elettrici (cavi scoperti, quadri elettrici accessibili)?\n"
                                        "    - Sono presenti rischi di caduta dall'alto di materiali?\n\n"
                                        "Fornisci una nota completa e dettagliata, indicando per ogni criticità riscontrata il riferimento normativo specifico del D.Lgs. 81/2008."
                                    )
                                },
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
                pdf.cell(0, 10, sanitize_text("Report SicurANCE Piemonte e Valle d’Aosta"), ln=True, align="C")
                pdf.set_font("Helvetica", style='', size=11)
                pdf.cell(0, 10, sanitize_text("Analisi della sicurezza nei cantieri - ai sensi del D.Lgs. 81/2008"), ln=True, align="C")
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

                pdf.set_font("Helvetica", style='B', size=12)
                label_text = f"{cleaned_label} - Risultato dell'analisi:"
                text_label_height = get_multicell_height(pdf, label_text, pdf.w - 30)
                if current_y + text_label_height > pdf.h - 30:
                    pdf.add_page()
                    add_header()
                    current_y = 40
                pdf.set_y(current_y)
                pdf.multi_cell(0, 6, label_text)
                current_y += text_label_height

                pdf.set_font("Helvetica", size=11)
                text_report_height = get_multicell_height(pdf, cleaned_report, pdf.w - 30)
                if current_y + text_report_height > pdf.h - 30:
                    pdf.add_page()
                    add_header()
                    current_y = 40
                pdf.set_y(current_y)
                pdf.multi_cell(0, 6, cleaned_report)
                current_y += text_report_height + 10

            if note:
                pdf.add_page()
                add_header()
                pdf.set_font("Helvetica", style='B', size=12)
                pdf.cell(0, 10, "Note aggiuntive:", ln=True)
                pdf.set_font("Helvetica", size=11)
                pdf.multi_cell(0, 6, sanitize_text(note))

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
