import numpy as np
import pandas as pd
import logging
from typing import Dict, Tuple
from scipy.optimize import minimize

logger = logging.getLogger(__name__)

def _nll_ou_var_dt(params: np.ndarray, data: np.ndarray, dts: np.ndarray) -> float:
    """
    Función de log-verosimilitud negativa para el modelo Vasicek/OU.
    
    FÓRMULAS MLE (según tesis - Maximum Likelihood Estimator Method):
        E[r_{t+s} | r_t] = θ + (r_t - θ)e^{-κs}
        Var[r_{t+s} | r_t] = (σ²/2κ)(1 - e^{-2κs})
    
    donde:
        κ (kappa): velocidad de reversión a la media
        θ (theta): nivel de largo plazo (media de largo plazo)
        σ (sigma): volatilidad
        s: intervalo de tiempo entre observaciones
    """
    try:
        kappa, theta, sigma = float(params[0]), float(params[1]), float(params[2])
    except Exception:
        return np.inf
    if not np.isfinite(kappa) or not np.isfinite(theta) or not np.isfinite(sigma):
        return np.inf
    if kappa <= 0.0 or sigma <= 0.0:
        return np.inf
    if dts is None or len(dts) == 0:
        return np.inf
    r_t = data[1:]
    r_tm1 = data[:-1]
    if len(r_tm1) != len(dts):
        n = min(len(r_tm1), len(dts))
        r_t = r_t[:n]
        r_tm1 = r_tm1[:n]
        dts = dts[:n]
    
    # Fórmula MLE: E[r_{t+s} | r_t] = θ + (r_t - θ)e^{-κs}
    exp_kdt = np.exp(-kappa * dts)
    mean = theta + (r_tm1 - theta) * exp_kdt
    
    # Fórmula MLE: Var[r_{t+s} | r_t] = (σ²/2κ)(1 - e^{-2κs})
    var = (sigma**2 / (2.0 * kappa)) * (1.0 - np.exp(-2.0 * kappa * dts))
    
    if not np.all(np.isfinite(var)) or np.any(var <= 0.0):
        return np.inf
    nll = 0.5 * np.sum(np.log(2.0 * np.pi * var) + ((r_t - mean) ** 2) / var)
    return float(nll)

def calibrar_parametros_vasicek_mle_por_tipo(df_tasas_mercado: pd.DataFrame) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, float]]]:
    logger.info("🔧 Iniciando calibración MLE de Vasicek por tipo de crédito con transformación EA → Short Rate...")

    df = df_tasas_mercado.copy()
    df['Fecha'] = pd.to_datetime(df['Fecha'], format='%d/%m/%Y')
    df = df.set_index('Fecha').sort_index()

    tipos_credito_validos = [col for col in df.columns if col in ["Comercial", "Consumo", "Vivienda"]]
    if not tipos_credito_validos:
        raise ValueError("El DataFrame debe contener al menos una de las columnas: 'Comercial', 'Consumo', 'Vivienda'.")

    parametros_base = {}

    for tipo_credito in tipos_credito_validos:
        tasas_ea = df[tipo_credito].dropna()
        if tasas_ea.max() > 1.0 and tasas_ea.max() <= 100.0:
            tasas_ea = tasas_ea / 100.0
        if len(tasas_ea) < 3:
            logger.warning(f"'{tipo_credito}' tiene menos de 3 observaciones. Se omite.")
            continue
        
        # TRANSFORMACIÓN CRÍTICA: EA → Short Rate usando ln(1 + r)
        logger.info(f"📊 Transformando {len(tasas_ea)} tasas EA → Short Rates para {tipo_credito}")
        tasas_short = pd.Series(np.log1p(tasas_ea.values), index=tasas_ea.index)
        logger.debug(f"🔍 {tipo_credito}: EA rango [{tasas_ea.min():.6f}, {tasas_ea.max():.6f}] → Short rango [{tasas_short.min():.6f}, {tasas_short.max():.6f}]")
        
        # Usar tasas short para calibración
        tasas = tasas_short

        # MLE OU con Δ variable por observación
        r = tasas.values.astype(float)
        if len(r) < 3:
            logger.warning(f"'{tipo_credito}' tiene menos de 3 observaciones tras conversión. Se omite.")
            continue

        # Forzar Δ semanal fijo para coherencia con simulación y control de varianza del paso
        # (si se requiere volver a Δ variable, restaurar el cálculo con diferencias de fechas)
        idx = tasas.index
        dts = np.full(len(r) - 1, 7.0/365.0, dtype=float)
        dr = np.diff(r)
        kappa_init = 0.2
        theta_init = float(np.mean(r))
        mean_dt = float(np.mean(dts)) if len(dts) > 0 else (7.0/365.0)
        sigma_init = float(np.std(dr) / np.sqrt(mean_dt)) if len(dr) > 1 else 0.01
        sigma_init = max(sigma_init, 1e-4)

        x0 = np.array([kappa_init, theta_init, sigma_init], dtype=float)
        
        # BOUNDS MEJORADOS: Evitar convergencia a parámetros no razonables
        # kappa: Mínimo 0.01 (reversión en ~69 semanas), sin máximo
        # theta: Usar rango razonable basado en los datos
        #        Mínimo: 70% de la media de los datos (permite ajuste pero no colapso)
        #        Máximo: 150% de la media de los datos (permite crecimiento)
        # sigma: Positivo, sin máximo
        kappa_min = 0.01
        theta_min = max(0.7 * theta_init, 0.05)  # Mínimo 70% de media, o 5% EA
        theta_max = min(1.5 * theta_init, 0.69)  # Máximo 150% de media, o 100% EA
        
        bounds = ((kappa_min, None), (theta_min, theta_max), (1e-6, None))
        
        logger.info(f"   🔒 Bounds aplicados: κ≥{kappa_min}, θ∈[{theta_min},{theta_max}], σ>0")
        
        # Calcular NLL inicial (valor de partida)
        nll_inicial = _nll_ou_var_dt(x0, r, dts)
        logger.info(f"   🎯 MLE - Valores iniciales: κ={kappa_init:.4f}, θ={theta_init:.4f}, σ={sigma_init:.4f}")
        logger.info(f"   📉 NLL inicial: {nll_inicial:.4f}")
        
        try:
            # Ejecutar optimización MLE
            res = minimize(_nll_ou_var_dt, x0=x0, args=(r, dts), method="L-BFGS-B", bounds=bounds)
            
            # Calcular NLL final
            nll_final = res.fun
            mejora = nll_inicial - nll_final
            mejora_pct = (mejora / abs(nll_inicial)) * 100 if nll_inicial != 0 else 0
            
            logger.info(f"   🔄 MLE - Iteraciones: {res.nit}, Convergencia: {'✓' if res.success else '✗'}")
            logger.info(f"   📈 NLL final: {nll_final:.4f} (mejora: {mejora:.4f}, {mejora_pct:.2f}%)")
            
            if res.success and np.all(np.isfinite(res.x)):
                kappa_mle, theta_mle, sigma_mle = map(float, res.x)
                logger.info(f"   ✅ Optimización exitosa")
            else:
                logger.warning(f"   ⚠️ Optimización no convergió, usando valores iniciales")
                logger.warning(f"   Mensaje: {res.message}")
                kappa_mle, theta_mle, sigma_mle = map(float, x0)
        except Exception as e:
            logger.error(f"   ❌ Error en optimización MLE: {e}")
            logger.error(f"   Usando valores iniciales como fallback")
            kappa_mle, theta_mle, sigma_mle = map(float, x0)

        parametros_base[tipo_credito] = {
            "kappa": round(float(kappa_mle), 6),
            "theta": round(float(theta_mle), 6),  # theta en short rate space
            "sigma": round(float(sigma_mle), 6)   # sigma en short rate space
        }
        
        # CONVERSIÓN PARA LOGGING: mostrar theta equivalente en EA para referencia
        theta_ea_equiv = np.exp(theta_mle) - 1
        logger.info(f"✅ PARÁMETROS CALIBRADOS (SHORT RATES) - {tipo_credito}: {parametros_base[tipo_credito]}")
        logger.info(f"📊 Theta equivalente en EA: {theta_ea_equiv:.6f} ({theta_ea_equiv*100:.2f}%)")
        
        # Reporte de equivalentes AR(1) (Δ semanal) para auditoría con la lectura
        delta_ref = 7.0/365.0
        beta_star = float(np.exp(-kappa_mle * delta_ref))
        alpha_star = float((1.0 - beta_star) * theta_mle)
        sigma_star = float(np.sqrt((sigma_mle**2 / (2.0 * kappa_mle)) * (1.0 - np.exp(-2.0 * kappa_mle * delta_ref))))
        logger.info(f"📑 Equivalente AR(1) (Δ=7/365): alpha*={alpha_star:.6f}, beta*={beta_star:.6f}, sigma*={sigma_star:.6f}")

    if not parametros_base:
        raise RuntimeError("No se pudo calibrar ningún tipo de crédito con éxito.")

    parametros_estresados = {
        tipo: {
            "kappa": p["kappa"],
            "theta": p["theta"],
            "sigma": round(p["sigma"] * 1.25, 6)
        }
        for tipo, p in parametros_base.items()
    }

    logger.info("Parámetros estresados generados (σ × 1.25):")
    for tipo, p in parametros_estresados.items():
        logger.info(f"{tipo} (estresado): {p}")

    return parametros_base, parametros_estresados
