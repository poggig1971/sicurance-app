import streamlit as st
from openai import OpenAI
import base64
from fpdf import FPDF
from io import BytesIO
from PIL import Image
import re

def sanitize_text(text):
    return re.sub(r'[^\x00-\x7F]+', '', text)

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])




st.set_page_config(page_title="TEST SicurANCE Piemonte e Valle d'Aosta", layout="centered")


# Header
col1, col2 = st.columns([1, 4])
with col1:
    st.image("logo_ance.jpg", width=220)
with col2:
    st.markdown("""
        <h1 style='font-size: 24px; margin-bottom: 5px;'> TEST SicurANCE Piemonte e Valle d'Aosta</h1>
        <h4 style='margin-top: 0;'>Analisi automatica della sicurezza nei cantieri</h4>
    """, unsafe_allow_html=True)




# Upload immagine
uploaded_file = st.file_uploader("📷 Carica una foto che riprenda il cantiere nella suo insieme, senza inquadrare direttamente le persone", type=["jpg", "jpeg", "png"])

if uploaded_file:
    st.session_state["uploaded_image"] = uploaded_file.read()
    st.session_state["image_ready"] = True
    st.image(BytesIO(st.session_state["uploaded_image"]), caption="📍 Immagine caricata", use_container_width=True)

# Form per le note
with st.form("note_form"):
    note = st.text_area("Note aggiuntive (facoltative)", placeholder="Scrivi qui eventuali note...", height=100)
    submitted = st.form_submit_button("✅ Conferma note")
    if submitted:
        st.session_state["note"] = note
        st.session_state["analyze"] = True

# Analisi solo se richiesto e immagine presente
if st.session_state.get("analyze") and st.session_state.get("image_ready"):
    with st.spinner("🧠 Analisi in corso..."):

        image_bytes = st.session_state["uploaded_image"]
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        note = st.session_state.get("note", "")

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            " Sei un esperto in sicurezza nei cantieri edili in Italia. Rispondi sempre in lingua italiana, anche se il contenuto o l’immagine non fosse chiarissima. Non usare mai frasi introduttive in inglese. Analizza le immagini come se fossi un ispettore del lavoro, secondo il D.Lgs. 81/2008."
                        )
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    " Analizza questa immagine come esperto di sicurezza nei cantieri secondo il D.Lgs. 81/2008. "
                                    "Non devi identificare le persone, ma puoi valutarne l'equipaggiamento e il comportamento. "
                                    "Verifica nel dettaglio se:\n"
                                    "- vengono indossati correttamente i dispositivi di protezione individuale (casco, guanti, imbracature, occhiali, scarpe antinfortunistiche)\n"
                                    "- i lavoratori operano in sicurezza in quota o in prossimità di carichi sospesi\n"
                                    "- i ponteggi o trabattelli rispettano i requisiti normativi\n"
                                    "- vi siano segnaletiche, recinzioni o delimitazioni di sicurezza adeguate\n"
                                    "- l’ambiente di lavoro presenta rischi elettrici, chimici, meccanici, da scivolamento o inciampo\n\n"
                                    "Fornisci una nota completa con tutte le criticità osservabili nella foto e indica, ove possibile, anche i riferimenti normativi violati."
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
            st.success("✅ Analisi completata")
            st.markdown("### Report tecnico:")
            st.write(report)

            disclaimer = (
                "Avvertenza sull’utilizzo dell’app\n\n"
                " L'app SicurANCE Piemonte e Valle d'Aosta è uno strumento di supporto all’analisi della sicurezza in cantiere. "
                "Non sostituisce la valutazione tecnica di figure abilitate (es. CSP, CSE, RSPP) e non esonera dagli obblighi di legge. "
                "Gli autori declinano ogni responsabilità per usi impropri o conseguenze derivanti da quanto riportato nei report generati."
            )

            # PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Arial", size=12)

            pdf.multi_cell(0, 10, "Report tecnico - SicurANCE Piemonte e Valle d'Aosta\n\n")
            pdf.multi_cell(0, 10, sanitize_text(report))
            if note:
                pdf.multi_cell(0, 10, "\nNote aggiuntive:\n" + sanitize_text(note) + "\n")
            pdf.multi_cell(0, 10, "\n" + sanitize_text(disclaimer))

            # Immagine nel PDF
            img = Image.open(BytesIO(image_bytes))
            img_path = "/tmp/temp_image.jpg"
            img.save(img_path)
            pdf.image(img_path, x=10, w=180)

            pdf_output = BytesIO()
            pdf_bytes = pdf.output(dest='S').encode('latin-1', 'replace')
            pdf_output.write(pdf_bytes)
            pdf_output.seek(0)

            st.download_button(
                label="📄 Scarica il report in PDF",
                data=pdf_output,
                file_name="report_sicurANCE.pdf",
                mime="application/pdf"
            )

            # Reset
            st.session_state["analyze"] = False

        except Exception as e:
            st.error("❌ Errore durante la generazione del report.")
            st.exception(e)

# Disclaimer
with st.expander("ℹ️ Avvertenza sull’utilizzo dell’app", expanded=True):
    st.markdown("""
        <div style='font-size: 14px; line-height: 1.5; color: gray;'>
        <strong>L'app SicurANCE Piemonte e Valle d'Aosta</strong> è uno strumento di supporto all’analisi della sicurezza in cantiere. "
                Non sostituisce la valutazione tecnica di figure abilitate (es. CSP, CSE, RSPP) e non esonera dagli obblighi di legge.
                Gli autori declinano ogni responsabilità per usi impropri o conseguenze derivanti da quanto riportato nei report generati.
        </div>
    """, unsafe_allow_html=True)
