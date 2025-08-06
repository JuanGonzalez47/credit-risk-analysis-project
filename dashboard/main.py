# dashboard/main.py
import streamlit as st
from datetime import datetime

# Importa los módulos de las páginas
import applicants
import credit
import risk_level


# ──────────────────────────────────────────────
# Configuración general
st.set_page_config(page_title="Dashboard Home Credit", layout="wide", page_icon="📊")


# Configuración del estado inicial
if "page" not in st.session_state:
    st.session_state.page = "Inicio"

# Estilo CSS para botones bonitos
st.markdown("""
<style>
div[data-testid="stSidebar"] button:hover {
    border: 1px solid #d8ddf9;
    background-color: #1E1E1E;
}
</style>
""", unsafe_allow_html=True)


# Función para cambiar de página
def navegar(pagina):
    st.session_state.page = pagina

# ──────────────────────────────────────────────
# Barra lateral con navegación
with st.sidebar:
    st.image("Images/logo_talento.svg", width=210)
    with st.expander("📂 Menú Principal", expanded=True):
        st.markdown("<div style='font-family: Arial;'>", unsafe_allow_html=True)
        if st.button("Inicio"):
            navegar("Inicio")
        if st.button("Modelos"):
            navegar("Modelos")
        if st.button("Análisis Crediticio"):
            navegar("Análisis Crediticio")
        if st.button("Historial de Aplicantes"):
            navegar("Aplicantes")
        st.markdown("</div>", unsafe_allow_html=True)



# Cuerpo de página
if st.session_state.page == "Inicio":
    # ──────────────────────────────────────────────
    # Encabezado con imagen al lado del título
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        <h1 style='color: #d8ddf9; font-family: Courier New; text-align: center; font-style: italic;'>
            Análisis de Riesgo Crediticio
        </h1>
        <div style="font-size: 16px; text-align: center; font-family: Courier New;">
            Transformamos datos financieros en inteligencia accionable
        </div>
        <div style="font-size: 16px; text-align: center; font-family: Courier New;">
            para decisiones bancarias más informadas y efectivas.
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.image("Images/credit_home.jpg")

    # ──────────────────────────────────────────────
    # Dos columnas: izquierda (descripción + enlace), derecha (objetivos)
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("""
        <div style="background-color: #2D2D2D; padding: 20px; border-radius: 10px;">
            <h2 style='color: #d8ddf9; font-family: Courier New; text-align: center; font-style: italic;'>
                Descripción del Proyecto
            </h2>
            <p style="font-size: 16px; color: white; font-family: Courier New;">
                📊 Este dashboard presenta un análisis detallado del riesgo crediticio utilizando datos reales de solicitantes. <br><br>
                Se aplicaron técnicas de ciencia de datos para entender patrones, predecir incumplimientos y generar recomendaciones valiosas para instituciones financieras.
            </p>
            <p style="font-size: 16px; font-family: Courier New; color: white;">
                📂 Basado en el conjunto de datos de <a href='https://www.kaggle.com/competitions/home-credit-default-risk' target='_blank' style='color: #d8ddf9;'>Home Credit Default Risk</a> (Kaggle).
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="background-color: #2D2D2D; padding: 20px; border-radius: 10px;">
            <h2 style='color: #d8ddf9; font-family: Courier New; text-align: center; font-style: italic;'>Objetivos del Proyecto</h2>
            <ul style="font-size: 16px; color: white; font-family: Courier New;">
                ✅ Identificar las variables más relevantes que afectan el incumplimiento crediticio<br>
                ✅ Analizar perfiles de clientes y detectar patrones comunes<br>
                ✅ Aplicar técnicas de EDA para limpiar, transformar y visualizar los datos<br>
                ✅ Desarrollar modelos de machine learning para predecir riesgo de impago<br>
                ✅ Evaluar el desempeño de los modelos con métricas adecuadas<br>
                ✅ Generar insights prácticos para mejorar la evaluación crediticia<br>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    # ──────────────────────────────────────────────
    # Título e imagen de la estructura de la base de datos
    st.markdown("""
    <h2 style='color: #d8ddf9; font-family: Courier New; text-align: center; font-style: italic;'>
        Estructura de la Base de Datos
    </h2>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.image("Images/db_structure.png", width=600)


    # ──────────────────────────────────────────────
    #Pie de página con información del equipo
    st.markdown("---")

    st.markdown(f"""
    <div style='text-align: center; color: white; font-family: Courier New; font-size: 16px;'>
        Desarrollado por el equipo de análisis de datos – Julio {datetime.now().year}<br>
        <br>
        <strong>Integrantes:</strong><br>
        Juan Pablo González Blandón<br>
        Juan Felipe Isaza Valencia<br>
        Alexis de Jesús Collante Genes<br>
        Jorge Antonio Álvarez Sayas<br>
        <br>
        <em>Participantes del programa Talento Tech</em>
    </div>
    """, unsafe_allow_html=True)

    # ──────────────────────────────────────────────
elif st.session_state.page == "Aplicantes":
    applicants.app()  # Define `app()` en applicants.py
elif st.session_state.page == "Análisis Crediticio":
    credit.app()
elif st.session_state.page == "Modelos":
    risk_level.app()

