"""
SicurANCE - Analisi AI della Sicurezza nei Cantieri
Applicazione web per l'analisi automatica della sicurezza nei cantieri edili tramite intelligenza artificiale.

Versione per Streamlit.io (file singolo)
"""

import streamlit as st
import logging
import time
import base64
from io import BytesIO
from PIL import Image, ImageOps, UnidentifiedImageError
import re
from datetime import datetime
from fpdf import FPDF
import os
import tempfile
from openai import OpenAI
from openai.types.error import APIError, RateLimitError, APIConnectionError, AuthenticationError

# ---- CONFIGURAZIONE ---- #

# Configurazione del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SicurANCE")

# Costanti dell'applicazione
APP_TITLE = "WebApp SicurANCE Piemonte e Valle d'Aosta"
APP_SUBTITLE = "Analisi AI della sicurezza nei cantieri"

# Configurazione per il caricamento delle immagini
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_IMAGES = 5
MAX_WIDTH = 1200
ALLOWED_EXTENSIONS = ["jpg", "jpeg", "png"]
IMAGE_QUALITY = 85

# Configurazione OpenAI
OPENAI_MODEL = "gpt-4o"
OPENAI_TEMPERATURE = 0.2
OPENAI_MAX_TOKENS = 1000

# Testo dell'avvertenza legale
DISCLAIMER_TEXT = """
<div style='font-size: 14px; line-height: 1.5; color: gray;'>
<strong>L'app SicurANCE Piemonte e Valle d'Aosta</strong> è uno strumento di supporto all'analisi della sicurezza in cantiere.
Non sostituisce la valutazione tecnica di figure abilitate (es. CSP, CSE, RSPP) e non esonera dagli obblighi di legge.
Gli autori declinano ogni responsabilità per usi impropri o conseguenze derivanti da quanto riportato nei report generati.
</div>
"""

# Prompt di sistema per OpenAI
SYSTEM_PROMPT = """
Sei un esperto in sicurezza nei cantieri edili in Italia. Non devi identificare le persone, ma puoi valutarne l'equipaggiamento, l'uso appropriato dell'equipaggiamento e il comportamento. Rispondi sempre in lingua italiana, anche se il contenuto o l'immagine non fosse chiarissima. Non usare mai frasi introduttive in inglese. Analizza le immagini come se fossi un ispettore del lavoro, secondo il D.Lgs. 81/2008.
"""

# Prompt utente per OpenAI
USER_PROMPT = """
Analizza questa immagine come esperto di sicurezza nei cantieri secondo il D.Lgs. 81/2008.
Rispondi sempre in lingua italiana.
Non devi identificare le persone, ma puoi valutarne l'equipaggiamento, l'uso appropriato dell'equipaggiamento e il comportamento.

Verifica nel dettaglio se sono presenti e se vengono rispettate le normative relative a:
- Dispositivi di protezione individuale (DPI): verifica se sono indossati correttamente (casco, guanti, imbracature, occhiali, scarpe antinfortunistiche, ecc.) e se sono appropriati per l'attività svolta.
- Lavori in quota: analizza se le operazioni in quota vengono svolte in sicurezza, con l'utilizzo di imbracature, linee vita o altre misure di protezione adeguate.
- Rischio di caduta di materiali o persone: verifica la presenza di protezioni contro la caduta di oggetti e se le aree di lavoro in elevato sono protette.
- i lavoratori operano in sicurezza in quota o in prossimità di carichi sospesi
- Ponteggi e trabattelli: valuta se sono montati correttamente, se presentano parapetti, tavole fermapiede e se l'accesso è sicuro.
- Attrezzature meccaniche (gru, macchine movimento terra, escavatori, ecc.):
    - Verifica se le attrezzature appaiono in buone condizioni di manutenzione e se sono presenti le marcature CE.
    - Analizza se gli operatori sembrano qualificati e autorizzati all'uso delle specifiche attrezzature.
    - Osserva se le operazioni di movimentazione vengono eseguite in sicurezza, rispettando le portate massime e le procedure operative.
    - Valuta la presenza di segnalatori o assistenti di manovra, se necessari.
    - Verifica la presenza di delimitazioni di sicurezza intorno alle aree operative delle macchine.
- Movimentazione di carichi (in generale): osserva se le operazioni di sollevamento e movimentazione di carichi vengono eseguite in sicurezza, con attrezzature adeguate e personale formato.
- Segnaletica di sicurezza: verifica la presenza e l'adeguatezza della segnaletica di sicurezza (divieti, obblighi, avvertimenti, emergenza).
- Delimitazione e accesso alle aree di lavoro: analizza se le aree pericolose sono adeguatamente delimitate e se l'accesso è controllato.
- Ordine e pulizia del cantiere: valuta se il cantiere è in ordine, pulito e privo di ostacoli che possano causare inciampi o cadute.
- Rischi elettrici: verifica la presenza di cavi scoperti, quadri elettrici non protetti o altre situazioni di potenziale rischio elettrico.
- Rischi da sostanze chimiche: osserva se sono presenti sostanze chimiche pericolose e se sono stoccate e utilizzate in modo sicuro, con la disponibilità di schede di sicurezza e DPI appropriati.
- Rischi meccanici (in generale): analizza la sicurezza delle attrezzature e dei macchinari utilizzati nel cantiere.
- Rischio di scivolamento o inciampo: verifica la presenza di pavimenti bagnati, detriti, o altri ostacoli che potrebbero causare scivolamenti o inciampi.
- Illuminazione: valuta se l'illuminazione del cantiere è adeguata per svolgere le attività in sicurezza.
- Viabilità interna del cantiere: osserva se la circolazione di persone e mezzi avviene in modo sicuro.
- Presenza e corretto utilizzo di scale portatili: verifica se le scale portatili sono in buone condizioni e utilizzate correttamente.

Fornisci una nota completa con tutte le criticità osservabili nella foto e indica, ove possibile, anche i riferimenti normativi violati.
Se non sono visibili elementi specifici relativi a una delle categorie sopra elencate, indica che non sono osservabili nell'immagine.
"""

# ---- FUNZIONI DI UTILITÀ ---- #

def init_session_state():
    """
    Inizializza lo stato della sessione Streamlit con valori predefiniti.
    """
    if "uploaded_images" not in st.session_state:
        st.session_state["uploaded_images"] = []
    
    if "image_ready" not in st.session_state:
        st.session_state["image_ready"] = False
    
    if "analyze" not in st.session_state:
        st.session_state["analyze"] = False
    
    if "report_texts" not in st.session_state:
        st.session_state["report_texts"] = []
    
    if "report_generated" not in st.session_state:
        st.session_state["report_generated"] = False
    
    if "processing_progress" not in st.session_state:
        st.session_state["processing_progress"] = 0
    
    if "current_image" not in st.session_state:
        st.session_state["current_image"] = ""

def check_api_key():
    """
    Verifica che la chiave API di OpenAI sia configurata.
    
    Returns:
        bool: True se la chiave API è configurata, False altrimenti
    """
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
        if not api_key:
            logger.error("Chiave API OpenAI non configurata")
            return False
        return True
    except Exception as e:
        logger.error(f"Errore nell'accesso alla chiave API OpenAI: {e}")
        return False

def sanitize_text(text):
    """
    Normalizza il testo sostituendo caratteri speciali e rimuovendo caratteri non supportati.
    
    Args:
        text (str): Testo da normalizzare
        
    Returns:
        str: Testo normalizzato
    """
    try:
        # Sostituisce caratteri speciali comuni
        text = text.replace("'", "'").replace("–", "-").replace(""", '"').replace(""", '"')
        
        # Rimuove altri caratteri Unicode potenzialmente problematici
        text = re.sub(r'[\u2018\u2019\u201C\u201D\u2013\u2014\u2026]', '', text)
        
        # Converte in latin-1 (ignorando caratteri non supportati) e poi di nuovo in unicode
        text = text.encode('latin-1', 'ignore').decode('latin-1')
        
        return text
    except Exception as e:
        logger.error(f"Errore durante la sanitizzazione del testo: {e}")
        # In caso di errore, ritorna il testo originale
        return text

def get_multicell_height(pdf, text, w):
    """
    Calcola l'altezza necessaria per un blocco di testo in un documento PDF.
    
    Args:
        pdf (FPDF): Oggetto FPDF
        text (str): Testo da misurare
        w (float): Larghezza della cella
        
    Returns:
        float: Altezza necessaria in mm
    """
    try:
        temp_pdf = FPDF()
        temp_pdf.add_page()
        temp_pdf.set_font(pdf.font_family, size=pdf.font_size_pt)
        start_y = temp_pdf.get_y()
        temp_pdf.multi_cell(w, 6, text)
        return temp_pdf.get_y() - start_y
    except Exception as e:
        logger.error(f"Errore nel calcolo dell'altezza del multicell: {e}")
        # In caso di errore, ritorna un valore predefinito
        return len(text.split('\n')) * 6  # Stima approssimativa

def evidenzia_criticita(report_text):
    """
    Aggiunge un indicatore rosso (🔴) davanti alle frasi che contengono parole chiave
    relative a criticità di sicurezza.
    
    Args:
        report_text (str): Testo del report
        
    Returns:
        str: Testo con criticità evidenziate
    """
    try:
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
            r"(Violazione .*)",
            r"(Non rispetta .*)",
            r"(Carenza di .*)",
        ]
        
        for pattern in patterns:
            report_text = re.sub(pattern, r"🔴 \1", report_text, flags=re.IGNORECASE)
        
        return report_text
    except Exception as e:
        logger.error(f"Errore durante l'evidenziazione delle criticità: {e}")
        # In caso di errore, ritorna il testo originale
        return report_text

def conta_criticita(report_text):
    """
    Conta il numero di criticità presenti nel testo del report.
    
    Args:
        report_text (str): Testo del report
        
    Returns:
        int: Numero di criticità rilevate
    """
    try:
        pattern = r"(?i)(Criticità:|Rischio di|Non è presente|Assenza di|Mancanza di|" \
                 r"Utilizzo non corretto di|DPI.*non.*indossato|Non conforme|" \
                 r"Inadempienza|Pericolo di|Violazione|Non rispetta|Carenza di)"
        
        return len(re.findall(pattern, report_text))
    except Exception as e:
        logger.error(f"Errore durante il conteggio delle criticità: {e}")
        # In caso di errore, ritorna 0
        return 0

def semaforo_criticita(n):
    """
    Restituisce un'icona a semaforo in base al numero di criticità rilevate.
    
    Args:
        n (int): Numero di criticità
        
    Returns:
        str: Emoji del semaforo (🟢, 🟡, 🔴)
    """
    if n == 0:
        return "🟢"
    elif n <= 2:
        return "🟡"
    else:
        return "🔴"

def generate_pdf_report(report_texts, include_images=True):
    """
    Genera un report PDF con tutte le analisi.
    
    Args:
        report_texts (list): Lista di tuple (image_bytes, label, report, criticita)
        include_images (bool): Se True, include le immagini nel PDF
        
    Returns:
        bytes: Contenuto del PDF generato
    """
    try:
        # Crea una directory temporanea
        with tempfile.TemporaryDirectory() as temp_dir:
            # Crea un nuovo PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # Imposta il font
            pdf.set_font("Arial", size=12)
            
            # Intestazione
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, "Report Sicurezza Cantiere", ln=True, align='C')
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, f"Data: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
            pdf.ln(10)
            
            # Contenuto
            for i, (image_bytes, label, report, criticita) in enumerate(report_texts):
                # Titolo della sezione
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(200, 10, f"{label} - {criticita} criticità - {semaforo_criticita(criticita)}", ln=True)
                pdf.set_font("Arial", size=12)
                
                # Aggiungi immagine se richiesto
                if include_images and image_bytes:
                    try:
                        # Salva temporaneamente l'immagine
                        img_path = os.path.join(temp_dir, f"temp_img_{i}.jpg")
                        with open(img_path, 'wb') as f:
                            f.write(image_bytes)
                        
                        # Aggiungi l'immagine al PDF
                        pdf.image(img_path, x=10, y=pdf.get_y(), w=100)
                        pdf.ln(70)  # Spazio per l'immagine
                    except Exception as e:
                        logger.error(f"Errore nell'aggiunta dell'immagine al PDF: {e}")
                        pdf.cell(200, 10, "Impossibile includere l'immagine", ln=True)
                        pdf.ln(5)
                
                # Aggiungi testo del report (senza emoji)
                clean_report = re.sub(r'🔴 ', '', report)
                pdf.multi_cell(0, 10, clean_report)
                pdf.ln(10)
            
            # Salva il PDF in un file temporaneo
            pdf_path = os.path.join(temp_dir, f"report_sicurezza.pdf")
            pdf.output(pdf_path)
            
            # Leggi il file PDF come bytes
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
            logger.info("Report PDF generato con successo")
            return pdf_bytes
    
    except Exception as e:
        logger.error(f"Errore nella generazione del report PDF: {e}")
        return None

# ---- FUNZIONI DI ELABORAZIONE IMMAGINI ---- #

@st.cache_data
def process_image(image_file, max_width=MAX_WIDTH, quality=IMAGE_QUALITY):
    """
    Processa un'immagine caricata: ridimensiona, normalizza l'orientamento e comprime.
    Utilizza il caching di Streamlit per migliorare le prestazioni.
    
    Args:
        image_file: File immagine caricato
        max_width (int): Larghezza massima dell'immagine
        quality (int): Qualità della compressione JPEG (0-100)
        
    Returns:
        bytes: Immagine processata in formato bytes
        str: Messaggio informativo o None
    """
    try:
        # Apri l'immagine
        image = Image.open(image_file)
        message = None
        
        # Ridimensiona se necessario
        if image.width > max_width:
            ratio = max_width / image.width
            new_size = (max_width, int(image.height * ratio))
            image = image.resize(new_size, Image.LANCZOS)
            message = f"L'immagine '{image_file.name}' è stata ridimensionata."
        
        # Normalizza l'orientamento EXIF
        image = ImageOps.exif_transpose(image)
        
        # Ottimizza la qualità in base alle dimensioni
        adaptive_quality = quality
        if image.width * image.height > 2000000:  # Immagini molto grandi
            adaptive_quality = max(65, quality - 20)
        elif image.width * image.height > 1000000:  # Immagini grandi
            adaptive_quality = max(75, quality - 10)
        
        # Salva l'immagine in un buffer
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=adaptive_quality, optimize=True)
        
        logger.info(f"Immagine '{image_file.name}' elaborata con successo")
        return buffered.getvalue(), message
    
    except UnidentifiedImageError:
        logger.error(f"File '{image_file.name}' non è un'immagine valida")
        raise ValueError(f"Il file '{image_file.name}' non è un'immagine valida")
    
    except Exception as e:
        logger.error(f"Errore nell'elaborazione dell'immagine '{image_file.name}': {e}")
        raise

def validate_image(image_file, max_size_bytes, allowed_extensions):
    """
    Valida un file immagine verificando dimensione e formato.
    
    Args:
        image_file: File immagine caricato
        max_size_bytes (int): Dimensione massima in bytes
        allowed_extensions (list): Lista di estensioni consentite
        
    Returns:
        bool: True se l'immagine è valida, False altrimenti
        str: Messaggio di errore o None
    """
    try:
        # Controlla la dimensione
        if image_file.size > max_size_bytes:
            return False, f"Il file '{image_file.name}' supera il limite di dimensione consentito"
        
        # Controlla l'estensione
        extension = image_file.name.split('.')[-1].lower()
        if extension not in allowed_extensions:
            return False, f"Il formato '{extension}' non è supportato. Formati consentiti: {', '.join(allowed_extensions)}"
        
        # Verifica che sia un'immagine valida
        try:
            Image.open(image_file).verify()
            image_file.seek(0)  # Reimposta la posizione del file dopo la verifica
        except Exception:
            return False, f"Il file '{image_file.name}' non è un'immagine valida o è corrotto"
        
        return True, None
    
    except Exception as e:
        logger.error(f"Errore nella validazione dell'immagine '{image_file.name}': {e}")
        return False, f"Errore nella validazione dell'immagine: {e}"

def process_images_batch(uploaded_files, max_width, max_size_bytes, allowed_extensions, max_images):
    """
    Processa un batch di immagini caricate, validando e processando ciascuna.
    
    Args:
        uploaded_files (list): Lista di file caricati
        max_width (int): Larghezza massima dell'immagine
        max_size_bytes (int): Dimensione massima in bytes
        allowed_extensions (list): Lista di estensioni consentite
        max_images (int): Numero massimo di immagini
        
    Returns:
        list: Lista di immagini processate (bytes)
        list: Lista di messaggi informativi
    """
    valid_images = []
    messages = []
    
    # Limita il numero di immagini
    if len(uploaded_files) > max_images:
        messages.append(f"⚠️ Hai caricato più di {max_images} immagini. Solo le prime {max_images} verranno analizzate.")
        uploaded_files = uploaded_files[:max_images]
    
    # Processa ogni immagine
    for file in uploaded_files:
        # Aggiorna lo stato di avanzamento
        if "processing_progress" in st.session_state:
            st.session_state["current_image"] = file.name
        
        # Valida l'immagine
        is_valid, error_message = validate_image(file, max_size_bytes, allowed_extensions)
        if not is_valid:
            messages.append(f"⚠️ {error_message}")
            continue
        
        try:
            # Processa l'immagine
            img_bytes, info_message = process_image(file, max_width)
            valid_images.append((img_bytes, file.name))
            
            if info_message:
                messages.append(f"ℹ️ {info_message}")
                
        except Exception as e:
            messages.append(f"❌ Errore con il file '{file.name}': {e}")
    
    return valid_images, messages

# ---- FUNZIONI API ---- #

@st.cache_resource
def get_openai_client():
    """
    Crea e restituisce un client OpenAI.
    Utilizza il caching di Streamlit per riutilizzare il client.
    
    Returns:
        OpenAI: Client OpenAI o None in caso di errore
    """
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
        if not api_key:
            logger.error("Chiave API OpenAI non configurata")
            return None
        
        client = OpenAI(api_key=api_key)
        logger.info("Client OpenAI inizializzato con successo")
        return client
    
    except Exception as e:
        logger.error(f"Errore nella creazione del client OpenAI: {e}")
        return None

def analyze_image_with_retry(image_bytes, max_retries=3, retry_delay=2):
    """
    Analizza un'immagine utilizzando l'API OpenAI con gestione degli errori e tentativi di ripetizione.
    
    Args:
        image_bytes (bytes): Immagine in formato bytes
        max_retries (int): Numero massimo di tentativi in caso di errore
        retry_delay (int): Ritardo iniziale tra i tentativi (in secondi)
        
    Returns:
        str: Testo del report generato o None in caso di errore
        str: Messaggio di errore o None in caso di successo
    """
    client = get_openai_client()
    if not client:
        return None, "Impossibile inizializzare il client OpenAI. Verifica la configurazione della chiave API."
    
    # Codifica l'immagine in base64
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    
    # Prepara i messaggi per l'API
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": [
            {"type": "text", "text": USER_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]}
    ]
    
    # Tentativi di chiamata API con backoff esponenziale
    retry_count = 0
    while retry_count <= max_retries:
        try:
            logger.info(f"Tentativo {retry_count + 1}/{max_retries + 1} di analisi dell'immagine")
            
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                max_tokens=OPENAI_MAX_TOKENS,
                temperature=OPENAI_TEMPERATURE
            )
            
            report = response.choices[0].message.content
            logger.info("Analisi dell'immagine completata con successo")
            return report, None
        
        except RateLimitError as e:
            retry_count += 1
            if retry_count <= max_retries:
                wait_time = retry_delay * (2 ** (retry_count - 1))  # Backoff esponenziale
                logger.warning(f"Limite di frequenza API superato. Attesa di {wait_time} secondi prima del nuovo tentativo.")
                time.sleep(wait_time)
            else:
                logger.error(f"Limite di frequenza API superato dopo {max_retries} tentativi: {e}")
                return None, f"Limite di frequenza API superato. Riprova più tardi."
        
        except AuthenticationError as e:
            logger.error(f"Errore di autenticazione OpenAI: {e}")
            return None, "Errore di autenticazione con OpenAI. Verifica la chiave API."
        
        except APIConnectionError as e:
            retry_count += 1
            if retry_count <= max_retries:
                wait_time = retry_delay * (2 ** (retry_count - 1))
                logger.warning(f"Errore di connessione API. Attesa di {wait_time} secondi prima del nuovo tentativo.")
                time.sleep(wait_time)
            else:
                logger.error(f"Errore di connessione API dopo {max_retries} tentativi: {e}")
                return None, f"Impossibile connettersi all'API OpenAI. Verifica la connessione internet."
        
        except APIError as e:
            retry_count += 1
            if retry_count <= max_retries and (e.status_code >= 500 or e.status_code == 429):
                wait_time = retry_delay * (2 ** (retry_count - 1))
                logger.warning(f"Errore API (codice {e.status_code}). Attesa di {wait_time} secondi prima del nuovo tentativo.")
                time.sleep(wait_time)
            else:
                logger.error(f"Errore API OpenAI: {e}")
                return None, f"Errore API OpenAI: {e}"
        
        except Exception as e:
            logger.error(f"Errore imprevisto durante l'analisi dell'immagine: {e}")
            return None, f"Errore imprevisto durante l'analisi: {e}"
    
    return None, "Impossibile completare l'analisi dopo diversi tentativi."

def analyze_images_batch(images, progress_callback=None):
    """
    Analizza un batch di immagini, con aggiornamento del progresso.
    
    Args:
        images (list): Lista di tuple (image_bytes, image_name)
        progress_callback (function): Funzione di callback per aggiornare il progresso
        
    Returns:
        list: Lista di tuple (image_bytes, label, report, criticita_count)
        list: Lista di messaggi di errore
    """
    results = []
    errors = []
    
    total_images = len(images)
    for i, (image_bytes, image_name) in enumerate(images):
        # Aggiorna il progresso
        if progress_callback:
            progress_callback(i, total_images, image_name)
        
        # Analizza l'immagine
        report, error = analyze_image_with_retry(image_bytes)
        
        if error:
            errors.append(f"❌ Errore nell'analisi dell'immagine '{image_name}': {error}")
            continue
        
        # Elabora il report
        report = evidenzia_criticita(report)
        criticita_count = conta_criticita(report)
        
        # Aggiungi ai risultati
        results.append((image_bytes, f"Immagine {i+1} ({image_name})", report, criticita_count))
    
    return results, errors

# ---- FUNZIONI UI ---- #

def setup_page():
    """
    Configura la pagina Streamlit con titolo e layout.
    """
    st.set_page_config(
        page_title=APP_TITLE,
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    # Rimuove il menu hamburger e il footer
    hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
    """
    st.markdown(hide_menu_style, unsafe_allow_html=True)

def show_header():
    """
    Mostra l'intestazione dell'applicazione con logo e titolo.
    """
    col1, col2 = st.columns([1, 4])
    
    with col1:
        # Logo placeholder
        st.markdown("🏗️")
    
    with col2:
        st.markdown(f"""
            <h1 style='font-size: 24px; margin-bottom: 5px;'>{APP_TITLE}</h1>
            <h4 style='margin-top: 0;'>{APP_SUBTITLE}</h4>
        """, unsafe_allow_html=True)

def show_disclaimer(expanded=True):
    """
    Mostra l'avvertenza legale in un expander.
    
    Args:
        expanded (bool): Se True, l'expander è aperto di default
    """
    with st.expander("ℹ️ Avvertenza sull'utilizzo dell'app", expanded=expanded):
        st.markdown(DISCLAIMER_TEXT, unsafe_allow_html=True)

def show_file_uploader():
    """
    Mostra l'uploader di file con informazioni sui limiti.
    
    Returns:
        list: Lista di file caricati
    """
    uploaded_files = st.file_uploader(
        f"Carica fino a {MAX_IMAGES} foto del cantiere (max {MAX_FILE_SIZE_MB} MB per immagine)",
        type=ALLOWED_EXTENSIONS,
        accept_multiple_files=True,
        help=f"Formati supportati: {', '.join(ALLOWED_EXTENSIONS)}. Le immagini verranno ridimensionate se necessario."
    )
    
    return uploaded_files

def show_image_preview(img_bytes, caption):
    """
    Mostra l'anteprima di un'immagine.
    
    Args:
        img_bytes (bytes): Immagine in formato bytes
        caption (str): Didascalia dell'immagine
    """
    st.image(BytesIO(img_bytes), caption=caption, use_container_width=True)

def show_analyze_button():
    """
    Mostra il pulsante per avviare l'analisi.
    
    Returns:
        bool: True se il pulsante è stato premuto
    """
    return st.button("✅ Avvia l'analisi delle foto", use_container_width=True)

def show_progress(current, total, current_item=""):
    """
    Mostra una barra di progresso.
    
    Args:
        current (int): Valore corrente
        total (int): Valore totale
        current_item (str): Nome dell'elemento corrente
    """
    if total > 0:
        progress_text = f"Analisi in corso... {current+1}/{total}"
        if current_item:
            progress_text += f" ({current_item})"
        
        progress_bar = st.progress(0)
        progress_value = float(current) / float(total)
        progress_bar.progress(progress_value, text=progress_text)
        
        # Aggiorna lo stato di avanzamento nella sessione
        st.session_state["processing_progress"] = progress_value
        st.session_state["current_image"] = current_item

def show_report(image_bytes, label, report, criticita_count):
    """
    Mostra un report di analisi.
    
    Args:
        image_bytes (bytes): Immagine in formato bytes
        label (str): Etichetta del report
        report (str): Testo del report
        criticita_count (int): Numero di criticità rilevate
    """
    # Crea un expander per ogni report
    with st.expander(f"{label} – {semaforo_criticita(criticita_count)} {criticita_count} criticità", expanded=True):
        # Mostra l'immagine e il report in colonne affiancate
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.image(BytesIO(image_bytes), use_container_width=True)
        
        with col2:
            st.markdown(report)

def show_reports(report_texts):
    """
    Mostra tutti i report di analisi.
    
    Args:
        report_texts (list): Lista di tuple (image_bytes, label, report, criticita_count)
    """
    st.success("✅ Analisi completata")
    
    # Mostra un riepilogo delle criticità
    total_criticita = sum(criticita for _, _, _, criticita in report_texts)
    st.markdown(f"### Riepilogo: {total_criticita} criticità totali in {len(report_texts)} immagini")
    
    # Mostra i singoli report
    for image_bytes, label, report, criticita in report_texts:
        show_report(image_bytes, label, report, criticita)

def show_download_button(report_texts):
    """
    Mostra un pulsante per scaricare il report in formato PDF.
    
    Args:
        report_texts (list): Lista di tuple (image_bytes, label, report, criticita_count)
    """
    if report_texts:
        try:
            # Genera il PDF
            pdf_bytes = generate_pdf_report(report_texts)
            
            if pdf_bytes:
                # Mostra il pulsante di download con stile più evidente
                st.markdown("### 📥 Scarica il report completo")
                st.download_button(
                    label="📥 Scarica Report PDF",
                    data=pdf_bytes,
                    file_name=f"report_sicurezza_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    help="Scarica un report PDF con tutte le analisi",
                    use_container_width=True
                )
            else:
                st.error("❌ Impossibile generare il PDF")
        except Exception as e:
            st.error(f"❌ Errore nella generazione del PDF: {e}")
            logger.error(f"Errore nella generazione del PDF: {e}")

def show_error_messages(messages):
    """
    Mostra messaggi di errore.
    
    Args:
        messages (list): Lista di messaggi di errore
    """
    for message in messages:
        if "⚠️" in message:
            st.warning(message)
        elif "❌" in message:
            st.error(message)
        elif "ℹ️" in message:
            st.info(message)
        else:
            st.info(message)

def show_settings():
    """
    Mostra un pannello di impostazioni nella sidebar.
    """
    with st.sidebar:
        st.title("Impostazioni")
        
        # Impostazioni per l'analisi delle immagini
        st.subheader("Analisi immagini")
        
        # Qualità della compressione
        quality = st.slider(
            "Qualità immagini (%)",
            min_value=50,
            max_value=100,
            value=85,
            step=5,
            help="Qualità della compressione JPEG. Valori più bassi riducono la dimensione del file ma possono peggiorare la qualità."
        )
        
        # Opzioni per il report
        st.subheader("Report")
        
        # Inclusione delle immagini nel PDF
        include_images = st.checkbox(
            "Includi immagini nel PDF",
            value=True,
            help="Se selezionato, le immagini verranno incluse nel report PDF."
        )
        
        # Restituisci le impostazioni
        return {
            "quality": quality,
            "include_images": include_images
        }

# ---- APPLICAZIONE PRINCIPALE ---- #

def update_progress_callback(current, total, current_item):
    """
    Callback per aggiornare il progresso dell'analisi.
    
    Args:
        current (int): Indice corrente
        total (int): Totale elementi
        current_item (str): Nome dell'elemento corrente
    """
    show_progress(current, total, current_item)

def main():
    """
    Funzione principale dell'applicazione.
    """
    # Configura la pagina
    setup_page()
    
    # Inizializza lo stato della sessione
    init_session_state()
    
    # Mostra l'intestazione
    show_header()
    
    # Verifica la chiave API
    if not check_api_key():
        st.error("❌ Chiave API OpenAI non configurata. Configura la chiave API nelle impostazioni di Streamlit.")
        show_disclaimer()
        return
    
    # Mostra il pannello delle impostazioni nella sidebar
    settings = show_settings()
    
    # Mostra l'uploader di file
    uploaded_files = show_file_uploader()
    
    # Gestione del caricamento delle immagini
    if uploaded_files:
        # Processa le immagini caricate
        valid_images, messages = process_images_batch(
            uploaded_files, 
            MAX_WIDTH, 
            MAX_FILE_SIZE, 
            ALLOWED_EXTENSIONS, 
            MAX_IMAGES
        )
        
        # Mostra eventuali messaggi di errore o avviso
        show_error_messages(messages)
        
        # Mostra le anteprime delle immagini valide
        for img_bytes, img_name in valid_images:
            show_image_preview(img_bytes, img_name)
        
        # Aggiorna lo stato della sessione
        if valid_images:
            st.session_state["uploaded_images"] = valid_images
            st.session_state["image_ready"] = True
        else:
            st.session_state["image_ready"] = False
            st.error("❌ Nessuna immagine valida caricata.")
    
    # Pulsante per avviare l'analisi
    if show_analyze_button() and st.session_state.get("image_ready"):
        st.session_state["analyze"] = True
    
    # Esecuzione dell'analisi
    if st.session_state.get("analyze") and st.session_state.get("image_ready"):
        with st.spinner("Analisi in corso..."):
            try:
                # Analizza le immagini
                report_texts, errors = analyze_images_batch(
                    st.session_state["uploaded_images"],
                    update_progress_callback
                )
                
                # Mostra eventuali errori
                show_error_messages(errors)
                
                # Mostra i report
                if report_texts:
                    # Salva i report nella sessione
                    st.session_state["report_texts"] = report_texts
                    st.session_state["report_generated"] = True
                    
                    # Mostra i report
                    show_reports(report_texts)
                    
                    # Mostra il pulsante di download
                    show_download_button(report_texts)
                else:
                    st.error("❌ Nessun report generato. Riprova.")
            
            except Exception as e:
                logger.error(f"Errore durante l'analisi: {e}")
                st.error(f"❌ Errore durante l'analisi: {e}")
            
            finally:
                # Reimposta lo stato di analisi
                st.session_state["analyze"] = False
    
    # Mostra il pulsante di download anche dopo il ricaricamento della pagina se ci sono report
    if st.session_state.get("report_generated") and st.session_state.get("report_texts"):
        # Aggiungi una separazione visiva
        st.markdown("---")
        # Mostra il pulsante di download
        show_download_button(st.session_state["report_texts"])
    
    # Mostra l'avvertenza legale
    show_disclaimer(expanded=False)

if __name__ == "__main__":
    main()
