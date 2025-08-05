import pandas as pd
import numpy as np
from sqlalchemy import create_engine


import pandas as pd
import numpy as np

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


def casos_cargos_adicionales(engine):
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
