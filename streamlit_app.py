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

def generate_pdf_report(report_texts):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Helvetica", size=12)

    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(200, 10, "Report Sicurezza Cantiere", ln=True, align='C')
    pdf.set_font("Helvetica", size=12)
    pdf.cell(200, 10, f"Data: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(10)

    for i, (image_bytes, label, report, criticita) in enumerate(report_texts):
        pdf.set_font("Helvetica", 'B', 14)

        emoji = semaforo_criticita(criticita)

        pdf.cell(200, 10, f"{label} - {criticita} criticità", ln=False) # ln=False per posizionare l'immagine sulla stessa linea

        if emoji == "🟢":
            try:
                pdf.image("green_light.png", x=pdf.get_x() + 5, y=pdf.get_y() - 8, w=8, h=8)
            except Exception as e:
                pdf.cell(10, 10, "[VERDE]", ln=True)
        elif emoji == "🟡":
            try:
                pdf.image("yellow_light.png", x=pdf.get_x() + 5, y=pdf.get_y() - 8, w=8, h=8)
            except Exception as e:
                pdf.cell(10, 10, "[GIALLO]", ln=True)
        else:
            try:
                pdf.image("red_light.png", x=pdf.get_x() + 5, y=pdf.get_y() - 8, w=8, h=8)
            except Exception as e:
                pdf.cell(10, 10, "[ROSSO]", ln=True)

        pdf.ln(10) # Sposta a una nuova linea dopo il titolo e l'immagine
        pdf.set_font("Helvetica", size=12)
        pdf.ln(5)

        temp_image_path = f"temp_image_{i}.jpg"
        with open(temp_image_path, "wb") as f:
            f.write(image_bytes)

        try:
            pdf.image(temp_image_path, x=10, w=100)
        except:
            pdf.set_text_color(255, 0, 0)
            pdf.cell(200, 10, "Immagine non disponibile", ln=True)
            pdf.set_text_color(0, 0, 0)

        os.remove(temp_image_path)

        clean_report = report.replace("🔴 ", ">> ")
        pdf.multi_cell(0, 10, sanitize_text(clean_report))
        pdf.ln(10)

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

# --- OPENAI CLIENT --- #
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- UI SETUP --- #
st.set_page_config(page_title="TESTING_WebApp_SicurANCE_Piemonte_ValleAosta", layout="centered")

col1, col2 = st.columns([1, 4])
with col1:
    st.image("logo_ance.jpg", width=220)
with col2:
    st.markdown("""
        <h1 style='font-size: 24px; margin-bottom: 5px;'> TESTING_WebApp_SicurANCE_Piemonte_ValleAosta</h1>
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
                            " Sei un esperto in sicurezza nei cantieri edili in Italia. Non devi identificare le persone, ma puoi valutarne l'equipaggiamento, l'uso appropriato dell'equipaggiamento e il comportamento. Rispondi sempre in lingua italiana, anche se il contenuto o l’immagine non fosse chiarissima. Non usare mai frasi introduttive in inglese. Analizza le immagini come se fossi un ispettore del lavoro, secondo il D.Lgs. 81/2008.")},

                        {"role": "user", "content": [
    {
        "type": "text",
        "text": (
            "Analizza questa immagine come esperto di sicurezza nei cantieri secondo il D.Lgs. 81/2008. "
            "Rispondi sempre in lingua italiana. "
            "Non devi identificare le persone, ma puoi valutarne l'equipaggiamento, l'uso appropriato dell'equipaggiamento e il comportamento.\n\n"
            "Verifica nel dettaglio se sono presenti e se vengono rispettate le normative relative a:\n"
            "- Dispositivi di protezione individuale (DPI): verifica se sono indossati correttamente (casco, guanti, imbracature, occhiali, scarpe antinfortunistiche, ecc.) e se sono appropriati per l'attività svolta.\n"
            "- Lavori in quota: analizza se le operazioni in quota vengono svolte in sicurezza, con l'utilizzo di imbracature, linee vita o altre misure di protezione adeguate.\n"
            "- Rischio di caduta di materiali o persone: verifica la presenza di protezioni contro la caduta di oggetti e se le aree di lavoro in elevato sono protette.\n"
            "- i lavoratori operano in sicurezza in quota o in prossimità di carichi sospesi\n"
            "- Ponteggi e trabattelli: valuta se sono montati correttamente, se presentano parapetti, tavole fermapiede e se l'accesso è sicuro.\n"
            "- Attrezzature meccaniche (gru, macchine movimento terra, escavatori, ecc.):\n"
            "    - Verifica se le attrezzature appaiono in buone condizioni di manutenzione e se sono presenti le marcature CE.\n"
            "    - Analizza se gli operatori sembrano qualificati e autorizzati all'uso delle specifiche attrezzature.\n"
            "    - Osserva se le operazioni di movimentazione vengono eseguite in sicurezza, rispettando le portate massime e le procedure operative.\n"
            "    - Valuta la presenza di segnalatori o assistenti di manovra, se necessari.\n"
            "    - Verifica la presenza di delimitazioni di sicurezza intorno alle aree operative delle macchine.\n"
            "- Movimentazione di carichi (in generale): osserva se le operazioni di sollevamento e movimentazione di carichi vengono eseguite in sicurezza, con attrezzature adeguate e personale formato.\n"
            "- Segnaletica di sicurezza: verifica la presenza e l'adeguatezza della segnaletica di sicurezza (divieti, obblighi, avvertimenti, emergenza).\n"
            "- Delimitazione e accesso alle aree di lavoro: analizza se le aree pericolose sono adeguatamente delimitate e se l'accesso è controllato.\n"
            "- Ordine e pulizia del cantiere: valuta se il cantiere è in ordine, pulito e privo di ostacoli che possano causare inciampi o cadute.\n"
            "- Rischi elettrici: verifica la presenza di cavi scoperti, quadri elettrici non protetti o altre situazioni di potenziale rischio elettrico.\n"
            "- Rischi da sostanze chimiche: osserva se sono presenti sostanze chimiche pericolose e se sono stoccate e utilizzate in modo sicuro, con la disponibilità di schede di sicurezza e DPI appropriati.\n"
            "- Rischi meccanici (in generale): analizza la sicurezza delle attrezzature e dei macchinari utilizzati nel cantiere.\n"
            "- Rischio di scivolamento o inciampo: verifica la presenza di pavimenti bagnati, detriti, o altri ostacoli che potrebbero causare scivolamenti o inciampi.\n"
            "- Illuminazione: valuta se l'illuminazione del cantiere è adeguata per svolgere le attività in sicurezza.\n"
            "- Viabilità interna del cantiere: osserva se la circolazione di persone e mezzi avviene in modo sicuro.\n"
            "- Presenza e corretto utilizzo di scale portatili: verifica se le scale portatili sono in buone condizioni e utilizzate correttamente.\n\n"
            "Fornisci una nota completa con tutte le criticità osservabili nella foto e indica, ove possibile, anche i riferimenti normativi violati.\n"
            "Se non sono visibili elementi specifici relativi a una delle categorie sopra elencate, indica che non sono osservabili nell'immagine."
        )
    },
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


# --- GENERAZIONE E SCARICAMENTO PDF --- #
if 'report_texts' in locals() and report_texts:
    pdf_buffer = generate_pdf_report(report_texts)
    st.markdown("### 📥 Scarica il report completo in PDF")
    st.download_button(
        label="📄 Scarica Report PDF",
        data=pdf_buffer,
        file_name=f"report_sicurezza_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        mime="application/pdf"
    )

# ————— AVVERTENZA ————— #
with st.expander("ℹ️ Avvertenza sull’utilizzo dell’app", expanded=True):
    st.markdown("""
        <div style='font-size: 14px; line-height: 1.5; color: gray;'>
        <strong>L'app SicurANCE Piemonte e Valle d'Aosta</strong> è uno strumento di supporto all’analisi della sicurezza in cantiere.
        Non sostituisce la valutazione tecnica di figure abilitate (es. CSP, CSE, RSPP) e non esonera dagli obblighi di legge.
        Gli autori declinano ogni responsabilità per usi impropri o conseguenze derivanti da quanto riportato nei report generati.
        </div>
    """, unsafe_allow_html=True)
