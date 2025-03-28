import streamlit as st
from openai import OpenAI
import base64
from fpdf import FPDF
from io import BytesIO
from PIL import Image

# Inizializza OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="SicurANCE Piemonte e Valle d'Aosta", layout="centered")

# Intestazione
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

# Upload e note
uploaded_file = st.file_uploader("Carica una foto che riprenda il cantiere nella sua interezza", type=["jpg", "jpeg", "png"])
note = st.text_area("Note aggiuntive (facoltative)")

if uploaded_file:
    st.image(uploaded_file, caption="Immagine caricata", use_container_width=True)

    with st.spinner("Analisi in corso..."):

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
                                    "Analizza questa immagine come esperto di sicurezza nei cantieri secondo il D.Lgs. 81/2008. "
                                    "Non devi identificare le persone, ma puoi valutarne l'equipaggiamento e il comportamento. "
                                    "Verifica nel dettaglio se:\n"
                                    "- vengono indossati correttamente i dispositivi di protezione individuale (casco, guanti, imbracature, occhiali, scarpe antinfortunistiche)\n"
                                    "- i lavoratori operano in sicurezza in quota o in prossimità di carichi sospesi\n"
                                    "- i ponteggi o trabattelli rispettano i requisiti normativi\n"
                                    "- vi siano segnaletiche, recinzioni o delimitazioni di sicurezza adeguate\n"
                                    "- l’ambiente di lavoro presenta rischi elettrici, chimici, meccanici, da scivolamento o inciampo\n\n"
                                    "Fornisci un report tecnico completo con tutte le criticità osservabili nella foto e indica, ove possibile, anche i riferimenti normativi violati."
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
            st.success("Analisi completata")
            st.markdown("### Report tecnico:")
            st.write(report)

            disclaimer = (
                "AVVERTENZA LEGALE\n\n"
                "L'applicazione SicurANCE Piemonte e Valle d'Aosta fornisce un supporto automatizzato all’analisi visiva dei cantieri edili, "
                "con l'obiettivo di promuovere comportamenti conformi al D.Lgs. 81/2008.\n\n"
                "Il contenuto generato non sostituisce le valutazioni tecniche di un Responsabile della Sicurezza o altre figure professionali qualificate.\n\n"
                "L’uso dell’app non esonera da obblighi normativi o responsabilità legali. Gli sviluppatori declinano ogni responsabilità per danni, incidenti o usi impropri dello strumento."
            )
            st.markdown(disclaimer)

            # Genera PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, "Report tecnico - SicurANCE Piemonte e Valle d'Aosta\n")
            pdf.multi_cell(0, 10, report)
            if note:
                pdf.multi_cell(0, 10, f"\nNote aggiuntive:\n{note}")
            pdf.multi_cell(0, 10, f"\n{disclaimer}")

            # Aggiungi immagine
            img = Image.open(BytesIO(image_bytes))
            img_path = "/tmp/temp_image.jpg"
            img.save(img_path)
            pdf.image(img_path, x=10, w=180)

            # Scaricamento
            pdf_output = BytesIO()
            pdf_bytes = pdf.output(dest='S').encode('latin-1', 'replace')
            pdf_output.write(pdf_bytes)
            pdf_output.seek(0)

            st.download_button(
                label="Scarica il report in PDF",
                data=pdf_output,
                file_name="report_sicurANCE.pdf",
                mime="application/pdf"
            )

        except Exception as e:
            st.error("Errore durante la generazione del report.")
            st.exception(e)
