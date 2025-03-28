import streamlit as st
import openai
import os
from PIL import Image
import base64

# Imposta la tua API Key in modo sicuro
openai.api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="SicurANCE", layout="centered")

st.title("**SicurANCE**")
st.subheader("L'Intelligenza Artificiale per la sicurezza nei cantieri")

uploaded_file = st.file_uploader("Carica una foto del cantiere", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Foto caricata", use_column_width=True)

    with st.spinner("Analisi in corso..."):

        # Converti l'immagine in base64 per l'input
        image_bytes = uploaded_file.getvalue()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        try:
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Sei un esperto di sicurezza nei cantieri. Analizza la seguente immagine e segnala le principali criticità legate alla sicurezza sul lavoro."},
                    {"role": "user", "content": [
                        {
                            "type": "text",
                            "text": "Analizza questa immagine del cantiere e individua i rischi per la sicurezza."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]}
                ],
                max_tokens=500
            )

            st.success("Analisi completata. Ecco il report di sicurezza:")
            st.markdown(response.choices[0].message.content)

        except Exception as e:
            st.error(f"Errore durante la generazione del report:\n\n{e}")
