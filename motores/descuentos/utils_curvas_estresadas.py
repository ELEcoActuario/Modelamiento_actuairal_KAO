# [VERSIÓN CORREGIDA] motores/descuentos/utils_curvas_estresadas.py

import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def calcular_curvas_estresadas(df_tasas_lr):
    """
    Calcula las 6 curvas estresadas oficiales para cada moneda, con nombres sin flechas.
    Extiende la curva hasta 12,000 días si es necesario, repitiendo la última tasa.
    
    IMPORTANTE: Después de calcular las curvas estresadas en EA, se transforman a
    tasas cortas (short rates) usando r = ln(1 + EA) para aplicar la fórmula
    normativa de descuento: FD(t_k) = exp(-r · t_k)
    """
    parametros = {
        "COP": {"S0": 0.04, "S1": 0.05},
        "USD": {"S0": 0.035, "S1": 0.045},
        "UVR": {"S0": 0.03, "S1": 0.04},
    }

    x = 4 # Parámetro para los choques (tasa de decaimiento)
    resultados = {}

    for moneda in ["COP", "USD", "UVR"]:
        if moneda not in df_tasas_lr.columns:
            continue

        df_moneda = df_tasas_lr[["Nodo", "Tiempo", moneda]].copy()
        df_moneda.rename(columns={moneda: "Tasa"}, inplace=True)

        # Es crucial que la columna "Tiempo" ya esté en la unidad correcta (ej. años = dias/365)
        # O realizar la conversión aquí si no lo está. Asumimos que ya está en años/fracciones.

        # EXTENSIÓN: garantizar hasta 12000 días (que son 12000/365 años en tu escala)
        t = df_moneda["Tiempo"].values # Estos son los valores en 'años'
        
        # Define el límite en la misma unidad que tu columna "Tiempo" (ej. años)
        limite_tiempo_en_anios = 12000 / 365.0  # 12000 días expresados en años base 365
        
        # Asegúrate de que t.max() sea numérico para la comparación
        max_t_actual = t.max()
        if pd.isna(max_t_actual): # Si hay NaNs, obtenemos el max de los no-NaNs
             max_t_actual = pd.Series(t).dropna().max()
             if pd.isna(max_t_actual): # Si todos son NaNs, no hay nada que extender
                 max_t_actual = 0 # O maneja el error

        if max_t_actual < limite_tiempo_en_anios:
            ultimo_tiempo_existente = df_moneda["Tiempo"].iloc[-1] # Ultimo valor en la columna Tiempo (en años)
            ultimo_tasa = df_moneda["Tasa"].iloc[-1]

            # Crea nuevos tiempos en la misma escala (años)
            # Empezamos desde el siguiente "paso" después del último tiempo existente.
            # Puedes ajustar el paso si los "nodos" de tiempo no son enteros.
            # Aquí asumimos que los tiempos son suficientemente densos o se pueden interpolar.
            
            # Para garantizar que se añadan valores si ultimo_tiempo_existente es flotante y no exacto
            # np.arange no incluye el final, así que sumamos un pequeño epsilon para incluir limite_tiempo_en_anios
            nuevos_tiempos_anios = np.arange(ultimo_tiempo_existente + (1/365.0), limite_tiempo_en_anios + (1/365.0), 1/365.0)
            
            # Filtra para evitar duplicados o valores que ya estén presentes si los "pasos" son muy finos
            nuevos_tiempos_anios = np.array([ti for ti in nuevos_tiempos_anios if ti > ultimo_tiempo_existente and ti <= limite_tiempo_en_anios])


            if len(nuevos_tiempos_anios) > 0:
                nuevos_df = pd.DataFrame({
                    "Nodo": (nuevos_tiempos_anios * 365).astype(int), # Convierte a días para el Nodo en base 365
                    "Tiempo": nuevos_tiempos_anios, # Mantén en años para la columna Tiempo
                    "Tasa": ultimo_tasa
                })
                df_moneda = pd.concat([df_moneda, nuevos_df], ignore_index=True)
                df_moneda.sort_values(by="Tiempo", inplace=True) # Asegurarse de que esté ordenado
                df_moneda.reset_index(drop=True, inplace=True) # Resetear índice después de concat/sort
                t = df_moneda["Tiempo"].values # Actualiza t con los nuevos valores
            logging.debug(f"Moneda {moneda}: Max 'Tiempo' después de extensión: {df_moneda['Tiempo'].max()} (años)")
            logging.debug(f"Moneda {moneda}: Total de filas después de extensión: {len(df_moneda)}")


        S0 = parametros[moneda]["S0"]
        S1 = parametros[moneda]["S1"]

        curvas = {}

        curvas["Paralelo_hacia_arriba"] = df_moneda.copy()
        curvas["Paralelo_hacia_arriba"]["Tasa"] += S0

        curvas["Paralelo_hacia_abajo"] = df_moneda.copy()
        curvas["Paralelo_hacia_abajo"]["Tasa"] -= S0

        # Los choques deben calcularse sobre 't' que representa los 'años'
        choque_corto = S1 * np.exp(-t / x)
        choque_largo = S1 * (1 - np.exp(-t / x))
        
        # 🔍 LOGGING: Verificar choques en puntos clave
        logger = logging.getLogger(__name__)
        logger.info(f"📊 Choques {moneda} - S0={S0}, S1={S1}, x={x}")
        
        # Buscar índices de nodos específicos
        idx_30 = df_moneda[df_moneda['Nodo']==30].index
        idx_365 = df_moneda[df_moneda['Nodo']==365].index
        
        if len(idx_30) > 0:
            i30 = idx_30[0]
            logger.info(f"   Nodo 30 días: choque_corto={choque_corto[i30]:.6f}, choque_largo={choque_largo[i30]:.6f}")
        
        if len(idx_365) > 0:
            i365 = idx_365[0]
            logger.info(f"   Nodo 365 días: choque_corto={choque_corto[i365]:.6f}, choque_largo={choque_largo[i365]:.6f}")

        curvas["Empinamiento"] = df_moneda.copy()
        curvas["Empinamiento"]["Tasa"] += (choque_largo - choque_corto)

        curvas["Aplanamiento"] = df_moneda.copy()
        curvas["Aplanamiento"]["Tasa"] -= (choque_largo - choque_corto)

        curvas["Corto_plazo_hacia_arriba"] = df_moneda.copy()
        curvas["Corto_plazo_hacia_arriba"]["Tasa"] += choque_corto

        curvas["Corto_plazo_hacia_abajo"] = df_moneda.copy()
        curvas["Corto_plazo_hacia_abajo"]["Tasa"] -= choque_corto

        for key in curvas:
            curvas[key]["Moneda"] = moneda
        
        # ========================================================================
        # TRANSFORMACIÓN NORMATIVA: EA → Short Rate para descuento exponencial
        # ========================================================================
        # Según normativa SFC, el descuento debe usar tasas cero cupón (short rates)
        # con la fórmula: FD(t_k) = exp(-r · t_k)
        # Transformación: r = ln(1 + EA)
        
        for key in curvas:
            tasa_ea = curvas[key]["Tasa"].values
            # Transformar EA a short rate: r = ln(1 + EA)
            tasa_short = np.log1p(tasa_ea)  # ln(1 + x)
            curvas[key]["Tasa_EA"] = tasa_ea  # Guardar EA original para referencia
            curvas[key]["Tasa"] = tasa_short  # Reemplazar con short rate para descuento
        
        logger.info(f"✅ {moneda}: Curvas transformadas a short rates para descuento normativo")
        logger.debug(f"   Ejemplo banda 1año: EA={curvas['Paralelo_hacia_arriba'][curvas['Paralelo_hacia_arriba']['Nodo']==365]['Tasa_EA'].values[0]:.6f} → Short={curvas['Paralelo_hacia_arriba'][curvas['Paralelo_hacia_arriba']['Nodo']==365]['Tasa'].values[0]:.6f}")

        resultados[moneda] = curvas

    return resultados

def generar_curvas_estresadas_por_moneda(df_tasas_lr: pd.DataFrame) -> dict:
    """
    Concatena las curvas estresadas por moneda con nombres legibles.
    """
    resultado = {}
    curvas_por_moneda = calcular_curvas_estresadas(df_tasas_lr)

    for moneda, dict_choques in curvas_por_moneda.items():
        filas = []
        for nombre_choque, df_choque in dict_choques.items():
            df_tmp = df_choque.copy()
            df_tmp["Choque"] = nombre_choque
            filas.append(df_tmp)
        resultado[moneda] = pd.concat(filas, ignore_index=True)

    return resultado