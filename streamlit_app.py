from fpdf import FPDF
import streamlit as st
from openai import OpenAI
import base64
from io import BytesIO
import tempfile
import os

# Inizializza client OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="SicurANCE Piemonte e Valle d'Aosta", layout="centered")

# Intestazione con logo e titolo
col1, col2 = st.columns([1, 4])
with col1:
    st.image("logo_ance.jpg", width=220)
with col2:
    st.markdown(
        """
        <h1 style='font-size: 24px; margin-bottom: 5px;'>🦺 SicurANCE Piemonte e Valle d'Aosta</h1>
        <h4 style='margin-top: 0;'>Analisi automatica della sicurezza nei cantieri</h4>
        """,
        unsafe_allow_html=True
    )

uploaded_file = st.file_uploader("📷 Carica una foto che riprenda il cantiere nella sua interezza", type=["jpg", "jpeg", "png"])
note = st.text_area("📝 Note personali (facoltative)", placeholder="Scrivi eventuali osservazioni o note personali...")

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
                                    "Analizza questa immagine come esperto di sicurezza nei cantieri secondo il D.Lgs. 81/2008. "
                                    "Non devi identificare le persone, ma puoi valutarne l'equipaggiamento e il comportamento. "
                                    "Verifica nel dettaglio se:\n"
                                    "- vengono indossati correttamente i dispositivi di protezione individuale (casco, guanti, imbracature, occhiali, scarpe antinfortunistiche)\n"
                                    "- i lavoratori operano in sicurezza in quota o in prossimità di carichi sospesi\n"
                                    "- i ponteggi o trabattelli rispettano i requisiti normativi\n"
                                    "- vi siano segnaletiche, recinzioni o delimitazioni di sicurezza adeguate\n"
                                    "- l’ambiente di lavoro presenta rischi elettrici, chimici, meccanici, da scivolamento o inciampo\n\n"
                                    "Fornisci un report tecnico completo con tutte le criticità osservabili nella foto e indica, ove possibile, anche i riferimenti normativi violati. "
                                    "Rispondi in lingua italiana, in modo tecnico e ordinato."
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
                max_tokens=1500,
                temperature=0.2
            )

            report = response.choices[0].message.content
            st.success("✅ Analisi completata")
            st.markdown("### 📄 Report tecnico:")
            st.write(report)

            # Crea PDF
            pdf = FPDF()
            pdf.add_page()

            # Carica font Unicode compatibile
            font_path = "DejaVuSans.ttf"  # Assicurati che il font sia presente nella cartella
            pdf.add_font("DejaVu", "", font_path, uni=True)
            pdf.set_font("DejaVu", size=12)

            pdf.cell(0, 10, "Report tecnico SicurANCE", ln=True)

            # Salva immagine temporanea
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                tmp_file.write(image_bytes)
                image_path = tmp_file.name

            try:
                pdf.image(image_path, x=10, y=25, w=180)
                pdf.ln(100)
            except Exception as e:
                st.warning("⚠️ Impossibile inserire immagine nel PDF.")
                st.exception(e)

            pdf.multi_cell(0, 10, report)

            if note:
                pdf.ln(5)
                pdf.set_font("DejaVu", style="B", size=12)
                pdf.cell(0, 10, "Note dell’utente:", ln=True)
                pdf.set_font("DejaVu", size=12)
                pdf.multi_cell(0, 10, note)

            # Esporta come BytesIO (non salva su disco)
            pdf_output = BytesIO()
            pdf_bytes = pdf.output(dest="S").encode("utf-8")
            pdf_output.write(pdf_bytes)
            pdf_output.seek(0)

            st.download_button(
                label="📥 Scarica il report in PDF",
                data=pdf_output,
                file_name="report_sicurANCE.pdf",
                mime="application/pdf"
            )

            os.remove(image_path)

        except Exception as e:
            st.error("❌ Errore durante la generazione del report.")
            st.exception(e)

