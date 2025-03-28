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

st.set_page_config(page_title="TEST SicurANCE Piemonte e Valle d'Aosta", layout="centered")

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

uploaded_file = st.file_uploader("📷 Carica una foto che riprenda il cantiere nella sua interezza, senza inquadrare direttamente una persona", type=["jpg", "jpeg", "png"])

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
                            "Analizza le immagini come se fossi un ispettore del lavoro, secondo il D.Lgs. 81/2008. "
                            "Fornisci sempre il report in lingua italiana."
                        )
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Analizza questa immagine come esperto di sicurezza nei cantieri secondo il D.Lgs. 81/2008. "
                                    "Non devi in alcun modo identificare o valutare le persone, ma puoi e devi analizzare esclusivamente se indossano correttamente i dispositivi di protezione individuale (DPI), senza fare riferimento a tratti somatici, genere, età o altri aspetti personali. "
                                    "Verifica nel dettaglio se:\n"
                                    "- vengono indossati correttamente i DPI obbligatori (casco, guanti, imbracature, occhiali, scarpe antinfortunistiche)\n"
                                    "- i lavoratori operano in sicurezza in quota o in prossimità di carichi sospesi\n"
                                    "- i ponteggi o trabattelli rispettano i requisiti normativi\n"
                                    "- vi siano segnaletiche, recinzioni o delimitazioni di sicurezza adeguate\n"
                                    "- l’ambiente di lavoro presenta rischi elettrici, chimici, meccanici, da scivolamento o inciampo\n\n"
                                    "Fornisci un report tecnico completo con tutte le criticità osservabili nella foto e indica, ove possibile, anche i riferimenti normativi violati. "
                                    "L’analisi deve rimanere in lingua italiana ed essere strutturata come una nota."
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
                "L'app SicurANCE Piemonte e Valle d'Aosta è uno strumento di supporto all’analisi della sicurezza in cantiere. "
                "Non sostituisce la valutazione tecnica di figure abilitate (es. CSP, CSE, RSPP) e non esonera dagli obblighi di legge. "
                "Gli autori declinano ogni responsabilità per usi impropri o conseguenze derivanti da quanto riportato nei report generati."
            )


            # Mostra l'avvertenza legale anche nell'app, in fondo alla pagina
with st.expander("Avvertenza sull’utilizzo dell’app", expanded=True):
    st.markdown(
        """
        <div style='font-size: 14px; line-height: 1.5; color: gray;'>
        <strong>L'app SicurANCE Piemonte e Valle d'Aosta</strong> è uno strumento di supporto all’analisi della sicurezza in cantiere.<br>
        Non sostituisce la valutazione tecnica di figure abilitate (es. CSP, CSE, RSPP) e non esonera dagli obblighi di legge.<br>
        Gli autori declinano ogni responsabilità per usi impropri o conseguenze derivanti da quanto riportato nei report generati.
        </div>
        """,
        unsafe_allow_html=True
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
