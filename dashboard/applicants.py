# applicants.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px

#Funciones de Carga de Datos con Caché

@st.cache_resource
def get_db_engine():
    """Crea y cachea la conexión a la base de datos Gold."""
    try:
        # Asegúrate de que esta cadena de conexión sea correcta para tu sistema
        engine = create_engine("mysql+pymysql://root:3136892780a@localhost/gold")
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

def app():
    
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
    engine = get_db_engine()
    df_previous = load_gold_data_previous(engine)
    # df_pos = load_gold_data_POS(engine)
    
    #Aquí se define la estructura de pestañas para la sección de Aplicantes
    tab1, tab2, = st.tabs(["📊 Información por cliente", "📈 Análisis por métricas generales"])
    
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
    
    #Se empieza a trabajar con la primera pestaña
    with tab1:
        st.subheader("🔍 Buscar registros por ID de solicitud")



        #Seleccionamos el tipo de búsqueda
        if df_previous.empty: # or df_pos.empty:
            st.warning("No hay datos disponibles para mostrar.")
        else:
             tipo_busqueda = st.selectbox("Selecciona tipo de búsqueda", ["Solicitud Actual", "Solicitud Previa"])

        #Si hay datos, se pide el ID de la solicitud
        if tipo_busqueda == "Solicitud Actual":
            id_input = st.text_input("🆔 Ingresa el ID de la solicitud actual", key="curr_input")
            columna_id = "SK_ID_CURR"
            
        else:
            id_input = st.text_input("🆔 Ingresa el ID de la solicitud previa", key="prev_input")
            columna_id = "SK_ID_PREV"
        
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
                            
                        df_line = df_filtrado[[
                            "SK_ID_PREV",
                            "AMT_APPLICATION",
                            "AMT_CREDIT"
                        ]].copy()
                        # Ordenar por ID de solicitud previa
                        df_line.sort_values("SK_ID_PREV", inplace=True)

                        st.markdown("<h3 style='text-align: 'left';'>📈 Comparación entre Monto solicitado y Monto aprobado por solicitud previa</h3>",
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
                            xaxis_title="SK_ID_PREV",
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

                        # Crear columnas para métricas
                        col1, col2, col3 = st.columns(3)

                        # Estilo de caja métrica
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

                        columnas = {
                            "SK_ID_CURR": "ID de solicitud actual",
                            "NAME_CONTRACT_TYPE": "Tipo de contrato",
                            "NAME_CONTRACT_STATUS": "Estado de contrato",
                            "AMT_APPLICATION": "Monto solicitado",
                            "AMT_CREDIT": "Monto aprobado",
                            "AMT_ANNUITY": "Monto anual a pagar",
                            "NAME_CLIENT_TYPE": "Tipo de cliente",
                            "CHANNEL_TYPE": "Canal de solicitud"
                        }
                        
                        df_mostrar_prev = df_filtrado[list(columnas.keys())].rename(columns=columnas)

                        df_mostrar_prev["Tipo de contrato"] = df_mostrar_prev["Tipo de contrato"].replace(traducciones_tipo_contrato)
                        df_mostrar_prev["Estado de contrato"] = df_mostrar_prev["Estado de contrato"].replace(traducciones_estado_contrato)
                        df_mostrar_prev["Tipo de cliente"] = df_mostrar_prev["Tipo de cliente"].replace(traducciones_tipo_cliente)
                        df_mostrar_prev["Canal de solicitud"] = df_mostrar_prev["Canal de solicitud"].replace(traducciones_canal_venta)

                        # Establecer índice
                        df_mostrar_prev.set_index("ID de solicitud actual", inplace=True)

                        st.dataframe(df_mostrar_prev)
            except ValueError:
                st.error("⚠️ El ID ingresado debe ser un número entero.")