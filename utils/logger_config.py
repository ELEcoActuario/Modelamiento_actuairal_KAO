"""
Configuración centralizada de logging para el proyecto.
"""

import logging
import os
from datetime import datetime
from functools import wraps
import traceback


def configurar_logging_global(nivel=logging.INFO, archivo_log=None):
    """
    Configura el sistema de logging global del proyecto.
    
    Args:
        nivel: Nivel de logging (default: INFO)
        archivo_log: Ruta del archivo de log (opcional, se genera automático si no se proporciona)
    
    Returns:
        Ruta del archivo de log configurado
    """
    # Crear directorio de logs si no existe
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Usar archivo proporcionado o generar uno con timestamp
    if archivo_log is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(log_dir, f'modelo_kao_{timestamp}.log')
    else:
        log_file = archivo_log
    
    # Configurar formato
    formato = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s'
    
    # Configurar logging
    logging.basicConfig(
        level=nivel,
        format=formato,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"📝 Logging configurado - Archivo: {log_file}")
    logger.info("🚀 Sistema de logging global inicializado correctamente")
    
    return log_file


def log_error_detallado(logger, mensaje, exception=None, contexto=None):
    """
    Registra un error con detalles completos.
    
    Args:
        logger: Instancia del logger
        mensaje: Mensaje descriptivo del error
        exception: Excepción capturada (opcional)
        contexto: Dict con contexto adicional (opcional)
    """
    logger.error(f"❌ {mensaje}")
    
    if exception:
        logger.error(f"Tipo de error: {type(exception).__name__}")
        logger.error(f"Mensaje: {str(exception)}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
    
    if contexto:
        logger.error(f"Contexto: {contexto}")


def log_inicio_proceso(logger, proceso, parametros=None):
    """
    Registra el inicio de un proceso con sus parámetros.
    
    Args:
        logger: Instancia del logger
        proceso: Nombre del proceso
        parametros: Dict con parámetros del proceso (opcional)
    """
    if parametros:
        logger.info(f"🚀 INICIANDO: {proceso} | Parámetros: {parametros}")
    else:
        logger.info(f"🚀 INICIANDO: {proceso}")


def log_fin_proceso(logger, proceso, resultados=None, exitoso=True):
    """
    Registra la finalización de un proceso.
    
    Args:
        logger: Instancia del logger
        proceso: Nombre del proceso
        resultados: Dict con resultados o métricas (opcional)
        exitoso: Si el proceso terminó exitosamente (default: True)
    """
    emoji = "✅" if exitoso else "❌"
    estado = "COMPLETADO" if exitoso else "FALLIDO"
    if resultados:
        logger.info(f"{emoji} {estado}: {proceso} | Detalles: {resultados}")
    else:
        logger.info(f"{emoji} {estado}: {proceso}")


def log_metodo(func):
    """
    Decorador para logging automático de métodos.
    
    Usage:
        @log_metodo
        def mi_funcion(self, arg1, arg2):
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        func_name = func.__qualname__
        
        logger.debug(f"→ Entrando: {func_name}")
        try:
            resultado = func(*args, **kwargs)
            logger.debug(f"← Saliendo: {func_name}")
            return resultado
        except Exception as e:
            logger.error(f"✗ Error en {func_name}: {type(e).__name__}: {str(e)}")
            raise
    
    return wrapper
