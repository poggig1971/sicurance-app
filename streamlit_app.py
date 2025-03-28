import streamlit as st
from openai import OpenAI
import os
import base64

# Inizializza il client OpenAI con la tua API key
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="SicurANCE Piemonte e Valle d'Aosta", layout="centered")

st.title("🦺 SicurANCE Piemonte e Valle d'Aosta")
st.subheader("L'agente AI per la sicurezza nei cantieri")

uploaded_file = st.file_uploader("📷 Carica una foto del cantiere", type=["jpg", "jpeg", "png"])

if uploaded_file:
    st.image(uploaded_file, caption="📍 Immagine caricata", use_column_width=True)
    
    with st.spinner("🔍 Analisi dell'immagine in corso..."):

        # Converti l'immagine in base64
        image_bytes = uploaded_file.read()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        try:
            # Richiesta a GPT con input immagine
            response = client.chat.completions.create(
                model="gpt-4o",  # oppure "gpt-4-vision-preview" se disponibile
                messages=[
                    {
  "role": "user",
  "content": [
    { "type": "text", "text":
      "Analizza questa immagine come esperto di sicurezza nei cantieri secondo il D.Lgs. 81/2008. Non devi identificare le persone, ma puoi valutarne l'equipaggiamento e il comportamento. Verifica nel dettaglio se:
- vengono indossati correttamente i dispositivi di protezione individuale (casco, guanti, imbracature, occhiali, scarpe antinfortunistiche)
- i lavoratori operano in sicurezza in quota o in prossimità di carichi sospesi
- i ponteggi o trabattelli rispettano i requisiti normativi
- vi siano segnaletiche, recinzioni o delimitazioni di sicurezza adeguate
- l’ambiente di lavoro presenta rischi elettrici, chimici, meccanici, da scivolamento o inciampo

Fornisci un report tecnico completo con tutte le criticità osservabili nella foto e indica, ove possibile, anche i riferimenti normativi violati." },
    {
      "type": "image_url",
      "image_url": { "url": f"data:image/jpeg;base64,{base64_image}" }
    }
  ]
}
                ],
                max_tokens=800
            )

            report = response.choices[0].message.content
            st.success("✅ Analisi completata")
            st.markdown("### 📝 Report di Sicurezza:")
            st.write(report)

        except Exception as e:
            st.error("❌ Errore durante la generazione del report.")
            st.exception(e)
