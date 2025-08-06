# applicants.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

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
        En esta sección, podrás explorar el historial de solicitudes de crédito de los clientes,\n incluyendo detalles sobre sus solicitudes de crédito y su estado.
    </div>
    """, unsafe_allow_html=True)
 
    #Cargamos datos de gold
    engine = get_db_engine()
    df_previous = load_gold_data_previous(engine)
    df_pos = load_gold_data_POS(engine)
    
    #Aquí se define la estructura de pestañas para la sección de Aplicantes
    tab1, tab2, = st.tabs(["📊 Información por cliente", "📈 Análisis por métricas generales"])
    
    #Se empieza a trabajar con la primera pestaña
    with tab1:
        st.subheader("🔍 Buscar registros por ID de solicitud")



        #Seleccionamos el tipo de búsqueda
        if df_previous.empty or df_pos.empty:
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
                            "AMT_APPLICATION": "Monto aplicado",
                            "AMT_CREDIT": "Monto aprobado"
                        }
                        df_mostrar = df_filtrado[list(columnas.keys())].rename(columns=columnas)

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

                        df_mostrar["Tipo de contrato"] = df_mostrar["Tipo de contrato"].replace(traducciones_tipo_contrato)
                        df_mostrar["Estado de contrato"] = df_mostrar["Estado de contrato"].replace(traducciones_estado_contrato)

                        # Establecer índice
                        df_mostrar.set_index("ID de solicitud previa", inplace=True)

                        st.dataframe(df_mostrar)

                else:
                    True
            except ValueError:
                st.error("⚠️ El ID ingresado debe ser un número entero.")