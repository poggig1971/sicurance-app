import streamlit as st
import requests
import base64
import openai
import os

st.set_page_config(page_title="SicurANCE", layout="centered")

st.title("SicurANCE")
st.subheader("L'Intelligenza Artificiale per la sicurezza nei cantieri – versione gratuita")

uploaded_file = st.file_uploader("Carica una foto del cantiere", type=["jpg", "jpeg", "png"])

if uploaded_file:
    st.image(uploaded_file, caption="Foto caricata", use_column_width=True)

    with st.spinner("Analisi dell'immagine in corso..."):

        image_bytes = uploaded_file.read()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        # Simulazione chiamata a modello YOLOv8 hosted su Roboflow o Hugging Face
        fake_detected_elements = [
            "operaio senza casco",
            "ponteggio senza parapetto",
            "attrezzatura a terra non segnalata"
        ]

        descrizione = (
            "Nell'immagine sono stati rilevati i seguenti elementi potenzialmente critici: "
            + ", ".join(fake_detected_elements) + "."
        )

        st.markdown("### Descrizione automatica:")
        st.write(descrizione)

        # Usa GPT-3.5 per generare report testuale
        openai.api_key = os.getenv("OPENAI_API_KEY")

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Sei un esperto di sicurezza nei cantieri edili, rispondi come tecnico."},
                    {"role": "user", "content": f"Genera un report di sicurezza a partire da questa descrizione: {descrizione}"}
                ],
                temperature=0.4,
                max_tokens=600
            )

            report = response["choices"][0]["message"]["content"]
            st.markdown("### Report di Sicurezza:")
            st.write(report)

        except Exception as e:
            st.error("Errore durante la generazione del report.")
            st.exception(e)
