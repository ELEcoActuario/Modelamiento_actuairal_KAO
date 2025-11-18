import pandas as pd
import logging

# Configurar logger para este módulo
logger = logging.getLogger(__name__)

def asignar_bandas_sfc(df_flujo: pd.DataFrame, fecha_referencia: pd.Timestamp) -> pd.DataFrame:
    logger.info(f"🏷️ Asignando bandas SFC a {len(df_flujo)} flujos desde fecha: {fecha_referencia}")
    """
    Asigna la banda normativa SFC (κ) a cada flujo según la diferencia de días entre
    la fecha de pago y la fecha de corte, conforme al Anexo 15 del Capítulo 31 del SIAR.

    Args:
        df_flujo (pd.DataFrame): DataFrame con al menos una columna 'Fecha_Pago'.
        fecha_referencia (pd.Timestamp): Fecha de corte.

    Returns:
        pd.DataFrame: Mismo DataFrame con columna adicional 'Banda_SFC'.

    Raises:
        ValueError: Si no existe la columna 'Fecha_Pago' o contiene datos inválidos.

    Ejemplo:
        >>> df = pd.DataFrame({"Fecha_Pago": ["2025-10-01", "2026-02-15"]})
        >>> asignar_bandas_sfc(df, pd.Timestamp("2025-07-01"))
    """
    if "Fecha_Pago" not in df_flujo.columns:
        raise ValueError("El DataFrame debe contener la columna 'Fecha_Pago'.")

    df = df_flujo.copy()
    try:
        df["Fecha_Pago"] = pd.to_datetime(df["Fecha_Pago"])
        logger.debug("📅 Fechas de pago convertidas correctamente")
    except Exception as e:
        logger.error(f"❌ Error convirtiendo fechas: {str(e)}")
        raise ValueError("La columna 'Fecha_Pago' contiene valores no convertibles a fecha.")

    df["Dias_Hasta_Pago"] = (df["Fecha_Pago"] - fecha_referencia).dt.days
    logger.debug(f"📊 Días calculados - Rango: {df['Dias_Hasta_Pago'].min()} a {df['Dias_Hasta_Pago'].max()} días")

    # Bandas SFC según normatividad oficial (Tabla 4)
    bandas_sfc = pd.DataFrame({
        "Banda": list(range(1, 20)),
        "Inicio_dias": [0, 1, 31, 92, 184, 275, 366, 549, 732, 1097,
                        1462, 1827, 2192, 2557, 2922, 3287, 3651, 5476, 7301],
        "Fin_dias":    [1, 30, 91, 183, 274, 365, 548, 731, 1096, 1461,
                        1826, 2191, 2556, 2921, 3286, 3650, 5475, 7300, 99999]
    })

    # Construimos intervalos como rango y usamos cut para asignar
    df["Banda_SFC"] = pd.cut(
        df["Dias_Hasta_Pago"],
        bins=[-float("inf")] + bandas_sfc["Fin_dias"].tolist(),
        labels=bandas_sfc["Banda"],
        right=True
    ).astype("Int64")  # Nullable int for missing

    if df["Banda_SFC"].isnull().any():
        nulos = df["Banda_SFC"].isnull().sum()
        logger.warning(f"⚠️ {nulos} flujos sin banda SFC (pagos antes de fecha de corte)")
    
    bandas_asignadas = df["Banda_SFC"].value_counts().sort_index()
    logger.info(f"✅ Bandas SFC asignadas: {len(bandas_asignadas)} bandas diferentes")
    logger.debug(f"📊 Distribución de bandas: {dict(bandas_asignadas)}")

    return df


def asignar_factor_tiempo_tk(nodo_dias: int) -> float:
    logger.debug(f"🔢 Asignando factor t_k para {nodo_dias} días")
    """
    Asigna el factor de tiempo t_k según el número de días (Nodo) desde la fecha de corte.
    Implementa el mapeo normativo para cálculo de Valor Presente.
    
    Args:
        nodo_dias (int): Número de días desde la fecha de corte hasta el pago del flujo
        
    Returns:
        float: Factor de tiempo t_k correspondiente a la banda
        
    Ejemplo:
        >>> asignar_factor_tiempo_tk(15)  # 15 días
        0.0417
        >>> asignar_factor_tiempo_tk(1000)  # ~2.7 años
        2.5
    """
    if nodo_dias <= 1:
        return 0.0028  # Overnight
    elif nodo_dias <= 30:  # 1 mes
        return 0.0417
    elif nodo_dias <= 90:  # 3 meses
        return 0.1667
    elif nodo_dias <= 180:  # 6 meses
        return 0.375
    elif nodo_dias <= 270:  # 9 meses
        return 0.625
    elif nodo_dias <= 360:  # 1 año
        return 0.8075
    elif nodo_dias <= 540:  # 1.5 años
        return 1.25
    elif nodo_dias <= 720:  # 2 años
        return 1.75
    elif nodo_dias <= 1080:  # 3 años
        return 2.5
    elif nodo_dias <= 1440:  # 4 años
        return 3.5
    elif nodo_dias <= 1800:  # 5 años
        return 4.5
    elif nodo_dias <= 2160:  # 6 años
        return 5.5
    elif nodo_dias <= 2520:  # 7 años
        return 6.5
    elif nodo_dias <= 2880:  # 8 años
        return 7.5
    elif nodo_dias <= 3240:  # 9 años
        return 8.5
    elif nodo_dias <= 3650:  # 10 años (365*10)
        return 9.5
    elif nodo_dias <= 5475:  # 15 años (365*15)
        return 12.5
    elif nodo_dias <= 7300:  # 20 años (365*20)
        return 17.5
    else:  # > 20 años
        return 25.0


def asignar_nodo_y_tk_a_flujos(df_flujo: pd.DataFrame, fecha_corte: pd.Timestamp) -> pd.DataFrame:
    logger.debug(f"🎯 Asignando nodos y factores t_k a {len(df_flujo)} flujos")
    """
    Asigna el Nodo (días desde fecha de corte) y el factor t_k a cada flujo.
    
    Args:
        df_flujo (pd.DataFrame): DataFrame con columna 'Fecha_Pago'
        fecha_corte (pd.Timestamp): Fecha de corte para calcular días
        
    Returns:
        pd.DataFrame: DataFrame con columnas adicionales 'Nodo' y 't_k'
    """
    if "Fecha_Pago" not in df_flujo.columns:
        logger.error("❌ Error: DataFrame sin columna 'Fecha_Pago'")
        raise ValueError("El DataFrame debe contener la columna 'Fecha_Pago'.")

    df = df_flujo.copy()
    df["Fecha_Pago"] = pd.to_datetime(df["Fecha_Pago"])
    
    # Calcular Nodo (días desde fecha de corte)
    df["Nodo"] = (df["Fecha_Pago"] - fecha_corte).dt.days
    logger.debug(f"📊 Nodos calculados - Rango: {df['Nodo'].min()} a {df['Nodo'].max()} días")
    
    # Asignar factor t_k usando la función de mapeo
    df["t_k"] = df["Nodo"].apply(asignar_factor_tiempo_tk)
    factores_unicos = sorted(df["t_k"].unique())
    logger.debug(f"🔢 Factores t_k únicos asignados: {factores_unicos}")
    logger.debug(f"✅ Nodos y factores t_k asignados correctamente")
    
    return df
