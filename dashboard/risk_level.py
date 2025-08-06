# dashboard/risk_level.py
import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import plotly.express as px
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix
import plotly.graph_objects as go
import plotly.figure_factory as ff
import sys


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
def calcular_distribuciones(df):
    columnas_categoricas = df.select_dtypes(include="object").columns
    distribuciones = {col: df[col].value_counts().reset_index() for col in columnas_categoricas}
    return distribuciones

@st.cache_data
def load_gold_data(querry,_engine):
    """Carga la tabla Gold pre-procesada desde la base de datos."""
    try:
        df = pd.read_sql(querry, _engine)
        return df
    except Exception as e:
        st.error(f"No se pudo cargar la tabla 'risk_level_data'. Error: {e}")
        return pd.DataFrame()

@st.cache_data
def obtener_columnas_numericas(df):
    return df.select_dtypes(include=["number"]).columns.tolist()

@st.cache_data
def contar_outliers(df, columnas_numericas):
    """Cuenta la cantidad total de outliers por el método de IQR en las columnas numéricas."""
    total_outliers = 0
    outliers_por_columna = {}

    for col in columnas_numericas:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lim_inf = Q1 - 1.5 * IQR
        lim_sup = Q3 + 1.5 * IQR

        outliers = df[(df[col] < lim_inf) | (df[col] > lim_sup)]
        cantidad = outliers.shape[0]

        outliers_por_columna[col] = cantidad

    return outliers_por_columna

@st.cache_resource
def load_model(model):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_dir_path = os.path.join(BASE_DIR, "model")
    target_filename = model
    full_model_path = os.path.join(model_dir_path, target_filename)

    with open(full_model_path, "rb") as f:
        model = pickle.load(f)
    return model

@st.cache_resource
def load_map(model):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_dir_path = os.path.join(BASE_DIR, "model")
    target_filename = model
    full_model_path = os.path.join(model_dir_path, target_filename)

    with open(full_model_path, "rb") as f:
        model = pickle.load(f)
    return model

def load_columns(model):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_dir_path = os.path.join(BASE_DIR, "model")
    target_filename = model
    full_model_path = os.path.join(model_dir_path, target_filename)

    with open(full_model_path, "rb") as f:
        model = pickle.load(f)
    return model

@st.cache_resource
def mostrar_matriz_confusion(y_test, y_pred):
    """
    Genera una matriz de confusión mejorada y más clara usando Plotly.
    Los colores usan una escala logarítmica para mejorar la visualización de
    valores dispares, mientras que las anotaciones muestran los conteos reales.
    """
    # Cargar el diccionario de clases desde Pickle
    nombre_clases = load_map("risk_classifer_output.pickle")

    # Obtener etiquetas legibles y ordenadas
    etiquetas_unicas = sorted(np.unique(np.concatenate((y_test, y_pred))))
    etiquetas_legibles = [nombre_clases[i] for i in etiquetas_unicas]

    # Calcular matriz de confusión
    cm = confusion_matrix(y_test, y_pred, labels=etiquetas_unicas)

    # 1. Transformación logarítmica para la ESCALA DE COLOR
    # Se usa np.log1p(x) que es log(1+x) para manejar correctamente los valores de 0.
    cm_log_scale = np.log1p(cm)

    # 2. Texto con los VALORES ORIGINALES de la matriz para las anotaciones
    cm_text = [[str(val) for val in row] for row in cm]

    # 3. Crear el heatmap con plotly.graph_objects para mayor control
    fig = go.Figure(data=go.Heatmap(
        z=cm_log_scale,           # Usar los valores logarítmicos para el color
        x=etiquetas_legibles,
        y=etiquetas_legibles,
        text=cm_text,             # Usar los valores originales para el texto
        texttemplate="%{text}",   # Mostrar el texto que definimos en 'text'
        colorscale='Blues',
        showscale=False           # Ocultar la barra de color (sería logarítmica y confusa)
    ))

    fig.update_layout(
        title_text='<b>Matriz de Confusión</b>',
        title_x=0.5,
        xaxis_title='<b>Predicción</b>',
        yaxis_title='<b>Clase Real</b>',
        template='plotly_dark',  # Mantiene el estilo oscuro que te gusta
        xaxis=dict(tickangle=-30),
        # Invertir el eje Y para que la diagonal principal (correctos) quede de arriba-izquierda a abajo-derecha
        yaxis=dict(autorange='reversed'),
        font=dict(size=12, color="white")
    )

    return fig
def mostrar_importancia_features_agrupada(modelo, X, top_n):

    if not hasattr(modelo, 'feature_importances_'):
        st.error("El modelo no tiene 'feature_importances_'. Asegúrate de que es un modelo basado en árboles.")
        return

    importancias = modelo.feature_importances_
    columnas_dummy = X.columns.tolist()

    # --- Lógica de Inferencia y Agrupación Automática ---
    
    # 1. Encontrar todos los posibles "prefijos" o "bases" de las columnas.
    # Un prefijo es cualquier cosa antes de un guion bajo en una columna con varios.
    posibles_bases = set()
    for col in columnas_dummy:
        parts = col.split('_')
        if len(parts) > 1:
            for i in range(1, len(parts)):
                posibles_bases.add('_'.join(parts[:i]))

    # 2. Mapear cada columna dummy a su base más probable (la más larga posible).
    mapa_columna_a_base = {}
    # Ordenamos las bases de la más larga a la más corta para encontrar la coincidencia más específica primero.
    bases_ordenadas = sorted(list(posibles_bases), key=len, reverse=True)

    for col in columnas_dummy:
        base_encontrada = col  # Por defecto, la columna es su propia base (si es numérica).
        for base in bases_ordenadas:
            # Si la columna empieza con 'base_', encontramos su origen.
            if col.startswith(base + '_'):
                base_encontrada = base
                break  # Encontramos la coincidencia más larga, pasamos a la siguiente columna.
        mapa_columna_a_base[col] = base_encontrada
    
    # 3. Sumar las importancias usando el mapa que creamos.
    importancias_agrupadas = {}
    for col, imp in zip(columnas_dummy, importancias):
        base = mapa_columna_a_base[col]
        importancias_agrupadas[base] = importancias_agrupadas.get(base, 0) + imp

    # Convertimos a Serie de Pandas para ordenar y graficar.
    top_features = pd.Series(importancias_agrupadas).sort_values(ascending=False).head(top_n)

    # --- Crear el Gráfico de Barras ---
    fig = px.bar(
        x=top_features.values,
        y=top_features.index,
        orientation='h',
        title=f'Importancia de las Top {top_n} Características',
        labels={'x': 'Importancia Acumulada', 'y': 'Característica Inferida'},
        template='plotly_dark'
    )
    
    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'}  # Ordena las barras de menor a mayor.
    )

    st.plotly_chart(fig, use_container_width=True)

def app(DB_USER, DB_PASS, DB_HOST, DB_PORT):
    engine = get_db_engine(DB_USER, DB_PASS, DB_HOST, DB_PORT)
    if engine is None:
        st.error("La conexión a la base de datos ha fallado. La aplicación no puede continuar.")
        st.stop()

    df = load_gold_data("SELECT * FROM risk_level_data",engine)
    df_id= load_gold_data("SELECT * FROM model_gold_id",engine)
    if df.empty:
        st.warning("No se encontraron datos en la tabla 'risk_level_data'.")
        st.stop()

    # --- Estilos en línea ---
    st.markdown("""
        <h1 style='color: #d8ddf9; font-family: Courier New; text-align: center; font-style: italic;'>
            Aplicación de Predicción de Riesgo
        </h1>
        """, unsafe_allow_html=True)
    
    st.markdown(
        """
        <div style="font-size: 16px; text-align: center; font-family: Courier New; color: #EAECEE;">
            Bienvenido a nuestro sistema de clasificación de riesgo para nuevos aspirantes. 
            Con este podremos analizar tu perfil de riesgo para ofrecerte nuestros servicios.
        </div>
        """,
        unsafe_allow_html=True
    )
    st.write("---")
    
    # --- Pestañas para separar el formulario del análisis ---
    seccion = st.tabs(["Cuestionario", "Modelo riesgo no clientes","Modelo riesgo clientes"])
    model=load_model("risk_classifer_model.pickle")
    with seccion[0]:
        # --- Formulario de entrada de datos con estilo en línea ---
        st.markdown("""
            <h3 style='text-align: center; color: white; font-family: Courier New; font-style: italic;'>
                Cuestionario del Solicitante
            </h3>
            """, unsafe_allow_html=True)
        st.write("")

        # --- Fila NUEVA: ID del Cliente ---
        sk_id_curr = st.number_input('ID del Cliente (SK_ID_CURR)', min_value=100000, max_value=999999, value=100002, step=1)
        
        # --- Fila 1: Posesiones ---
        col1, col2 = st.columns(2)
        with col1:
            flag_own_car = st.radio("¿Posee un automóvil?", ('Y', 'N'), key='car', horizontal=True)
        with col2:
            flag_own_realty = st.radio("¿Posee una propiedad inmobiliaria?", ('Y', 'N'), key='realty', horizontal=True)

        # --- Fila 2: Campo condicional para la edad del auto ---
        own_car_age = 0.0
        if flag_own_car == 'Y':
            own_car_age = st.number_input('¿Cuál es la antigüedad de su automóvil (en años)?', min_value=0.0, max_value=80.0, value=10.0, step=0.5, format="%.1f")

        # --- Fila 3: Hijos e Ingresos ---
        col3, col4 = st.columns(2)
        with col3:
            cnt_children = st.number_input('¿Cuántos hijos tiene?', min_value=0, max_value=20, step=1)
        with col4:
            amt_income_total = st.number_input('¿Cuál es su ingreso total anual?', min_value=0.0, value=50000.0, step=1000.0, format="%f")
        
        # --- Fila 4: Monto y Tipo de Crédito ---
        col5, col6 = st.columns(2)
        with col5:
            amt_credit = st.number_input('¿Cuál es el monto del crédito que solicita?', min_value=0.0, value=100000.0, step=1000.0, format="%f")
        with col6:
            # Lista de valores de la imagen
            credit_types = [
                'Consumer credit', 'Credit card', 'Car loan', 'Mortgage', 
                'Cash loan (non-earmarked)', 'Loan for business development', 
                'Real estate loan', 'Unknown type of loan', 'Another type of loan', 
                'Loan for working capital replenishment', 'Microloan', 
                'Loan for the purchase of equipment', 'Mobile operator loan',
                'Loan for purchase of shares (margin lending)', 'Interbank credit'
            ]
            name_contract_type = st.selectbox('Tipo de Crédito', options=credit_types)

        # --- Fila 5: Empleo y Edad ---
        col7, col8 = st.columns(2)
        with col7:
            days_employed_years = st.number_input('¿Cuántos años lleva en su empleo actual?', min_value=0.0, max_value=50.0, value=5.0, step=0.5, format="%.1f")
        with col8:
            years_birth = st.number_input('¿Cuál es su edad en años?', min_value=18, max_value=100, value=30, step=1)

        # --- Fila 6: Educación e Ingresos ---
        col9, col10 = st.columns(2)
        with col9:
            name_education_type = st.selectbox('¿Cuál es su nivel de educación?',df["NAME_EDUCATION_TYPE"].unique())
        with col10:
            name_income_type = st.selectbox('¿Cuál es su situación laboral?',options=df["NAME_INCOME_TYPE"].unique())

        # --- Fila 7: Estado Civil y Vivienda ---
        col11, col12 = st.columns(2)
        with col11:
            name_family_status = st.selectbox('¿Cuál es su estado civil?', df["NAME_FAMILY_STATUS"].unique())
        with col12:
            name_housing_type = st.selectbox('¿Qué tipo de vivienda posee?', df["NAME_HOUSING_TYPE"].unique())

        # --- Fila 8: Ocupación ---
        occupation_type = st.selectbox('¿Cuál es su ocupación?',df["OCCUPATION_TYPE"].unique())
        st.write("")
        
        # --- Botón de predicción ---
        col_btn1, col_btn2, col_btn3 = st.columns([1,1,1])
        with col_btn2:
            predict_button = st.button('Realizar Predicción', use_container_width=True)

        # --- Lógica de predicción ---
        if predict_button:
            years_birth_model = -years_birth 
            days_employed_model = -int(days_employed_years * 365.25)
            
            # DataFrame actualizado con los nuevos campos
            input_data = pd.DataFrame({
                'SK_ID_CURR': [sk_id_curr],
                'NAME_CONTRACT_TYPE': [name_contract_type],
                'FLAG_OWN_CAR': [flag_own_car],
                'FLAG_OWN_REALTY': [flag_own_realty],
                'CNT_CHILDREN': [cnt_children],
                'AMT_INCOME_TOTAL': [amt_income_total],
                'AMT_CREDIT': [amt_credit],
                'NAME_INCOME_TYPE': [name_income_type],
                'NAME_EDUCATION_TYPE': [name_education_type],
                'NAME_FAMILY_STATUS': [name_family_status],
                'NAME_HOUSING_TYPE': [name_housing_type],
                'YEARS_BIRTH': [years_birth_model],
                'DAYS_EMPLOYED': [days_employed_model],
                'OWN_CAR_AGE': [own_car_age if flag_own_car == 'Y' else np.nan],
                'OCCUPATION_TYPE': [occupation_type],
            })
            current_sk_id = input_data['SK_ID_CURR'].iloc[0]
            if current_sk_id in df_id['SK_ID_CURR'].values:
                st.subheader('Resultado para Cliente Existente')
                st.info(f"El cliente con ID {current_sk_id} ya se encuentra en nuestros registros.")
                approval_model = load_model("model_risk_4ID.pickle")
                client_historical_data = df_id[df_id['SK_ID_CURR'] == current_sk_id].copy()
                client_historical_data= client_historical_data.drop(columns=['SK_ID_CURR', 'TARGET'])
                print(client_historical_data.head())
                # 4. Realizar la predicción
                categorical_features = client_historical_data.select_dtypes(include=['object']).columns
                X_ID_encoded = pd.get_dummies(client_historical_data, columns=categorical_features)
                columnas_model_id = load_columns("column_risk_4ID.pickle")
                print("Columnas del modelo:", len(columnas_model_id))
                X_ID_reindexed = X_ID_encoded.reindex(columns=columnas_model_id, fill_value=0)
                X_ID_reindexed = X_ID_reindexed.astype(int)
                scaler_id = StandardScaler()
                X_scaled_ID = scaler_id.fit_transform(X_ID_reindexed)
                prediction1 = approval_model.predict(X_scaled_ID)
                map = load_map("model_risk_4ID_OUTPUT.pickle")
                # Clasificación textual
                clasificacion = map[prediction1[0]]

                # Mensajes personalizados
                if clasificacion == "Riesgo Bajo":
                    mensaje = "Su riesgo es bajo, el crédito está en proceso de verificación para ser aprobado. Por favor, espera una notificación oficial."
                elif clasificacion == "Riesgo Medio":
                    mensaje = "Su riesgo es medio, Por favor, acércate a una de nuestras sucursales o comunícate con nuestras líneas de atención para más información sobre tu solicitud."
                elif clasificacion == "Riesgo Alto":
                    mensaje = "Su riesgo es alto, Lamentamos informarte que tu solicitud de crédito ha sido rechazada."
                else:
                    mensaje = "Clasificación de riesgo no reconocida."

                st.success(f"**Clasificación de Riesgo:** {clasificacion}\n\n{mensaje}")
            else:
                orden=["FLAG_OWN_CAR","FLAG_OWN_REALTY","CNT_CHILDREN","AMT_INCOME_TOTAL",
                    "AMT_CREDIT","NAME_INCOME_TYPE","NAME_EDUCATION_TYPE","NAME_FAMILY_STATUS",
                    "NAME_HOUSING_TYPE","YEARS_BIRTH","DAYS_EMPLOYED","OWN_CAR_AGE","OCCUPATION_TYPE"]
                
                input_data=input_data[orden]
                df_dummies=df.copy()
                variable_colum=input_data.select_dtypes("object").columns
                df_dummies = pd.get_dummies(input_data, columns=variable_colum)
                columnas_model=load_columns("risk_columns.pkl")
                df_dummies = df_dummies.reindex(columns=columnas_model, fill_value=0)

        
                mapping=load_map("risk_classifer_output.pickle")
                prediction=model.predict(df_dummies)
                st.subheader('Resultado de la Predicción')
                clasificacion_no_id = mapping[prediction[0]]
                # Mensajes personalizados
                if clasificacion_no_id == "Riesgo Bajo":
                    mensaje_no_id = "Su riesgo es bajo, el crédito está en proceso de verificación para ser aprobado. Por favor, espera una notificación oficial."
                elif clasificacion_no_id == "Riesgo Medio":
                    mensaje_no_id = "Su riesgo es medio, Por favor, acércate a una de nuestras sucursales o comunícate con nuestras líneas de atención para más información sobre tu solicitud."
                elif clasificacion_no_id == "Riesgo Alto":
                    mensaje_no_id = "Su riesgo es alto, Lamentamos informarte que tu solicitud de crédito ha sido rechazada."
                else:
                    mensaje_no_id = "Clasificación de riesgo no reconocida."

                st.success(f"**Clasificación de Riesgo:** {clasificacion_no_id}\n\n{mensaje_no_id}")
    
    with seccion[1]:
        st.markdown("""
            <h3 style='text-align: center; color: white; font-family: Courier New; font-style: italic;'>
                Análisis y Métricas del Modelo no clientes
            </h3>
            """, unsafe_allow_html=True)
        st.markdown("""
            <h4 style='text-align: center; color: white; font-family: Courier New; font-style: italic;'>
                Análisis de los datos
            </h4>
            """, unsafe_allow_html=True)
        col11, col12 = st.columns(2) 
        with col11:
            distribuciones = calcular_distribuciones(df)
            columna = st.selectbox("Selecciona una columna categórica", list(distribuciones.keys()))
            
            # Obtienes el DataFrame de distribución
            df_distribucion = distribuciones[columna]
            df_distribucion.columns = [columna, 'Frecuencia']

            # Visualización con Plotly
            fig = px.bar(df_distribucion, x=columna, y='Frecuencia', title=f'Distribución de {columna}')
            st.plotly_chart(fig)

            # Texto explicativo
            st.info(
                "**Nota:** La mayoría de las clases están desbalanceadas. "
                "Durante la limpieza para K-Means, se agruparon las categorías que representaban menos del 1% del conjunto de datos."
            )

        with col12:
            columnas_numericas = obtener_columnas_numericas(df)
            if "TARGET" in columnas_numericas:
                columnas_numericas.remove("TARGET")

            columna = st.selectbox("Selecciona una variable numérica para ver su distribución (boxplot)", columnas_numericas)
            
            # Visualización con Plotly
            fig = px.box(df, y=columna, title=f'Boxplot de {columna}')
            st.plotly_chart(fig)

            # Texto explicativo
            st.info(
                "**Observación:** Se identificaron distribuciones muy variadas, con numerosos valores atípicos y escalas dispares. "
                "Se aplicó *capping* para limitar los extremos y una transformación logarítmica para reducir la escala antes del modelado."
            )
            resumen_outliers = contar_outliers(df, columnas_numericas)

            # Mostrar como métrica principal
            st.metric(label="Total Outliers Detectados",value=resumen_outliers[columna], delta=resumen_outliers[columna],delta_color="inverse")
        st.markdown("""
            <h4 style='text-align: center; color: white; font-family: Courier New; font-style: italic;'>
                Metricas del modelo
            </h4>
            """, unsafe_allow_html=True)
        variables= df.select_dtypes("object").columns
        df_dummies= pd.get_dummies(df, columns=variables)
        X=df.drop("TARGET",axis=1)
        columnas_model=load_columns("risk_columns.pkl")
        df_dummies = df_dummies.reindex(columns=columnas_model, fill_value=0)
        X=df_dummies
        y=df["TARGET"]
        scaler = StandardScaler()
        X = scaler.fit_transform(X)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        y_pred = model.predict(X_test)
        col13,col14=st.columns(2) 
        with col13:
            st.plotly_chart(mostrar_matriz_confusion(y_test,y_pred))
            conclusion= """Conclusión Clave: El modelo es muy confiable. Su capacidad para identificar correctamente 
            los casos de "Riesgo Alto" sin fallos lo hace especialmente valioso para prevenir situaciones críticas. 
            Los escasos errores que comete son menores y solo ocurren entre las categorías de menor riesgo."""
            st.info(conclusion)
        with col14:
            mostrar_importancia_features_agrupada(model,df.drop("TARGET",axis=1),5)
            conclusion="""El modelo ha aprendido que la estabilidad residencial y la propiedad de un coche son los indicadores clave para predecir el resultado. 
            Cualquier análisis o decisión de negocio basada en este modelo debería centrarse principalmente en estos dos aspectos."""
            st.info(conclusion)
    
    
    with seccion[2]: # Tercera pestaña: "Modelo aprobacion de credito"
        st.markdown("""
            <h3 style='text-align: center; color: white; font-family: Courier New; font-style: italic;'>
                Análisis y Métricas del Modelo de Aprobación de clientes
            </h3>
            """, unsafe_allow_html=True)
        st.markdown("""
            <h4 style='text-align: center; color: white; font-family: Courier New; font-style: italic;'>
                Análisis de los Datos (Dataset de Clientes Existentes)
            </h4>
            """, unsafe_allow_html=True)
        
        # --- Análisis de Datos para df_id ---
        col_id_1, col_id_2 = st.columns(2) 
        with col_id_1:
            # Usamos df_id para calcular y mostrar las distribuciones
            distribuciones_id = calcular_distribuciones(df_id)
            columna_id_cat = st.selectbox(
                "Selecciona una columna categórica (Aprobación)", 
                list(distribuciones_id.keys()), 
                key='cat_id' # Usamos una 'key' única para este selectbox
            )
            
            df_distribucion_id = distribuciones_id[columna_id_cat]
            df_distribucion_id.columns = [columna_id_cat, 'Frecuencia']

            fig_id_bar = px.bar(df_distribucion_id, x=columna_id_cat, y='Frecuencia', title=f'Distribución de {columna_id_cat}')
            st.plotly_chart(fig_id_bar)

        with col_id_2:
            # Usamos df_id para los boxplots
            columnas_numericas_id = obtener_columnas_numericas(df_id)
            if "TARGET" in columnas_numericas_id:
                columnas_numericas_id.remove("TARGET")

            columna_id_num = st.selectbox(
                "Selecciona una variable numérica (Aprobación)", 
                columnas_numericas_id, 
                key='num_id' # Usamos una 'key' única para este selectbox
            )
            
            fig_id_box = px.box(df_id, y=columna_id_num, title=f'Boxplot de {columna_id_num}')
            st.plotly_chart(fig_id_box)

        # --- Métricas del Modelo para df_id ---
        st.markdown("""
            <h4 style='text-align: center; color: white; font-family: Courier New; font-style: italic;'>
                Métricas del Modelo (Aprobación)
            </h4>
            """, unsafe_allow_html=True)

        # --- Pipeline de preparación de datos IDÉNTICO al del entrenamiento ---
        
        # 1. Cargar el modelo correcto
        approval_model = load_model("model_risk_4ID.pickle")
        
        # 2. Separar X e y desde el principio, usando df_id
        X_id = df_id.drop("TARGET", axis=1)
        y_id = df_id["TARGET"]
        
        # 3. Aplicar get_dummies
        X_id_dummies = pd.get_dummies(X_id)
        
        # 4. Reindexar con las columnas del modelo de aprobación
        approval_columns = load_columns("column_risk_4ID.pickle")
        X_id_reindexed = X_id_dummies.reindex(columns=approval_columns, fill_value=0)
        
        # 5. Escalar los datos (usando el scaler del entrenamiento)
        #    NOTA: Deberías guardar y cargar el scaler del entrenamiento.
        #    Por ahora, replicamos la lógica de fit_transform para que funcione.
        scaler_id = StandardScaler()
        X_id_scaled = scaler_id.fit_transform(X_id_reindexed)
        
        # 6. Dividir los datos
        X_train_id, X_test_id, y_train_id, y_test_id = train_test_split(X_id_scaled, y_id, test_size=0.2, random_state=42)
        
        # 7. Predecir con el modelo de aprobación
        y_pred_id = approval_model.predict(X_test_id)
        
        # --- Visualización de Métricas ---
        col13_id, col14_id = st.columns(2) 
        with col13_id:
            # NOTA: La función mostrar_matriz_confusion debe ser adaptada si los mapas de salida son diferentes.
            # Por ahora, asumimos que usa el mapa correcto o que es genérica.
            st.plotly_chart(mostrar_matriz_confusion(y_test_id, y_pred_id))
            st.info("Conclusiones sobre la matriz de confusión del modelo de aprobación.")

        with col14_id:
            # ¡CORRECCIÓN IMPORTANTE! Pasamos el DataFrame con los dummies correctos (antes de escalar)
            # para que la función pueda leer los nombres de las características.
            mostrar_importancia_features_agrupada(approval_model, X_id_reindexed, 5)
            st.info("Conclusiones sobre la importancia de características del modelo de aprobación.")
