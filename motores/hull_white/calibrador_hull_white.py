import numpy as np
import pandas as pd
import logging
from dataclasses import dataclass
from typing import Tuple
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


@dataclass
class ParametrosHullWhite:
    a: float
    sigma: float
    lambda_: float
    r0: float
    tiempos: np.ndarray
    theta_base: np.ndarray
    theta_estres: np.ndarray


def _cols_nodo(df: pd.DataFrame) -> np.ndarray:
    cols = []
    for c in df.columns:
        if c == "Fecha":
            continue
        try:
            cols.append(int(str(c).strip()))
        except Exception:
            pass
    cols = np.array(sorted(set(cols)), dtype=int)
    return cols


def _to_continuous(ea_values: np.ndarray) -> np.ndarray:
    return np.log1p(ea_values)


def _forward_from_curve(y_cont: np.ndarray, taus: np.ndarray) -> np.ndarray:
    lnD = -y_cont * taus
    dlnD = np.gradient(lnD, taus, edge_order=2)
    fwd = -dlnD
    return fwd


def _theta_grid(a: float, sigma: float, lambda_: float, taus: np.ndarray, fwd_curve: np.ndarray) -> np.ndarray:
    dfwd = np.gradient(fwd_curve, taus, edge_order=2)
    mu_q = dfwd + a * fwd_curve + (sigma**2 / (2.0 * a)) * (1.0 - np.exp(-2.0 * a * taus))
    theta_p = mu_q + sigma * lambda_
    return theta_p


def _build_forwards_table(df: pd.DataFrame, nodo_max: int) -> Tuple[pd.DatetimeIndex, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    fechas = pd.to_datetime(df["Fecha"], dayfirst=True).sort_values()
    df_sorted = df.set_index(pd.to_datetime(df["Fecha"], dayfirst=True)).loc[fechas]
    nodos = _cols_nodo(df_sorted)
    nodos = nodos[nodos <= nodo_max]
    if len(nodos) < 2:
        raise ValueError("Se requieren al menos 2 nodos (días) para construir la curva forward")
    cols = [str(n) for n in nodos]
    curvas_ea = df_sorted[cols].astype(float).values
    # Normalización defensiva: si las tasas parecen porcentajes (1..100), dividir por 100
    try:
        max_val = float(np.nanmax(curvas_ea))
        if max_val > 1.0 and max_val <= 100.0:
            logger.warning("CurvaHW detectada en porcentaje; normalizando /100 en histórico")
            curvas_ea = curvas_ea / 100.0
    except Exception:
        pass
    taus = nodos / 365.0
    curvas_cont = _to_continuous(curvas_ea)
    fwds = np.apply_along_axis(lambda row: _forward_from_curve(row, taus), 1, curvas_cont)
    r_short_fw0 = fwds[:, 0]
    return fechas.values, taus, fwds, r_short_fw0, nodos, curvas_ea


def _negative_log_likelihood(params: np.ndarray, r_series: np.ndarray, r_fw0: np.ndarray, fwds: np.ndarray, fechas: np.ndarray) -> float:
    a, sigma, lambda_ = params
    if a <= 0.0 or sigma <= 0.0:
        return np.inf
    if np.any(~np.isfinite(r_series)) or np.any(~np.isfinite(r_fw0)) or np.any(~np.isfinite(fwds)):
        return np.inf
    n = len(r_series)
    if n < 3:
        return np.inf
    fechas = pd.to_datetime(fechas)
    dts = np.diff(fechas) / np.timedelta64(1, "D")
    dts = dts.astype(float) / 365.0
    dts = np.clip(dts, 1.0 / 365.0, None)
    j_days = np.maximum((np.round(dts * 365.0)).astype(int), 1)
    j_idx = np.minimum(j_days - 1, fwds.shape[1] - 1)
    
    m = min(len(dts), n - 1, fwds.shape[0] - 1)
    if m <= 0:
        return np.inf
    j_idx = j_idx[:m]

    nll = 0.0
    for k in range(m):
        dt = dts[k]
        j = j_idx[k]
        f_dt = fwds[k, j]
        one = 1.0 - np.exp(-a * dt)
        exp_term = np.exp(-a * dt)
        # Media bajo Q con c = s pero r(s) tomado como overnight histórico en lugar de f^M(s,s)
        mean_q = exp_term * (r_series[k] - r_fw0[k]) + f_dt + (sigma**2 / (2.0 * a**2)) * (one**2)
        # Cambio de medida a P: + (sigma*lambda_/a)*(1 - e^{-a dt})
        mean = mean_q + (sigma * lambda_ / a) * one
        var = (sigma**2 / (2.0 * a)) * (1.0 - np.exp(-2.0 * a * dt))
        if var <= 0.0 or not np.isfinite(var):
            return np.inf
        x = r_series[k + 1]
        nll += 0.5 * (np.log(2.0 * np.pi * var) + ((x - mean) ** 2) / var)
    return float(nll)


def calibrar_hull_white_por_credito(
    df_curva_hw: pd.DataFrame,
    fecha_corte: pd.Timestamp,
    fecha_vencimiento: pd.Timestamp,
) -> Tuple[ParametrosHullWhite, ParametrosHullWhite]:
    df = df_curva_hw.copy()
    if "Fecha" not in df.columns:
        raise ValueError("El DataFrame debe tener la columna 'Fecha'")

    df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True)
    df = df.sort_values("Fecha")

    # Si no hay exactamente fecha_corte, usar la última disponible <= fecha_corte
    if df[df["Fecha"] <= fecha_corte].empty:
        raise ValueError("No hay curvas anteriores o en la fecha de corte")

    dias_horizonte = int(max(1, (fecha_vencimiento - fecha_corte).days))
    nodo_max = dias_horizonte
    fechas_hist = df[df["Fecha"] <= fecha_corte]
    if len(fechas_hist) < 5:
        raise ValueError("Histórico insuficiente antes de la fecha de corte")

    fechas, taus, fwds, r_short_fw0, nodos_hist, curvas_ea_hist = _build_forwards_table(fechas_hist, nodo_max)
    # Construir serie histórica de overnight r(s) desde nodo 1 si existe; si no, usar forward τ=0
    if 1 in nodos_hist:
        idx1_hist = int(np.where(nodos_hist == 1)[0][0])
        r_series = np.log1p(curvas_ea_hist[:, idx1_hist]).astype(float)
    else:
        r_series = r_short_fw0.astype(float)

    a_init = 0.1
    dt_mean = np.mean(np.diff(pd.to_datetime(fechas)) / np.timedelta64(1, "D")) / 365.0
    dt_mean = float(dt_mean) if np.isfinite(dt_mean) and dt_mean > 0 else 1.0 / 365.0
    dr = np.diff(r_series)
    sigma_init = float(np.std(dr) / np.sqrt(dt_mean)) if len(dr) > 1 else 0.01
    sigma_init = max(sigma_init, 1e-3)
    lambda_init = 0.0

    x0 = np.array([a_init, sigma_init, lambda_init], dtype=float)
    a_min = 10**(-6)  
    bounds = [(a_min, None), (1e-6, None), (None, None)]
    
    logger.info(f"   🔒 Bounds HW aplicados: a≥{a_min}, σ>0, λ∈ℝ")

    res = minimize(
        _negative_log_likelihood,
        x0=x0,
        args=(r_series, r_short_fw0, fwds, fechas),
        bounds=bounds,
        method="L-BFGS-B",
    )

    if not res.success:
        raise RuntimeError(f"MLE Hull-White no convergió: {res.message}")

    a_mle, sigma_mle, lambda_mle = res.x

    try:
        dts_days_dbg = (np.diff(pd.to_datetime(fechas)) / np.timedelta64(1, "D")).astype(float)
        dts_years_dbg = dts_days_dbg / 365.0
        logger.info(
            "HW MLE dt stats: days[min/med/max]=[%.1f/%.1f/%.1f], years[min/med/max]=[%.4f/%.4f/%.4f]",
            float(np.min(dts_days_dbg)), float(np.median(dts_days_dbg)), float(np.max(dts_days_dbg)),
            float(np.min(dts_years_dbg)), float(np.median(dts_years_dbg)), float(np.max(dts_years_dbg)),
        )
        logger.info("HW MLE params: a=%.6f 1/año, sigma=%.6f 1/sqrt(año), lambda=%.6f", float(a_mle), float(sigma_mle), float(lambda_mle))
    except Exception:
        pass

    fila_corte = df[df["Fecha"] <= fecha_corte].iloc[-1]
    nodos = _cols_nodo(df)
    nodos = nodos[nodos <= nodo_max]
    cols = [str(n) for n in nodos]
    y_ea_corte = fila_corte[cols].astype(float).values
    # Normalización defensiva en la fila de corte
    try:
        max_val_c = float(np.nanmax(y_ea_corte))
        if max_val_c > 1.0 and max_val_c <= 100.0:
            logger.warning("CurvaHW (fila corte) detectada en porcentaje; normalizando /100")
            y_ea_corte = y_ea_corte / 100.0
    except Exception:
        pass
    taus_c = nodos / 365.0
    y_cont_corte = _to_continuous(y_ea_corte)
    fwd_corte = _forward_from_curve(y_cont_corte, taus_c)

    if dias_horizonte > nodos[-1]:
        raise ValueError("Horizonte supera el último nodo disponible en CurvaHW")

    t_grid = np.arange(0, dias_horizonte + 1, dtype=float) / 365.0
    f_interp = np.interp(t_grid, taus_c, fwd_corte)
    theta_base = _theta_grid(a_mle, sigma_mle, lambda_mle, t_grid, f_interp)
    sigma_estres = 1.25 * sigma_mle
    theta_estres = _theta_grid(a_mle, sigma_estres, lambda_mle, t_grid, f_interp)

    # r0: usar overnight del nodo 1 de la última curva (EA -> continua) si existe; si no, fallback al método anterior
    try:
        if 1 in nodos:
            idx_overnight = int(np.where(nodos == 1)[0][0])
            r0 = float(np.log1p(y_ea_corte[idx_overnight]))
        else:
            r0 = float(np.interp(1.0 / 365.0, taus_c, fwd_corte))
    except Exception:
        r0 = float(np.interp(1.0 / 365.0, taus_c, fwd_corte))

    params_base = ParametrosHullWhite(
        a=float(a_mle),
        sigma=float(sigma_mle),
        lambda_=float(lambda_mle),
        r0=r0,
        tiempos=t_grid,
        theta_base=theta_base,
        theta_estres=theta_estres,
    )

    params_estres = ParametrosHullWhite(
        a=float(a_mle),
        sigma=float(sigma_estres),
        lambda_=float(lambda_mle),
        r0=r0,
        tiempos=t_grid,
        theta_base=theta_base,
        theta_estres=theta_estres,
    )

    try:
        b_base = theta_base / max(a_mle, 1e-12)
        b_est = theta_estres / max(a_mle, 1e-12)
        logger.info(
            "HW theta/a stats (base): min=%.4f med=%.4f max=%.4f | r0=%.4f",
            float(np.min(b_base)), float(np.median(b_base)), float(np.max(b_base)), float(r0)
        )
        logger.info(
            "HW theta/a stats (estres): min=%.4f med=%.4f max=%.4f",
            float(np.min(b_est)), float(np.median(b_est)), float(np.max(b_est))
        )
    except Exception:
        pass

    return params_base, params_estres

