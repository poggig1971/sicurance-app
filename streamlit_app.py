import streamlit as st
from PIL import Image

st.set_page_config(page_title="SicurANCE", layout="centered")

st.title("SicurANCE")
st.subheader("L'Intelligenza Artificiale per la sicurezza nei cantieri")

uploaded_file = st.file_uploader("Carica una foto del cantiere", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Foto caricata", use_column_width=True)

    st.markdown("**Analisi automatica in corso...**")
    
    # Placeholder per il report generato
    st.markdown("""
    ### Report SicurANCE
    - **Rischio**: Operai senza dispositivi di protezione individuale (DPI)
    - **Articolo violato**: Art. 115 D.Lgs. 81/2008
    - **Correzione consigliata**: Fornire e far indossare i DPI (imbracature, caschi, linea vita)

    - **Rischio**: Carico sospeso sopra gli operatori
    - **Articolo violato**: Art. 71, comma 4, lett. c), D.Lgs. 81/2008
    - **Correzione consigliata**: Vietare il transito/sosta sotto il carico, segnalare l’area
    """)

    st.success("Analisi completata.")
