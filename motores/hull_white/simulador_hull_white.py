import numpy as np
import pandas as pd
import logging
from typing import Tuple, Optional, List, Union

from motores.hull_white.calibrador_hull_white import ParametrosHullWhite

logger = logging.getLogger(__name__)


def _one_minus_exp(x: np.ndarray) -> np.ndarray:
    out = 1.0 - np.exp(-x)
    small = np.abs(x) < 1e-6
    if np.any(small):
        xs = x[small]
        out[small] = xs * (1.0 - 0.5 * xs)
    return out


def simular_hull_white(
    parametros: ParametrosHullWhite,
    n_simulaciones: int = 100,
    usar_estres: bool = False,
    semilla: Optional[int] = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    a = float(parametros.a)
    sigma = float(parametros.sigma)
    tiempos = np.asarray(parametros.tiempos, dtype=float)
    theta = np.asarray(parametros.theta_estres if usar_estres else parametros.theta_base, dtype=float)

    n_pasos = len(tiempos)
    if n_pasos < 2:
        raise ValueError("Se requieren al menos 2 tiempos para simular")

    dt = np.diff(tiempos, prepend=tiempos[0])
    dt[0] = 0.0

    r_mat = np.zeros((n_pasos, n_simulaciones), dtype=float)
    r_mat[0, :] = parametros.r0

    rng = np.random.default_rng(semilla)
    z = rng.standard_normal((n_pasos - 1, n_simulaciones))
    shocks_dt = z * np.sqrt(np.maximum(dt[1:], 0.0))[:, None]

    exp_a_dt = np.exp(-a * dt[1:])
    one = _one_minus_exp(a * dt[1:])
    var_step = (sigma**2 / (2.0 * a)) * (1.0 - np.exp(-2.0 * a * dt[1:]))
    std_eff = np.sqrt(np.maximum(var_step, 0.0) / np.maximum(dt[1:], 1e-16))

    for i in range(n_pasos - 1):
        mean_i = r_mat[i, :] * exp_a_dt[i] + (theta[i] / a) * one[i]
        r_mat[i + 1, :] = mean_i + std_eff[i] * shocks_dt[i, :]

    cum_int = np.cumsum(r_mat * dt[:, None], axis=0)
    t = tiempos[:, None]
    with np.errstate(divide='ignore', invalid='ignore'):
        D = np.exp(-cum_int)
        inv_t = np.where(t > 0, 1.0 / t, 0.0)
        ea_mat = np.power(D, -inv_t, where=np.isfinite(inv_t)) - 1.0
        if np.any(t == 0):
            ea_mat[t[:, 0] == 0, :] = np.expm1(r_mat[0, :])

    return r_mat, ea_mat


def _fechas_evaluacion(desde, df_credito):
    import pandas as pd
    fechas = pd.to_datetime(df_credito["Fecha_Pago"]) if "Fecha_Pago" in df_credito.columns else None
    if fechas is None or len(fechas) == 0:
        return np.array([desde], dtype="datetime64[ns]")
    fechas = fechas[fechas > desde]
    if len(fechas) == 0:
        return np.array([desde], dtype="datetime64[ns]")
    if len(fechas) == 1:
        f_venc = fechas.iloc[0]
        dias = (f_venc - desde).days
        if dias <= 5 * 365:
            step = 30
        else:
            step = 365
        pts = []
        cur = desde + np.timedelta64(step, "D")
        while cur < f_venc:
            pts.append(cur)
            cur = cur + np.timedelta64(step, "D")
        pts.append(f_venc)
        return np.array(pts, dtype="datetime64[ns]")
    return fechas.values.astype("datetime64[ns]")


def _interp_ea(ea_mat: np.ndarray, tiempos: np.ndarray, fechas_eval: np.ndarray, fecha_corte: np.datetime64) -> np.ndarray:
    dias_eval = (fechas_eval.astype("datetime64[D]") - fecha_corte.astype("datetime64[D]")).astype(int).astype(float)
    t_eval = np.maximum(dias_eval, 0.0) / 365.0
    n_eval = len(t_eval)
    n_pasos, n_sim = ea_mat.shape
    t = tiempos
    idx_hi = np.searchsorted(t, t_eval, side="right")
    idx_hi = np.clip(idx_hi, 1, n_pasos - 1)
    idx_lo = idx_hi - 1
    w = (t_eval - t[idx_lo]) / (t[idx_hi] - t[idx_lo] + 1e-16)
    ea_lo = ea_mat[idx_lo, :]
    ea_hi = ea_mat[idx_hi, :]
    return (1.0 - w[:, None]) * ea_lo + w[:, None] * ea_hi

# ==============================
# Construcción de flujos
# ==============================

def _construir_flujo_bullet_prepago(
    df_futuro: pd.DataFrame,
    fecha_prepago: pd.Timestamp,
    fecha_corte: pd.Timestamp,
    tasa_contractual: float,
    fecha_desembolso: Optional[pd.Timestamp] = None,
    moneda: str = "COP",
) -> pd.DataFrame:
    flujo_orig = df_futuro.iloc[0]
    capital = float(flujo_orig.get("Capital", 0))
    fecha_venc = pd.to_datetime(flujo_orig["Fecha_Pago"]) if "Fecha_Pago" in flujo_orig else fecha_prepago

    # Capitalización compuesta: usar fecha_desembolso si está disponible; de lo contrario, capitalizar desde fecha_corte
    fecha_base = pd.to_datetime(fecha_desembolso) if fecha_desembolso is not None else pd.to_datetime(fecha_corte)
    dias_trans = (pd.to_datetime(fecha_prepago) - fecha_base).days
    anos_trans = max(dias_trans, 0) / 365.0
    if tasa_contractual is not None and tasa_contractual > 0:
        int_dev = capital * ((1.0 + tasa_contractual) ** anos_trans - 1.0)
    else:
        int_dev = 0.0

    return pd.DataFrame([
        {
            "Fecha_Pago": pd.to_datetime(fecha_prepago),
            "Capital": capital,
            "Intereses": int_dev,
            "Flujo_Total": capital + int_dev,
            "Saldo_Pendiente": 0.0,
            "Capital_Ajustado": capital,
            "Intereses_Ajustados": int_dev,
            "Prepago_Esperado": capital,
            "Flujo_Total_Ajustado": capital + int_dev,
            "Moneda": moneda,  # ✅ Agregar moneda
        }
    ])


def _construir_flujo_normal_prepago(df_futuro: pd.DataFrame, idx_prepago: int, moneda: str = "COP") -> pd.DataFrame:
    df_prev = df_futuro.iloc[:idx_prepago].copy()
    cap_pag = float(df_prev.get("Capital", 0).sum())
    cap_tot = float(df_futuro.get("Capital", 0).sum())
    cap_rem = cap_tot - cap_pag
    int_p = float(df_futuro.iloc[idx_prepago].get("Intereses", 0))

    flujo_prep = {
        "Fecha_Pago": pd.to_datetime(df_futuro.iloc[idx_prepago]["Fecha_Pago"]),
        "Capital": cap_rem,
        "Intereses": int_p,
        "Flujo_Total": cap_rem + int_p,
        "Saldo_Pendiente": 0.0,
        "Capital_Ajustado": cap_rem,
        "Intereses_Ajustados": int_p,
        "Prepago_Esperado": cap_rem,
        "Flujo_Total_Ajustado": cap_rem + int_p,
        "Moneda": moneda,  # ✅ Agregar moneda
    }

    if not df_prev.empty:
        df_prev = df_prev.copy()
        df_prev["Capital_Ajustado"] = df_prev.get("Capital", 0)
        df_prev["Intereses_Ajustados"] = df_prev.get("Intereses", 0)
        df_prev["Prepago_Esperado"] = 0.0
        df_prev["Flujo_Total_Ajustado"] = df_prev["Capital_Ajustado"] + df_prev["Intereses_Ajustados"]
        df_prev["Moneda"] = moneda  # ✅ Agregar moneda
        return pd.concat([df_prev, pd.DataFrame([flujo_prep])], ignore_index=True)
    else:
        return pd.DataFrame([flujo_prep])


def generar_flujos_con_prepago(
    df_credito: pd.DataFrame,
    parametros_base: ParametrosHullWhite,
    parametros_estres: ParametrosHullWhite,
    diferencial_prepago: float,
    fecha_corte: pd.Timestamp,
    tasa_contractual: float,
    fecha_desembolso: Optional[pd.Timestamp] = None,
    n_simulaciones: int = 100,
    return_matrices: bool = False,
) -> Union[Tuple[List[pd.DataFrame], List[pd.DataFrame]], Tuple[List[pd.DataFrame], List[pd.DataFrame], np.ndarray, np.ndarray]]:
    """
    Genera flujos por simulación aplicando criterio de prepago sobre EA simulada.
    Retorna listas de DataFrames por simulación para BASE y ESTRES; opcionalmente
    matrices de short rates para visualización.
    """
    logger.info("💰 Generando flujos Hull-White con prepago")
    df_credito = df_credito.copy()
    df_credito["Fecha_Pago"] = pd.to_datetime(df_credito["Fecha_Pago"]) if "Fecha_Pago" in df_credito.columns else pd.to_datetime(df_credito.index)

    # ✅ Detectar moneda del crédito
    moneda_credito = "COP"
    if "Moneda" in df_credito.columns:
        monedas_unicas = df_credito["Moneda"].dropna().unique()
        if len(monedas_unicas) > 0:
            moneda_credito = monedas_unicas[0]
    
    fecha_corte = pd.to_datetime(fecha_corte)
    df_futuro = df_credito[df_credito["Fecha_Pago"] > fecha_corte].copy()
    if df_futuro.empty:
        logger.warning("   ⚠️ No hay fechas futuras para el crédito")
        vacio = []
        return (vacio, vacio, None, None) if return_matrices else (vacio, vacio)

    es_bullet = len(df_futuro) == 1
    fechas_eval = _fechas_evaluacion(fecha_corte, df_futuro)

    r_b, ea_b = simular_hull_white(parametros_base, n_simulaciones=n_simulaciones, usar_estres=False)
    r_e, ea_e = simular_hull_white(parametros_estres, n_simulaciones=n_simulaciones, usar_estres=True)
    ea_eval_b = _interp_ea(ea_b, parametros_base.tiempos, fechas_eval, fecha_corte.to_datetime64())
    ea_eval_e = _interp_ea(ea_e, parametros_estres.tiempos, fechas_eval, fecha_corte.to_datetime64())

    diff_b = tasa_contractual - ea_eval_b
    diff_e = tasa_contractual - ea_eval_e
    trig_b = diff_b >= diferencial_prepago
    trig_e = diff_e >= diferencial_prepago
    any_b = trig_b.any(axis=0)
    any_e = trig_e.any(axis=0)
    first_b = np.where(any_b, trig_b.argmax(axis=0), -1)
    first_e = np.where(any_e, trig_e.argmax(axis=0), -1)

    flujos_base: List[pd.DataFrame] = []
    flujos_estres: List[pd.DataFrame] = []

    for j in range(n_simulaciones):
        # BASE: sólo agregar si hay prepago
        idx = int(first_b[j]) if any_b[j] else -1
        if idx >= 0:
            if es_bullet:
                df_sim = _construir_flujo_bullet_prepago(
                    df_futuro,
                    pd.to_datetime(fechas_eval[idx]),
                    fecha_corte,
                    tasa_contractual,
                    fecha_desembolso=fecha_desembolso,
                    moneda=moneda_credito,  # ✅ Pasar moneda
                )
            else:
                df_sim = _construir_flujo_normal_prepago(df_futuro, idx, moneda=moneda_credito)  # ✅ Pasar moneda
            try:
                df_sim.attrs['indice_simulacion'] = j + 1
            except Exception:
                pass
            flujos_base.append(df_sim)

        # ESTRES: sólo agregar si hay prepago
        idx = int(first_e[j]) if any_e[j] else -1
        if idx >= 0:
            if es_bullet:
                df_sim_e = _construir_flujo_bullet_prepago(
                    df_futuro,
                    pd.to_datetime(fechas_eval[idx]),
                    fecha_corte,
                    tasa_contractual,
                    fecha_desembolso=fecha_desembolso,
                    moneda=moneda_credito,  # ✅ Pasar moneda
                )
            else:
                df_sim_e = _construir_flujo_normal_prepago(df_futuro, idx, moneda=moneda_credito)  # ✅ Pasar moneda
            try:
                df_sim_e.attrs['indice_simulacion'] = j + 1
            except Exception:
                pass
            flujos_estres.append(df_sim_e)

    if return_matrices:
        return flujos_base, flujos_estres, r_b, r_e
    return flujos_base, flujos_estres

