# credit.py
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine

#Funciones de Carga de Datos con Caché

@st.cache_resource
def get_db_engine(DB_USER, DB_PASS, DB_HOST, DB_PORT):
    """Crea y cachea la conexión a la base de datos Gold."""
    try:
        # Asegúrate de que esta cadena de conexión sea correcta para tu sistema
        engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/gold")
        return engine
    except Exception as e:
        st.error(f"Error de conexión a la base de datos: {e}")
        return None

@st.cache_data
def load_gold_data(_engine, table_name="gold_active_customer_profile"):
    """Carga una tabla específica desde la base de datos."""
    try:
        df = pd.read_sql(f"SELECT * FROM {table_name}", _engine)
        return df
    except Exception as e:
        st.error(f"No se pudo cargar la tabla '{table_name}'. Error: {e}")
        return pd.DataFrame()


# Función para crear una tarjeta de KPI
def crear_kpi_box(title, value, color):
    """
    Función de ayuda para crear una tarjeta de KPI con estilo personalizado.
    """
    box_style = """
        border: 1px solid #d8ddf9; 
        border-radius: 7px; 
        padding: 20px; 
        text-align: center;
        height: 150px; /* Altura fija para alinear las cajas */
        display: flex;
        flex-direction: column;
        justify-content: center;
    """
    title_style = "color: white; font-size: 18px; margin-bottom: 10px;"
    value_style = f"color: {color}; font-size: 36px; font-weight: bold;"

    # Creamos el HTML para la tarjeta
    html_content = f"""
    <div style="{box_style}">
        <div style="{title_style}">{title}</div>
        <div style="{value_style}">{value}</div>
    </div>
    """
    return html_content

#Función Principal de la Página

def app(DB_USER, DB_PASS, DB_HOST, DB_PORT):
    """
    Párametros: credenciales usadas para conectarse a la base de datos gold de forma local

    Retorno: Esta función construye toda la página de 'Análisis Crediticio'.
    """
    st.markdown("<h1 style='color: #d8ddf9; font-family: Courier New; text-align: center;'>Análisis de Comportamiento Crediticio</h1>", unsafe_allow_html=True)

    engine = get_db_engine(DB_USER, DB_PASS, DB_HOST, DB_PORT)
    if engine is None:
        st.error("La conexión a la base de datos ha fallado. La aplicación no puede continuar.")
        st.stop()

    df = load_gold_data(engine, "gold_active_customer_profile")
    if df.empty:
        st.warning("No se encontraron datos en la tabla 'gold_active_customer_profile'.")
        st.stop()

    df['RISK_SCORE'] = (
        (df['FRAC_LATE_INSTALLMENTS'].rank(pct=True) * 0.20) +
        (df['AVG_UTILIZATION_RATIO_TDC'].rank(pct=True) * 0.30) +
        (df['MAX_DAYS_LATE'].rank(pct=True) * 0.25) +
        (df['MAX_DPD_TDC'].rank(pct=True) * 0.25)
    )

    # --- Barra Lateral con Filtros (Sin cambios) ---
    with st.sidebar.expander("🔍 Filtros de Cartera"):
        max_avg_balance = int(df['AVG_BALANCE_TDC'].max())
        selected_balance = st.slider('Filtrar por Saldo Promedio en TDC:', min_value=0, max_value=max_avg_balance, value=(0, max_avg_balance))
        max_loans = int(df['TOTAL_LOANS_WITH_INSTALLMENTS'].max())
        selected_loans = st.slider('Filtrar por Nro. Total de Préstamos:', min_value=0, max_value=max_loans, value=(0, max_loans))

    # Aplicar filtros al DataFrame que YA CONTIENE el RISK_SCORE estable
    df_filtered = df[
        (df['AVG_BALANCE_TDC'] >= selected_balance[0]) &
        (df['AVG_BALANCE_TDC'] <= selected_balance[1]) &
        (df['TOTAL_LOANS_WITH_INSTALLMENTS'] >= selected_loans[0]) &
        (df['TOTAL_LOANS_WITH_INSTALLMENTS'] <= selected_loans[1])
    ]

    st.markdown("---")

    #Título de la sección con estilo personalizado
    st.markdown("<h2 style='color: #d8ddf9; font-family: Courier New; text-align: center;'>Visión General de la Cartera Filtrada</h2>", unsafe_allow_html=True)


    # Dividir el espacio en 4 columnas para mostrar los KPIs
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)


    # --- KPI 1: Total de Clientes Activos (Verde) ---
    total_clientes_valor = f"{len(df_filtered):,}"
    kpi1_html = crear_kpi_box(
        title="👥 Total Clientes Activos", 
        value=total_clientes_valor, 
        color="#28a745"  # Verde
    )
    kpi1.markdown(kpi1_html, unsafe_allow_html=True)

    # --- KPI 2: Tasa de Clientes con Atrasos (Rojo) ---
    total_clientes = len(df_filtered)
    clientes_con_atrasos = df_filtered[df_filtered['FRAC_LATE_INSTALLMENTS'] > 0].shape[0]
    if total_clientes > 0:
        tasa_atrasos = (clientes_con_atrasos / total_clientes) * 100
    else:
        tasa_atrasos = 0
    tasa_atrasos_valor = f"{tasa_atrasos:.1f}%"
    kpi2_html = crear_kpi_box(
        title="⚠️ % Clientes con Atrasos", 
        value=tasa_atrasos_valor, 
        color="#dc3545"  # Rojo
    )
    kpi2.markdown(kpi2_html, unsafe_allow_html=True)


    # --- KPI 3: Utilización Promedio de TDC (Verde) ---
    #Redondeo a entero
    utilizacion_promedio = df_filtered['AVG_UTILIZATION_RATIO_TDC'].mean() * 100
    utilizacion_valor = f"{utilizacion_promedio:.0f}" # .0f para redondear a entero
    kpi3_html = crear_kpi_box(
        title="💳 Utilización Promedio TDC", 
        value=utilizacion_valor, 
        color="#28a745"  # Verde
    )
    kpi3.markdown(kpi3_html, unsafe_allow_html=True)


    # --- KPI 4: Deuda Promedio en TDC (Rojo) ---
    #Formateo a dos decimales
    deuda_promedio = df_filtered['AVG_BALANCE_TDC'].mean()
    deuda_valor = f"${deuda_promedio:,.2f}" # .2f para dos cifras decimales
    kpi4_html = crear_kpi_box(
        title="💰 Deuda Promedio en TDC", 
        value=deuda_valor, 
        color="#dc3545"  # Rojo
    )
    kpi4.markdown(kpi4_html, unsafe_allow_html=True)


    st.markdown("---")

    # --- Sección de Análisis Detallado ---

    st.markdown("<h2 style='color: #d8ddf9; font-family: Courier New; text-align: center;'>Análisis Detallado del Comportamiento</h2>", unsafe_allow_html=True)

    # Crear pestañas para organizar las visualizaciones
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Comportamiento en Cuotas", "💳 Comportamiento en Tarjetas de Crédito", "🎯 Segmentación y Riesgo", "🔬 Análisis Avanzado", '📊 Tipo de credito y estado'])

    # --- Contenido de la Pestaña 1: Comportamiento en Cuotas ---
    with tab1:
        
        col1, col2 = st.columns(2)
        
        # Visualización 1: Frecuencia de Atrasos
        with col1:
            st.markdown("<h3 style='text-align: center; color: white;'>Frecuencia de Atrasos</h3>", unsafe_allow_html=True)
            fig_freq = px.histogram(
                df_filtered, 
                x='FRAC_LATE_INSTALLMENTS',
                nbins=30, # Agrupar en 30 barras para mejor visualización
                labels={'FRAC_LATE_INSTALLMENTS': 'Proporción de Pagos Atrasados del Cliente'},
                color_discrete_sequence=['#d8ddf9']
            )
            fig_freq.update_layout(
                yaxis_title="Número de Clientes",
                bargap=0.1
            )
            st.plotly_chart(fig_freq, use_container_width=True)
            st.info("""
            **Análisis:** Este gráfico muestra qué tan a menudo los clientes pagan tarde. 
            - Un pico grande en `0.0` indica que la mayoría de los clientes son puntuales.
            - Barras en el extremo derecho representan clientes crónicos que casi siempre pagan tarde.
            """)

        # Visualización 2: Severidad de los Atrasos
        with col2:
            st.markdown("<h3 style='text-align: center; color: white;'>Severidad de los Atrasos</h3>", unsafe_allow_html=True)
            # Filtramos para ver solo los clientes que tienen al menos un atraso
            df_con_atrasos = df_filtered[df_filtered['MAX_DAYS_LATE'] > 0]
            
            fig_sever = px.histogram(
                df_con_atrasos, 
                x='MAX_DAYS_LATE',
                nbins=30,
                labels={'MAX_DAYS_LATE': 'Máximo de Días de Atraso del Cliente'},
                color_discrete_sequence=['#dc3545'] # Rojo para indicar severidad
            )
            fig_sever.update_layout(
                yaxis_title="Número de Clientes",
                bargap=0.1
            )
            st.plotly_chart(fig_sever, use_container_width=True)
            st.info("""
            **Análisis:** De los clientes que se atrasan, este gráfico muestra la gravedad de su peor atraso.
            - Picos cerca de `0` indican atrasos menores (pocos días).
            - Barras hacia la derecha (`>30`, `>60` días) señalan eventos de alto riesgo.
            """)

    # --- Contenido de la Pestaña 2: Comportamiento en Tarjetas de Crédito ---
    with tab2:

        col1, col2 = st.columns(2)
        
        # Visualización 3: Distribución de la Utilización de Crédito
        with col1:
            st.markdown("<h3 style='text-align: center; color: white;'>Utilización de Línea de Crédito</h3>", unsafe_allow_html=True)
            # Filtramos para ver solo clientes con utilización > 0 para un gráfico más claro
            df_con_utilizacion = df_filtered[df_filtered['AVG_UTILIZATION_RATIO_TDC'] > 0]

            fig_util = px.histogram(
                df_con_utilizacion, 
                x='AVG_UTILIZATION_RATIO_TDC',
                nbins=30,
                labels={'AVG_UTILIZATION_RATIO_TDC': 'Ratio de Utilización Promedio'},
                color_discrete_sequence=['#17a2b8'] # Color cian/azul claro
            )
            fig_util.update_layout(
                yaxis_title="Número de Clientes",
                bargap=0.1
            )
            st.plotly_chart(fig_util, use_container_width=True)
            st.info("""
            **Análisis:** Muestra qué porcentaje de su límite de crédito usan los clientes.
            - `Utilización > 70%` (0.7) a menudo se asocia con un mayor estrés financiero y riesgo de impago.
            - Picos a la izquierda indican un uso saludable y conservador del crédito.
            """)

        # Visualización 4: Persistencia de la Morosidad en TDC
        with col2:
            st.markdown("<h3 style='text-align: center; color: white;'>Persistencia de Morosidad (DPD)</h3>", unsafe_allow_html=True)
            
            # Creamos categorías para la morosidad para que el gráfico sea más legible
            df_dpd = df_filtered.copy()
            df_dpd['DPD_CATEGORY'] = pd.cut(
                df_dpd['TOTAL_MONTHS_WITH_DPD_TDC'],
                bins=[-1, 0, 2, 5, 100],
                labels=['Puntual (0 meses)', 'Ocasional (1-2)', 'Recurrente (3-5)', 'Crónico (5+)']
            )
            
            # Contamos cuántos clientes caen en cada categoría
            dpd_counts = df_dpd['DPD_CATEGORY'].value_counts().reset_index()

            fig_dpd = px.bar(
                dpd_counts, 
                x='DPD_CATEGORY', 
                y='count',
                title='', # El título ya está en el markdown
                labels={'count': 'Número de Clientes', 'DPD_CATEGORY': 'Categoría de Morosidad'},
                color='DPD_CATEGORY', # Colorear por categoría
                color_discrete_map={ # Mapa de colores personalizado
                    'Puntual (0 meses)': '#28a745',
                    'Ocasional (1-2)': '#ffc107',
                    'Recurrente (3-5)': '#fd7e14',
                    'Crónico (5+)': '#dc3545'
                }
            )
            fig_dpd.update_layout(xaxis={'categoryorder':'total descending'}) # Ordenar de mayor a menor
            st.plotly_chart(fig_dpd, use_container_width=True)
            
            st.info("""
            **Análisis:** Clasifica a los clientes por la cantidad de meses que han estado en mora (DPD > 0).
            - `Puntual:` El segmento más saludable.
            - `Ocasional:` Pueden ser errores o problemas puntuales.
            - `Recurrente/Crónico:` El segmento de mayor riesgo que requiere atención inmediata.
            """)

    # --- Pestaña 3: Segmentación y Riesgo (Versión Mejorada) ---
    with tab3:
        
        st.markdown("<h3 style='text-align: center; color: white;'>Matriz de Riesgo vs. Valor del Cliente</h3>", unsafe_allow_html=True)
        fig_scatter = px.scatter(
            df_filtered, 
            x='AVG_UTILIZATION_RATIO_TDC', 
            y='TOTAL_INSTALLMENTS_PAID', 
            color='RISK_SCORE', 
            color_continuous_scale=px.colors.sequential.OrRd, 
            hover_name=df_filtered['SK_ID_CURR'], 
            hover_data={'SK_ID_CURR': False, 'RISK_SCORE': ':.2f'}, 
            labels={
                'AVG_UTILIZATION_RATIO_TDC': 'RIESGO (Utilización de Crédito)', 
                'TOTAL_INSTALLMENTS_PAID': 'VALOR (Experiencia del Cliente)', 
                'RISK_SCORE': 'Puntuación de Riesgo'
            }
        )
        fig_scatter.update_traces(marker=dict(size=8, opacity=0.7))
        st.plotly_chart(fig_scatter, use_container_width=True)

        # Visualización 3: Buscador de Clientes
        st.markdown("<h3 style='text-align: center; color: white;'>Diagnóstico Individual de Cliente</h3>", unsafe_allow_html=True)
        list_of_clients = sorted(df_filtered['SK_ID_CURR'].unique())
        selected_client_id = st.selectbox("Selecciona un ID de Cliente para analizar:", options=list_of_clients, key='client_selector')
        if selected_client_id:
            client_data = df_filtered[df_filtered['SK_ID_CURR'] == selected_client_id].iloc[0]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Puntuación de Riesgo", f"{client_data['RISK_SCORE']:.2f}")
            m2.metric("% Utilización TDC", f"{client_data['AVG_UTILIZATION_RATIO_TDC']:.1%}")
            m3.metric("% Cuotas Atrasadas", f"{client_data['FRAC_LATE_INSTALLMENTS']:.1%}")
            m4.metric("Peor Atraso (Días)", f"{max(client_data['MAX_DAYS_LATE'], client_data['MAX_DPD_TDC']):.0f}")

        st.info("""
        **Segmentos Estratégicos:**
        1.  `Arriba a la Izquierda (Bajo Riesgo, Alto Valor):` **Clientes Estrella.** (Fidelizar)
        2.  `Arriba a la Derecha (Alto Riesgo, Alto Valor):` **Clientes Clave en Riesgo.** (Monitorear)
        3.  `Abajo a la Izquierda (Bajo Riesgo, Bajo Valor):` **Nuevos o Inactivos.** (Activar)
        4.  `Abajo a la Derecha (Alto Riesgo, Bajo Valor):` **Clientes Problemáticos.** (Gestionar)
        """)
        
        st.markdown("---")
        
        # --- Parte 2: Tabla "Top 10" mejorada y más clara ---
        st.markdown("<h3 style='text-align: center; color: white;'>Top 10 Clientes de Mayor Riesgo</h3>", unsafe_allow_html=True)
        top_10_riesgo = df_filtered.sort_values('RISK_SCORE', ascending=False).head(10)
        
        # Añadimos la columna 'MAX_DAYS_LATE' para dar contexto completo
        display_columns = {
            'SK_ID_CURR': 'ID Cliente',
            'RISK_SCORE': 'Puntuación de Riesgo',
            'FRAC_LATE_INSTALLMENTS': '% Cuotas Atrasadas',
            'AVG_UTILIZATION_RATIO_TDC': '% Utilización TDC',
            'MAX_DAYS_LATE': 'Peor Atraso Cuotas (Días)', # La columna que faltaba
            'MAX_DPD_TDC': 'Peor Atraso TDC (Días)'
        }

        # Aplicar formato y estilo mejorados
        st.dataframe(
            top_10_riesgo[display_columns.keys()]
            .rename(columns=display_columns)
            .style
            .format({
                'Puntuación de Riesgo': '{:.2f}',
                '% Cuotas Atrasadas': '{:.1%}',
                '% Utilización TDC': '{:.1%}',
                'Peor Atraso Cuotas (Días)': '{:.0f}', # Sin decimales
                'Peor Atraso TDC (Días)': '{:.0f}'      # Sin decimales
            })
            .background_gradient(cmap='OrRd', subset=['Puntuación de Riesgo'], vmin=0.5, vmax=1.0)
            .apply(
                lambda x: ['background-color: #552222' if v > 0 else '' for v in x],
                subset=['Peor Atraso Cuotas (Días)', 'Peor Atraso TDC (Días)']
            ) # Resaltar en rojo oscuro cualquier celda de atraso > 0
        )
    with tab4:
        # --- Visualización 1: Matriz de Correlación ---
        st.markdown("<h3 style='text-align: center; color: white;'>Matriz de Correlación de Métricas Clave</h3>", unsafe_allow_html=True)

        # Seleccionar solo las columnas numéricas más relevantes para la correlación
        correlation_cols = [
            'FRAC_LATE_INSTALLMENTS',
            'AVG_DAYS_LATE',
            'MAX_DAYS_LATE',
            'AVG_UTILIZATION_RATIO_TDC',
            'AVG_DPD_TDC',
            'MAX_DPD_TDC',
            'RISK_SCORE'
        ]
        corr_matrix = df_filtered[correlation_cols].corr()

        # Crear el mapa de calor con Plotly Express
        fig_corr = px.imshow(
            corr_matrix,
            text_auto=True,  # Mostrar los valores de correlación en las celdas
            aspect="auto",
            color_continuous_scale='RdBu_r', # Rojo (negativo) - Blanco (cero) - Azul (positivo)
            zmin=-1, zmax=1 # Forzar la escala de color de -1 a 1
        )
        st.plotly_chart(fig_corr, use_container_width=True)

        st.info("""
        **Análisis:** Esta matriz muestra la relación entre las métricas de riesgo.
        - `Valores cercanos a -1.0 (azul oscuro):` Fuerte correlación negativa (cuando una sube, la otra baja).
        - `Valores cercanos a  1.0 (rojo oscuro):` Fuerte correlación positiva (cuando una sube, la otra también)..
        - `Valores cercanos a 0 (blanco):` Poca o ninguna correlación lineal.
        """)

        # --- Visualización 2: Riesgo por Antigüedad ---
        st.markdown("<h3 style='text-align: center; color: white;'>Perfil de Riesgo por Antigüedad del Cliente</h3>", unsafe_allow_html=True)

        # Crear categorías (bins) para la antigüedad del cliente
        df_antiguedad = df_filtered.copy()
        df_antiguedad['TENURE_CATEGORY'] = pd.cut(
            df_antiguedad['TOTAL_LOANS_WITH_INSTALLMENTS'],
            bins=[0, 1, 3, 5, 10, 100],
            labels=['Nuevo (1 Préstamo)', 'Principiante (2-3)', 'Intermedio (4-5)', 'Experimentado (6-10)', 'Veterano (10+)'],
            right=True # Incluye el borde derecho
        )

        # Calcular el riesgo promedio por categoría
        risk_by_tenure = df_antiguedad.groupby('TENURE_CATEGORY', observed=True)['RISK_SCORE'].mean().reset_index()

        fig_tenure = px.bar(
            risk_by_tenure,
            x='TENURE_CATEGORY',
            y='RISK_SCORE',
            color='RISK_SCORE',
            color_continuous_scale='YlOrRd',
            labels={'RISK_SCORE': 'Puntuación de Riesgo Promedio', 'TENURE_CATEGORY': 'Antigüedad del Cliente (Nro. de Préstamos)'}
        )
        st.plotly_chart(fig_tenure, use_container_width=True)

        st.info("""
        **Análisis:** Este gráfico revela si el riesgo promedio varía según la cantidad de préstamos que un cliente ha tenido. Permite responder si la lealtad o la experiencia se correlacionan con un mejor o peor comportamiento de pago.
        """)

    with tab5:
        df_tab5 = load_gold_data(engine, "bureau")
        if df_tab5.empty:
            st.warning("No se encontraron datos en la tabla 'gold_active_customer_profile'.")
            st.stop()
        # Entrada manual del ID
        id_input = st.number_input("Ingrese el ID del cliente (SK_ID_CURR)", 
                                min_value=int(df_tab5['SK_ID_CURR'].min()), 
                                max_value=int(df_tab5['SK_ID_CURR'].max()), step=1)

        # Filtrar datos por cliente
        df_filtrado = df_tab5[df_tab5['SK_ID_CURR'] == id_input]
        st.dataframe(df_filtrado[['SK_ID_CURR', 'CREDIT_TYPE', 'CREDIT_ACTIVE']])

        # Mostrar tabla del cliente
        if not df_filtrado.empty:
            st.markdown(f"## Información para el cliente **{id_input}**")
            st.dataframe(df_filtrado[['SK_ID_CURR', 'CREDIT_TYPE', 'CREDIT_ACTIVE']])

            # Métricas
            total_creditos = len(df_filtrado)
            creditos_activos = df_filtrado[df_filtrado['CREDIT_ACTIVE'] == 'Active'].shape[0]
            creditos_cerrados = df_filtrado[df_filtrado['CREDIT_ACTIVE'] == 'Closed'].shape[0]
            tipos_credito_unicos = df_filtrado['CREDIT_TYPE'].nunique()

            st.markdown("---")
            st.subheader("📌 Métricas del Cliente")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Créditos Totales", total_creditos)
            m2.metric("Activos", creditos_activos)
            m3.metric("Cerrados", creditos_cerrados)
            m4.metric("Tipos de Crédito", tipos_credito_unicos)

        else:
            st.warning("⚠️ No se encontró información para el ID ingresado.")

        # ==============================
        # GRÁFICOS GLOBALES
        # ==============================
        st.markdown("---")
        st.subheader("📊 Distribución General de Créditos")

        # Estado de crédito global - gráfico de barras
        estado_global = df_tab5['CREDIT_ACTIVE'].value_counts().reset_index()
        estado_global.columns = ['Estado', 'Frecuencia']

        fig_estado_global = px.bar(
            estado_global,
            x='Estado',
            y='Frecuencia',
            color='Estado',
            title='Distribución General de Estado de Créditos',
            text_auto=True
        )

        # Tipo de crédito global - torta top 4
        tipo_global = df_tab5['CREDIT_TYPE'].value_counts().nlargest(4).reset_index()
        tipo_global.columns = ['Tipo', 'Frecuencia']

        fig_tipo_global = px.pie(
            tipo_global,
            names='Tipo',
            values='Frecuencia',
            title='Top 4 Tipos de Crédito (Global)',
            hole=0  # pastel completo
        )

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig_estado_global, use_container_width=True)

        with col2:
            st.plotly_chart(fig_tipo_global, use_container_width=True)
        df_tab5= pd.read_sql("select * from bureau", engine)
                  
        # --- Tabla de Frecuencias (Activos y Cerrados) ---
        creditos_activos = df_tab5[df_tab5['CREDIT_ACTIVE'] == 'Active']
        creditos_cerrados = df_tab5[df_tab5['CREDIT_ACTIVE'] == 'Closed']

        frecuencia_activos = creditos_activos['CREDIT_TYPE'].value_counts()
        frecuencia_cerrados = creditos_cerrados['CREDIT_TYPE'].value_counts()

        frecuencia_comparada = pd.concat(
            [frecuencia_activos, frecuencia_cerrados],
            axis=1,
            keys=['Activos', 'Cerrados']
        ).fillna(0).astype(int)
