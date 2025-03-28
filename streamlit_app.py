import streamlit as st
from openai import OpenAI
import base64
from fpdf import FPDF
from io import BytesIO
from PIL import Image
import re

# Funzione per "pulire" il testo da caratteri non compatibili col PDF
def sanitize_text(text):
    return re.sub(r'[^\x00-\x7F]+', '', text)

# Inizializza il client con la chiave segreta
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="SicurANCE Piemonte e Valle d'Aosta", layout="centered")

# Header con logo e titolo personalizzato
col1, col2 = st.columns([1, 4])
with col1:
    st.image("logo_ance.jpg", width=220)
with col2:
    st.markdown(
        """
        <h1 style='font-size: 24px; margin-bottom: 5px;'>SicurANCE Piemonte e Valle d'Aosta</h1>
        <h4 style='margin-top: 0;'>Analisi automatica della sicurezza nei cantieri</h4>
        """,
        unsafe_allow_html=True
    )

uploaded_file = st.file_uploader("📷 Carica una foto che riprenda il cantiere nella sua interezza", type=["jpg", "jpeg", "png"])

note = st.text_area("Note aggiuntive (facoltative)")

if uploaded_file:
    st.image(uploaded_file, caption="📍 Immagine caricata", use_container_width=True)

    with st.spinner("🧠 Analisi in corso..."):

        image_bytes = uploaded_file.read()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Sei un esperto in sicurezza nei cantieri edili. "
                            "Analizza le immagini come se fossi un ispettore del lavoro, secondo il D.Lgs. 81/2008."
                        )
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Analizza l'immagine seguente come **esperto di sicurezza nei cantieri edili**, ai sensi del D.Lgs. 81/2008. "
                                    "Fornisci un **report tecnico dettagliato e in lingua italiana**, incentrato esclusivamente sull’osservazione degli elementi visibili.\n\n"
                                    "**Non valutare le persone in quanto tali**, ma limita la tua analisi a ciò che è visibile nella foto, ad esempio:\n"
                                    "- Se i lavoratori **indossano correttamente i dispositivi di protezione individuale (DPI)**: casco, guanti, imbracature, occhiali, scarpe antinfortunistiche\n"
                                    "- Se vi sono **lavori in quota** o **carichi sospesi** in condizioni non sicure\n"
                                    "- Se i **ponteggi** o i **trabattelli** sono conformi alle norme (parapetti, tavole fermapiede, accessi)\n"
                                    "- Se esiste **segnaletica di sicurezza, recinzioni** o delimitazioni delle aree di rischio\n"
                                    "- Se l’ambiente presenta **rischi elettrici, chimici, meccanici, da inciampo o scivolamento**\n\n"
                                    "Riporta tutte le criticità **visibili** con tono tecnico e oggettivo, indicando ove possibile anche gli **articoli del D.Lgs. 81/2008** violati.\n"
                                    "**Non fornire risposte generiche.**"
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
                "Avvertenza legale\n\n"
                "L'app SicurANCE Piemonte e Valle d'Aosta è uno strumento di supporto all’analisi della sicurezza in cantiere. "
                "Non sostituisce la valutazione tecnica di figure abilitate (es. CSP, CSE, RSPP) e non esonera dagli obblighi di legge. "
                "Gli autori declinano ogni responsabilità per usi impropri o conseguenze derivanti da quanto riportato nei report generati."
            )

            # ✅ Generazione PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Arial", size=12)

            pdf.multi_cell(0, 10, "Report tecnico - SicurANCE Piemonte e Valle d'Aosta\n\n")
            pdf.multi_cell(0, 10, sanitize_text(report))

            if note:
                pdf.multi_cell(0, 10, "\nNote aggiuntive:\n" + sanitize_text(note) + "\n")

            pdf.multi_cell(0, 10, "\n" + sanitize_text(disclaimer))

            # Inserisci immagine
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

        except Exception as e:
            st.error("❌ Errore durante la generazione del report.")
            st.exception(e)
