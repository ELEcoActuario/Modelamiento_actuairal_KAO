import pandas as pd
import logging

# Configurar logger para este módulo
logger = logging.getLogger(__name__)

def validar_hojas_y_columnas(df_creditos, df_tasas_mercado, df_tasas_libres, df_curva_hw=None):
    logger.info(" Iniciando validación de hojas y columnas")
    """
    Valida que los DataFrames contengan las columnas mínimas necesarias.
    Lanza ValueError si falta alguna columna.
    """
    # Normalización de compatibilidad para rutas que no pasen por la UI
    try:
        if 'Periodisidad_Pago' in df_creditos.columns and 'Periodicidad_Pago' not in df_creditos.columns:
            logger.warning("Renombrando columna 'Periodisidad_Pago' -> 'Periodicidad_Pago' por compatibilidad")
            df_creditos.rename(columns={'Periodisidad_Pago': 'Periodicidad_Pago'}, inplace=True)
        if 'Monto' in df_creditos.columns and 'Valor' not in df_creditos.columns:
            logger.warning("Renombrando columna 'Monto' -> 'Valor' por compatibilidad")
            df_creditos.rename(columns={'Monto': 'Valor'}, inplace=True)
    except Exception:
        # Si algo falla en aliasing, se sigue con la validación para reportar faltantes
        logger.exception("Error intentando normalizar columnas de compatibilidad en df_creditos")
    columnas_creditos = [
        'ID_producto', 'Tipo_Amortizacion', 'Tipo_producto', 'Valor', 'Tasa',
        'Numero_Cuotas', 'Fecha_Desembolso', 'Fecha_Vencimiento', 'Moneda', 'Periodicidad_Pago'
    ]
    columnas_tasasM = ['Fecha']
    columnas_tasasLR = ['Nodo', 'Tiempo', 'COP', 'USD', 'UVR']
    
    logger.debug(f" Validando {len(df_creditos)} créditos, {len(df_tasas_mercado)} tasas mercado, {len(df_tasas_libres)} tasas LR")

    faltantes = []
    for col in columnas_creditos:
        if col not in df_creditos.columns:
            logger.error(f" Columna faltante en créditos: {col}")
            faltantes.append(f"data_credito: {col}")
    for col in columnas_tasasM:
        if col not in df_tasas_mercado.columns:
            logger.error(f" Columna faltante en tasas mercado: {col}")
            faltantes.append(f"data_tasasM: {col}")
    for col in columnas_tasasLR:
        if col not in df_tasas_libres.columns:
            logger.error(f" Columna faltante en tasas LR: {col}")
            faltantes.append(f"data_tasasLR: {col}")
    
    # Validar CurvaHW si se proporciona
    if df_curva_hw is not None:
        if df_curva_hw.empty:
            logger.error(" CurvaHW está vacía")
            faltantes.append("CurvaHW: La hoja está vacía")
        else:
            # Validar que tiene al menos una columna numérica
            columnas_numericas = df_curva_hw.select_dtypes(include=['float64', 'int64']).columns
            if len(columnas_numericas) == 0:
                logger.error(" CurvaHW no tiene columnas numéricas")
                faltantes.append("CurvaHW: No se encontraron columnas numéricas con tasas de mercado")
            else:
                # Mostrar solo el conteo y rango de columnas (no la lista completa)
                logger.info(f" CurvaHW validada: {len(df_curva_hw)} registros, {len(columnas_numericas)} columnas numéricas ('{columnas_numericas[0]}' a '{columnas_numericas[-1]}')")

    if faltantes:
        logger.error(f" Validación fallida: {len(faltantes)} columnas faltantes")
        raise ValueError(f"Faltan columnas requeridas: {', '.join(faltantes)}")

    logger.info(" Validación de columnas completada exitosamente")
    return True