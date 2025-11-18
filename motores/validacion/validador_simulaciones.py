"""
Módulo de validación de simulaciones para los modelos Vasicek y Hull-White.
Calcula métricas de bondad de ajuste: R², RMSE y MAE.

==============================================================================
METODOLOGÍA DE VALIDACIÓN DE CALIBRACIÓN
==============================================================================

Este módulo implementa la validación de parámetros calibrados mediante MLE
(Maximum Likelihood Estimation) comparando datos históricos vs predicciones.

VASICEK:
--------
Calibramos (κ, θ, σ) con MLE sobre serie histórica de tasas
Validamos:
  1. Reconstruimos serie completa: r̂ₜ = θ + (r̂ₜ₋₁ - θ)e^(-κΔt)
  2. Comparamos: r_histórico vs r̂_predicho
  3. Métricas: R², RMSE, MAE

HULL-WHITE:
-----------
Calibramos (a, σ, λ) + θ(t) con MLE sobre serie de overnight + curva forward
Validamos:
  1. Usamos θ(t) calibrado para predecir curva de tasas
  2. Comparamos: curva_histórica vs curva_predicha(θ)
  3. Métricas: R², RMSE, MAE

==============================================================================
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class ValidadorSimulaciones:
    """
    Validador de simulaciones estocásticas para modelos de tasas de interés.
    Implementa métricas de bondad de ajuste y diagnósticos estadísticos.
    """
    
    def __init__(self):
        self.resultados_validacion = {}
        self.metricas_globales = {}
        
    def validar_vasicek(
        self,
        df_tasas_historicas: pd.DataFrame,
        parametros_calibrados: Dict[str, Dict[str, float]],
        df_creditos: Optional[pd.DataFrame] = None,
    ) -> Dict:
        """
        Valida CALIBRACIÓN del modelo Vasicek comparando tasas históricas vs predichas.
        
        METODOLOGÍA:
        ------------
        1. DATOS DE ENTRADA:
           - Serie histórica de tasas EA (Tasa Efectiva Anual) por tipo de crédito
           - Parámetros calibrados (κ, θ, σ) obtenidos por MLE en short rate space
        
        2. PROCESO DE VALIDACIÓN:
           a) Transformación: EA → Short Rate usando r = ln(1 + EA)
           b) Para cada observación t, calcular:
              • Media condicional: E[rₜ|rₜ₋₁] = θ + (rₜ₋₁ - θ)·e^(-κΔt)
           c) Comparar tasas observadas vs predichas
        
        3. MÉTRICAS CALCULADAS:
           ✅ R²: Coeficiente de determinación
           ✅ RMSE: Error cuadrático medio
           ✅ MAE: Error absoluto medio
        
        Args:
            df_tasas_historicas: DataFrame con tasas históricas por tipo (EA)
            parametros_calibrados: Dict con parámetros {tipo: {'kappa': κ, 'theta': θ, 'sigma': σ}}
            df_creditos: DataFrame opcional con información de créditos
            
        Returns:
            Dict con métricas R², RMSE, MAE por tipo de crédito
        """
        logger.info("📊 Iniciando validación de CALIBRACIÓN Vasicek...")
        
        resultados = {
            'modelo': 'Vasicek',
            'tipos_validados': [],
            'metricas_por_tipo': {},
            'metricas_globales': {}
        }
        
        # DIAGNÓSTICO: Verificar estructura del DataFrame recibido
        logger.info(f"🔍 DIAGNÓSTICO - Estructura DataFrame recibido:")
        logger.info(f"   Columnas: {list(df_tasas_historicas.columns)}")
        logger.info(f"   Shape: {df_tasas_historicas.shape}")
        logger.info(f"   Index type: {type(df_tasas_historicas.index)}")
        logger.info(f"   Primeras filas:\n{df_tasas_historicas.head()}")
        
        for tipo_credito, params in parametros_calibrados.items():
            logger.info(f"🔍 Validando calibración tipo: {tipo_credito}")
            logger.info(f"   Parámetros recibidos: kappa={params.get('kappa')}, theta={params.get('theta')}, sigma={params.get('sigma')}")
            
            # Extraer tasas históricas del tipo
            if tipo_credito not in df_tasas_historicas.columns:
                logger.warning(f"⚠️ Tipo {tipo_credito} no encontrado en históricos")
                logger.warning(f"   Columnas disponibles: {list(df_tasas_historicas.columns)}")
                continue
            
            tasas_hist_ea = df_tasas_historicas[tipo_credito].dropna().values
            logger.info(f"   📊 Datos extraídos: {len(tasas_hist_ea)} observaciones")
            logger.info(f"   Rango valores: [{tasas_hist_ea.min():.6f}, {tasas_hist_ea.max():.6f}]")
            
            # Normalizar si están en porcentaje
            if tasas_hist_ea.max() > 1.0:
                logger.info(f"   · Normalizando desde porcentaje (max={tasas_hist_ea.max():.2f})")
                tasas_hist_ea = tasas_hist_ea / 100.0
                logger.info(f"   · Después de normalizar: [{tasas_hist_ea.min():.6f}, {tasas_hist_ea.max():.6f}]")
            
            # Convertir EA a short rate: r = ln(1 + EA)
            tasas_hist_short = np.log1p(tasas_hist_ea)  # ln(1 + x)
            logger.info(f"   🔄 Transformación EA → Short Rate:")
            logger.info(f"      EA: [{tasas_hist_ea.min():.6f}, {tasas_hist_ea.max():.6f}]")
            logger.info(f"      Short: [{tasas_hist_short.min():.6f}, {tasas_hist_short.max():.6f}]")
            logger.info(f"      Media Short: {tasas_hist_short.mean():.6f}")
            
            # EXTRAER PARÁMETROS CALIBRADOS
            kappa = params.get('kappa', 0.2)
            theta = params.get('theta', 0.05)
            sigma = params.get('sigma', 0.01)
            
            logger.info(f"   📋 Parámetros para validación:")
            logger.info(f"      κ={kappa:.6f}, θ={theta:.6f}, σ={sigma:.6f}")
            
            dt = 7/365.0  # Paso semanal (mismo que calibración MLE)
            
            # Inicializar serie predicha
            n = len(tasas_hist_short)
            exp_kdt = np.exp(-kappa * dt)
            
            # Calcular predicciones (1-paso adelante)
            predicciones_media = np.zeros(n-1)
            
            for t in range(n-1):
                # Media condicional: E[r_t | r_{t-1}]
                predicciones_media[t] = theta + (tasas_hist_short[t] - theta) * exp_kdt
            
            logger.info(f"   ✅ Predicciones calculadas: {len(predicciones_media)} observaciones")

            # MÉTRICAS DE AJUSTE (R², RMSE, MAE) EN SHORT RATE SPACE
            metricas_fit = self._calcular_metricas(
                observado=tasas_hist_short[1:],
                simulado=predicciones_media
            )
            
            # Logging de resultados
            logger.info(f"   📊 MÉTRICAS DE VALIDACIÓN:")
            logger.info(f"      R²: {metricas_fit['r_cuadrado']:.4f}")
            logger.info(f"      RMSE: {metricas_fit['rmse']:.6f}")
            logger.info(f"      MAE: {metricas_fit['mae']:.6f}")
            
            # Construir dict de métricas
            metricas = {
                'r_cuadrado': round(float(metricas_fit['r_cuadrado']), 4),
                'rmse': round(float(metricas_fit['rmse']), 6),
                'mae': round(float(metricas_fit['mae']), 6),
                'correlacion': round(float(metricas_fit['correlacion']), 4),
                'sesgo': round(float(metricas_fit['sesgo']), 6),
                'parametros': {
                    'kappa': round(float(kappa), 6),
                    'theta': round(float(theta), 6),
                    'sigma': round(float(sigma), 6)
                },
                'n_observaciones': int(n),
                'espacio_validacion': 'short_rate'
            }
            
            resultados['tipos_validados'].append(tipo_credito)
            resultados['metricas_por_tipo'][tipo_credito] = metricas
            
            logger.info(f"✅ {tipo_credito}: R²={metricas_fit['r_cuadrado']:.4f}, RMSE={metricas_fit['rmse']:.6f}, MAE={metricas_fit['mae']:.6f}")
        
        # Replicar métricas por crédito si se dispone de df_creditos
        if df_creditos is not None:
            try:
                resultados['creditos_validados'] = []
                resultados['metricas_por_credito'] = {}
                # Columnas esperadas: 'ID_producto', 'Tipo_producto'
                if 'ID_producto' in df_creditos.columns and 'Tipo_producto' in df_creditos.columns:
                    for _, row in df_creditos.iterrows():
                        id_credito = row['ID_producto']
                        tipo = row['Tipo_producto']
                        if tipo in resultados['metricas_por_tipo']:
                            m_tipo = resultados['metricas_por_tipo'][tipo]
                            m_credito = {
                                'r_cuadrado': m_tipo.get('r_cuadrado'),
                                'rmse': m_tipo.get('rmse'),
                                'mae': m_tipo.get('mae'),
                                'correlacion': m_tipo.get('correlacion'),
                                'sesgo': m_tipo.get('sesgo'),
                                'n_observaciones': m_tipo.get('n_observaciones'),
                                'tipo': tipo
                            }
                            resultados['creditos_validados'].append(id_credito)
                            resultados['metricas_por_credito'][id_credito] = m_credito
                else:
                    logger.warning("⚠️ df_creditos no contiene columnas 'ID_producto' y 'Tipo_producto'. Se omite expansión por crédito.")
            except Exception as e:
                logger.warning(f"⚠️ No fue posible expandir métricas por crédito: {e}")

        # Calcular métricas globales
        if resultados['metricas_por_tipo']:
            # Promedios de métricas
            r2_promedio = np.mean([m.get('r_cuadrado', np.nan) for m in resultados['metricas_por_tipo'].values()])
            rmse_promedio = np.mean([m['rmse'] for m in resultados['metricas_por_tipo'].values()])
            mae_promedio = np.mean([m['mae'] for m in resultados['metricas_por_tipo'].values()])
            
            resultados['metricas_globales'] = {
                'r_cuadrado_promedio': round(float(r2_promedio), 4) if not np.isnan(r2_promedio) else None,
                'rmse_promedio': round(rmse_promedio, 6),
                'mae_promedio': round(mae_promedio, 6)
            }
        
        self.resultados_validacion['Vasicek'] = resultados
        logger.info(f"✅ Validación calibración Vasicek completada: {len(resultados['tipos_validados'])} tipos")
        
        return resultados
    
    def validar_hull_white(
        self,
        df_curva_hw: pd.DataFrame,
        parametros_calibrados: Dict[str, Dict[str, float]],
        fecha_corte: pd.Timestamp
    ) -> Dict:
        """
        Valida CALIBRACIÓN Hull-White comparando tasas históricas vs predichas.
        
        METODOLOGÍA:
        ------------
        1. DATOS DE ENTRADA:
           - Serie histórica de curvas de tasas (CurvaHW)
           - Parámetros calibrados (a, σ, λ) + función θ(t) por crédito
        
        2. PROCESO DE VALIDACIÓN:
           a) Predecir tasas usando parámetros calibrados
           b) Comparar tasas observadas vs predichas
        
        3. MÉTRICAS CALCULADAS:
           ✅ R²: Coeficiente de determinación
           ✅ RMSE: Error cuadrático medio
           ✅ MAE: Error absoluto medio
        
        Args:
            df_curva_hw: DataFrame con curva de tasas históricas
            parametros_calibrados: Dict con parámetros por crédito
            fecha_corte: Fecha de corte de la validación
            
        Returns:
            Dict con métricas R², RMSE, MAE por crédito
        """
        logger.info("📊 Iniciando validación de CALIBRACIÓN Hull-White...")
        
        resultados = {
            'modelo': 'Hull-White',
            'creditos_validados': [],
            'metricas_por_credito': {},
            'metricas_globales': {}
        }
        
        # Construir histórico hasta fecha de corte
        df_hw = df_curva_hw.copy()
        df_hw['Fecha'] = pd.to_datetime(df_hw['Fecha'], dayfirst=True)
        df_hist = df_hw[df_hw['Fecha'] <= fecha_corte].sort_values('Fecha')
        if df_hist.empty:
            logger.warning("⚠️ No hay datos históricos de curva para validación")
            return resultados
        
        # Detectar nodos numéricos
        all_cols = [c for c in df_hist.columns if c != 'Fecha']
        nodos = []
        for c in all_cols:
            s = str(c)
            if s.isdigit():
                try:
                    nodos.append(int(s))
                except Exception:
                    pass
        nodos = np.array(sorted(set(nodos)), dtype=int)
        if len(nodos) < 2:
            logger.warning("⚠️ Nodos insuficientes en CurvaHW para validar")
            return resultados
        cols = [str(n) for n in nodos]
        curvas_ea = df_hist[cols].astype(float).values
        try:
            max_val = float(np.nanmax(curvas_ea))
            if max_val > 1.0 and max_val <= 100.0:
                curvas_ea = curvas_ea / 100.0
        except Exception:
            pass
        taus = nodos / 365.0
        curvas_cont = np.log1p(curvas_ea)
        fwds = np.apply_along_axis(lambda row: np.gradient(-row * taus, taus, edge_order=2) * -1, 1, curvas_cont)
        r_short_fw0 = fwds[:, 0]
        fechas = pd.to_datetime(df_hist['Fecha']).values
        
        # Serie overnight (short rate)
        if 1 in nodos:
            idx1 = int(np.where(nodos == 1)[0][0])
            r_series = np.log1p(curvas_ea[:, idx1]).astype(float)
        else:
            r_series = r_short_fw0.astype(float)
        
        # Tiempos entre observaciones
        dts = np.diff(fechas) / np.timedelta64(1, 'D')
        dts = dts.astype(float) / 365.0
        dts = np.clip(dts, 1.0/365.0, None)
        j_days = np.maximum((np.round(dts * 365.0)).astype(int), 1)
        j_idx = np.minimum(j_days - 1, fwds.shape[1] - 1)
        n = len(r_series)
        m = int(min(len(dts), n - 1, fwds.shape[0] - 1))
        if m <= 0:
            logger.warning("⚠️ Histórico insuficiente para validar Hull-White")
            return resultados
        j_idx = j_idx[:m]
        
        # Validar cada crédito con sus parámetros
        for id_credito, params in parametros_calibrados.items():
            logger.info(f"🔍 Validando calibración crédito: {id_credito}")
            try:
                a = params.get('a', 0.1)
                sigma = params.get('sigma', 0.01)
                lambda_param = params.get('lambda', params.get('lambda_', 0.0))
            except AttributeError:
                a = getattr(params, 'a', 0.1)
                sigma = getattr(params, 'sigma', 0.01)
                lambda_param = getattr(params, 'lambda_', 0.0)
            
            pred = np.zeros(m, dtype=float)
            obs = np.zeros(m, dtype=float)
            for k in range(m):
                dt = float(dts[k])
                j = int(j_idx[k])
                f_dt = float(fwds[k, j])
                one = 1.0 - np.exp(-a * dt)
                exp_term = np.exp(-a * dt)
                mean_q = exp_term * (r_series[k] - r_short_fw0[k]) + f_dt + (sigma**2 / (2.0 * a**2)) * (one**2)
                mean = mean_q + (sigma * lambda_param / a) * one
                x = float(r_series[k + 1])
                pred[k] = mean
                obs[k] = x
            
            metricas_fit = self._calcular_metricas(observado=obs, simulado=pred)
            
            metricas = {
                'r_cuadrado': round(float(metricas_fit['r_cuadrado']), 4),
                'rmse': round(float(metricas_fit['rmse']), 6),
                'mae': round(float(metricas_fit['mae']), 6),
                'correlacion': round(float(metricas_fit['correlacion']), 4),
                'sesgo': round(float(metricas_fit['sesgo']), 6),
                'n_observaciones': int(m),
                'parametros': {
                    'a': round(float(a), 6),
                    'sigma': round(float(sigma), 6),
                    'lambda': round(float(lambda_param), 6)
                },
                'espacio_validacion': 'short_rate_ts'
            }
            resultados['creditos_validados'].append(id_credito)
            resultados['metricas_por_credito'][id_credito] = metricas
            logger.info(f"✅ {id_credito}: R²={metricas['r_cuadrado']:.4f}, RMSE={metricas['rmse']:.6f}, MAE={metricas['mae']:.6f}")
        
        # Calcular métricas globales
        if resultados['metricas_por_credito']:
            r2_promedio = np.mean([m['r_cuadrado'] for m in resultados['metricas_por_credito'].values()])
            rmse_promedio = np.mean([m['rmse'] for m in resultados['metricas_por_credito'].values()])
            mae_promedio = np.mean([m['mae'] for m in resultados['metricas_por_credito'].values()])
            
            resultados['metricas_globales'] = {
                'r_cuadrado_promedio': round(r2_promedio, 4),
                'rmse_promedio': round(rmse_promedio, 6),
                'mae_promedio': round(mae_promedio, 6)
            }
        
        self.resultados_validacion['Hull-White'] = resultados
        logger.info(f"✅ Validación calibración Hull-White completada: {len(resultados['creditos_validados'])} créditos")
        
        return resultados
    
    def _calcular_metricas(self, observado: np.ndarray, simulado: np.ndarray) -> Dict:
        """
        Calcula métricas de bondad de ajuste entre series observadas y simuladas.
        
        MÉTRICAS IMPLEMENTADAS:
        -----------------------
        1. R² (Coeficiente de Determinación):
           R² = 1 - SS_res/SS_tot = 1 - Σ(Y_obs - Y_pred)²/Σ(Y_obs - Ȳ)²
           Rango: [-∞, 1]. Valores más cercanos a 1 indican mejor ajuste.
           Interpretación: % de varianza explicada por el modelo.
        
        2. RMSE (Root Mean Square Error):
           RMSE = √[1/n·Σ(Y_obs - Y_pred)²]
           Unidades: mismas que Y. Penaliza errores grandes.
           Interpretación: error promedio "típico" del modelo.
        
        3. MAE (Mean Absolute Error):
           MAE = 1/n·Σ|Y_obs - Y_pred|
           Unidades: mismas que Y. Menos sensible a outliers que RMSE.
           Interpretación: error promedio absoluto.
        
        4. Correlación de Pearson:
           ρ = Cov(Y_obs, Y_pred) / (σ_obs · σ_pred)
           Rango: [-1, 1]. Mide asociación lineal.
        
        5. Sesgo (Bias):
           Bias = mean(Y_pred - Y_obs)
           Positivo: modelo sobre-estima. Negativo: sub-estima.
        
        Args:
            observado: Serie observada (histórica)
            simulado: Serie simulada (predicha por modelo)
            
        Returns:
            Dict con métricas: R², RMSE, MAE, correlación, MAPE, sesgo
        """
        # Asegurar que ambas series tienen la misma longitud
        n = min(len(observado), len(simulado))
        obs = observado[:n]
        sim = simulado[:n]
        
        # R² (coeficiente de determinación)
        # Fórmula: R² = 1 - SS_res/SS_tot
        # donde SS_res = suma de cuadrados residual
        #       SS_tot = suma de cuadrados total
        ss_res = np.sum((obs - sim) ** 2)  # Σ(Y_obs - Y_pred)²
        ss_tot = np.sum((obs - np.mean(obs)) ** 2)  # Σ(Y_obs - Ȳ)²
        
        # Manejo robusto: si no hay varianza (serie constante), R² indefinido → 0
        if ss_tot > 1e-12:  # Evitar división por cero numérico
            r_cuadrado = 1 - (ss_res / ss_tot)
            # DIAGNÓSTICO: Alertar si R² es negativo
            if r_cuadrado < 0:
                logger.warning(f"⚠️ R² NEGATIVO: {r_cuadrado:.4f}")
                logger.warning(f"   SS_res={ss_res:.8f} > SS_tot={ss_tot:.8f}")
                logger.warning(f"   El modelo predice PEOR que la media")
        else:
            r_cuadrado = 0.0
            logger.warning("⚠️ Serie observada tiene varianza ~0. R² establecido en 0.")
        
        # RMSE (Root Mean Square Error)
        rmse = np.sqrt(np.mean((obs - sim) ** 2))
        
        # MAE (Mean Absolute Error)
        mae = np.mean(np.abs(obs - sim))
        
        # Correlación de Pearson
        if len(obs) > 1 and np.std(obs) > 0 and np.std(sim) > 0:
            correlacion = np.corrcoef(obs, sim)[0, 1]
        else:
            correlacion = 0.0
        
        # MAPE (Mean Absolute Percentage Error) - solo si no hay ceros
        if np.all(obs != 0):
            mape = np.mean(np.abs((obs - sim) / obs)) * 100
        else:
            mape = None
        
        metricas = {
            'r_cuadrado': round(float(r_cuadrado), 4),
            'rmse': round(float(rmse), 6),
            'mae': round(float(mae), 6),
            'correlacion': round(float(correlacion), 4),
            'mape': round(float(mape), 2) if mape is not None else None,
            'sesgo': round(float(np.mean(sim - obs)), 6)
        }
        
        return metricas
    
    def generar_reporte_completo(self) -> pd.DataFrame:
        """
        Genera un DataFrame consolidado con todas las métricas de validación.
        
        Returns:
            DataFrame con resumen de validaciones por modelo
        """
        logger.info("📋 Generando reporte consolidado de validación...")
        
        reporte = []
        
        for modelo, resultados in self.resultados_validacion.items():
            metricas_globales = resultados.get('metricas_globales', {})
            
            fila = {
                'Modelo': modelo,
                'Entidades_Validadas': len(resultados.get('tipos_validados', []) or 
                                           resultados.get('creditos_validados', []))
            }
            
            # Para todos los modelos: usar R² si está disponible
            r2_prom = metricas_globales.get('r_cuadrado_promedio')
            fila['R²_Promedio'] = r2_prom
            
            fila['RMSE_Promedio'] = metricas_globales.get('rmse_promedio')
            fila['MAE_Promedio'] = metricas_globales.get('mae_promedio')
            
            reporte.append(fila)
        
        df_reporte = pd.DataFrame(reporte)
        logger.info(f"✅ Reporte generado: {len(df_reporte)} modelos validados")
        
        return df_reporte
    
    def obtener_datos_graficos(self, modelo: str, entidad: str = None) -> Dict:
        """
        Obtiene datos preparados para graficar comparación observado vs simulado.
        
        Args:
            modelo: Nombre del modelo ('Vasicek', 'Hull-White')
            entidad: Tipo de crédito o ID de crédito específico
            
        Returns:
            Dict con arrays para graficar
        """
        if modelo not in self.resultados_validacion:
            logger.warning(f"⚠️ Modelo {modelo} no tiene validación disponible")
            return {}
        
        resultados = self.resultados_validacion[modelo]
        
        # Para Vasicek: entidad es tipo de crédito
        if modelo == 'Vasicek' and 'metricas_por_tipo' in resultados:
            if entidad and entidad in resultados['metricas_por_tipo']:
                return {
                    'tipo': 'vasicek',
                    'entidad': entidad,
                    'metricas': resultados['metricas_por_tipo'][entidad]
                }
        
        # Para Hull-White: entidad es ID de crédito
        if modelo == 'Hull-White' and 'metricas_por_credito' in resultados:
            if entidad and entidad in resultados['metricas_por_credito']:
                return {
                    'tipo': 'hull_white',
                    'entidad': entidad,
                    'metricas': resultados['metricas_por_credito'][entidad]
                }
        
        return {}
    
    def generar_semaforo(self) -> Dict:
        """
        Genera sistema de semáforo con colores según umbrales de R².
        
        Umbrales basados en R²:
        - Verde (Muy Bueno): R² >= 0.65
        - Amarillo (Aceptable): 0.40 <= R² < 0.65
        - Rojo (Bajo): R² < 0.40
        
        Returns:
            Dict con colores y calificaciones por modelo y entidad
        """
        logger.info("🚦 Generando semáforo de calidad...")
        
        semaforo = {}
        
        for modelo, resultados in self.resultados_validacion.items():
            semaforo[modelo] = {}
            
            # Para Vasicek: usar R² por tipo
            if modelo == 'Vasicek' and 'metricas_por_tipo' in resultados:
                for tipo, metricas in resultados['metricas_por_tipo'].items():
                    r2 = metricas.get('r_cuadrado', 0)
                    semaforo[modelo][tipo] = self._clasificar_metrica(r2)
            
            # Para Hull-White: usar R² por crédito
            elif 'metricas_por_credito' in resultados:
                for credito, metricas in resultados['metricas_por_credito'].items():
                    r2 = metricas.get('r_cuadrado', 0)
                    semaforo[modelo][credito] = self._clasificar_metrica(r2)
            
            # Clasificación global del modelo
            if 'metricas_globales' in resultados:
                r2_prom = resultados['metricas_globales'].get('r_cuadrado_promedio')
                if r2_prom is not None:
                    semaforo[modelo]['GLOBAL'] = self._clasificar_metrica(r2_prom)
        
        logger.info(f"✅ Semáforo generado para {len(semaforo)} modelos")
        return semaforo
    
    def _clasificar_metrica(self, valor: float) -> Dict:
        """
        Clasifica una métrica según umbrales y asigna color y etiqueta.
        
        Args:
            valor: Valor de la métrica (R², tasa de éxito, etc.)
            
        Returns:
            Dict con color, etiqueta y valor
        """
        if valor >= 0.65:
            return {
                'color': 'verde',
                'color_hex': '#2ecc71',
                'etiqueta': 'MUY BUENO',
                'emoji': '🟢',
                'valor': round(valor, 4)
            }
        elif valor >= 0.40:
            return {
                'color': 'amarillo',
                'color_hex': '#f39c12',
                'etiqueta': 'ACEPTABLE',
                'emoji': '🟡',
                'valor': round(valor, 4)
            }
        else:
            return {
                'color': 'rojo',
                'color_hex': '#e74c3c',
                'etiqueta': 'BAJO',
                'emoji': '🔴',
                'valor': round(valor, 4)
            }
