import numpy as np
import pandas as pd
from typing import List, Dict
import logging
from motores.bandas.utils_bandas import asignar_nodo_y_tk_a_flujos

# Configurar logger para este módulo
logger = logging.getLogger(__name__)

ESCENARIOS_ESTRES = [
    "Paralelo_hacia_arriba",
    "Paralelo_hacia_abajo", 
    "Empinamiento",
    "Aplanamiento",
    "Corto_plazo_hacia_arriba",
    "Corto_plazo_hacia_abajo"
]

def calcular_descuentos_normativos(
    portafolio_estresado: Dict[str, List[pd.DataFrame]],
    curvas_estresadas: Dict[str, Dict[str, pd.DataFrame]],
    fecha_corte: pd.Timestamp
) -> Dict[str, pd.DataFrame]:
    logger.info(f"📊 Calculando descuentos normativos para {len(portafolio_estresado)} créditos en 6 escenarios de estrés")
    resultados = {esc: [] for esc in ESCENARIOS_ESTRES}
    logger.debug(f"🎯 Escenarios de estrés: {ESCENARIOS_ESTRES}")

    for id_credito, lista_flujos in portafolio_estresado.items():
        if not lista_flujos:
            continue

        moneda = _detectar_moneda(lista_flujos[0])
        curvas_moneda = curvas_estresadas.get(moneda, {})
        
        if not curvas_moneda:
            logger.warning(f"⚠️ Crédito {id_credito}: No hay curvas estresadas para moneda {moneda}")
            continue
        
        # 🔍 DIAGNÓSTICO: Analizar estructura de flujos del crédito
        num_simulaciones = len(lista_flujos)
        if num_simulaciones > 0 and lista_flujos[0] is not None:
            primer_flujo = lista_flujos[0]
            num_pagos = len(primer_flujo)
            if "Fecha_Pago" in primer_flujo.columns:
                fecha_max = pd.to_datetime(primer_flujo["Fecha_Pago"]).max()
                fecha_min = pd.to_datetime(primer_flujo["Fecha_Pago"]).min()
                duracion_dias = (fecha_max - fecha_corte).days
                tiene_prepago = "Prepago_Esperado" in primer_flujo.columns and primer_flujo["Prepago_Esperado"].sum() > 0
                logger.info(f"📋 {id_credito}: {num_simulaciones} sims, {num_pagos} pagos, duración {duracion_dias} días, prepago={'SÍ' if tiene_prepago else 'NO'}")
        
        for esc in ESCENARIOS_ESTRES:
            curva_df = curvas_moneda.get(esc, pd.DataFrame())
            
            if curva_df.empty or not all(col in curva_df.columns for col in ["Tiempo", "Tasa"]):
                logger.warning(f"⚠️ Curva vacía o incompleta para {esc} en moneda {moneda}")
                continue

            vps = []
            for df in lista_flujos:
                if df is not None and not df.empty:
                    try:
                        vp = _descontar_flujo(df, curva_df, fecha_corte)
                        vps.append(vp)
                    except Exception as e:
                        logger.error(f"❌ Error descontando flujo para {id_credito} en {esc}: {str(e)}")
                        vps.append(0) 

            vp_prom = np.mean(vps) if vps else 0
            logger.info(f"💰 {id_credito} - {esc}: VP={vp_prom:,.2f} ({len(vps)} sims)")

            resultados[esc].append({
                "ID_producto": id_credito,
                "VP_promedio": vp_prom
            })

    final_results_df_dict = {}
    for esc, data_list in resultados.items():
        if data_list:
            final_results_df_dict[esc] = pd.DataFrame(data_list)
            logger.info(f"✅ Escenario {esc}: {len(data_list)} créditos procesados")
        else:
            final_results_df_dict[esc] = pd.DataFrame(columns=["ID_producto", "VP_promedio"])
            logger.warning(f"⚠️ Escenario {esc}: Sin resultados")
    
    logger.info(f"🎯 Descuentos normativos completados para {len(ESCENARIOS_ESTRES)} escenarios")
    return final_results_df_dict


def _descontar_flujo(df_flujo: pd.DataFrame, curva_estresada: pd.DataFrame, fecha_corte: pd.Timestamp) -> float:
    logger.debug(f"🔄 Descontando {len(df_flujo)} flujos con curva de {len(curva_estresada)} puntos")
    """
    Descuenta flujos usando metodología normativa con factores t_k discretos.
    Utiliza búsqueda exacta por Nodo en la curva estresada específica.
    
    FÓRMULA NORMATIVA SFC:
    --------------------
    FD(t_k) = exp(-r · t_k)
    VP = Flujo × FD(t_k)
    
    donde r = ln(1 + EA) es la tasa cero cupón (short rate) de la curva estresada
    y t_k es el factor de tiempo discreto normativo SFC
    
    Args:
        df_flujo: DataFrame con flujos de caja
        curva_estresada: DataFrame con curva de estrés específica (columnas: Nodo, Tiempo, Tasa)
                        IMPORTANTE: La Tasa debe estar en SHORT RATES (ya transformada)
        fecha_corte: Fecha de corte para cálculo de días
        
    Returns:
        float: Valor presente total descontado
    """
    if df_flujo.empty or curva_estresada.empty:
        logger.debug("⚠️ DataFrame vacío, retornando VP = 0")
        return 0.0

    # Filtrar solo flujos futuros
    df = df_flujo.copy()
    df["Fecha_Pago"] = pd.to_datetime(df["Fecha_Pago"])
    df = df[df["Fecha_Pago"] >= fecha_corte].copy()
    if df.empty:
        return 0.0

    # Asignar Nodo y factor t_k a cada flujo
    logger.debug("🔢 Asignando nodos y factores t_k...")
    df = asignar_nodo_y_tk_a_flujos(df, fecha_corte)
    logger.debug(f"📊 Nodos asignados - Rango: {df['Nodo'].min()} a {df['Nodo'].max()} días")
    
    # Preparar curva estresada para búsqueda exacta
    curva_clean = curva_estresada[curva_estresada["Tasa"].notnull()].copy()
    if curva_clean.empty:
        logger.warning("⚠️ Curva estresada sin tasas válidas")
        return 0.0
    logger.debug(f"📈 Curva limpia con {len(curva_clean)} puntos válidos")
    
    # Determinar columna de flujo a usar
    if "Flujo_Total_Ajustado" in df.columns:
        df["Flujo"] = df["Flujo_Total_Ajustado"]
    elif "Flujo_Total" in df.columns:
        df["Flujo"] = df["Flujo_Total"]
    else:
        df["Flujo"] = 0.0

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
            
        # Búsqueda exacta por Nodo en curva estresada
        if "Nodo" in curva_clean.columns:
            tasa_row = curva_clean[curva_clean["Nodo"] == nodo]
        else:
            # Si no hay columna Nodo, usar Tiempo (convertir días a años)
            tiempo_anios = nodo / 365.0
            tasa_row = curva_clean[abs(curva_clean["Tiempo"] - tiempo_anios) < 0.01]
        
        if not tasa_row.empty:
            tasa_short = tasa_row["Tasa"].iloc[0]  # Ya es short rate
            matches_exactos += 1
        else:
            # Si no hay coincidencia exacta, buscar el más cercano
            if "Nodo" in curva_clean.columns:
                diferencias = abs(curva_clean["Nodo"] - nodo)
                idx_cercano = diferencias.idxmin()
            else:
                tiempo_anios = nodo / 365.0
                diferencias = abs(curva_clean["Tiempo"] - tiempo_anios)
                idx_cercano = diferencias.idxmin()
            tasa_short = curva_clean.loc[idx_cercano, "Tasa"]
        
        # ========================================================================
        # FÓRMULA NORMATIVA SFC: FD(t_k) = exp(-r · t_k)
        # ========================================================================
        # donde r es la tasa short rate (ya transformada desde curva estresada)
        # y t_k es el factor de tiempo discreto normativo
        
        if not pd.isna(tasa_short):
            factor_descuento = np.exp(-tasa_short * t_k)  # FD = e^(-r·t_k)
            vp_flujo = flujo * factor_descuento  # VP = Flujo × FD
            vp_total += vp_flujo
    
    logger.debug(f"📊 VP calculado: {vp_total:,.2f} ({flujos_procesados} flujos, {matches_exactos} matches exactos)")
    return vp_total

def _detectar_moneda(df_flujo: pd.DataFrame) -> str:
    if "Moneda" in df_flujo.columns:
        valores = df_flujo["Moneda"].dropna().unique()
        if len(valores) > 0:
            return valores[0]
    return "COP"