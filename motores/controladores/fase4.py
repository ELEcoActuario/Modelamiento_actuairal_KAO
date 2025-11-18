import pandas as pd
import numpy as np
import logging
from motores.descuentos.descuento_base import calcular_descuento_base
from motores.descuentos.descuento_normativo import calcular_descuentos_normativos

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

def validar_estructura_flujos(portafolio, nombre_portafolio="portafolio"):
    """
    Valida que todos los flujos tengan la estructura correcta para Fase 4.
    
    Args:
        portafolio: Dict[id_credito] -> List[DataFrame]
        nombre_portafolio: Nombre del portafolio para logging
        
    Returns:
        bool: True si la estructura es válida
        
    Raises:
        ValueError: Si encuentra problemas críticos de estructura
    """
    columnas_requeridas = ['Capital_Ajustado', 'Intereses_Ajustados', 
                          'Flujo_Total_Ajustado', 'Prepago_Esperado']
    
    creditos_invalidos = []
    
    for id_credito, lista_flujos in portafolio.items():
        if not isinstance(lista_flujos, list):
            creditos_invalidos.append(f"{id_credito}: no es lista")
            continue
            
        if not lista_flujos:
            logger.debug(f"📋 {nombre_portafolio} - Crédito {id_credito}: lista vacía")
            continue
            
        for i, df_flujo in enumerate(lista_flujos):
            if df_flujo is None or df_flujo.empty:
                continue
                
            # Validar columnas requeridas
            columnas_faltantes = [col for col in columnas_requeridas if col not in df_flujo.columns]
            if columnas_faltantes:
                creditos_invalidos.append(
                    f"{id_credito}[{i}]: faltan columnas {columnas_faltantes}"
                )
    
    if creditos_invalidos:
        logger.error(f"❌ {nombre_portafolio} - Estructura inválida en {len(creditos_invalidos)} flujos:")
        for error in creditos_invalidos[:5]:  # Mostrar solo primeros 5 errores
            logger.error(f"   • {error}")
        if len(creditos_invalidos) > 5:
            logger.error(f"   • ... y {len(creditos_invalidos) - 5} errores más")
        
        raise ValueError(f"Estructura de flujos inválida en {nombre_portafolio}. "
                        f"Verifique que todos los DataFrames tengan las columnas: {columnas_requeridas}")
    
    logger.info(f"✅ {nombre_portafolio} - Estructura validada correctamente")
    return True

def construir_dataframe_flujos_descuentos(
    curvas_base,
    curvas_estresadas,
    portafolio_base,
    portafolio_estresado,
    fecha_corte
):
    logger.info(f"💰 Iniciando construcción de DataFrame de descuentos para {len(portafolio_base)} créditos")
    
    # AUDITORÍA: Logging detallado del estado inicial
    logger.info(f"📊 AUDITORÍA - Estado inicial:")
    logger.info(f"   • Portafolio base: {len(portafolio_base)} créditos")
    logger.info(f"   • Portafolio estresado: {len(portafolio_estresado)} créditos")
    logger.info(f"   • Curvas base disponibles: {list(curvas_base.keys()) if curvas_base else 'None'}")
    logger.info(f"   • Curvas estresadas disponibles: {list(curvas_estresadas.keys()) if curvas_estresadas else 'None'}")
    
    # VALIDACIÓN CRÍTICA: Verificar estructura de portafolios antes del procesamiento
    try:
        validar_estructura_flujos(portafolio_base, "portafolio_base")
        validar_estructura_flujos(portafolio_estresado, "portafolio_estresado")
        logger.info("✅ AUDITORÍA - Validación de estructura completada exitosamente")
    except ValueError as e:
        logger.error(f"❌ AUDITORÍA - Error de validación de estructura: {e}")
        raise
    
    resultados_intermedios_base = []

    for id_credito, lista_flujos_base_sims in portafolio_base.items():
        if not lista_flujos_base_sims:
            logger.warning(f"⚠️ Crédito {id_credito}: Sin flujos base")
            continue

        moneda = _detectar_moneda(lista_flujos_base_sims[0])
        logger.debug(f"💱 Crédito {id_credito}: Moneda detectada = {moneda}")
        
        curva_base = curvas_base.get(moneda)
        if curva_base is None or curva_base.empty:
            logger.warning(f"⚠️ Crédito {id_credito}: Sin curva base para moneda {moneda}")
            resultados_intermedios_base.append({
                "ID_producto": id_credito,
                "VP_base": 0
            })
            continue

        vps_base_por_simulacion = []
        for i, df_flujo_base_sim in enumerate(lista_flujos_base_sims):
            if df_flujo_base_sim is not None and not df_flujo_base_sim.empty:
                # VALIDACIÓN ADICIONAL: Verificar que el DataFrame tiene las columnas correctas
                try:
                    columnas_criticas = ['Capital_Ajustado', 'Flujo_Total_Ajustado']
                    for col in columnas_criticas:
                        if col not in df_flujo_base_sim.columns:
                            logger.error(f"❌ Crédito {id_credito}[{i}]: Falta columna crítica '{col}'")
                            logger.error(f"   Columnas disponibles: {list(df_flujo_base_sim.columns)}")
                            continue
                    
                    vp = calcular_descuento_base(df_flujo_base_sim, curva_base, fecha_corte, moneda)
                    vps_base_por_simulacion.append(vp)
                    if i == 0:  # Log solo primera simulación para evitar spam
                        logger.debug(f"💰 Crédito {id_credito}: VP simulación {i+1} = {vp:,.2f}")
                        
                except Exception as e:
                    logger.error(f"❌ Error calculando VP para crédito {id_credito}[{i}]: {e}")
                    logger.debug(f"   DataFrame shape: {df_flujo_base_sim.shape}")
                    logger.debug(f"   DataFrame columns: {list(df_flujo_base_sim.columns)}")
                    continue
        
        vp_base_prom = np.mean(vps_base_por_simulacion) if vps_base_por_simulacion else 0
        logger.debug(f"📊 Crédito {id_credito}: VP base promedio = {vp_base_prom:,.2f} ({len(vps_base_por_simulacion)} simulaciones)")

        resultados_intermedios_base.append({
            "ID_producto": id_credito,
            "VP_base": vp_base_prom
        })

    df_resultados_final = pd.DataFrame(resultados_intermedios_base)
    logger.info(f"✅ VP base calculados para {len(df_resultados_final)} créditos")
    
    logger.info("🔥 Iniciando cálculo de VP estresados por escenario...")
    vps_estresados_por_escenario = calcular_descuentos_normativos(
        portafolio_estresado,
        curvas_estresadas,
        fecha_corte
    )
    
    for esc in ESCENARIOS_ESTRES:
        col_name = f"VP_est_{esc}"  # Ya no reemplazamos espacios, usamos el nombre directo
        df_vp_proms_esc = vps_estresados_por_escenario.get(esc)
        
        if df_vp_proms_esc is not None and not df_vp_proms_esc.empty:
            logger.debug(f"🔥 Escenario {esc}: {len(df_vp_proms_esc)} VP calculados")
            
            # AUDITORÍA: Log de primeros valores para verificación
            if not df_vp_proms_esc.empty:
                primer_credito = df_vp_proms_esc.iloc[0]
                logger.info(f"🔍 AUDITORÍA - {esc} - Primer crédito: {primer_credito['ID_producto']} = {primer_credito['VP_promedio']:,.2f}")
            
            df_vp_proms_esc = df_vp_proms_esc.rename(columns={"VP_promedio": col_name})
            
            df_resultados_final = pd.merge(
                df_resultados_final,
                df_vp_proms_esc[["ID_producto", col_name]],
                on="ID_producto",
                how="left"
            )
            df_resultados_final[col_name] = df_resultados_final[col_name].fillna(0)
            
        else:
            logger.warning(f"⚠️ Escenario {esc}: Sin datos de VP")
            if col_name not in df_resultados_final.columns:
                df_resultados_final[col_name] = 0.0

    logger.info(f"✅ DataFrame de descuentos construido: {len(df_resultados_final)} créditos, {len(df_resultados_final.columns)} columnas")
    
    # AUDITORÍA: Mostrar nombres de columnas finales
    logger.info(f"🔍 AUDITORÍA - Columnas finales en DataFrame: {list(df_resultados_final.columns)}")
    
    # AUDITORÍA: Mostrar primera fila completa
    if not df_resultados_final.empty:
        primera_fila = df_resultados_final.iloc[0]
        logger.info(f"🔍 AUDITORÍA - Primera fila completa:")
        logger.info(f"   ID: {primera_fila['ID_producto']}")
        logger.info(f"   VP_base: {primera_fila['VP_base']:,.2f}")
        for esc in ESCENARIOS_ESTRES:
            col_name = f"VP_est_{esc}"
            if col_name in primera_fila:
                logger.info(f"   {col_name}: {primera_fila[col_name]:,.2f}")
    
    return df_resultados_final

def _detectar_moneda(df_flujo):
    if "Moneda" in df_flujo.columns:
        valores = df_flujo["Moneda"].dropna().unique()
        if len(valores) > 0:
            return valores[0]
    return "COP"

def formatear_curva_base(df_tasas_libres, moneda):
    """
    Formatea la curva base y TRANSFORMA tasas EA a short rates según normativa.
    
    TRANSFORMACIÓN NORMATIVA:
    ------------------------
    r = ln(1 + EA)
    
    Esta transformación es necesaria para aplicar la fórmula de descuento:
    FD(t_k) = exp(-r · t_k)
    """
    if df_tasas_libres.empty or moneda not in df_tasas_libres.columns:
        return pd.DataFrame()
    
    df = df_tasas_libres[["Nodo", "Tiempo", moneda]].copy()
    
    # Transformar EA a short rate
    tasa_ea = df[moneda].values
    
    # Normalizar si está en porcentaje
    if np.max(tasa_ea) > 1.0:
        logger.warning(f"⚠️ Curva base {moneda} detectada en porcentaje, normalizando /100")
        tasa_ea = tasa_ea / 100.0
    
    tasa_short = np.log1p(tasa_ea)  # ln(1 + EA)
    
    df["Tasa_EA"] = tasa_ea  # Guardar EA original
    df["Tasa"] = tasa_short  # Short rate para descuento
    df["Moneda"] = moneda
    
    logger.info(f"✅ Curva base {moneda} transformada: EA → Short Rate")
    logger.debug(f"   Rango EA: [{tasa_ea.min():.6f}, {tasa_ea.max():.6f}]")
    logger.debug(f"   Rango Short: [{tasa_short.min():.6f}, {tasa_short.max():.6f}]")
    
    return df

def formatear_curvas_estresadas(dict_curvas_norm, moneda):
    curvas = {}
    df_moneda = dict_curvas_norm.get(moneda, pd.DataFrame())
    
    if 'Choque' not in df_moneda.columns:
        return curvas

    for esc in ESCENARIOS_ESTRES:
        df_esc = df_moneda[df_moneda["Choque"] == esc].copy()
        if not df_esc.empty:
            curvas[esc] = df_esc[["Nodo", "Tiempo", "Tasa", "Moneda"]]
        else:
            curvas[esc] = pd.DataFrame()
    return curvas