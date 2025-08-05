# dashboard/main.py

import streamlit as st

# Centrar contenido usando columnas
col1, col2, col3 = st.columns([1, 6, 1])
with col2:
    st.title("🏦 Análisis de Riesgo Crediticio - Home Credit")

    st.markdown("""
    <div style="text-align: justify; font-size: 16px;">
        Bienvenido al dashboard del proyecto Análisis de Riesgo Crediticio, basado en el conjunto de datos de 
        <a href='https://www.kaggle.com/competitions/home-credit-default-risk' target='_blank'>Home Credit Default Risk</a> (Kaggle). <br><br>

        Este proyecto tiene como propósito identificar los factores que influyen en el riesgo de incumplimiento de crédito 
        a partir del análisis de información socioeconómica y financiera de los solicitantes. Se busca entender el perfil de los clientes, 
        predecir su nivel de riesgo y aportar a la toma de decisiones más informadas por parte de las instituciones financieras.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("## 🎯 Objetivos del Proyecto")
    st.markdown("""
    - Identificar las variables más relevantes que afectan el incumplimiento crediticio.
    - Analizar perfiles de clientes y detectar patrones comunes de comportamiento financiero.
    - Aplicar técnicas de EDA para limpiar, transformar y visualizar los datos.
    - Desarrollar modelos de machine learning para predecir riesgo de impago.
    - Evaluar el desempeño de los modelos con métricas adecuadas.
    - Generar insights prácticos para mejorar la evaluación crediticia.
    """)

    st.markdown("## 📁 Estructura de los Datos")
    st.markdown("""
    - `application_train.csv` y `application_test.csv`: Información principal de los solicitantes.
    - `bureau.csv` y `bureau_balance.csv`: Historial crediticio con otras entidades.
    - `previous_application.csv`: Préstamos anteriores con Home Credit.
    - `installments_payments.csv`: Pagos realizados en cuotas.
    - `credit_card_balance.csv`: Estado de las tarjetas de crédito.
    - `POS_CASH_balance.csv`: Detalles de productos POS.

    Todas las tablas están relacionadas mediante claves como `SK_ID_CURR` y `SK_ID_PREV`, lo que permite integrar los datos fácilmente.
    """)

    st.markdown("---")
    st.markdown("<div style='text-align: center;'>📊 Desarrollado por el equipo de análisis de datos - Julio 2025</div>", unsafe_allow_html=True)

