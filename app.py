# app.py

import streamlit as st
from layout.main_layout import render_page

# Configuración básica de la app (tú ya la usabas arriba del todo)
st.set_page_config(
    page_title="Prospecting Assistant",
    page_icon="🤖",
    layout="wide"
)

# Renderiza toda la UI
render_page()

