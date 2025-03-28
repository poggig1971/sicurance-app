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
                        "role": "system",
                        "content": "Tu sei un esperto di sicurezza nei cantieri edili, con particolare attenzione alle normative vigenti nelle regioni Piemonte e Valle d'Aosta. Quando ricevi una foto, la analizzi per individuare qualsiasi violazione del D.Lgs. 81/2008 e di eventuali normative regionali applicabili in Piemonte e Valle d'Aosta. Per ogni rischio che identifichi, spiega chiaramente il problema, cita l’articolo della norma violata (sia nazionale che regionale, se presente), e suggerisci una misura correttiva."
                    },
                    {
                        "role": "user",
                        "content": [
                            { "type": "text", "text": "Analizza questa immagine e individua tutti i rischi per la sicurezza presenti nel cantiere." },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
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
