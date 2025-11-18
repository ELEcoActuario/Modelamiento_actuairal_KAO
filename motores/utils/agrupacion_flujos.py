import pandas as pd
from motores.bandas.utils_bandas import asignar_bandas_sfc


def agrupar_flujos_originales(df_orig: pd.DataFrame, agrupacion: str, fecha_corte: pd.Timestamp) -> pd.DataFrame:
    """
    Agrupa los flujos originales según la periodicidad especificada.
    
    Args:
        df_orig: DataFrame con flujos originales
        agrupacion: Tipo de agrupación ("Exacta", "Mensual", "Trimestral", "Semestral", "Anual", "Bandas SFC")
        fecha_corte: Fecha de referencia para las bandas SFC
    
    Returns:
        DataFrame agrupado con columna "Periodo" añadida
    """
    if df_orig.empty:
        return pd.DataFrame()

    df_orig = df_orig.copy()

    if agrupacion == "Exacta":
        df_orig["Periodo"] = pd.to_datetime(df_orig["Fecha_Pago"]).dt.strftime("%Y-%m-%d")
        return df_orig

    if agrupacion == "Bandas SFC":
        if 'Banda_SFC' not in df_orig.columns:
            df_orig = asignar_bandas_sfc(df_orig, fecha_corte)
        df_orig = df_orig[df_orig['Banda_SFC'].notnull()]
        df_grouped = df_orig.groupby("Banda_SFC", dropna=False)[["Capital", "Intereses", "Flujo_Total"]].sum().reset_index()
        df_grouped["Periodo"] = df_grouped["Banda_SFC"].astype('Int64').astype(str)
        return df_grouped

    # Para agrupaciones temporales (Mensual, Trimestral, etc.)
    df_orig['Fecha_Pago'] = pd.to_datetime(df_orig['Fecha_Pago'])
    df_orig = df_orig.set_index('Fecha_Pago')[["Capital", "Intereses", "Flujo_Total"]].resample(_freq_resample(agrupacion)).sum().reset_index()

    if agrupacion == "Semestral":
        df_orig["Periodo"] = df_orig['Fecha_Pago'].dt.year.astype(str) + "-S" + df_orig['Fecha_Pago'].dt.month.apply(lambda m: '1' if m <= 6 else '2')
    else:
        df_orig["Periodo"] = df_orig['Fecha_Pago'].dt.to_period(_freq_resample(agrupacion)).astype(str)

    return df_orig


def agrupar_flujos_ajustados(df1: pd.DataFrame, df2: pd.DataFrame, agrupacion: str) -> tuple:
    """
    Agrupa dos DataFrames de flujos ajustados según la periodicidad especificada.
    
    Args:
        df1: Primer DataFrame (flujos base)
        df2: Segundo DataFrame (flujos estresados)
        agrupacion: Tipo de agrupación
    
    Returns:
        Tupla con los dos DataFrames agrupados
    """
    def agrupar(df, cols):
        if df.empty:
            return pd.DataFrame()
        df = df.copy()

        if agrupacion == "Exacta":
            df["Periodo"] = pd.to_datetime(df["Fecha_Pago"]).dt.strftime("%Y-%m-%d")
            return df

        if agrupacion == "Bandas SFC":
            if 'Banda_SFC' not in df.columns:
                df = asignar_bandas_sfc(df, pd.to_datetime(df['Fecha_Pago']).min())
            df = df[df['Banda_SFC'].notnull()]
            df_grouped = df.groupby("Banda_SFC", dropna=False)[cols].sum().reset_index()
            df_grouped["Periodo"] = df_grouped["Banda_SFC"].astype('Int64').astype(str)
            return df_grouped

        df['Fecha_Pago'] = pd.to_datetime(df['Fecha_Pago'])
        df = df.set_index('Fecha_Pago')[cols].resample(_freq_resample(agrupacion)).sum().reset_index()

        if agrupacion == "Semestral":
            df["Periodo"] = df['Fecha_Pago'].dt.year.astype(str) + "-S" + df['Fecha_Pago'].dt.month.apply(lambda m: '1' if m <= 6 else '2')
        else:
            df["Periodo"] = df['Fecha_Pago'].dt.to_period(_freq_resample(agrupacion)).astype(str)

        return df

    cols_ajustado = ['Capital_Ajustado', 'Intereses_Ajustados', 'Flujo_Total_Ajustado']
    return agrupar(df1, cols_ajustado), agrupar(df2, cols_ajustado)


def _freq_resample(agrupacion: str) -> str:
    """Convierte el tipo de agrupación a frecuencia de pandas para resample."""
    return {
        "Mensual": "M",
        "Trimestral": "Q",
        "Semestral": "6M",
        "Anual": "A"
    }.get(agrupacion, "D")
