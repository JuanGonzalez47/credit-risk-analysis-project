# Solo cuando estemos en la etapa de modelado
def prepare_features_for_modeling(df):
    """Crear variables explícitas para el modelo de ML: estas variables hablan acerca de la conducta del cliente
    por ejemplo, si el cliente tiene un saldo a favor (AMT_RECEIVABLE < 0), si ha tenido retrasos en los pagos 
    (AMT_PAYMENT_TOTAL_CURRENT > AMT_PAYMENT_CURRENT), si ha tenido cargos adicionales (AMT_TOTAL_RECIVABLE > AMT_RECIVABLE), etc."""
    
    # Variables de comportamiento (más importantes para el modelo)
    df['HAS_CREDIT_BALANCE'] = (df['AMT_RECEIVABLE'] < 0).astype(int)
    df['HAS_LATE_PAYMENTS'] = (
        df['AMT_PAYMENT_TOTAL_CURRENT'] > df['AMT_PAYMENT_CURRENT']
    ).astype(int)
    df['HAS_ADDITIONAL_CHARGES'] = (
        df['AMT_TOTAL_RECEIVABLE'] > df['AMT_RECIVABLE']
    ).astype(int)
    
    # Variables de magnitud (para algoritmos que necesitan valores numéricos)
    df['CREDIT_BALANCE_AMOUNT'] = df['AMT_RECEIVABLE'].clip(upper=0) * -1
    df['DEBT_BALANCE_AMOUNT'] = df['AMT_RECEIVABLE'].clip(lower=0)
    
    return df