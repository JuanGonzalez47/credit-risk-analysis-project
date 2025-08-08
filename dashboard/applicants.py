# applicants.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go

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
def load_gold_data_POS(_engine):
    """Carga la tabla Gold pre-procesada desde la base de datos."""
    try:
        df = pd.read_sql("SELECT * FROM pos_cash_balance_gold", _engine)
        return df
    except Exception as e:
        st.error(f"No se pudo cargar la tabla 'pos_cash_balance_gold'. Error: {e}")
        return pd.DataFrame()

@st.cache_data
def load_gold_data_previous(_engine):
    """Carga la tabla Gold pre-procesada desde la base de datos."""
    try:
        df = pd.read_sql("SELECT * FROM previous_application_gold", _engine)
        return df
    except Exception as e:
        st.error(f"No se pudo cargar la tabla 'previous_application_gold'. Error: {e}")
        return pd.DataFrame()

# Traducir valores únicos de texto
traducciones_tipo_contrato = {
    "Cash loans": "Préstamo en efectivo",
    "Consumer loans": "Préstamo de consumo",
    "Revolving loans": "Crédito rotativo",
    "XNA": "No especificado"
}

traducciones_estado_contrato = {
    "Approved": "Aprobado",
    "Refused": "Rechazado",
    "Canceled": "Cancelado",
    "Unused offer": "Oferta no utilizada"
}

traducciones_tipo_cliente = {
    "Repeater": "Recurrente",
    "New": "Nuevo",
    "Refreshed": "Renovado",
    "XNA": "No especificado"
}

traducciones_canal_venta = {
    "Contact center": "Centro de contacto",
    "Credit and cash offices": "Oficinas de crédito y efectivo",
    "Country-wide": "A nivel nacional",
    "Stone": "Sucursal física",
    "Regional / Local": "Regional / Local",
    "AP+ (Cash loan)": "AP+ (Préstamo en efectivo)",
    "Channel of corporate sales": "Canal de ventas corporativas",
    "Car dealer": "Concesionario"
}

traducciones_dias = {
    "MONDAY": "Lunes",
    "TUESDAY": "Martes",
    "WEDNESDAY": "Miércoles",
    "THURSDAY": "Jueves",
    "FRIDAY": "Viernes",
    "SATURDAY": "Sábado",
    "SUNDAY": "Domingo"
}

def app(DB_USER, DB_PASS, DB_HOST, DB_PORT):
    
    #Este es el título principal de la sección de Aplicantes
    st.markdown("""
    <h1 style='color: #d8ddf9; font-family: Courier New; text-align: center; font-style: italic;'>
    🧑‍💼 Historial de Aplicantes
    </h1>
    <div style="font-size: 16px; text-align: center; font-family: Courier New;">
        En esta sección podrás explorar el historial de solicitudes de crédito de los clientes,\n incluyendo detalles sobre sus solicitudes de crédito y su estado.
    </div>
    """, unsafe_allow_html=True)
 
    #Cargamos datos de gold
    engine = get_db_engine(DB_USER, DB_PASS, DB_HOST, DB_PORT)
    df_previous = load_gold_data_previous(engine)
    df_pos = load_gold_data_POS(engine)
    
    #Aquí se define la estructura de pestañas para la sección de Aplicantes
    tab1, tab2, tab3 = st.tabs(["📊 Información por ID de solicitud", "📈 Análisis por métricas generales", "📅 Comportamiento en pago de cuotas"])
    
    #Se empieza a trabajar con la primera pestaña
    with tab1:
        
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("🔍 Buscar registros por ID de solicitud")

        #Seleccionamos el tipo de búsqueda
        if df_previous.empty or df_pos.empty:
            st.warning("No hay datos disponibles para mostrar.")
        else:
             tipo_busqueda = st.selectbox("Selecciona tipo de búsqueda", ["Solicitud Actual", "Solicitud Previa"])

        st.markdown("<br>", unsafe_allow_html=True)
        #Si hay datos, se pide el ID de la solicitud
        if tipo_busqueda == "Solicitud Actual":
            id_input = st.text_input("🆔 Ingresa el ID de la solicitud actual", key="curr_input")
            columna_id = "SK_ID_CURR"
            
        else:
            id_input = st.text_input("🆔 Ingresa el ID de la solicitud previa", key="prev_input")
            columna_id = "SK_ID_PREV"
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        if id_input:
            try:
                id_input = int(id_input)

                if columna_id == "SK_ID_CURR":
                    df_filtrado = df_previous[df_previous["SK_ID_CURR"] == id_input]

                    if df_filtrado.empty:
                        st.info(f"No se encontraron solicitudes previas para SK_ID_CURR = {id_input}")
                    else:
                        st.markdown(f"### 📄 Solicitudes previas asociadas a \n`ID = {id_input}`")

                        # Seleccionar y renombrar columnas
                        columnas = {
                            "SK_ID_PREV": "ID de solicitud previa",
                            "NAME_CONTRACT_TYPE": "Tipo de contrato",
                            "NAME_CONTRACT_STATUS": "Estado de contrato",
                            "AMT_APPLICATION": "Monto solicitado",
                            "AMT_CREDIT": "Monto aprobado"
                        }
                        df_mostrar = df_filtrado[list(columnas.keys())].rename(columns=columnas)

                        df_mostrar["Tipo de contrato"] = df_mostrar["Tipo de contrato"].replace(traducciones_tipo_contrato)
                        df_mostrar["Estado de contrato"] = df_mostrar["Estado de contrato"].replace(traducciones_estado_contrato)

                        # Establecer índice
                        df_mostrar.set_index("ID de solicitud previa", inplace=True)

                        st.dataframe(df_mostrar)
                        
                        # Calcular porcentaje de cada estado de contrato
                        conteo_estado = df_mostrar["Estado de contrato"].value_counts(normalize=True).reset_index()
                        conteo_estado.columns = ["Estado de contrato", "Porcentaje"]
                        conteo_estado["Porcentaje"] = conteo_estado["Porcentaje"] * 100  # convertir a %
                        
                        # Agrupar y contar cada tipo de contrato
                        conteo_tipo_contrato = df_previous['NAME_CONTRACT_TYPE'].value_counts().reset_index()
                        conteo_tipo_contrato.columns = ['Tipo de contrato', 'Cantidad']
                        conteo_tipo_contrato['Tipo de contrato'] = conteo_tipo_contrato['Tipo de contrato'].replace(
                            traducciones_tipo_contrato
                        )
                        
                        st.markdown("<br><br>", unsafe_allow_html=True)
                        # ----------------------------
                        # Pie Chart - Tipo de contrato
                        # ----------------------------
                        fig_contrato = px.pie(
                            conteo_tipo_contrato,
                            names="Tipo de contrato",
                            values="Cantidad",
                            color_discrete_sequence=["#fcff3c", "#ffa93a", "#e90b0b", "white"],
                            title=" ",
                            hole=0.1
                        )

                        # -------------------------------
                        # Pie Chart - Estado de contrato
                        # -------------------------------
                        fig_estado = px.pie(
                            conteo_estado,
                            names="Estado de contrato",
                            values="Porcentaje",
                            color_discrete_sequence=["#fcff3c", "#ffa93a", "#e90b0b"],
                            title=" ",
                            hole=0.1
                        )

                        # -------------------------------
                        # Estilo común para ambos gráficos
                        # -------------------------------
                        for fig in [fig_contrato, fig_estado]:
                            fig.update_traces(
                                textinfo='percent+label',
                                textfont_size=18,
                                textposition='inside',
                                insidetextorientation='radial'
                            )
                            fig.update_layout(
                                title_font=dict(size=22, family="Arial", color="white"),
                                legend=dict(font=dict(size=14)),
                                margin=dict(t=60, b=0, l=0, r=0)
                            )

                        # -------------------------------
                        # Mostrar en columnas Streamlit
                        # -------------------------------
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("<h3 style='text-align: center;'>📊 Distribución del tipo de contrato</h3>", unsafe_allow_html=True)
                            st.plotly_chart(fig_contrato, use_container_width=True)

                        with col2:
                            st.markdown("<h3 style='text-align: center;'>📊 Distribución del estado de contrato</h3>", unsafe_allow_html=True)
                            st.plotly_chart(fig_estado, use_container_width=True)
                        
                        st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)
                        df_line = df_filtrado[[
                            "SK_ID_PREV",
                            "AMT_APPLICATION",
                            "AMT_CREDIT"
                        ]].copy()
                        # Ordenar por ID de solicitud previa
                        df_line.sort_values("SK_ID_PREV", inplace=True)

                        st.markdown("<h3 style='text-align: center;'>📈 Comparación entre Monto solicitado y Monto aprobado por solicitud previa</h3>",
                                    unsafe_allow_html=True)
                        # Convertir a formato largo para gráfico de líneas
                        df_melted = df_line.melt(
                            id_vars="SK_ID_PREV",
                            value_vars=["AMT_APPLICATION", "AMT_CREDIT"],
                            var_name="Tipo de monto",
                            value_name="Valor"
                        )

                        # Reemplazo para mostrar la leyenda en español
                        df_melted["Tipo de monto"] = df_melted["Tipo de monto"].replace({
                            "AMT_APPLICATION": "Monto solicitado",
                            "AMT_CREDIT": "Monto aprobado"
                        })
                        

                        # Crear gráfico interactivo de líneas
                        fig_line = px.line(
                            df_melted,
                            x="SK_ID_PREV",
                            y="Valor",
                            color="Tipo de monto",
                            markers=True,
                            title=" "
                        )

                        fig_line.update_layout(
                            xaxis_title="ID de solicitud previa",
                            yaxis_title="Monto ($)",
                            legend_title="Tipo de monto",
                            title_x=0.5,
                            font=dict(size=14),
                            xaxis=dict(
                                tickmode='array',
                                tickvals=df_filtrado['SK_ID_PREV'].unique(),
                                tickangle=80,
                                tickfont=dict(size=14),
                                type='category'  # Forzar a que se muestre como categoría ordenada y equiespaciada
                            )
                        )

                        st.plotly_chart(fig_line, use_container_width=True)
                        
                        st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)
                        st.markdown("<h3 style='text-align: center;'>📊 Métricas generales de solicitudes previas</h3>", unsafe_allow_html=True)
                        #Establecimiento de métricas
                        promedio_solicitado = df_filtrado["AMT_APPLICATION"].mean()
                        promedio_aprobado = df_filtrado["AMT_CREDIT"].mean()

                        aprobados = df_filtrado[df_filtrado["NAME_CONTRACT_STATUS"] == "Approved"].shape[0]
                        rechazados = df_filtrado[df_filtrado["NAME_CONTRACT_STATUS"] == "Refused"].shape[0]

                        if aprobados > 0:
                            proporcion = rechazados / aprobados
                        else:
                            proporcion = float("nan")

                        # Determinar color de la proporción
                        color_proporcion = "#dc3545" if proporcion > 0.5 else "#28a745"

                        #Crear columnas para métricas
                        col1, col2, col3 = st.columns(3)

                        #Estilo de caja métrica
                        def caja_metrica(titulo, valor, color_fondo):
                            st.markdown(
                                f"""
                                <div style="
                                    background-color: {color_fondo};
                                    padding: 20px;
                                    border-radius: 10px;
                                    text-align: center;
                                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                                ">
                                    <h4 style='color: #2c3e50; margin-bottom: 8px;'>{titulo}</h4>
                                    <h2 style='color: #2c3e50; font-weight: bold;'>{valor}</h2>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                        with col1:
                            caja_metrica("📌 Promedio solicitado ($)", f"{promedio_solicitado:,.0f}", "#d0e7ff")

                        with col2:
                            caja_metrica("✅ Promedio aprobado ($)", f"{promedio_aprobado:,.0f}", "#d0e7ff")

                        with col3:
                            caja_metrica("⚖️ Rechazos / Aprobaciones", f"{proporcion:.2f}", color_proporcion)

                else:
                    df_filtrado = df_previous[df_previous["SK_ID_PREV"] == id_input]

                    if df_filtrado.empty:
                        st.info(f"No se encontraron resultados para ID = {id_input}")
                    else:
                        st.markdown(f"### 📄 Detalle de solicitud previa \n `ID = {id_input}`")

                        # Extraer valores individuales
                        tipo_contrato = df_filtrado["NAME_CONTRACT_TYPE"].iloc[0]
                        estado_contrato = df_filtrado["NAME_CONTRACT_STATUS"].iloc[0]
                        monto_solicitado = df_filtrado["AMT_APPLICATION"].iloc[0]
                        monto_aprobado = df_filtrado["AMT_CREDIT"].iloc[0]
                        monto_anual = df_filtrado["AMT_ANNUITY"].iloc[0]
                        tipo_cliente = df_filtrado["NAME_CLIENT_TYPE"].iloc[0]
                        canal = df_filtrado["CHANNEL_TYPE"].iloc[0]

                        # Aplicar traducción si aplica
                        estado_contrato = traducciones_estado_contrato.get(estado_contrato, estado_contrato)
                        tipo_contrato = traducciones_tipo_contrato.get(tipo_contrato, tipo_contrato)
                        tipo_cliente = traducciones_tipo_cliente.get(tipo_cliente, tipo_cliente)
                        canal = traducciones_canal_venta.get(canal, canal)

                        def crear_box(titulo, valor, icono="📌", color="#d0e7ff"):
                            return f"""
                            <div style="
                                background-color: {color};
                                padding: 20px;
                                border-radius: 10px;
                                margin-bottom: 10px;
                                box-shadow: 0 0 5px rgba(0,0,0,0.1);
                                text-align: center;
                            ">
                                <p style="margin: 0; color: #2c3e50; font-weight: bold;">{icono} {titulo}</p>
                                <p style="margin: 5px 0 0 0; color: #2c3e50; font-size: 25px;">{valor}</p>
                            </div>
                            """

                        # Estado de contrato
                        color_estado = "##28a745" if estado_contrato == "Aprobado" else "#dc3545"
                        icono_estado = "🟢" if estado_contrato == "Aprobado" else "🔴"

                        # ──────────────────────────────
                        # Fila centrada: Estado del contrato
                        st.markdown("### 📌 Información individual")
                        col_estado = st.columns([1, 2, 1])[1]  # Columna central
                        with col_estado:
                            st.markdown(crear_box("Estado del contrato", f"{icono_estado} {estado_contrato}", icono="📊", color=color_estado), unsafe_allow_html=True)

                        # ──────────────────────────────
                        # Fila de 3 columnas
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.markdown(crear_box("Tipo de contrato", tipo_contrato, icono="📄"), unsafe_allow_html=True)
                            st.markdown(crear_box("Monto solicitado", f"${monto_solicitado:,.0f}", icono="💰"), unsafe_allow_html=True)

                        with col2:
                            st.markdown(crear_box("Tipo de cliente", tipo_cliente, icono="👥"), unsafe_allow_html=True)
                            st.markdown(crear_box("Monto aprobado", f"${monto_aprobado:,.0f}", icono="💵"), unsafe_allow_html=True)

                        with col3:
                            st.markdown(crear_box("Canal de solicitud", canal, icono="🏢"), unsafe_allow_html=True)
                            st.markdown(crear_box("Monto anual a pagar", f"${monto_anual:,.0f}", icono="📅"), unsafe_allow_html=True)
            except ValueError:
                st.error("⚠️ El ID ingresado debe ser un número entero.")
    
    with tab2:
        
        #Selección de tipo de análisis
        visualizacion = st.selectbox("Selecciona el tipo de análisis", ["Tasa de aprobación por tipo de cliente", "Distribución del monto solicitado por estado del contrato", "Promedio del monto solicitado por estado del contrato", "Tasa de aprobación por canal de solicitud", "Distribución de solicitudes y aprobaciones por día de la semana"])
        
        if visualizacion == "Tasa de aprobación por tipo de cliente":
            st.subheader("📈 Tasa de aprobación por tipo de cliente")

            # Filtrar datos aprobados/rechazados
            df_filtrado = df_previous[df_previous["NAME_CONTRACT_STATUS"].isin(["Approved", "Refused"])].copy()

            # Aplicar traducción
            df_filtrado["NAME_CLIENT_TYPE"] = df_filtrado["NAME_CLIENT_TYPE"].map(traducciones_tipo_cliente)

            # Agrupar y calcular tasas
            conteo = df_filtrado.groupby(["NAME_CLIENT_TYPE", "NAME_CONTRACT_STATUS"]).size().unstack(fill_value=0)
            conteo["Tasa_aprobación"] = conteo["Approved"] / (conteo["Approved"] + conteo["Refused"])

            # Mostrar tabla con títulos en español
            st.dataframe(
                conteo.rename(columns={
                    "NAME_CLIENT_TYPE": "Tipo de cliente",
                    "Approved": "Aprobados",
                    "Refused": "Rechazados",
                    "Tasa_aprobación": "Tasa de aprobación"
                })[["Aprobados", "Rechazados", "Tasa de aprobación"]].style.format({
                    "Tasa de aprobación": "{:.2%}"
                })
            )

            # Gráfico de barras
            fig = px.bar(
                conteo.reset_index(),
                x="NAME_CLIENT_TYPE",
                y="Tasa_aprobación",
                title="Tasa de aprobación por tipo de cliente",
                labels={
                    "Tasa_aprobación": "Tasa de aprobación",
                    "NAME_CLIENT_TYPE": "Tipo de cliente"
                },
                color="Tasa_aprobación",
                color_continuous_scale=["red", "orange", "green"],
                text=conteo["Tasa_aprobación"].apply(lambda x: f"{x:.1%}")
            )

            # Estilo del gráfico
            fig.update_traces(
                textposition="inside",
                textfont_size=20,
                insidetextanchor="middle"
            )
            fig.update_layout(
                yaxis_tickformat=".0%",
                yaxis_range=[0, 1],
                xaxis_title=None
            )

            # Mostrar gráfico
            st.plotly_chart(fig)
        
            #Análisis
            st.markdown(
                """
                <div style="font-size:25px">
                    <ul>
                        <li>🔴 <strong>Clientes no especificados</strong> tienen la tasa de aprobación más baja (<strong>62%</strong>), lo cual podría indicar problemas con la calidad de los datos o menor confiabilidad.</li>
                        <li>🟢 <strong>Clientes nuevos</strong> sorprendentemente presentan la tasa más alta (<strong>95.1%</strong>), lo cual sugiere políticas de entrada bastante flexibles o una evaluación optimista para nuevos perfiles.</li>
                        <li>🟠 <strong>Clientes recurrentes</strong>, aunque numerosos, tienen una tasa moderada (<strong>71.6%</strong>), lo que podría sugerir mayor escrutinio en su historial crediticio.</li>
                        <li>🟡 <strong>Clientes renovados</strong> mantienen una tasa alta (<strong>86.6%</strong>), indicando buena experiencia previa y confianza por parte del sistema crediticio.</li>
                    </ul>
                    <p>Estos patrones pueden ser clave para ajustar estrategias de evaluación de riesgo y segmentación de clientes.</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        elif visualizacion == "Distribución del monto solicitado por estado del contrato":
            st.subheader("📊 Distribución del monto solicitado por estado del contrato")

            # Verificar si hay datos
            if df_previous.empty:
                st.warning("No hay datos disponibles para mostrar.")
            else:
                # Filtrar y traducir estados
                df_estado = df_previous.copy()
            df_estado = df_previous.copy()
            df_estado["Estado traducido"] = df_estado["NAME_CONTRACT_STATUS"].replace(traducciones_estado_contrato)

            # Filtrar estados más relevantes
            df_estado = df_estado[df_estado["Estado traducido"].isin(["Aprobado", "Rechazado"])]

            # Gráfico de violín
            plt.figure(figsize=(10, 6))
            sns.violinplot(
                data=df_estado,
                x="Estado traducido",
                y="AMT_APPLICATION",
                palette={"Aprobado": "#28a745", "Rechazado": "#dc3545"}
            )
            plt.title("Distribución del monto solicitado por estado del contrato", fontsize=14)
            plt.xlabel("Estado del contrato", fontsize=12)
            plt.ylabel("Monto solicitado ($)", fontsize=12)
            plt.tight_layout()
            st.pyplot(plt)
            
            #Análisis
            st.markdown(
                """
                <div style="font-size:25px">
                    <ul>
                        <li>🟩 <strong>Contratos aprobados</strong> muestran una distribución más concentrada en montos bajos, con una mediana significativamente menor. Esto sugiere que los créditos de menor monto tienen mayor probabilidad de aprobación.</li>
                        <li>🟥 <strong>Contratos rechazados</strong> presentan una mayor dispersión y una mediana más alta. También hay una presencia notoria de valores extremos, lo que indica que solicitudes por montos altos tienden a ser rechazadas con mayor frecuencia.</li>
                        <li>📉 La forma de los violines indica que la mayor densidad de solicitudes rechazadas está en rangos intermedios a altos, mientras que en los aprobados, la mayoría se concentra en montos bajos.</li>
                    </ul>
                    <p>Este comportamiento puede orientar al establecimiento de umbrales de monto más claros o a revisar criterios de aprobación en función del riesgo asociado a montos elevados.</p>
                </div>
                """,
                unsafe_allow_html=True
            )

        elif visualizacion == "Promedio del monto solicitado por estado del contrato":
            st.subheader("📊 Promedio del monto solicitado por estado del contrato")

            # Verificar si hay datos
            if df_previous.empty:
                st.warning("No hay datos disponibles para mostrar.")
                return

            # Filtrar y traducir estados
            df_estado = df_previous.copy()
            df_estado["Estado traducido"] = df_estado["NAME_CONTRACT_STATUS"].replace(traducciones_estado_contrato)

            # Filtrar estados más relevantes
            df_estado = df_estado[df_estado["Estado traducido"].isin(["Aprobado", "Rechazado"])]
            # Agrupar por estado y calcular promedio
            df_mean_amount = df_estado.groupby("Estado traducido")["AMT_APPLICATION"].mean().reset_index()

            # Gráfico de barras
            plt.figure(figsize=(8, 5))
            sns.barplot(
                data=df_mean_amount,
                x="Estado traducido",
                y="AMT_APPLICATION",
                palette={"Aprobado": "#28a745", "Rechazado": "#dc3545"}
            )
            plt.title("Promedio del monto solicitado por estado del contrato", fontsize=14)
            plt.xlabel("Estado del contrato", fontsize=12)
            plt.ylabel("Monto solicitado promedio ($)", fontsize=12)

            # Mostrar valores en la parte superior
            for i, val in enumerate(df_mean_amount["AMT_APPLICATION"]):
                plt.text(i, val + 1000, f"${val:,.0f}", ha='center', fontsize=11)

            plt.tight_layout()
            st.pyplot(plt)
        
            #Análisis
            st.markdown(
                """
                <div style="font-size:25px">
                    <ul>
                        <li>🟩 <strong>Contratos aprobados</strong> tienen un promedio de monto solicitado significativamente menor (<strong>$180,567</strong>), lo que sugiere que las solicitudes de crédito más modestas tienen mayor probabilidad de ser aceptadas.</li>
                        <li>🟥 <strong>Contratos rechazados</strong> muestran un promedio mucho más alto (<strong>$331,761</strong>), indicando que los montos elevados están más asociados al rechazo, posiblemente por el riesgo financiero que representan.</li>
                        <li>📊 La diferencia entre ambos promedios evidencia una posible política de aprobación conservadora, donde los montos altos enfrentan mayor escrutinio o requisitos más estrictos.</li>
                    </ul>
                    <p>Este patrón puede servir como base para ajustar los criterios de evaluación, estableciendo límites más definidos o segmentando las solicitudes por rangos de monto para mejorar la eficiencia del proceso de aprobación.</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        elif visualizacion == "Tasa de aprobación por canal de solicitud":
            
            st.subheader("📊 Tasa de aprobación por canal de solicitud")
            df_canal = df_previous.copy()

            df_canal["Estado traducido"] = df_canal["NAME_CONTRACT_STATUS"].replace(traducciones_estado_contrato)

            df_canal["Canal traducido"] = df_canal["CHANNEL_TYPE"].replace(traducciones_canal_venta)

            # Filtrar solo Aprobado y Rechazado
            df_canal = df_canal[df_canal["Estado traducido"].isin(["Aprobado", "Rechazado"])]

            # Conteo de estados por canal
            df_grouped = df_canal.groupby(["Canal traducido", "Estado traducido"]).size().reset_index(name="Cantidad")

            # Pivot para crear proporciones por canal
            df_pivot = df_grouped.pivot(index="Canal traducido", columns="Estado traducido", values="Cantidad").fillna(0)

            # Calcular proporción de aprobados
            df_pivot["Tasa de aprobación (%)"] = (df_pivot["Aprobado"] / (df_pivot["Aprobado"] + df_pivot["Rechazado"])) * 100
            df_pivot = df_pivot.sort_values("Tasa de aprobación (%)", ascending=False)

            # Visualizar
            plt.figure(figsize=(10, 6))
            sns.barplot(
                data=df_pivot.reset_index(),
                x="Tasa de aprobación (%)",
                y="Canal traducido",
                palette="Blues_d"
            )

            # Mostrar valores sobre las barras
            for i, val in enumerate(df_pivot["Tasa de aprobación (%)"]):
                plt.text(val + 1, i, f"{val:.1f}%", va='center', fontsize=11)

            plt.title("Tasa de aprobación por canal de solicitud", fontsize=14)
            plt.xlabel("Tasa de aprobación (%)")
            plt.ylabel("Canal")
            plt.xlim(0, 100)
            plt.tight_layout()
            st.pyplot(plt)
        
            #Análisis
            st.markdown(
                """
                <div style="font-size:25px">
                    <ul>
                        <li>🏢 <strong>Sucursal física</strong> y <strong>Regional / Local</strong> lideran con tasas de aprobación superiores al <strong>89%</strong>, lo que indica que los canales presenciales tradicionales siguen siendo los más efectivos para lograr aprobaciones.</li>
                        <li>📉 <strong>Canales no presenciales</strong> como <strong>Centro de contacto</strong> (61.8%) y <strong>AP+ (Préstamo en efectivo)</strong> (58.6%) muestran tasas considerablemente más bajas, lo que sugiere que la falta de interacción directa podría influir negativamente en la aprobación.</li>
                        <li>🚫 <strong>Canal de ventas corporativas</strong> tiene la tasa más baja (<strong>44.0%</strong>), lo que podría reflejar una mayor exigencia en los criterios de evaluación o un perfil de cliente más riesgoso.</li>
                    </ul>
                    <p>Este análisis permite identificar los canales más eficientes para la aprobación de solicitudes, lo que puede orientar estrategias comerciales, asignación de recursos y diseño de campañas según el canal más favorable.</p>
                </div>
                """,
                unsafe_allow_html=True
            )

        elif visualizacion == "Distribución de solicitudes y aprobaciones por día de la semana":
            
            st.subheader("📅 Distribución de solicitudes y aprobaciones por día de la semana")
            # Copia del dataframe
            df_dias = df_previous.copy()
            df_dias["Día de la semana"] = df_dias["WEEKDAY_APPR_PROCESS_START"].replace(traducciones_dias)
            df_dias["Estado traducido"] = df_dias["NAME_CONTRACT_STATUS"].replace(traducciones_estado_contrato)

            # Orden lógico de los días
            orden_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            df_dias["Día de la semana"] = pd.Categorical(df_dias["Día de la semana"], categories=orden_dias, ordered=True)

            # Conteo total de solicitudes y aprobadas por día
            conteo_total = df_dias["Día de la semana"].value_counts().reindex(orden_dias)
            conteo_aprobadas = df_dias[df_dias["Estado traducido"] == "Aprobado"]["Día de la semana"].value_counts().reindex(orden_dias)

            # Calcular proporción aprobadas/solicitadas (%)
            proporcion = (conteo_aprobadas / conteo_total * 100).round(1)

            # ────────────────────────────────
            # GRÁFICO
            plt.figure(figsize=(10, 6))
            bar1 = sns.barplot(x=conteo_total.index, y=conteo_total.values, label="Solicitudes", color="lightgray")
            bar2 = sns.barplot(x=conteo_aprobadas.index, y=conteo_aprobadas.values, label="Aprobadas", color="seagreen")

            # Agregar proporciones sobre las barras de aprobaciones
            for i, (total, aprobadas, prop) in enumerate(zip(conteo_total.values, conteo_aprobadas.values, proporcion.values)):
                plt.text(i, aprobadas + total * 0.03, f"{prop}%", ha='center', va='bottom', fontsize=11, weight='bold', color='black')

            # Estética
            plt.title("📅 Distribución de solicitudes y aprobaciones por día de la semana", fontsize=14)
            plt.xlabel("Día de la semana")
            plt.ylabel("Cantidad de solicitudes")
            plt.xticks(rotation=45)
            plt.legend()
            plt.tight_layout()

            # Mostrar en Streamlit
            st.pyplot(plt)
            
            #Análisis
            st.markdown(
                """
                <div style="font-size:25px">
                    <ul>
                        <li>📅 <strong>Fines de semana</strong> muestran las tasas de aprobación más altas: <strong>71.8%</strong> el domingo y <strong>67.7%</strong> el sábado. Esto sugiere que las decisiones tomadas en estos días son más favorables para los solicitantes.</li>
                        <li>📈 <strong>Días hábiles</strong> mantienen tasas de aprobación más estables, entre <strong>59.0%</strong> y <strong>60.7%</strong>, con un ligero incremento hacia el viernes. Esto podría reflejar una mayor rigurosidad en los procesos durante la semana laboral.</li>
                        <li>🔍 A pesar de que la mayoría de las solicitudes se concentran entre lunes y viernes, los fines de semana presentan una mayor proporción de aprobaciones, lo que podría indicar un cambio en el perfil de solicitante o en la política de evaluación durante esos días.</li>
                    </ul>
                    <p>Este comportamiento puede ser útil para ajustar estrategias de atención, redistribuir recursos operativos o incluso diseñar campañas que aprovechen los días con mayor probabilidad de aprobación.</p>
                </div>
                """,
                unsafe_allow_html=True
            )

    with tab3:
        st.subheader("📈 Evolución de pago de cuotas en el tiempo")

        # Caja de texto para ingresar ID
        cliente_input = st.text_input("Ingresa el ID de la solicitud actual del cliente:")

        # Verificar si el input es numérico
        if cliente_input.strip().isdigit():
            cliente_id = int(cliente_input)

            # Verificar si el ID existe en el DataFrame
            if cliente_id in df_pos["SK_ID_CURR"].values:
                # Filtrar por cliente
                df_cliente = df_pos[df_pos["SK_ID_CURR"] == cliente_id]

                # Crear figura
                fig = go.Figure()

                for sk_prev, sub_df in df_cliente.groupby("SK_ID_PREV"):
                    sub_df = sub_df.sort_values("MONTHS_BALANCE")
                    fig.add_trace(go.Scatter(
                        x=sub_df["MONTHS_BALANCE"],
                        y=sub_df["CNT_INSTALMENT_FUTURE"],
                        mode="lines+markers",
                        name=f"Crédito {sk_prev}"
                    ))

                # Personalizar layout
                fig.update_layout(
                    title="📈 Evolución de pago de cuotas por crédito",
                    xaxis_title="Meses antes de la fecha de la solicitud actual",
                    yaxis_title="Cuotas pendientes",
                    hovermode="x unified",
                    template="plotly_white",
                    legend_title="Créditos",
                    height=450
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("❌ El ID ingresado no se encuentra en los registros.")
        elif cliente_input.strip() != "":
            st.error("⚠️ Por favor ingresa solo números.")