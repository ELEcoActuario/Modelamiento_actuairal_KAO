import numpy as np
import logging
from typing import Dict

logger = logging.getLogger(__name__)

def simular_trayectorias_vasicek_por_tipo(
    parametros_por_tipo: Dict[str, Dict[str, float]],
    r0_por_tipo: Dict[str, float],
    n_simulaciones: int,
    plazo_semanas: int,
    metodo_simulacion: str = "em"
) -> Dict[str, np.ndarray]:
    """
    Simula trayectorias semanales del modelo Vasicek por tipo de crédito.

    IMPORTANTE: Los parámetros están en SHORT RATE SPACE, pero r0_por_tipo viene en EA.
    Se simula en short rates y se retorna en EA para compatibilidad.

    EULER-MARUYAMA DISCRETIZATION (según tesis):
    ============================================
    Ecuación diferencial estocástica:
        dr_t = κ(θ - r_t)dt + σdX_t
    
    Discretización Euler-Maruyama para paso Δ:
        r_{t+Δ} - r_t = κ(θ - r_t)Δ + ε_{t+Δ}
        r_{t+Δ} = r_t + κ(θ - r_t)Δ + ε_{t+Δ}
    
    donde ε_{t+Δ} ~ N(0, σ²Δ)

    Args:
        parametros_por_tipo (dict): Parámetros calibrados en SHORT RATE SPACE
        r0_por_tipo (dict): Tasa inicial por tipo de crédito EN EA (se transforma internamente)
        n_simulaciones (int): Número de simulaciones Monte Carlo.
        plazo_semanas (int): Horizonte de simulación en semanas.
        metodo_simulacion (str): Método de simulación (solo 'em' para Euler-Maruyama)

    Returns:
        dict: {'Comercial': ndarray(tiempos × simulaciones), ...} EN EA PARA COMPATIBILIDAD
    """
    logger.info("🎲 Iniciando simulación de trayectorias Vasicek semanales (SHORT RATES → EA)...")

    resultados_simulacion = {}
    dt = 7 / 365.0  # paso semanal (años) homogenizado a base 365

    for tipo_credito, params in parametros_por_tipo.items():
        kappa = params["kappa"]
        theta = params["theta"]  # theta en short rate space
        sigma = params["sigma"]  # sigma en short rate space
        
        # TRANSFORMACIÓN CRÍTICA: EA → Short Rate para r0
        r0_ea = r0_por_tipo.get(tipo_credito, np.exp(theta) - 1)  # fallback a theta convertido
        # Guardar robustez: si r0 viene en porcentaje (e.g., 15 → 15%), normalizar a decimal
        if r0_ea > 1.0 and r0_ea <= 100.0:
            logger.warning(f"r0 EA para '{tipo_credito}' parece porcentaje ({r0_ea}); se normaliza dividiendo por 100")
            r0_ea = r0_ea / 100.0
        r0_short = np.log(1 + r0_ea)  # Transformar EA → Short Rate
        
        if tipo_credito not in r0_por_tipo:
            logger.warning(f"No se encontró r0 EA para '{tipo_credito}'. Se usa θ convertido = {r0_ea:.4f} EA como inicial.")
        
        logger.info(f"🔄 {tipo_credito}: r0 EA={r0_ea:.6f} → Short Rate={r0_short:.6f}")

        # SIMULACIÓN EN SHORT RATE SPACE USANDO EULER-MARUYAMA
        tasas_short = np.zeros((plazo_semanas + 1, n_simulaciones))
        tasas_short[0, :] = r0_short
        rng = np.random.default_rng()
        
        # Generar choques aleatorios ε_{t+Δ} ~ N(0, σ²Δ)
        # Implementación: primero N(0,1), luego multiplicar por σ√Δ
        shocks_dt = rng.normal(loc=0.0, scale=1.0, size=(plazo_semanas, n_simulaciones))

        # Pre-cálculos para Euler-Maruyama
        kdt = kappa * dt  # κΔ
        sigma_sqrt_dt = sigma * np.sqrt(dt)  # σ√Δ
        
        logger.info(f"🧭 Vasicek '{tipo_credito}': Euler-Maruyama con Δ={dt:.6f}, κΔ={kdt:.6f}, σ√Δ={sigma_sqrt_dt:.6f}")

        # DISCRETIZACIÓN EULER-MARUYAMA:
        # r_{t+Δ} = r_t + κ(θ - r_t)Δ + σ√Δ·Z_t, donde Z_t ~ N(0,1)
        for t in range(1, plazo_semanas + 1):
            prev = tasas_short[t - 1, :]  # r_t
            drift = kdt * (theta - prev)  # κ(θ - r_t)Δ
            diffusion = sigma_sqrt_dt * shocks_dt[t - 1, :]  # σ√Δ·Z_t = ε_{t+Δ}
            tasas_short[t, :] = prev + drift + diffusion  # r_{t+Δ}
        
        # Diagnóstico: verificar varianza empírica del término aleatorio vs. σ²Δ teórico
        try:
            # Residuales: ε = r_{t+Δ} - [r_t + κ(θ - r_t)Δ]
            resid = tasas_short[1:, :] - (tasas_short[:-1, :] + kdt * (theta - tasas_short[:-1, :]))
            var_emp = float(np.var(resid, ddof=1))
            var_teo = float((sigma ** 2) * dt)  # σ²Δ
            ratio = var_emp / var_teo if var_teo > 0 else np.nan
            logger.info(f"🧪 Vasicek '{tipo_credito}': Var(emp)/Var(teo)={ratio:.3f} (emp={var_emp:.6g}, teo={var_teo:.6g})")
        except Exception:
            pass
        
        # RETRANSFORMACIÓN CRÍTICA: Short Rate → EA para compatibilidad
        tasas_ea = np.exp(tasas_short) - 1
        
        # Logging de verificación
        logger.debug(f"📊 {tipo_credito}: Short rates rango [{tasas_short.min():.6f}, {tasas_short.max():.6f}]")
        logger.debug(f"📊 {tipo_credito}: EA convertidas rango [{tasas_ea.min():.6f}, {tasas_ea.max():.6f}]")

        resultados_simulacion[tipo_credito] = tasas_ea  # RETORNAR EN EA
        logger.info(f"✅ Simulación completada para '{tipo_credito}' (Short → EA convertido).")

    logger.info(f"🎯 Simulación Vasicek completada: {len(resultados_simulacion)} tipos, matrices en EA para comparación directa")
    return resultados_simulacion
