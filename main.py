from interfaces.app_principal import App
from utils.logger_config import configurar_logging_global
import logging
import os
from datetime import datetime

if __name__ == "__main__":
    # Configurar logging global
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_log = f"logs/modelo_kao_{timestamp}.log"
    
    try:
        configurar_logging_global(
            nivel=logging.INFO,  # INFO para ver mensajes de diagnóstico
            archivo_log=archivo_log
        )
        
        logger = logging.getLogger(__name__)
        logger.info("Iniciando aplicación Modelo KAO MultiMode")
        
        app = App()
        app.mainloop()
        
    except Exception as e:
        if 'logger' in locals():
            logger.critical(f"Error crítico en inicialización: {e}", exc_info=True)
        else:
            # Configuración mínima de logging para registrar el error antes de la configuración global
            logging.basicConfig(level=logging.CRITICAL)
            logging.critical("Error crítico antes de configurar logging: %s", e, exc_info=True)
        raise
