from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy import text
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
sys.path.append('..')
from scripts.function import *
import seaborn as sns
from collections import defaultdict

# Define tus credenciales locales aquí.
# Asegúrate de que las bases de datos 'bronze', 'silver', y 'gold' existan en tu MySQL con el proceso dado en data, y load to sql.
DB_USER = "root"
DB_PASS = "Tu_contraseña" # Reemplaza con tu contraseña
DB_HOST = "localhost"
DB_PORT = "3306"

# Motores para cada capa
try:
    engine_bronze = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/bronze")
    engine_silver = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/silver")
    engine_gold = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/gold")
    print("Motores de base de datos configurados correctamente.")
except Exception as e:  
    print(f"Error al configurar los motores de base de datos: {e}")
    sys.exit(1)

# Limpieza y EDA de application_train

df_train= pd.read_sql("select * from application_train", engine_bronze)
df_train["NAME_TYPE_SUITE"].replace("", "Unaccompanied", inplace=True)
df_train["OCCUPATION_TYPE"].replace("", "Others", inplace=True)
variables=["FONDKAPREMONT_MODE","HOUSETYPE_MODE","WALLSMATERIAL_MODE","EMERGENCYSTATE_MODE"]
for variable in variables:
    df_train[variable].replace("", "not specified", inplace=True)
df_train.DAYS_BIRTH=(df_train.DAYS_BIRTH / 365).astype(np.int64)
df_train.rename(columns={'DAYS_BIRTH': 'YEARS_BIRTH'}, inplace=True)
df_train.DAYS_EMPLOYED.replace({365243:0},inplace=True)

# Subir limpieza a silver
try:
    df_train.to_sql('application_train', con=engine_silver, if_exists="replace", index=False)
    print("Dataframes saved to silver schema successfully.")
except Exception as e:
    print(f"Error saving dataframes to silver schema: {e}")
    sys.exit(1)

# Limpieza y EDA de credit_card_balance y installments_payments

df_credit_data = pd.read_sql("select * from credit_card_balance", engine_bronze)
df_installments = pd.read_sql("select * from installments_payments", engine_bronze)
columnas_float = df_credit_data.select_dtypes(include=['float64']).columns
# Redondear todas las columnas float64 a 2 decimales
df_credit_data[columnas_float] = df_credit_data[columnas_float].round(2)
df_credit_data.drop(columns=['AMT_DRAWINGS_CURRENT', 'CNT_DRAWINGS_CURRENT', 'AMT_DRAWINGS_OTHER_CURRENT', 'SK_DPD_DEF'], inplace=True)
df_credit_data = df_credit_data.rename(columns={'AMT_RECIVABLE': 'AMT_RECEIVABLE'})
obtener_conteo_clientes_unicos(engine_bronze)
# Clientes con saldo a favor
clientes_saldo_a_favor(engine_bronze)
# Clientes con deuda pendiente
clientes_con_deuda(engine_bronze)
# Casos con pagos atrasados
casos_pagos_atrasados(engine_bronze)
# Casos con cargos adicionales
casos_cargos_adicionales(engine_bronze)
# Análisis por estado de contrato
analizar_estado_contrato(engine_bronze)
# Análisis de perfil de clientes - TODOS los clientes
analizar_perfil_clientes(engine_bronze)
df_installments[['AMT_INSTALMENT', 'AMT_PAYMENT']] = df_installments[['AMT_INSTALMENT', 'AMT_PAYMENT']].round(2)
# Convertir las columnas float64 a int
cols_to_convert = ['NUM_INSTALMENT_VERSION', 'DAYS_INSTALMENT', 'DAYS_ENTRY_PAYMENT']
# Asegúrate de que no hay valores nulos
df_installments[cols_to_convert] = df_installments[cols_to_convert].fillna(0).astype(int)
# Total de pagos realizados y promedio por cliente
obtener_pagos_por_cliente(engine_bronze)
# Pagos atrasados: diferencia entre DAYS_ENTRY_PAYMENT y DAYS_INSTALMENT
obtener_resumen_atrasos(engine_bronze)
# Distribución de pagos incompletos
obtener_distribucion_incompletos(engine_bronze)
# Guardar los DataFrames procesados en la base de datos 'bronze' en el esquema 'silver'
try:
    df_credit_data.to_sql("credit_card_balance", engine_silver, if_exists='replace', index=False)
    df_installments.to_sql("installments_payments", engine_silver, if_exists='replace', index=False)
    print("DataFrames guardados exitosamente en la base de datos silver")
except Exception as e:
    print(f"Error al guardar los DataFrames: {e}")

# Limpieza y EDA de previous_application y pos_cash_balance
df_POS = pd.read_sql_table("pos_cash_balance", engine_bronze)
df_previous = pd.read_sql_table("previous_application", engine_bronze)
with engine_bronze.connect() as conn:
    conn.execute(text('ALTER TABLE previous_application MODIFY COLUMN AMT_DOWN_PAYMENT FLOAT;'))

#Reemplazamos los valores vacíos en RATE_DOWN_PAYMENT por 0.0
with engine_bronze.begin() as conn:
    conn.execute(
        text("""
            UPDATE previous_application
            SET RATE_DOWN_PAYMENT = 0.0
            WHERE RATE_DOWN_PAYMENT = '';
        """)
    )
with engine_bronze.connect() as conn:
    conn.execute(text('ALTER TABLE previous_application MODIFY COLUMN RATE_DOWN_PAYMENT FLOAT;'))
#Reemplazamos los valores vacíos en RATE_INTEREST_PRIMARY por 0.0
with engine_bronze.begin() as conn:
    conn.execute(
        text("""
            UPDATE previous_application
            SET RATE_INTEREST_PRIMARY = 0.0
            WHERE RATE_INTEREST_PRIMARY = '';
        """)
    )
#Reemplazamos los valores vacíos en RATE_INTEREST_PRIVILEGED por 0.0
with engine_bronze.begin() as conn:
    conn.execute(
        text("""
            UPDATE previous_application
            SET RATE_INTEREST_PRIVILEGED = 0.0
            WHERE RATE_INTEREST_PRIVILEGED = '';
        """)
    )
#Modificamos el tipo de dato de RATE_INTEREST_PRIMARY y RATE_INTEREST_PRIVILEGED a FLOAT
with engine_bronze.connect() as conn:
    conn.execute(text('ALTER TABLE previous_application MODIFY COLUMN RATE_INTEREST_PRIMARY FLOAT;'))
with engine_bronze.connect() as conn:
    conn.execute(text('ALTER TABLE previous_application MODIFY COLUMN RATE_INTEREST_PRIVILEGED FLOAT;'))
#Reemplazamos los valores vacíos en NAME_TYPE_SUITE por "Unaccompanied"
with engine_bronze.begin() as conn:
    conn.execute(
        text("""
            UPDATE previous_application
            SET NAME_TYPE_SUITE = "Unnancompanied"
            WHERE NAME_TYPE_SUITE = '';
        """)
    )
#Reemplazamos los valores vacíos en PRODUCT_COMBINATION por "Cash"
with engine_bronze.begin() as conn:
    conn.execute(
        text("""
            UPDATE previous_application
            SET PRODUCT_COMBINATION = "Cash"
            WHERE PRODUCT_COMBINATION = '';
        """)
    )
#Reemplazamos los valores vacíos en DAYS_FIRST_DRAWING por 0.0. En este caso no se usa la cláusula WHERE porque se quiere actualizar todos los valores de la columna.
with engine_bronze.begin() as conn:
    conn.execute(
        text("""
            UPDATE previous_application
            SET DAYS_FIRST_DRAWING = 0.0;
        """)
    )
#Modificamos el tipo de dato de DAYS_FIRST_DRAWING a FLOAT
with engine_bronze.connect() as conn:
    conn.execute(text('ALTER TABLE previous_application MODIFY COLUMN DAYS_FIRST_DRAWING FLOAT;'))
#Reemplazamos los valores vacíos en DAYS_FIRST_DUE por 0.0. En este caso no se usa la cláusula WHERE porque se quiere actualizar todos los valores de la columna.
with engine_bronze.begin() as conn:
    conn.execute(
        text("""
            UPDATE previous_application
            SET DAYS_FIRST_DUE = 0.0;
        """)
    )
#Modificamos el tipo de dato de DAYS_FIRST_DUE a FLOAT
with engine_bronze.connect() as conn:
    conn.execute(text('ALTER TABLE previous_application MODIFY COLUMN DAYS_FIRST_DUE FLOAT;'))
#Reemplazamos los valores vacíos en DAYS_LAST_DUE_1ST_VERSION por 0.0. En este caso no se usa la cláusula WHERE porque se quiere actualizar todos los valores de la columna.
with engine_bronze.begin() as conn:
    conn.execute(
        text("""
            UPDATE previous_application
            SET DAYS_LAST_DUE_1ST_VERSION = 0.0;
        """)
    )
#Reemplazamos los valores vacíos en DAYS_LAST_DUE por 0.0. En este caso no se usa la cláusula WHERE porque se quiere actualizar todos los valores de la columna.
with engine_bronze.begin() as conn:
    conn.execute(
        text("""
            UPDATE previous_application
            SET DAYS_LAST_DUE = 0.0;
        """)
    )
#Reemplazamos los valores vacíos en DAYS_TERMINATION por 0.0. En este caso no se usa la cláusula WHERE porque se quiere actualizar todos los valores de la columna.
with engine_bronze.begin() as conn:
    conn.execute(
        text("""
            UPDATE previous_application
            SET DAYS_TERMINATION = 0.0;
        """)
    )
#Modificamos el tipo de dato de DAYS_LAST_DUE_1ST_VERSION a FLOAT
with engine_bronze.connect() as conn:
    conn.execute(text('ALTER TABLE previous_application MODIFY COLUMN DAYS_LAST_DUE_1ST_VERSION FLOAT;'))
#Modificamos el tipo de dato de DAYS_LAST_DUE a FLOAT
with engine_bronze.connect() as conn:
    conn.execute(text('ALTER TABLE previous_application MODIFY COLUMN DAYS_LAST_DUE FLOAT;'))
#Modificamos el tipo de dato de DAYS_FIRST_DUE a FLOAT
with engine_bronze.connect() as conn:
    conn.execute(text('ALTER TABLE previous_application MODIFY COLUMN DAYS_TERMINATION FLOAT;'))
#Reemplazamos los valores vacíos en NFLAG_INSURED_ON_APPROVAL por 0.0. En este caso no se usa la cláusula WHERE porque se quiere actualizar todos los valores de la columna.
with engine_bronze.begin() as conn:
    conn.execute(
        text("""
            UPDATE previous_application
            SET NFLAG_INSURED_ON_APPROVAL = 0.0;
        """)
    )
#Modificamos el tipo de dato de NFLAG_INSURED_ON_APPROVAL a FLOAT
with engine_bronze.connect() as conn:
    conn.execute(text('ALTER TABLE previous_application MODIFY COLUMN NFLAG_INSURED_ON_APPROVAL FLOAT;'))

try:
    df_previous.to_sql('previous_application_silver', engine_silver, if_exists='replace', index=False)
    df_POS.to_sql('pos_cash_balance_silver', engine_silver, if_exists='replace', index=False)
    print("DataFrames guardados exitosamente en la base de datos silver")
except Exception as e:
    print(f"Error al guardar los DataFrames: {e}")  

# Limpieza y EDA de bureau y bureau_balance
df_bureau = pd.read_sql("select * from bureau", engine_bronze)
df_bureau['CREDIT_ACTIVE'] = df_bureau['CREDIT_ACTIVE'].astype('category')
df_bureau['CREDIT_CURRENCY'] = df_bureau['CREDIT_CURRENCY'].astype('category')
df_bureau['CREDIT_TYPE'] = df_bureau['CREDIT_TYPE'].astype('category')

# Convertir columnas numéricas que están como object a float
float_cols = [
    'DAYS_CREDIT_ENDDATE',
    'DAYS_ENDDATE_FACT',
    'AMT_CREDIT_MAX_OVERDUE',
    'AMT_CREDIT_SUM_DEBT',
    'AMT_CREDIT_SUM_LIMIT',
    'AMT_ANNUITY'
]

for col in float_cols:
    df_bureau[col] = pd.to_numeric(df_bureau[col], errors='coerce')

#  ELIMINAR DUPLICADOS
df_bureau = df_bureau.drop_duplicates()

# ELIMINAR COLUMNAS CON >40% NULOS
umbral_nulos = 0.4
df_bureau = df_bureau.loc[:, df_bureau.isnull().mean() < umbral_nulos]

#  RELLENO DE NULOS

# Numéricas → Mediana
num_cols = df_bureau.select_dtypes(include=[np.number]).columns
df_bureau[num_cols] = df_bureau[num_cols].fillna(df_bureau[num_cols].median())

# Categóricas → Moda
cat_cols = df_bureau.select_dtypes(include='category').columns
for col in cat_cols:
    df_bureau[col] = df_bureau[col].fillna(df_bureau[col].mode()[0])

def remove_outliers_iqr(df, col):
    Q1 = df[col].quantile(0.25)
    Q3 = df[col].quantile(0.75)
    IQR = Q3 - Q1
    return df[(df[col] >= Q1 - 1.5*IQR) & (df[col] <= Q3 + 1.5*IQR)]

cols_outliers = ['CREDIT_DAY_OVERDUE', 'AMT_CREDIT_SUM', 'AMT_CREDIT_SUM_DEBT', 'AMT_CREDIT_SUM_OVERDUE']
for col in cols_outliers:
    if col in df_bureau.columns:
        df_bureau = remove_outliers_iqr(df_bureau, col)

columnas_a_eliminar = ['AMT_CREDIT_SUM_OVERDUE', 'AMT_CREDIT_SUM_DEBT', 'CREDIT_DAY_OVERDUE']

# Elimina solo las que existen
columnas_existentes = [col for col in columnas_a_eliminar if col in df_bureau.columns]

# Aplica el drop
df_bureau.drop(columns=columnas_existentes, inplace=True)

df_bureau = df_bureau.rename(columns={"SK_ID_CURR" : "SK_ID_PREV"})
df_bureau = df_bureau.rename(columns={"SK_ID_BUREAU" : "SK_ID_CURR"})

try:
    df_bureau.to_sql('bureau', con=engine_silver, if_exists="replace", index=False)
    print("DataFrame bureau guardado exitosamente en la base de datos silver")
except Exception as e:
    print(f"Error al guardar el DataFrame bureau: {e}")

# Filtrar solo las variables numéricas
df_numericas = df_bureau.select_dtypes(include=['float64', 'int64'])

# Calcular la matriz de correlación
matriz_correlacion = df_numericas.corr()

# Mostrar la matriz numérica (opcional)
print(matriz_correlacion)

# Graficar el mapa de calor (heatmap)
plt.figure(figsize=(12, 8))
sns.heatmap(matriz_correlacion, annot=True, cmap='coolwarm', fmt=".2f", linewidths=0.5)
plt.title('Matriz de Correlación - Variables Numéricas')
plt.show()

# Elimina solo las que existen
columnas_existentes = [col for col in columnas_a_eliminar if col in df_bureau.columns]

# Aplica el drop
df_bureau.drop(columns=columnas_existentes, inplace=True)

# Tabla informativa de las variables
info_tabla = pd.DataFrame({
    'Tipo de Dato': df_bureau.dtypes,
    'Valores Nulos': df_bureau.isnull().sum(),
    'Valores Únicos': df_bureau.nunique(),
})

# Agregar estadísticas numéricas básicas si es variable numérica
stats = df_bureau.describe().T[['mean', 'std', 'min', 'max']]
tabla_variables = info_tabla.merge(stats, left_index=True, right_index=True, how='left')

# Mostrar la tabla informativa
print("\n🔎 Tabla informativa de la base de datos:")
print(tabla_variables)

 #Lista segura con solo columnas que realmente existen

plt.figure(figsize=(8, 4))
sns.histplot(df_bureau['AMT_CREDIT_SUM'], kde=True, bins=30)
plt.title('Distribución del Monto del Crédito')
plt.xlabel('AMT_CREDIT_SUM')
plt.ylabel('Frecuencia')
plt.tight_layout()
plt.show()

plt.figure(figsize=(8, 4))
sns.boxplot(x=df_bureau['AMT_CREDIT_SUM'])
plt.title('Boxplot del Monto del Crédito')
plt.xlabel('AMT_CREDIT_SUM')
plt.tight_layout()
plt.show()

plt.figure(figsize=(10, 5))
sns.boxplot(data=df_bureau, x='CREDIT_TYPE', y='AMT_CREDIT_SUM')
plt.xticks(rotation=45)
plt.title('Monto del Crédito por Tipo de Crédito')
plt.tight_layout()
plt.show()

plt.figure(figsize=(8, 4))
sns.countplot(data=df_bureau, x='CREDIT_TYPE')
plt.xticks(rotation=45)
plt.title('Conteo por Tipo de Crédito')
plt.tight_layout()
plt.show()

chunk_size = 10_000  # Ajusta según tu RAM

query = """
SELECT 
  SK_ID_BUREAU,
  STATUS,
  MONTHS_BALANCE
FROM bronze.bureau_balance
"""

chunks = pd.read_sql(query, engine_bronze, chunksize=chunk_size)

for i, chunk in enumerate(chunks):
    # Aquí haces transformaciones parciales por lote
    print(f"Procesando chunk {i+1} con {len(chunk)} filas")

    # Ejemplo: contar por STATUS por lote
    status_summary = chunk.groupby('STATUS').size()

    # Guardar o agregar a un archivo o base (ejemplo)
    status_summary.to_csv(f"output_chunk_{i+1}.csv")

chunk.to_sql('bureau_balance', con=engine_silver, if_exists="replace", index=False)

# Paso 1: Crear tabla temporal con cambios
query_crear_nueva = text("""
CREATE TABLE bureau_balance_temp AS
SELECT 
    SK_ID_BUREAU AS SK_ID_CURR,
    MONTHS_BALANCE,
    STATUS
FROM bureau_balance;
""")

# Paso 2: Eliminar la tabla original
query_eliminar_original = text("DROP TABLE bureau_balance;")

# Paso 3: Renombrar la tabla temporal
query_renombrar_tabla = text("ALTER TABLE bureau_balance_temp RENAME TO bureau_balance;")

# Ejecutar todo en una única sesión
with engine_silver.begin() as conn:  # begin() hace commit automáticamente
    conn.execute(query_crear_nueva)
    conn.execute(query_eliminar_original)
    conn.execute(query_renombrar_tabla)

# 📊 MÉTRICAS GLOBALES
total_filas = 0
status_counts = defaultdict(int)
min_balance = None
max_balance = None

# 📈 AGRUPACIÓN POR SK_ID_BUREAU
resumen = defaultdict(lambda: {
    'duracion_meses': 0,
    'meses_al_dia': 0,
    'meses_mora': 0,
    'meses_cerrado': 0,
    'meses_desconocido': 0,
    'max_mora': 0,
    'mes_antiguo': 0,
    'mes_reciente': 0
})

for i, chunk in enumerate(pd.read_sql(query, engine_silver, chunksize=chunk_size)):
    total_filas += len(chunk)

    # Conteo por STATUS global
    status_counts_chunk = chunk['STATUS'].value_counts().to_dict()
    for status, count in status_counts_chunk.items():
        status_counts[status] += count

    # Agrupar por SK_ID_BUREAU
    for bureau_id, group in chunk.groupby('SK_ID_BUREAU'):
        r = resumen[bureau_id]
        r['duracion_meses'] += len(group)
        r['meses_al_dia'] += (group['STATUS'] == '0').sum()
        r['meses_mora'] += group['STATUS'].isin(['1', '2', '3', '4', '5']).sum()
        r['meses_cerrado'] += (group['STATUS'] == 'C').sum()
        r['meses_desconocido'] += (group['STATUS'] == 'X').sum()
        
        # Máximo STATUS como número (sólo si numérico)
        max_mora = pd.to_numeric(group['STATUS'], errors='coerce').fillna(0).max()
        r['max_mora'] = max(r['max_mora'], max_mora)

        r['mes_antiguo'] = min(r['mes_antiguo'], group['MONTHS_BALANCE'].min()) if r['duracion_meses'] > len(group) else group['MONTHS_BALANCE'].min()
        r['mes_reciente'] = max(r['mes_reciente'], group['MONTHS_BALANCE'].max())

    print(f"Chunk {i+1} procesado, filas: {len(chunk)}")

# 📄 CONVERTIR A DATAFRAME
df_resumen = pd.DataFrame.from_dict(resumen, orient='index')
df_resumen.index.name = 'SK_ID_BUREAU'
df_resumen.reset_index(inplace=True)

# ✅ GUARDAR RESULTADO
df_resumen.to_csv("resumen_bureau_balance.csv", index=False)

# 🔍 METRICAS GLOBALES
print("\n🔢 Total de filas:", total_filas)
print("\n📊 Frecuencia STATUS:")
print(pd.Series(status_counts))

print("\n📌 Vista previa de resumen:")
print(df_resumen.head())

# 📈 GRAFICO DE STATUS
pd.Series(status_counts).sort_index().plot(kind='bar', title='Distribución de STATUS')
plt.xlabel("STATUS")
plt.ylabel("Frecuencia")
plt.tight_layout()
plt.show()

def simplificar_status(valor):
    if valor in ['1', '2', '3', '4', '5']:
        return 'MORA'
    elif valor == '0':
        return 'AL_DIA'
    elif valor == 'C':
        return 'CERRADO'
    elif valor == 'X':
        return 'DESCONOCIDO'
    else:
        return 'OTRO'

# Aplica al DataFrame
chunk['STATUS_SIMPLIFICADO'] = chunk['STATUS'].apply(simplificar_status)

chunk_size = 10_000
query = "SELECT SK_ID_BUREAU, MONTHS_BALANCE, STATUS FROM bureau_balance"

status_por_mes = []

for chunk in pd.read_sql(query, engine_silver, chunksize=chunk_size):
    chunk['STATUS_SIMPLE'] = chunk['STATUS'].apply(simplificar_status)

    # Agrupar y guardar resultados del chunk
    resumen = chunk.groupby(['MONTHS_BALANCE', 'STATUS_SIMPLE']).size().unstack(fill_value=0)
    status_por_mes.append(resumen)

serie_tiempo_df = pd.concat(status_por_mes).groupby(level=0).sum().sort_index()

plt.figure(figsize=(12, 6))
for col in serie_tiempo_df.columns:
    plt.plot(serie_tiempo_df.index, serie_tiempo_df[col], label=col)

plt.title("Evolución de créditos por STATUS en el tiempo")
plt.xlabel("MONTHS_BALANCE (meses en el pasado)")
plt.ylabel("Cantidad de registros")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# -- crear tablas GOLD con los resultados finales

try:
    print("Loading raw data from Silver layer...")
    df_installments = pd.read_sql("SELECT * FROM installments_payments", engine_silver)
    df_credit_balance = pd.read_sql("SELECT * FROM credit_card_balance", engine_silver)
except Exception as e:
    print(f"Error loading data from Silver layer: {e}")
    raise

df_gold_final = create_active_customer_gold_table(df_inst=df_installments, df_balance=df_credit_balance)
try:
    print("Saving processed data to Gold layer...")
    df_gold_final.to_sql('gold_active_customer_profile', engine_gold, if_exists='replace', index=False)
    print("Data saved successfully to Gold layer.")
    print("\nSample of the final Gold table:")
    print(df_gold_final.head().to_string())
except Exception as e: 
    print(f"Error saving data to Gold layer: {e}")
    raise

df=pd.read_sql_query("SELECT*FROM silver.application_train",engine_silver)

features = [
    "FLAG_OWN_CAR",
    "FLAG_OWN_REALTY",
    "CNT_CHILDREN",
    "AMT_INCOME_TOTAL",
    "AMT_CREDIT",
    "NAME_INCOME_TYPE",
    "NAME_EDUCATION_TYPE",
    "NAME_FAMILY_STATUS",
    "NAME_HOUSING_TYPE",
    "YEARS_BIRTH",
    "DAYS_EMPLOYED",
    "OWN_CAR_AGE",
    "OCCUPATION_TYPE",
]
df=df[features]
df.to_sql("risk_level_data",engine_gold,if_exists="replace",index=False)

#Columnas para gold
df_previous = pd.read_sql("previous_application_silver",engine_silver)
columnas_gold = [
    'SK_ID_CURR',
    'SK_ID_PREV',
    'NAME_CONTRACT_TYPE',
    'AMT_ANNUITY',
    'AMT_APPLICATION',
    'AMT_CREDIT',
    'WEEKDAY_APPR_PROCESS_START',
    'NAME_CONTRACT_STATUS',
    'NAME_CLIENT_TYPE',
    'CHANNEL_TYPE'
]

df_previous_gold = df_previous[columnas_gold]
df_previous_gold

df_POS = pd.read_sql("pos_cash_balance_silver", engine_silver)
df_POS_gold = df_POS[['SK_ID_PREV', 'SK_ID_CURR', 'MONTHS_BALANCE', 'CNT_INSTALMENT', 'CNT_INSTALMENT_FUTURE']]

df_previous_gold.to_sql('previous_application_gold', engine_gold, if_exists='replace', index=False)
df_POS_gold.to_sql('pos_cash_balance_gold', engine_gold, if_exists='replace', index=False)

df_bureau_gold = df_bureau[['SK_ID_CURR', 'SK_ID_PREV', 'CREDIT_TYPE', 'CREDIT_ACTIVE']].copy()

df_bureau_gold.to_sql('bureau', con=engine_gold, if_exists="replace", index=False)

df_creditos = df_bureau[['SK_ID_CURR', 'CREDIT_TYPE', 'CREDIT_ACTIVE']]

# Contamos la frecuencia de cada tipo de crédito por estado (activo/cerrado)
frecuencia = df_creditos.groupby(['CREDIT_TYPE', 'CREDIT_ACTIVE']).size().unstack(fill_value=0)

# Sumamos totales por tipo
frecuencia['TOTAL'] = frecuencia.sum(axis=1)

# Filtramos los tipos de crédito con frecuencia total mayor a un umbral (ej: 5000)
umbral = 5000
frecuencia_filtrada = frecuencia[frecuencia['TOTAL'] > umbral].drop(columns='TOTAL')

# --- TABLA ---
print("\nFrecuencia filtrada de tipos de crédito (más representativos):")
print(frecuencia_filtrada)

# --- GRÁFICO ---
frecuencia_filtrada.plot(kind='bar', stacked=True, figsize=(10, 6))
plt.title('Tipos de Crédito por Estado (solo los más frecuentes)')
plt.xlabel('Tipo de Crédito')
plt.ylabel('Cantidad')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.show()

df_credit_data = pd.read_sql("credit_card_balance", engine_silver)
df_installments = pd.read_sql("installments_payments", engine_silver)
df_previous_gold_model = df_previous[['SK_ID_CURR', 'SK_ID_PREV', 'NAME_CONTRACT_TYPE', 'AMT_APPLICATION', 'AMT_CREDIT', 'NAME_CLIENT_TYPE']]
df_POS_gold_model = df_POS_gold[['SK_ID_CURR', 'SK_ID_PREV', 'CNT_INSTALMENT_FUTURE']]
df_bureau_gold_model = df_bureau_gold.copy()

#tabla para gold
df_model_gold = create_final_ml_gold_table(df_installments=df_installments, df_credit_card=df_credit_data, df_bureau_for_model=df_bureau_gold_model, df_pos=df_POS_gold_model, df_previous=df_previous_gold_model)

df_model_gold.to_sql("model_gold_ID", engine_gold, if_exists="replace", index=False)





