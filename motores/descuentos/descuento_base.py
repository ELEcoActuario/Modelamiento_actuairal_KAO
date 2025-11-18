import pandas as pd
import numpy as np
import logging

# Configurar logger para este módulo
logger = logging.getLogger(__name__)
from motores.bandas.utils_bandas import asignar_nodo_y_tk_a_flujos, asignar_factor_tiempo_tk

def calcular_descuento_base(df_flujo: pd.DataFrame, curva_base: pd.DataFrame, fecha_corte: pd.Timestamp, moneda: str) -> float:
    logger.debug(f"💰 Calculando descuento base para {len(df_flujo)} flujos en {moneda}")
    """
    Calcula el valor presente usando curva base y metodología normativa.
    
    FÓRMULA NORMATIVA SFC:
    --------------------
    FD(t_k) = exp(-r · t_k)
    VP = Flujo × FD(t_k)
    
    donde r = ln(1 + EA) es la tasa cero cupón (short rate)
    y t_k es el factor de tiempo discreto normativo SFC
    
    Args:
        df_flujo: DataFrame con flujos de caja
        curva_base: DataFrame con curva de descuento base (EN SHORT RATES)
        fecha_corte: Fecha de corte
        moneda: Moneda del crédito
    
    Returns:
        float: Valor presente total
    """
    if df_flujo.empty or curva_base.empty:
        logger.debug("⚠️ DataFrame vacío, retornando VP = 0")
        return 0.0
    
    # Filtrar solo flujos futuros
    df = df_flujo.copy()
    df["Fecha_Pago"] = pd.to_datetime(df["Fecha_Pago"])
    df = df[df["Fecha_Pago"] >= fecha_corte].copy()
    if df.empty:
        logger.debug("⚠️ Sin flujos futuros")
        return 0.0
    
    # Asignar Nodo y factor t_k
    logger.debug("🔢 Asignando nodos y factores t_k...")
    df = asignar_nodo_y_tk_a_flujos(df, fecha_corte)
    logger.debug(f"📊 Nodos - Rango: {df['Nodo'].min()} a {df['Nodo'].max()} días")
    logger.debug(f"🔢 Factores t_k únicos: {sorted(df['t_k'].unique())}")
    
    # Determinar columna de flujo
    if "Flujo_Total_Ajustado" in df.columns:
        df["Flujo"] = df["Flujo_Total_Ajustado"]
    elif "Flujo_Total" in df.columns:
        df["Flujo"] = df["Flujo_Total"]
    else:
        df["Flujo"] = 0.0
    
    # ========================================================================
    # TRANSFORMAR CURVA BASE EA → SHORT RATE (si no está transformada)
    # ========================================================================
    curva_base_work = curva_base.copy()
    
    # Verificar si la curva ya está en short rates (columna Tasa_EA existe)
    if "Tasa_EA" not in curva_base_work.columns:
        # Transformar EA a short rate
        logger.debug("🔄 Transformando curva base EA → Short Rate...")
        tasa_ea = curva_base_work["Tasa"].values
        
        # Normalizar si está en porcentaje
        if np.max(tasa_ea) > 1.0:
            tasa_ea = tasa_ea / 100.0
        
        tasa_short = np.log1p(tasa_ea)  # ln(1 + EA)
        curva_base_work["Tasa_EA"] = tasa_ea
        curva_base_work["Tasa"] = tasa_short
        logger.debug(f"   ✅ Transformación completada: EA rango [{tasa_ea.min():.6f}, {tasa_ea.max():.6f}] → Short [{tasa_short.min():.6f}, {tasa_short.max():.6f}]")
    
    # ========================================================================
    # CALCULAR VP CON FÓRMULA NORMATIVA: FD(t_k) = exp(-r · t_k)
    # ========================================================================
    logger.debug("💰 Calculando VP con fórmula normativa exponencial...")
    vp_total = 0.0
    flujos_procesados = 0
    matches_exactos = 0
    
    for _, row in df.iterrows():
        nodo = row["Nodo"]
        t_k = row["t_k"]
        flujo = row["Flujo"]
        
        if flujo == 0 or t_k == 0:
            continue
        
        flujos_procesados += 1
        
        # Búsqueda exacta por Nodo en curva base
        if "Nodo" in curva_base_work.columns:
            tasa_row = curva_base_work[curva_base_work["Nodo"] == nodo]
        else:
            # Si no hay columna Nodo, usar Tiempo
            tiempo_anios = nodo / 365.0
            tasa_row = curva_base_work[abs(curva_base_work["Tiempo"] - tiempo_anios) < 0.01]
        
        if not tasa_row.empty:
            tasa_short = tasa_row["Tasa"].iloc[0]  # Ya es short rate
            matches_exactos += 1
        else:
            # Buscar el más cercano
            if "Nodo" in curva_base_work.columns:
                diferencias = abs(curva_base_work["Nodo"] - nodo)
                idx_cercano = diferencias.idxmin()
            else:
                tiempo_anios = nodo / 365.0
                diferencias = abs(curva_base_work["Tiempo"] - tiempo_anios)
                idx_cercano = diferencias.idxmin()
            tasa_short = curva_base_work.loc[idx_cercano, "Tasa"]
        
        # ========================================================================
        # FÓRMULA NORMATIVA SFC: FD(t_k) = exp(-r · t_k)
        # ========================================================================
        # donde r es la tasa short rate (ya transformada)
        # y t_k es el factor de tiempo discreto normativo
        
        if not pd.isna(tasa_short):
            factor_descuento = np.exp(-tasa_short * t_k)  # FD = e^(-r·t_k)
            vp_flujo = flujo * factor_descuento  # VP = Flujo × FD
            vp_total += vp_flujo
    
    logger.debug(f"📊 VP base: {vp_total:,.2f} ({flujos_procesados} flujos, {matches_exactos} matches exactos)")
    return vp_total