import pandas as pd
import numpy as np
import logging
from typing import Union

logger = logging.getLogger(__name__)

def interpolar_tasas_diarias(
    trayectorias_semanales: np.ndarray,
    fecha_inicio_sim: pd.Timestamp,
    fechas_pago: Union[pd.Series, pd.DatetimeIndex],
    modo: str = "ea"
) -> np.ndarray:
    """
    Interpola tasas diarias para fechas de pago específicas usando trayectorias simuladas semanalmente.

    IMPORTANTE:
    - Por defecto (modo="ea"), la interpolación se hace en EA para compatibilidad total con el sistema existente.
    - Opcionalmente (modo="short"), se convierte a short rate (ln(1+EA)), se interpola lineal en short
      y al final se reconvierte a EA. Esto evita el sesgo de promediar exponenciales.

    Cumple con requisitos normativos de interpolación en flujos proyectados por simulación estocástica (e.g. Vasicek).

    Args:
        trayectorias_semanales (np.ndarray): Shape (n_semanas+1, n_simulaciones) EN EA
        fecha_inicio_sim (pd.Timestamp): Fecha base desde la cual inicia la simulación.
        fechas_pago (pd.Series): Fechas objetivo a interpolar (debe ser convertible a datetime).

    Returns:
        np.ndarray: Shape (n_simulaciones, n_fechas_pago) con tasas interpoladas EN EA.
    """
    if trayectorias_semanales.ndim != 2:
        raise ValueError("La matriz de trayectorias debe tener 2 dimensiones: (tiempo, simulaciones).")

    fechas_pago = pd.to_datetime(fechas_pago)
    dias_desde_inicio = (fechas_pago - fecha_inicio_sim).dt.days.values

    if np.any(dias_desde_inicio < 0):
        logger.warning("⚠️ Algunas fechas de pago están antes de la fecha de inicio de simulación. Se truncarán a t=0.")

    indices_previos = (dias_desde_inicio // 7).astype(int)
    pesos = ((dias_desde_inicio % 7) / 7).astype(float)
    indices_siguientes = indices_previos + 1

    max_idx = trayectorias_semanales.shape[0] - 1
    indices_previos = np.clip(indices_previos, 0, max_idx)
    indices_siguientes = np.clip(indices_siguientes, 0, max_idx)

    # Seleccionar matrices según modo
    if modo.lower() == "short":
        # Convertir EA → short para interpolar linealmente
        base_prev = np.log1p(trayectorias_semanales[indices_previos, :])
        base_next = np.log1p(trayectorias_semanales[indices_siguientes, :])
        interpolado_short = base_prev + (base_next - base_prev) * pesos[:, np.newaxis]
        # Reconversión a EA
        tasas_interpoladas = np.expm1(interpolado_short)
        logger.debug("📐 Interpolación en SHORT realizada y convertida a EA")
    else:
        # Interpolación lineal en EA (comportamiento por defecto)
        tasas_previas = trayectorias_semanales[indices_previos, :]
        tasas_siguientes = trayectorias_semanales[indices_siguientes, :]
        tasas_interpoladas = tasas_previas + (tasas_siguientes - tasas_previas) * pesos[:, np.newaxis]
    
    # Logging de verificación
    logger.debug(f"📊 Interpolación completada: {tasas_interpoladas.shape[1]} fechas, rango EA [{tasas_interpoladas.min():.6f}, {tasas_interpoladas.max():.6f}] (modo={modo})")

    return tasas_interpoladas.T  # Shape: (n_simulaciones, n_fechas_pago) EN EA
