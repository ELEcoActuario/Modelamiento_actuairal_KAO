#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidad para analizar información específica de créditos individuales.
Identifica moneda, fecha de finalización y nodos necesarios para cada crédito.
"""

import pandas as pd
import logging
from typing import Dict, Tuple, Optional

def identificar_info_credito(id_credito: str, df_creditos: pd.DataFrame, 
                           flujos_credito: pd.DataFrame, fecha_corte: pd.Timestamp) -> Dict:
    """
    Identifica información específica de un crédito individual.
    
    Args:
        id_credito: ID del crédito a analizar
        df_creditos: DataFrame con información de créditos
        flujos_credito: DataFrame con flujos contractuales del crédito
        fecha_corte: Fecha de corte para el cálculo
        
    Returns:
        Dict con información del crédito: {
            'moneda': str,
            'fecha_finalizacion': pd.Timestamp,
            'dias_hasta_finalizacion': int,
            'nodos_necesarios': list,
            'valido': bool
        }
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 1. Identificar moneda del crédito
        credito_info = df_creditos[df_creditos["ID_producto"] == id_credito]
        if credito_info.empty:
            logger.warning(f"⚠️ Crédito {id_credito} no encontrado en df_creditos")
            return {'valido': False, 'error': 'Crédito no encontrado'}
        
        moneda = credito_info["Moneda"].values[0] if "Moneda" in credito_info.columns else "COP"
        
        # 2. Calcular fecha de finalización de amortización
        if flujos_credito.empty:
            logger.warning(f"⚠️ No hay flujos para crédito {id_credito}")
            return {'valido': False, 'error': 'Sin flujos contractuales'}
        
        # Convertir fechas de pago a datetime si no lo están
        # Intentar con 'Fecha_Pago' primero, luego con 'Fecha'
        if 'Fecha_Pago' in flujos_credito.columns:
            fechas_pago = pd.to_datetime(flujos_credito['Fecha_Pago'])
        elif 'Fecha' in flujos_credito.columns:
            fechas_pago = pd.to_datetime(flujos_credito['Fecha'])
        else:
            logger.error(f"❌ No se encontró columna de fecha en flujos de crédito {id_credito}")
            return {'valido': False, 'error': 'Sin columna de fecha'}
        
        fecha_finalizacion = fechas_pago.max()
        
        # 3. Contar días entre fecha corte y fecha finalización
        dias_hasta_finalizacion = (fecha_finalizacion - fecha_corte).days
        
        # 4. Generar lista de nodos necesarios (desde día 1 hasta finalización)
        nodos_necesarios = list(range(1, dias_hasta_finalizacion + 1))
        
        logger.debug(f"📋 Crédito {id_credito}: {moneda}, {dias_hasta_finalizacion} días, {len(nodos_necesarios)} nodos")
        
        return {
            'id_credito': id_credito,
            'moneda': moneda,
            'fecha_finalizacion': fecha_finalizacion,
            'dias_hasta_finalizacion': dias_hasta_finalizacion,
            'nodos_necesarios': nodos_necesarios,
            'cantidad_nodos': len(nodos_necesarios),
            'valido': True
        }
        
    except Exception as e:
        logger.error(f"❌ Error analizando crédito {id_credito}: {e}")
        return {'valido': False, 'error': str(e)}

def filtrar_curva_por_credito(df_tasas_lr: pd.DataFrame, info_credito: Dict, 
                             fecha_corte: pd.Timestamp) -> pd.DataFrame:
    """
    Filtra la curva de tasas LR para usar solo los nodos necesarios del crédito específico.
    
    Args:
        df_tasas_lr: DataFrame con data_tasasLR completa
        info_credito: Información del crédito (resultado de identificar_info_credito)
        fecha_corte: Fecha de corte
        
    Returns:
        DataFrame filtrado con solo los nodos necesarios para este crédito
    """
    logger = logging.getLogger(__name__)
    
    if not info_credito.get('valido', False):
        logger.error(f"❌ Información de crédito inválida: {info_credito.get('error', 'Error desconocido')}")
        return pd.DataFrame()
    
    moneda = info_credito['moneda']
    nodos_necesarios = info_credito['nodos_necesarios']
    
    # Verificar que la moneda existe en data_tasasLR
    if moneda not in df_tasas_lr.columns:
        logger.error(f"❌ Moneda {moneda} no encontrada en data_tasasLR")
        return pd.DataFrame()
    
    # Filtrar solo los nodos necesarios
    curva_filtrada = df_tasas_lr[df_tasas_lr['Nodo'].isin(nodos_necesarios)].copy()
    
    if curva_filtrada.empty:
        logger.warning(f"⚠️ No se encontraron nodos para crédito en moneda {moneda}")
        return pd.DataFrame()
    
    # Asignar fechas si no existen
    if 'Fecha' not in curva_filtrada.columns:
        curva_filtrada['Fecha'] = curva_filtrada['Nodo'].apply(
            lambda nodo: fecha_corte + pd.Timedelta(days=int(nodo))
        )
    
    # Seleccionar solo las columnas necesarias para el modelo
    columnas_modelo = ['Nodo', 'Tiempo', 'Fecha', moneda]
    curva_modelo = curva_filtrada[columnas_modelo].copy()
    curva_modelo = curva_modelo.rename(columns={moneda: 'Tasa'})
    curva_modelo = curva_modelo.dropna()
    curva_modelo = curva_modelo.sort_values('Nodo').reset_index(drop=True)
    
    logger.info(f"📊 Curva filtrada para crédito {info_credito['id_credito']}: "
               f"{len(curva_modelo)} nodos ({moneda})")
    
    return curva_modelo

def procesar_todos_creditos(df_creditos: pd.DataFrame, flujos_originales: Dict, 
                          fecha_corte: pd.Timestamp) -> Dict:
    """
    Procesa todos los créditos para identificar su información específica.
    
    Args:
        df_creditos: DataFrame con información de todos los créditos
        flujos_originales: Dict con flujos contractuales por ID_producto
        fecha_corte: Fecha de corte
        
    Returns:
        Dict con información procesada de todos los créditos
    """
    logger = logging.getLogger(__name__)
    logger.info("🔍 Procesando información específica de todos los créditos...")
    
    creditos_procesados = {}
    
    for id_credito, flujos in flujos_originales.items():
        info_credito = identificar_info_credito(id_credito, df_creditos, flujos, fecha_corte)
        creditos_procesados[id_credito] = info_credito
    
    # Estadísticas de procesamiento
    creditos_validos = sum(1 for info in creditos_procesados.values() if info.get('valido', False))
    total_creditos = len(creditos_procesados)
    
    logger.info(f"✅ Procesamiento completado: {creditos_validos}/{total_creditos} créditos válidos")
    
    # Mostrar estadísticas por moneda
    monedas_stats = {}
    for info in creditos_procesados.values():
        if info.get('valido', False):
            moneda = info['moneda']
            if moneda not in monedas_stats:
                monedas_stats[moneda] = {'count': 0, 'max_dias': 0, 'min_dias': float('inf')}
            monedas_stats[moneda]['count'] += 1
            monedas_stats[moneda]['max_dias'] = max(monedas_stats[moneda]['max_dias'], 
                                                   info['dias_hasta_finalizacion'])
            monedas_stats[moneda]['min_dias'] = min(monedas_stats[moneda]['min_dias'], 
                                                   info['dias_hasta_finalizacion'])
    
    for moneda, stats in monedas_stats.items():
        logger.info(f"💰 {moneda}: {stats['count']} créditos, "
                   f"rango {stats['min_dias']}-{stats['max_dias']} días")
    
    return creditos_procesados


def obtener_curva_especifica_credito(df_tasas_lr: pd.DataFrame, id_credito: str,
                                    df_creditos: pd.DataFrame, flujos_credito: pd.DataFrame,
                                    fecha_corte: pd.Timestamp) -> pd.DataFrame:
    """
    Función principal que obtiene la curva específica filtrada para un crédito.
    
    Args:
        df_tasas_lr: DataFrame con data_tasasLR completa
        id_credito: ID del crédito
        df_creditos: DataFrame con información de créditos
        flujos_credito: DataFrame con flujos del crédito
        fecha_corte: Fecha de corte
        
    Returns:
        DataFrame con curva filtrada específica para el crédito
    """
    logger = logging.getLogger(__name__)
    
    # Identificar información del crédito
    info_credito = identificar_info_credito(id_credito, df_creditos, flujos_credito, fecha_corte)
    
    if not info_credito.get('valido', False):
        logger.error(f"❌ No se pudo procesar crédito {id_credito}")
        return pd.DataFrame()
    
    # Filtrar curva específica
    curva_especifica = filtrar_curva_por_credito(df_tasas_lr, info_credito, fecha_corte)
    
    return curva_especifica
