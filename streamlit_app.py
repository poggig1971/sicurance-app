
import streamlit as st
from openai import OpenAI
from PIL import Image
import base64
import os

# Inizializza il client OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Titolo
st.title("SicurANCE")
st.subheader("L'Intelligenza Artificiale per la sicurezza nei cantieri")

# Caricamento immagine
uploaded_file = st.file_uploader("Carica una foto del cantiere", type=["jpg", "jpeg", "png"])
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Foto caricata", use_container_width=True)

    # Converti immagine in base64
    image_bytes = uploaded_file.read()
    image_base64 = base64.b64encode(image_bytes).decode()

    with st.spinner("Analisi in corso con SicurANCE..."):
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "system",
                    "content": "Sei un tecnico della sicurezza sul lavoro esperto in D.Lgs. 81/2008. Analizza la foto di un cantiere e restituisci un report tecnico dettagliato dei rischi individuabili, con riferimenti normativi e azioni correttive."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analizza la seguente immagine di cantiere e genera un report sicurezza completo."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]
                }
            ],
            max_tokens=1200
        )

        report = response.choices[0].message.content

        st.markdown("## Report SicurANCE â Analisi AI personalizzata")
        st.markdown(report)
