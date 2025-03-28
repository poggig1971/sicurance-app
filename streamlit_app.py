import streamlit as st
from openai import OpenAI
import base64
from fpdf import FPDF
import datetime

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
        <h1 style='font-size: 24px; margin-bottom: 5px;'>🦺 SicurANCE Piemonte e Valle d'Aosta</h1>
        <h4 style='margin-top: 0;'>Analisi automatica della sicurezza nei cantieri</h4>
        """,
        unsafe_allow_html=True
    )

uploaded_file = st.file_uploader("📷 Carica una foto che riprenda il cantiere nella sua interezza", type=["jpg", "jpeg", "png"])

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
                                    "- l'ambiente di lavoro presenta rischi elettrici, chimici, meccanici, da scivolamento o inciampo\n\n"
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
            st.success("✅ Analisi completata")
            st.markdown("### 📄 Report tecnico:")
            st.write(report)

            # ✅ Generazione PDF con checklist
            class PDFReport(FPDF):
                def header(self):
                    self.set_font("Arial", "B", 12)
                    self.cell(0, 10, "Report SicurANCE Piemonte Valle d'Aosta", ln=True, align="C")
                    self.ln(5)

                def footer(self):
                    self.set_y(-15)
                    self.set_font("Arial", "I", 8)
                    self.cell(0, 10, f"Pagina {self.page_no()}", align="C")

                def chapter_title(self, title):
                    self.set_font("Arial", "B", 12)
                    self.cell(0, 10, title, ln=True)
                    self.ln(5)

                def chapter_body(self, body):
                    self.set_font("Arial", "", 11)
                    self.multi_cell(0, 10, body)
                    self.ln()

            checklist = """
Checklist di verifica (da completare):

[ ] Tutti i lavoratori indossano il casco protettivo
[ ] Presenza di segnaletica di sicurezza nelle aree operative
[ ] Verifica dell'ancoraggio di ponteggi e trabattelli
[ ] Utilizzo corretto dei DPI (guanti, occhiali, scarpe)
[ ] Delimitazioni visibili delle aree a rischio
[ ] Assenza di ostacoli o rischi da scivolamento/inciampo
"""

            pdf = PDFReport()
            pdf.add_page()
            pdf.chapter_title(f"Data: {datetime.date.today().strftime('%d/%m/%Y')}")
            pdf.chapter_body(report.replace("’", "'"))
            pdf.chapter_title("Checklist di verifica")
            pdf.chapter_body(checklist)

            pdf_path = "/mnt/data/report_sicurANCE_Piemonte_Valle_d_Aostacompleto.pdf"
            pdf.output(pdf_path)

            st.download_button(
                label="📥 Scarica il report completo in PDF",
                data=open(pdf_path, "rb").read(),
                file_name="report_sicurANCE.pdf",
                mime="application/pdf"
            )

        except Exception as e:
            st.error("❌ Errore durante la generazione del report.")
            st.exception(e)
