import pandas as pd
import numpy as np
from sqlalchemy import create_engine

def prepare_features_for_modeling(df_balance, df_inst, 
                                  umbral_pago=0.0, umbral_cargo=0.0, umbral_balance=0.0):
    """
    Prepara un dataset 'gold' con features relevantes para modelado de riesgo crediticio,
    combinando indicadores desde credit_card_balance y agregaciones inteligentes desde installments_payments.

    Parámetros:
    ----------
    df_balance : pandas.DataFrame
        Dataset de credit_card_balance.

    df_inst : pandas.DataFrame
        Dataset de installments_payments.

    umbral_pago : float
        Umbral adicional para considerar pagos atrasados.

    umbral_cargo : float
        Umbral adicional para considerar cargos adicionales.

    umbral_balance : float
        Umbral mínimo en saldo a favor.

    Retorna:
    --------
    df_gold : pandas.DataFrame
        Dataset por cliente con variables transformadas para modelado.
    """

    df = df_balance.copy()
    df_inst = df_inst.copy()

    # --- 1. Features desde credit_card_balance (todo en mayúsculas)
    df['HAS_CREDIT_BALANCE'] = (df['AMT_RECEIVABLE'] < -umbral_balance).astype(int)
    df['HAS_LATE_PAYMENTS'] = (df['AMT_PAYMENT_TOTAL_CURRENT'] > df['AMT_PAYMENT_CURRENT'] + umbral_pago).astype(int)
    df['HAS_ADDITIONAL_CHARGES'] = (df['AMT_TOTAL_RECEIVABLE'] > df['AMT_RECEIVABLE'] + umbral_cargo).astype(int)
    df['CREDIT_BALANCE_AMOUNT'] = (-df['AMT_RECEIVABLE']).clip(lower=0)
    df['DEBT_BALANCE_AMOUNT'] = df['AMT_RECEIVABLE'].clip(lower=0)

    # Agrupación por cliente
    base_flags = ['HAS_CREDIT_BALANCE', 'HAS_LATE_PAYMENTS', 'HAS_ADDITIONAL_CHARGES']
    df_core = df.groupby('SK_ID_CURR')[base_flags].max().reset_index()

    # --- 2. Features desde installments_payments (renombrado en mayúsculas)
    df_inst['DELAY'] = df_inst['DAYS_ENTRY_PAYMENT'] - df_inst['DAYS_INSTALMENT']
    df_inst['PAYMENT_RATIO'] = df_inst['AMT_PAYMENT'] / df_inst['AMT_INSTALMENT'].replace(0, 1)
    df_inst['IS_LATE'] = (df_inst['DELAY'] > 0).astype(int)
    df_inst['IS_MISSED'] = (df_inst['AMT_PAYMENT'] == 0).astype(int)
    df_inst['IS_UNDERPAID'] = (df_inst['AMT_PAYMENT'] < df_inst['AMT_INSTALMENT']).astype(int)
    df_inst['IS_OVERPAID'] = (df_inst['AMT_PAYMENT'] > df_inst['AMT_INSTALMENT']).astype(int)

    ag = df_inst.groupby('SK_ID_CURR').agg(
        NUM_LOANS_TOTAL=('SK_ID_PREV', 'count'),
        AVG_PAYMENT_RATIO=('PAYMENT_RATIO', 'mean'),
        FRAC_PAYMENTS_LATE=('IS_LATE', 'mean'),
        AVG_DELAY_DAYS=('DELAY', lambda x: x[x > 0].mean() if (x > 0).any() else 0.0),
        MAX_DELAY_DAYS=('DELAY', 'max'),
        FRAC_MISSED_PAYMENTS=('IS_MISSED', 'mean'),
        FRAC_UNDERPAID=('IS_UNDERPAID', 'mean'),
        FRAC_OVERPAID=('IS_OVERPAID', 'mean'),
        LAST_ENTRY_DAYS=('DAYS_ENTRY_PAYMENT', lambda x: x.min() if x.notna().any() else np.nan)
    ).reset_index()

    # Recency: convertir días negativos en positivos
    ag['RECENCY_DAYS'] = -ag['LAST_ENTRY_DAYS']

    # --- 3. Merge datasets (cliente final)
    df_gold = df_core.merge(ag.drop(columns='LAST_ENTRY_DAYS'), on='SK_ID_CURR', how='left').fillna({
        'NUM_LOANS_TOTAL': 0,
        'AVG_PAYMENT_RATIO': 1.0,
        'FRAC_PAYMENTS_LATE': 0.0,
        'AVG_DELAY_DAYS': 0.0,
        'MAX_DELAY_DAYS': 0.0,
        'FRAC_MISSED_PAYMENTS': 0.0,
        'FRAC_UNDERPAID': 0.0,
        'FRAC_OVERPAID': 0.0,
        'RECENCY_DAYS': 999.0
    })

    # --- 4. Prints de control
    print("\n== Primeras filas del dataset preparado (GOLD) ==")
    print(df_gold.head())

    print("\n== Distribución de variables clave ==")
    print(df_gold[['NUM_LOANS_TOTAL', 'FRAC_PAYMENTS_LATE', 'AVG_PAYMENT_RATIO', 'RECENCY_DAYS']].describe())

    return df_gold


def clientes_saldo_a_favor(engine):
    """
    Consulta la cantidad y el porcentaje de registros en los que los clientes tienen saldo a favor 
    (es decir, `AMT_RECIVABLE < 0`) en la tabla `credit_card_balance`.

    Parámetros:
    ----------
    engine : sqlalchemy.engine.base.Engine
        Conexión activa a la base de datos.

    Retorna:
    -------
    pandas.DataFrame
        Contiene:
        - total_clientes_credito : cantidad de registros con saldo a favor
        - porcentaje : porcentaje respecto al total de registros
    """
    query = """
    SELECT COUNT(*) as total_clientes_credito,
           COUNT(*) * 100.0 / (SELECT COUNT(*) FROM credit_card_balance) as porcentaje
    FROM credit_card_balance 
    WHERE AMT_RECIVABLE < 0
    """
    result = pd.read_sql(query, engine)
    print(f"Clientes con saldo a favor: {result['total_clientes_credito'].iloc[0]:,} ({result['porcentaje'].iloc[0]:.2f}%)")
    return result


def clientes_con_deuda(engine):
    """
    Consulta la cantidad y el porcentaje de registros en los que los clientes tienen deuda pendiente 
    (`AMT_RECIVABLE > 0`) en la tabla `credit_card_balance`.

    Parámetros:
    ----------
    engine : sqlalchemy.engine.base.Engine

    Retorna:
    -------
    pandas.DataFrame
        Contiene:
        - total_clientes_deuda : cantidad de registros con deuda
        - porcentaje : porcentaje respecto al total de registros
    """
    query = """
    SELECT COUNT(*) as total_clientes_deuda,
           COUNT(*) * 100.0 / (SELECT COUNT(*) FROM credit_card_balance) as porcentaje
    FROM credit_card_balance 
    WHERE AMT_RECIVABLE > 0
    """
    result = pd.read_sql(query, engine)
    print(f"Clientes con deuda pendiente: {result['total_clientes_deuda'].iloc[0]:,} ({result['porcentaje'].iloc[0]:.2f}%)")
    return result


def casos_pagos_atrasados(engine):
    """
    Consulta la cantidad y el porcentaje de registros donde se detectan pagos atrasados, es decir, 
    cuando `AMT_PAYMENT_TOTAL_CURRENT > AMT_PAYMENT_CURRENT`.

    Parámetros:
    ----------
    engine : sqlalchemy.engine.base.Engine

    Retorna:
    -------
    pandas.DataFrame
        Contiene:
        - total_pagos_atrasados : cantidad de registros con pagos mayores a lo esperado
        - porcentaje : porcentaje respecto al total de registros
    """
    query = """
    SELECT COUNT(*) as total_pagos_atrasados,
           COUNT(*) * 100.0 / (SELECT COUNT(*) FROM credit_card_balance) as porcentaje
    FROM credit_card_balance 
    WHERE AMT_PAYMENT_TOTAL_CURRENT > AMT_PAYMENT_CURRENT
    """
    result = pd.read_sql(query, engine)
    print(f"Casos con pagos atrasados: {result['total_pagos_atrasados'].iloc[0]:,} ({result['porcentaje'].iloc[0]:.2f}%)")
    return result


def casos_cargos_adicionales(engine):
    """
    Consulta la cantidad y el porcentaje de registros con cargos adicionales, es decir, 
    cuando `AMT_TOTAL_RECEIVABLE > AMT_RECIVABLE`.

    Parámetros:
    ----------
    engine : sqlalchemy.engine.base.Engine

    Retorna:
    -------
    pandas.DataFrame
        Contiene:
        - total_cargos_adicionales : cantidad de registros con cargos adicionales
        - porcentaje : porcentaje respecto al total de registros
    """
    query = """
    SELECT COUNT(*) as total_cargos_adicionales,
           COUNT(*) * 100.0 / (SELECT COUNT(*) FROM credit_card_balance) as porcentaje
    FROM credit_card_balance 
    WHERE AMT_TOTAL_RECEIVABLE > AMT_RECIVABLE
    """
    result = pd.read_sql(query, engine)
    print(f"Casos con cargos adicionales: {result['total_cargos_adicionales'].iloc[0]:,} ({result['porcentaje'].iloc[0]:.2f}%)")
    return result


def obtener_conteo_clientes_unicos(engine):
    """
    Ejecuta una consulta SQL sobre la tabla `credit_card_balance` para obtener:
    - El total de clientes únicos (`SK_ID_CURR`)
    - El total de registros en la tabla
    - El promedio de registros por cliente

    Parámetros:
    ----------
    engine : sqlalchemy.engine.base.Engine
        Conexión activa a la base de datos.

    Retorna:
    -------
    pandas.DataFrame
        Un DataFrame con una sola fila que contiene:
        - total_clientes_unicos
        - total_registros
        - promedio_registros_por_cliente
    """
    query = """
    SELECT 
        COUNT(DISTINCT SK_ID_CURR) as total_clientes_unicos,
        COUNT(*) as total_registros,
        COUNT(*) / COUNT(DISTINCT SK_ID_CURR) as promedio_registros_por_cliente
    FROM credit_card_balance
    """

    try:
        df = pd.read_sql(query, engine)

        print("=== CONTEO DE CLIENTES ÚNICOS ===")
        print(f"Total de clientes únicos: {df['total_clientes_unicos'].iloc[0]:,}")
        print(f"Total de registros: {df['total_registros'].iloc[0]:,}")
        print(f"Promedio de registros por cliente: {df['promedio_registros_por_cliente'].iloc[0]:.1f}")

        return df

    except Exception as e:
        print(f"Error en la consulta: {e}")
        return None
    
def analizar_estado_contrato(engine):
    """
    Realiza un análisis por estado de contrato (`NAME_CONTRACT_STATUS`) en la tabla `credit_card_balance`.

    Para cada estado de contrato, calcula:
    - El número total de registros.
    - La cantidad de registros con saldo a favor (`AMT_RECIVABLE < 0`).
    - La cantidad de registros con deuda (`AMT_RECIVABLE > 0`).
    - El promedio del valor de `AMT_RECIVABLE`.

    Parámetros:
    ----------
    engine : sqlalchemy.engine.base.Engine
        Conexión activa a la base de datos.

    Retorna:
    -------
    pandas.DataFrame
        Contiene:
        - NAME_CONTRACT_STATUS
        - total_registros
        - con_credito
        - con_deuda
        - promedio_receivable
    """
    query = """
    SELECT NAME_CONTRACT_STATUS,
           COUNT(*) as total_registros,
           SUM(CASE WHEN AMT_RECIVABLE < 0 THEN 1 ELSE 0 END) as con_credito,
           SUM(CASE WHEN AMT_RECIVABLE > 0 THEN 1 ELSE 0 END) as con_deuda,
           AVG(AMT_RECIVABLE) as promedio_receivable
    FROM credit_card_balance 
    GROUP BY NAME_CONTRACT_STATUS
    ORDER BY total_registros DESC
    """
    try:
        result = pd.read_sql(query, engine)
        print("\n=== ANÁLISIS POR ESTADO DE CONTRATO ===")
        print(result)
        return result
    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")
        return None

def analizar_perfil_clientes(engine):
    """
    Realiza un análisis completo del perfil de clientes a partir de la tabla `credit_card_balance`.
    
    Filtra clientes con al menos 3 meses de historial y límite de crédito mayor a 0.
    Calcula promedios de variables clave, identifica clientes sin atrasos, con atrasos, 
    VIP (alto receivable y sin atrasos) y de alto riesgo (alto receivable y con atrasos).

    Parámetros:
    -----------
    engine : sqlalchemy.engine.base.Engine
        Conexión activa a la base de datos.

    Retorna:
    --------
    perfil_completo : pd.DataFrame
        Dataset con métricas agregadas por cliente.
    """
    query_perfil_completo = """
    SELECT 
        SK_ID_CURR,
        COUNT(*) as total_registros,
        AVG(AMT_RECIVABLE) as promedio_receivable,
        AVG(AMT_CREDIT_LIMIT_ACTUAL) as promedio_limite_credito,
        AVG(SK_DPD) as promedio_dias_atraso,
        MAX(SK_DPD) as max_dias_atraso,
        SUM(CASE WHEN SK_DPD = 0 THEN 1 ELSE 0 END) as meses_sin_atraso,
        SUM(CASE WHEN SK_DPD > 0 THEN 1 ELSE 0 END) as meses_con_atraso,
        AVG(AMT_PAYMENT_CURRENT) as promedio_pagos,
        AVG(AMT_RECIVABLE / AMT_CREDIT_LIMIT_ACTUAL) as ratio_utilizacion,
        NAME_CONTRACT_STATUS
    FROM credit_card_balance 
    WHERE AMT_CREDIT_LIMIT_ACTUAL > 0
    GROUP BY SK_ID_CURR, NAME_CONTRACT_STATUS
    HAVING COUNT(*) > 3
    ORDER BY promedio_receivable DESC
    """
    try:
        perfil_completo = pd.read_sql(query_perfil_completo, engine)

        print("=== ANÁLISIS DE PERFIL DE CLIENTES - DATASET COMPLETO ===")
        print(f"Total de clientes analizados: {len(perfil_completo):,}")
        print(f"Promedio de límite de crédito: ${perfil_completo['promedio_limite_credito'].mean():,.2f}")
        print(f"Promedio de días de atraso: {perfil_completo['promedio_dias_atraso'].mean():.1f}")
        print(f"Clientes sin atrasos: {(perfil_completo['meses_con_atraso'] == 0).sum():,}")
        print(f"Clientes con atrasos: {(perfil_completo['meses_con_atraso'] > 0).sum():,}")

        print("\n=== TOP 5 CLIENTES CON MAYOR RECEIVABLE ===")
        top_5_receivable = perfil_completo[['SK_ID_CURR', 'promedio_receivable', 'promedio_limite_credito', 
                                           'promedio_dias_atraso', 'ratio_utilizacion']].head()
        print(top_5_receivable.to_string(index=False))

        print("\n=== TOP 5 CLIENTES CON MAYOR ATRASO ===")
        top_5_atraso = perfil_completo[['SK_ID_CURR', 'promedio_receivable', 'promedio_limite_credito', 
                                       'promedio_dias_atraso', 'max_dias_atraso']].sort_values('promedio_dias_atraso', ascending=False).head()
        print(top_5_atraso.to_string(index=False))

        print("\n=== CLIENTES VIP (Alto receivable, sin atrasos) ===")
        clientes_vip = perfil_completo[
            (perfil_completo['promedio_receivable'] > 50000) & 
            (perfil_completo['meses_con_atraso'] == 0)
        ][['SK_ID_CURR', 'promedio_receivable', 'promedio_limite_credito', 'ratio_utilizacion']]
        print(f"Total clientes VIP: {len(clientes_vip):,}")
        if len(clientes_vip) > 0:
            print("TOP 5 clientes VIP:")
            print(clientes_vip.head().to_string(index=False))

        print("\n=== CLIENTES DE ALTO RIESGO (Alto receivable, con atrasos) ===")
        clientes_riesgo = perfil_completo[
            (perfil_completo['promedio_receivable'] > 50000) & 
            (perfil_completo['meses_con_atraso'] > 0)
        ][['SK_ID_CURR', 'promedio_receivable', 'promedio_dias_atraso', 'max_dias_atraso']]
        print(f"Total clientes de alto riesgo: {len(clientes_riesgo):,}")
        if len(clientes_riesgo) > 0:
            print("TOP 5 clientes de alto riesgo:")
            print(clientes_riesgo.head().to_string(index=False))

        print(f"\n=== RESUMEN ESTADÍSTICO ===")
        print(f"Porcentaje de clientes sin atrasos: {(perfil_completo['meses_con_atraso'] == 0).sum() / len(perfil_completo) * 100:.1f}%")
        print(f"Porcentaje de clientes con atrasos: {(perfil_completo['meses_con_atraso'] > 0).sum() / len(perfil_completo) * 100:.1f}%")
        print(f"Porcentaje de clientes VIP: {len(clientes_vip) / len(perfil_completo) * 100:.1f}%")
        print(f"Porcentaje de clientes de alto riesgo: {len(clientes_riesgo) / len(perfil_completo) * 100:.1f}%")

        return perfil_completo

    except Exception as e:
        print(f"Error en la consulta: {e}")
        return None

def obtener_pagos_por_cliente(engine):
    """
    Retorna y muestra el total de pagos realizados, el promedio de cuotas e importes pagados,
    y el conteo de pagos incompletos y excedidos por cliente. Se limita a los 10 clientes con más pagos.

    Parámetros:
    - engine: conexión SQLAlchemy a la base de datos.

    Retorna:
    - pd.DataFrame: información agregada por cliente.
    """
    query = """
    SELECT 
        SK_ID_CURR,
        COUNT(*) AS total_pagos,
        AVG(AMT_INSTALMENT) AS promedio_instalment,
        AVG(AMT_PAYMENT) AS promedio_payment,
        SUM(CASE WHEN AMT_PAYMENT < AMT_INSTALMENT THEN 1 ELSE 0 END) AS pagos_incompletos,
        SUM(CASE WHEN AMT_PAYMENT > AMT_INSTALMENT THEN 1 ELSE 0 END) AS pagos_excedidos
    FROM installments_payments
    GROUP BY SK_ID_CURR
    ORDER BY total_pagos DESC
    LIMIT 10
    """
    try:
        result = pd.read_sql(query, engine)
        print("=== TOP 10 CLIENTES CON MÁS PAGOS ===")
        print(result.to_string(index=False))
        return result
    except Exception as e:
        print(f"Error al obtener pagos por cliente: {e}")
        return None

def obtener_resumen_atrasos(engine):
    """
    Retorna y muestra un resumen general de pagos atrasados y adelantados, junto con el promedio de días de diferencia.

    Parámetros:
    - engine: conexión SQLAlchemy a la base de datos.

    Retorna:
    - pd.DataFrame: resumen de atrasos y adelantos.
    """
    query = """
    SELECT 
        COUNT(*) AS total_registros,
        SUM(CASE WHEN DAYS_ENTRY_PAYMENT > DAYS_INSTALMENT THEN 1 ELSE 0 END) AS pagos_atrasados,
        SUM(CASE WHEN DAYS_ENTRY_PAYMENT < DAYS_INSTALMENT THEN 1 ELSE 0 END) AS pagos_adelantados,
        AVG(DAYS_ENTRY_PAYMENT - DAYS_INSTALMENT) AS promedio_dias_diferencia
    FROM installments_payments
    """
    try:
        result = pd.read_sql(query, engine)
        print("\n=== RESUMEN DE PAGOS ATRASADOS Y ADELANTADOS ===")
        print(result.to_string(index=False))
        return result
    except Exception as e:
        print(f"Error al obtener resumen de atrasos: {e}")
        return None

def obtener_distribucion_incompletos(engine):
    """
    Retorna y muestra un resumen de los pagos incompletos con el promedio de la diferencia entre el monto de la cuota 
    y el monto realmente pagado.

    Parámetros:
    - engine: conexión SQLAlchemy a la base de datos.

    Retorna:
    - pd.DataFrame: información de pagos incompletos.
    """
    query = """
    SELECT 
        COUNT(*) AS total_incompletos,
        AVG(AMT_INSTALMENT - AMT_PAYMENT) AS promedio_diferencia
    FROM installments_payments
    WHERE AMT_PAYMENT < AMT_INSTALMENT
    """
    try:
        result = pd.read_sql(query, engine)
        print("\n=== DISTRIBUCIÓN DE PAGOS INCOMPLETOS ===")
        print(result.to_string(index=False))
        return result
    except Exception as e:
        print(f"Error al obtener distribución de pagos incompletos: {e}")
        return None

def _aggregate_installments_by_customer(df_inst):
    """
    Agrega los datos de pago de cuotas a nivel de cliente (SK_ID_CURR).

    Esta función de ayuda procesa el DataFrame de 'installments_payments' para calcular
    métricas clave del comportamiento de pago de cada cliente, como el retraso promedio,
    la proporción de cuotas pagadas con retraso y la actividad general.

    Parámetros:
    ----------
    df_inst : pd.DataFrame
        DataFrame crudo que contiene los datos de la tabla 'installments_payments'.

    Retorna:
    --------
    pd.DataFrame
        Un DataFrame agregado con una fila por SK_ID_CURR y columnas que resumen
        el comportamiento de pago de cuotas del cliente.
    """
    print("Step 1: Aggregating 'installments_payments' by customer...")
    
    inst = df_inst.copy()
    inst['DAYS_LATE'] = inst['DAYS_ENTRY_PAYMENT'] - inst['DAYS_INSTALMENT']
    inst['PAYMENT_RATIO'] = inst['AMT_PAYMENT'] / inst['AMT_INSTALMENT'].replace(0, np.nan)
    
    inst['IS_LATE'] = (inst['DAYS_LATE'] > 0).astype(int)
    inst['IS_UNDERPAID'] = (inst['AMT_PAYMENT'] < inst['AMT_INSTALMENT']).astype(int)

    agg = inst.groupby('SK_ID_CURR').agg(
        # Métricas de tiempo de pago a nivel de cliente
        AVG_DAYS_LATE=('DAYS_LATE', lambda x: x[x > 0].mean()),
        MAX_DAYS_LATE=('DAYS_LATE', 'max'),
        FRAC_LATE_INSTALLMENTS=('IS_LATE', 'mean'),
        
        # Métricas de monto de pago a nivel de cliente
        AVG_PAYMENT_RATIO=('PAYMENT_RATIO', 'mean'),
        FRAC_UNDERPAID_INSTALLMENTS=('IS_UNDERPAID', 'mean'),
        
        # Métricas de actividad a nivel de cliente
        TOTAL_INSTALLMENTS_PAID=('SK_ID_PREV', 'count'),
        TOTAL_LOANS_WITH_INSTALLMENTS=('SK_ID_PREV', 'nunique'),
        DAYS_SINCE_LAST_PAYMENT=('DAYS_ENTRY_PAYMENT', 'max')
    ).reset_index()

    agg['DAYS_SINCE_LAST_PAYMENT'] = -agg['DAYS_SINCE_LAST_PAYMENT']
    agg['AVG_DAYS_LATE'] = agg['AVG_DAYS_LATE'].fillna(0)

    return agg

def _aggregate_credit_card_by_customer(df_balance):
    """
    Agrega los datos del balance de tarjetas de crédito a nivel de cliente (SK_ID_CURR).

    Esta función de ayuda procesa el DataFrame de 'credit_card_balance' para calcular
    métricas sobre el uso de la tarjeta de crédito, como el saldo promedio, la utilización
    del crédito y el historial de morosidad (DPD - Días de Atraso).

    Parámetros:
    ----------
    df_balance : pd.DataFrame
        DataFrame crudo que contiene los datos de la tabla 'credit_card_balance'.

    Retorna:
    --------
    pd.DataFrame
        Un DataFrame agregado con una fila por SK_ID_CURR y columnas que resumen
        el comportamiento del cliente con tarjetas de crédito.
    """
    print("Step 2: Aggregating 'credit_card_balance' by customer...")
    
    ccb = df_balance.copy()
    ccb['UTILIZATION_RATIO'] = ccb['AMT_BALANCE'] / ccb['AMT_CREDIT_LIMIT_ACTUAL'].replace(0, np.nan)
    
    agg = ccb.groupby('SK_ID_CURR').agg(
        # Métricas de saldo y límite
        AVG_BALANCE_TDC=('AMT_BALANCE', 'mean'),
        MAX_BALANCE_TDC=('AMT_BALANCE', 'max'),
        AVG_CREDIT_LIMIT_TDC=('AMT_CREDIT_LIMIT_ACTUAL', 'mean'),
        AVG_UTILIZATION_RATIO_TDC=('UTILIZATION_RATIO', 'mean'),
        
        # Métricas de morosidad
        AVG_DPD_TDC=('SK_DPD', 'mean'),
        MAX_DPD_TDC=('SK_DPD', 'max'),
        TOTAL_MONTHS_WITH_DPD_TDC=('SK_DPD', lambda x: (x > 0).sum())
    ).reset_index()
    
    return agg


def create_active_customer_gold_table(df_inst, df_balance):
    """
    Orquesta la creación de una tabla maestra 'Gold' a nivel de cliente (SK_ID_CURR),
    incluyendo únicamente a los clientes con actividad en los DataFrames proporcionados.

    Esta función consolida el comportamiento del cliente a partir de los datos de cuotas y
    tarjetas de crédito. Utiliza una unión externa ('outer join') para fusionar los
    resultados de las funciones de ayuda, creando un perfil completo para cada cliente
    activo. El resultado es una tabla optimizada, lista para ser usada en dashboards
    de alto rendimiento y modelos de machine learning.

    Parámetros:
    ----------
    df_inst : pd.DataFrame
        DataFrame crudo que contiene los datos de la tabla 'installments_payments'.
        
    df_balance : pd.DataFrame
        DataFrame crudo que contiene los datos de la tabla 'credit_card_balance'.

    Retorna:
    --------
    df_gold : pd.DataFrame
        Un único DataFrame a nivel de SK_ID_CURR que contiene a todos los clientes
        activos con sus características pre-calculadas y limpias.
    """
    print("--- Starting Gold Table Creation for Active Customers ---")
    
    # Procesar cada fuente de datos usando las funciones de ayuda
    installments_agg = _aggregate_installments_by_customer(df_inst)
    credit_card_agg = _aggregate_credit_card_by_customer(df_balance)
    
    # Fusionar los dos DataFrames agregados usando una unión externa.
    # Esto asegura que cualquier cliente en al menos una de las tablas sea incluido.
    print("Step 3: Merging data sources with an 'outer' join...")
    df_gold = pd.merge(installments_agg, credit_card_agg, on='SK_ID_CURR', how='outer')
    
    # Limpieza final: la unión externa crea NaNs para clientes que están en una
    # tabla pero no en la otra. Los rellenamos con valores por defecto con sentido de negocio.
    df_gold.fillna({
        # Columnas de cuotas
        'AVG_DAYS_LATE': 0, 'MAX_DAYS_LATE': 0, 'FRAC_LATE_INSTALLMENTS': 0,
        'AVG_PAYMENT_RATIO': 0, 'FRAC_UNDERPAID_INSTALLMENTS': 0,
        'TOTAL_INSTALLMENTS_PAID': 0, 'TOTAL_LOANS_WITH_INSTALLMENTS': 0,
        'DAYS_SINCE_LAST_PAYMENT': 9999,
        # Columnas de tarjeta de crédito
        'AVG_BALANCE_TDC': 0, 'MAX_BALANCE_TDC': 0, 'AVG_CREDIT_LIMIT_TDC': 0,
        'AVG_UTILIZATION_RATIO_TDC': 0, 'AVG_DPD_TDC': 0, 'MAX_DPD_TDC': 0,
        'TOTAL_MONTHS_WITH_DPD_TDC': 0
    }, inplace=True)
    
    print("--- Gold Table Creation Complete ---")
    return df_gold


def aggregate_previous_applications(df_previous):
    """
    Agrega los datos de solicitudes de crédito anteriores a nivel de cliente (SK_ID_CURR).

    Esta función procesa el historial de un cliente con Home Credit para extraer
    características clave como el número de préstamos anteriores, los montos
    promedio solicitados y los tipos de productos más comunes.

    Parámetros:
    ----------
    df_previous : pd.DataFrame
        DataFrame a nivel de préstamo (`SK_ID_PREV`) con datos de 'previous_application'.
        Debe contener: 'SK_ID_CURR', 'SK_ID_PREV', 'NAME_CONTRACT_TYPE', 
        'AMT_APPLICATION', 'AMT_CREDIT', 'NAME_CLIENT_TYPE'.

    Retorna:
    --------
    pd.DataFrame
        Un DataFrame agregado con una fila por SK_ID_CURR.
    """
    print("Procesando 'previous_application' data...")
    
    # Agregaciones numéricas
    agg_numeric = df_previous.groupby('SK_ID_CURR').agg(
        PREV_LOAN_COUNT=('SK_ID_PREV', 'count'),
        PREV_AVG_APPLICATION_AMT=('AMT_APPLICATION', 'mean'),
        PREV_MAX_CREDIT_AMT=('AMT_CREDIT', 'max'),
        PREV_TOTAL_CREDIT_SUM=('AMT_CREDIT', 'sum')
    ).reset_index()

    # Agregaciones categóricas (obteniendo la moda)
    agg_categorical = df_previous.groupby('SK_ID_CURR').agg(
        PREV_MOST_COMMON_CONTRACT_TYPE=('NAME_CONTRACT_TYPE', lambda x: x.mode().iloc[0]),
        PREV_MOST_COMMON_CLIENT_TYPE=('NAME_CLIENT_TYPE', lambda x: x.mode().iloc[0])
    ).reset_index()

    # Unir agregaciones numéricas y categóricas
    df_agg = pd.merge(agg_numeric, agg_categorical, on='SK_ID_CURR')
    print("-> Agregación de 'previous_application' completada.")
    return df_agg

def aggregate_pos_cash(df_pos):
    """
    Agrega los datos de balances de préstamos POS y Cash a nivel de cliente (SK_ID_CURR).

    Esta función procesa el historial mensual de los préstamos tipo POS/Cash para
    extraer características como el total y el promedio de cuotas futuras
    pendientes de pago.

    Parámetros:
    ----------
    df_pos : pd.DataFrame
        DataFrame a nivel de préstamo (`SK_ID_PREV`) con datos de 'POS_CASH_balance'.
        Debe contener: 'SK_ID_CURR', 'SK_ID_PREV', 'CNT_INSTALMENT_FUTURE'.

    Retorna:
    --------
    pd.DataFrame
        Un DataFrame agregado con una fila por SK_ID_CURR.
    """
    print("Procesando 'POS_CASH_balance' data...")
    
    df_agg = df_pos.groupby('SK_ID_CURR').agg(
        POS_TOTAL_FUTURE_INSTALLMENTS=('CNT_INSTALMENT_FUTURE', 'sum'),
        POS_AVG_FUTURE_INSTALLMENTS=('CNT_INSTALMENT_FUTURE', 'mean')
    ).reset_index()
    
    print("-> Agregación de 'POS_CASH_balance' completada.")
    return df_agg

def aggregate_bureau(df_bureau_for_model):
    """
    Agrega los datos del historial crediticio externo (bureau) a nivel de cliente (SK_ID_CURR).

    Esta función procesa el historial de un cliente con otras instituciones financieras
    para extraer características como el número de créditos externos, el estado de
    dichos créditos (activos, cerrados) y los tipos de crédito que maneja.

    Parámetros:
    ----------
    df_bureau : pd.DataFrame
        DataFrame a nivel de préstamo (`SK_ID_PREV`) con datos de 'bureau'.
        Debe contener: 'SK_ID_CURR', 'SK_ID_PREV', 'CREDIT_TYPE', 'CREDIT_ACTIVE'.

    Retorna:
    --------
    pd.DataFrame
        Un DataFrame agregado con una fila por SK_ID_CURR.
    """
    print("Procesando datos del 'bureau'...")
    
    # Contar créditos totales en el bureau
    bureau_loan_counts = df_bureau_for_model.groupby('SK_ID_CURR', as_index=False)['SK_ID_PREV'].count().rename(columns={'SK_ID_PREV': 'BUREAU_LOAN_COUNT'})
    
    # Contar créditos por estado (Active, Closed, etc.)
    credit_status_counts = pd.crosstab(df_bureau_for_model['SK_ID_CURR'], df_bureau_for_model['CREDIT_ACTIVE']).reset_index()
    credit_status_counts.columns = ['SK_ID_CURR'] + [f'BUREAU_STATUS_{col.upper()}' for col in credit_status_counts.columns[1:]]

    # Contar créditos por tipo (Credit card, Consumer credit, etc.)
    credit_type_counts = pd.crosstab(df_bureau_for_model['SK_ID_CURR'], df_bureau_for_model['CREDIT_TYPE']).reset_index()
    credit_type_counts.columns = ['SK_ID_CURR'] + [f'BUREAU_TYPE_{col.upper().replace(" ", "_")}' for col in credit_type_counts.columns[1:]]
    
    # Unir todas las agregaciones del bureau
    df_agg = pd.merge(bureau_loan_counts, credit_status_counts, on='SK_ID_CURR', how='left')
    df_agg = pd.merge(df_agg, credit_type_counts, on='SK_ID_CURR', how='left')
    
    # Asegurarse de rellenar NaNs si alguna categoría no existía para algún cliente
    df_agg.fillna(0, inplace=True)
    
    print("-> Agregación de 'bureau' completada.")
    return df_agg

def create_final_ml_gold_table(df_installments, df_credit_card, df_previous, df_pos, df_bureau_for_model):
    """
    Orquesta la creación de la tabla Gold, consolidada y legible para el análisis.

    Esta función integra el trabajo de cuatro fuentes de datos distintas, llamando a
    funciones de agregación específicas para cada una y uniéndolas en un único

    DataFrame a nivel de cliente. El resultado es una tabla rica en características,
    limpia y fácil de interpretar, ideal para análisis exploratorio y como base
    para futuros modelos.

    NOTA: Esta función NO realiza transformaciones específicas para Machine Learning
    como One-Hot Encoding o normalización.

    Parámetros:
    ----------
    df_installments : pd.DataFrame
        DataFrame crudo con los datos de 'installments_payments'.
    df_credit_card : pd.DataFrame
        DataFrame crudo con los datos de 'credit_card_balance'.
    df_previous : pd.DataFrame
        DataFrame crudo con los datos de 'previous_application'.
    df_pos : pd.DataFrame
        DataFrame crudo con los datos de 'POS_CASH_balance'.
    df_bureau : pd.DataFrame
        DataFrame crudo con los datos de 'bureau'.

    Retorna:
    --------
    pd.DataFrame
        La tabla Gold final, lista para análisis y como punto de partida para el modelado.
    """
    
    # 1. Llamar a la función que ya tenías para crear la base
    # (Asumiendo que tienes una función `prepare_features_for_modeling` disponible)
    df_base_gold = prepare_features_for_modeling(df_credit_card, df_installments)
    
    # 2. Llamar a cada una de las nuevas funciones de agregación
    df_previous_agg = aggregate_previous_applications(df_previous)
    df_pos_agg = aggregate_pos_cash(df_pos)
    df_bureau_agg = aggregate_bureau(df_bureau_for_model)
    
    # 3. Realizar el merge secuencial usando 'left' join
    print("\nIniciando el merge final de todas las fuentes de datos...")
    df_final_model = df_base_gold.copy()
    df_final_model = pd.merge(df_final_model, df_previous_agg, on='SK_ID_CURR', how='left')
    df_final_model = pd.merge(df_final_model, df_pos_agg, on='SK_ID_CURR', how='left')
    df_final_model = pd.merge(df_final_model, df_bureau_agg, on='SK_ID_CURR', how='left')
    print("-> Merge completado.")
    
    # 4. Limpieza final (Imputación de Nulos)
    print("Realizando limpieza final...")
    
    # Rellenar todos los posibles NaNs con valores por defecto legibles
    numeric_cols_to_fill = [col for col in df_final_model.columns if col.startswith(('PREV_', 'POS_', 'BUREAU_')) and df_final_model[col].dtype != 'object']
    df_final_model[numeric_cols_to_fill] = df_final_model[numeric_cols_to_fill].fillna(0)
    
    categorical_cols_to_fill = [col for col in df_final_model.columns if col.startswith(('PREV_')) and df_final_model[col].dtype == 'object']
    df_final_model[categorical_cols_to_fill] = df_final_model[categorical_cols_to_fill].fillna('No_History')
    
    print("-> Limpieza completada.")
    print("\n¡Proceso finalizado! La tabla Gold legible está lista.")
    
    return df_final_model

