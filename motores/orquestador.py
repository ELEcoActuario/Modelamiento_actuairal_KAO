import pandas as pd 
import numpy as np
import logging

from motores.amortizacion.francesa import generar_flujo_frances
from motores.amortizacion.alemana import generar_flujo_aleman
from motores.amortizacion.americana import generar_flujo_americano
from motores.amortizacion.bullet import generar_flujo_bullet

from motores.vasicek.calibrador_vasicek import calibrar_parametros_vasicek_mle_por_tipo
from motores.vasicek.simulador_vasicek import simular_trayectorias_vasicek_por_tipo
from motores.vasicek.utils_interpolacion import interpolar_tasas_diarias


from motores.hull_white.calibrador_hull_white import (
    calibrar_hull_white_por_credito,
)
from motores.hull_white.simulador_hull_white import generar_flujos_con_prepago

from motores.bandas.utils_bandas import asignar_bandas_sfc
from motores.descuentos.utils_curvas_estresadas import generar_curvas_estresadas_por_moneda

class MotorCalculo:
    """
    Clase que encapsula toda la lógica de negocio y los datos de sesión.
    Maneja DataFrames de créditos, tasas, resultados intermedios y finales.
    """
    
    def __init__(self):
        # Datos de entrada
        self.df_creditos = None
        self.df_tasas_mercado = None
        self.df_tasas_libres = None
        self.df_curva_hw = None  # Nueva: curva de mercado para Hull-White
        
        # Resultados de cálculos
        self.portafolio_flujos_originales = {}
        self.portafolio_flujos_analisis = {}
        self.portafolio_flujos_estresados = {}
        
        # Resultados para fase 4
        self.portafolio_flujos_analisis_fase4 = {}
        self.portafolio_flujos_estresados_fase4 = {}
        
        # Matrices de simulación
        self.matrices_simuladas = {}
        self.matrices_simuladas_estresadas = {}
        
        # Simuladores para visualización
        self.simuladores_hull_white = {}
        
        # Auditoría Hull-White por crédito y escenario (para UI, evita recálculos)
        self.auditoria_hull_white = {'base': {}, 'estresado': {}}
        
        # Curvas de descuento
        self.dict_curvas_base = {}
        self.dict_curvas_norm = {}
        
        # Resultados de descuentos
        self.df_descuentos = pd.DataFrame()
        
        # Otros datos de sesión
        self.fecha_real_corte = None
        
        # Configuración Vasicek
        self.modo_interpolacion_vasicek = "ea"  # 'ea' (por defecto) o 'short'

    def configurar_vasicek(self, *, modo_interpolacion: str = "ea"):
        """Configura opciones del modelo Vasicek sin romper la API actual."""
        import logging
        self.modo_interpolacion_vasicek = str(modo_interpolacion).lower()
        logging.getLogger(__name__).info(f"Vasicek: modo_interpolacion={self.modo_interpolacion_vasicek}")
    
    def ejecutar_proceso_completo(
        self,
        df_creditos: pd.DataFrame,
        df_tasas_mercado: pd.DataFrame,
        df_tasas_lr: pd.DataFrame,
        fecha_de_corte,
        diferencial_prepago: float,
        modelo_seleccionado: str = "Vasicek",
        n_simulaciones: int = 100
    ) -> tuple:
        """Ejecuta el proceso completo de cálculo y almacena los resultados en la instancia."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🚀 Iniciando proceso completo con modelo {modelo_seleccionado}")
        logger.info(f"📊 Procesando {len(df_creditos)} créditos, diferencial prepago: {diferencial_prepago*100:.2f}%")
        logger.info(f"🎲 Número de simulaciones configuradas: {n_simulaciones}")
        logger.info(f"🔍 RASTREO DIFERENCIAL - ORQUESTADOR: Recibido de APP: {diferencial_prepago:.6f}")
        
        # Almacenar datos de entrada en la instancia
        self.df_creditos = df_creditos.copy()
        self.df_tasas_mercado = df_tasas_mercado.copy()
        self.df_tasas_libres = df_tasas_lr.copy()

        fecha_de_corte = pd.to_datetime(fecha_de_corte)
        df_creditos['Fecha_Desembolso'] = pd.to_datetime(df_creditos['Fecha_Desembolso'], format='%d/%m/%Y')
        df_creditos['Fecha_Vencimiento'] = pd.to_datetime(df_creditos['Fecha_Vencimiento'], format='%d/%m/%Y')

        motores_map = {
            "Francés": generar_flujo_frances,
            "Alemán": generar_flujo_aleman,
            "Americano": generar_flujo_americano,
            "Bullet": generar_flujo_bullet,
        }

        flujos_originales = {
            fila["ID_producto"]: motores_map[fila["Tipo_Amortizacion"]](fila.to_dict())
            for _, fila in df_creditos.iterrows()
            if fila["Tipo_Amortizacion"] in motores_map
        }
        
        # ✅ Agregar columna Moneda a todos los flujos originales
        for id_producto, df_flujo in flujos_originales.items():
            credito_info = df_creditos[df_creditos["ID_producto"] == id_producto]
            if not credito_info.empty:
                moneda = credito_info["Moneda"].values[0] if "Moneda" in credito_info.columns else "COP"
                df_flujo["Moneda"] = moneda
                logger.debug(f"💱 Flujo original {id_producto}: Moneda = {moneda}")
        
        logger.info(f"✅ Flujos determinísticos generados para {len(flujos_originales)} créditos")

        logger.info(f"🔍 Buscando datos históricos para fecha de corte: {fecha_de_corte.strftime('%d/%m/%Y')}")
        df_tasas_mercado['Fecha'] = pd.to_datetime(df_tasas_mercado['Fecha'], format='%d/%m/%Y')
        df_tasas_mercado = df_tasas_mercado.sort_values(by='Fecha')
        tasas_para_corte = df_tasas_mercado[df_tasas_mercado['Fecha'] <= fecha_de_corte]
        if tasas_para_corte.empty:
            raise ValueError("La fecha de corte es anterior a cualquier fecha en los datos históricos.")
        fecha_real_corte = tasas_para_corte['Fecha'].iloc[-1]
        tasas_iniciales_r0 = tasas_para_corte[tasas_para_corte['Fecha'] == fecha_real_corte].iloc[0].to_dict()
        historico_filtrado = df_tasas_mercado[df_tasas_mercado['Fecha'] <= fecha_real_corte]
        logger.info(f"📅 Usando datos del {fecha_real_corte.strftime('%d/%m/%Y')} como punto de partida")

        logger.info(f"🎲 Iniciando simulación estocástica con modelo {modelo_seleccionado}...")
        
        max_fecha_vencimiento = df_creditos['Fecha_Vencimiento'].max()
        dias_a_simular = (max_fecha_vencimiento - fecha_real_corte).days
        
        if modelo_seleccionado == "Vasicek":
            # Modelo Vasicek - usa tasas de mercado históricas con transformación EA → Short Rate
            logger.info("🔧 Iniciando calibración Vasicek con transformación EA → Short Rate...")
            parametros_base, parametros_estresados = calibrar_parametros_vasicek_mle_por_tipo(historico_filtrado)
            
            # GUARDAR PARÁMETROS CALIBRADOS para validación posterior
            self.parametros_vasicek = parametros_base
            self.parametros_vasicek_estresados = parametros_estresados
            logger.info(f"💾 Parámetros Vasicek guardados: {list(parametros_base.keys())}")
            
            # Validar parámetros calibrados
            try:
                from motores.vasicek.validador_transformaciones import validar_parametros_calibrados
                validar_parametros_calibrados(parametros_base, parametros_estresados)
            except ImportError:
                logger.warning("⚠️ No se pudo importar validador de transformaciones")
            semanas_a_simular = int(np.ceil(dias_a_simular / 7)) if dias_a_simular > 0 else 1

            # SIMULACIÓN: Parámetros en SHORT RATE SPACE, r0 en EA (se transforma internamente)
            logger.info("🎲 Simulando trayectorias Vasicek (SHORT RATES → EA)...")
            matrices_simuladas_base = simular_trayectorias_vasicek_por_tipo(
                parametros_base, r0_por_tipo=tasas_iniciales_r0,
                n_simulaciones=n_simulaciones, plazo_semanas=semanas_a_simular,
                metodo_simulacion="exacta"
            )
            matrices_simuladas_estresadas = simular_trayectorias_vasicek_por_tipo(
                parametros_estresados, r0_por_tipo=tasas_iniciales_r0,
                n_simulaciones=n_simulaciones, plazo_semanas=semanas_a_simular,
                metodo_simulacion="exacta"
            )
            logger.info("✅ Matrices simuladas generadas en EA para comparación directa con tasas contractuales")

            flujos_con_prepago_base = {}
            flujos_con_prepago_estresado = {}
            
            logger.info("💰 Generando flujos con prepago Vasicek (escenario base) - Comparación EA vs EA...")
            flujos_vasicek_base = self._generar_flujos_prepago_por_simulacion(
                df_creditos, flujos_originales, fecha_real_corte,
                matrices_simuladas_base, diferencial_prepago, fecha_de_corte
            )
            logger.info(f"✅ Vasicek base completado: {len(flujos_vasicek_base)} créditos procesados")
            
            logger.info("🔥 Generando flujos con prepago Vasicek (escenario estresado) - Comparación EA vs EA...")
            flujos_vasicek_estresado = self._generar_flujos_prepago_por_simulacion(
                df_creditos, flujos_originales, fecha_real_corte,
                matrices_simuladas_estresadas, diferencial_prepago, fecha_de_corte
            )
            logger.info(f"✅ Vasicek estresado completado: {len(flujos_vasicek_estresado)} créditos procesados")
            
            # Acumular flujos de Vasicek
            flujos_con_prepago_base.update(flujos_vasicek_base)
            flujos_con_prepago_estresado.update(flujos_vasicek_estresado)
            logger.info(f"📊 Flujos Vasicek acumulados (EA transformado) - Base: {len(flujos_con_prepago_base)}, Estresado: {len(flujos_con_prepago_estresado)}")
            logger.info("🎯 VASICEK: Proceso completo EA → Short Rate → Simulación → EA → Comparación completado")
            
        elif modelo_seleccionado == "Hull-White":
            # Inicializar diccionarios para acumular flujos
            flujos_con_prepago_base = {}
            flujos_con_prepago_estresado = {}
            
            # Modelo Hull-White - usa tasas libres de riesgo únicamente
            logger.info("🏦 Hull-White: CALIBRACIÓN ESPECÍFICA POR CRÉDITO (no global por moneda)")
            
            fecha_real_corte = fecha_de_corte
            logger.info(f"📅 Fecha de corte para Hull-White: {fecha_real_corte.strftime('%d/%m/%Y')}")
            
            # Asignar fechas a las tasas libres de riesgo
            df_tasas_lr_con_fechas = self._asignar_fechas_a_tasas_lr(self.df_tasas_libres, fecha_real_corte)
            logger.info(f"📊 Tasas LR con fechas asignadas: {len(df_tasas_lr_con_fechas)} registros")
            
            # ✅ CORRECCIÓN: Validar nodos disponibles para Hull-White antes de calibración
            nodos_disponibles = sorted(df_tasas_lr_con_fechas['Nodo'].dropna().astype(int).unique())
            logger.info(f"📊 Nodos Hull-White: {len(nodos_disponibles)} disponibles (rango: {nodos_disponibles[0] if nodos_disponibles else 'N/A'}-{nodos_disponibles[-1] if nodos_disponibles else 'N/A'})")
            
            if len(nodos_disponibles) == 0:
                raise ValueError("❌ No hay nodos válidos en curva de tasas libres para Hull-White")
            if nodos_disponibles[0] > 7:
                logger.warning(f"⚠️ Primer nodo {nodos_disponibles[0]} días - Hull-White puede fallar con nodos tempranos faltantes")
            
            # Almacenar para uso en calibración
            self.df_tasas_libres = df_tasas_lr_con_fechas
            
            # No se realiza calibración global por moneda
            # Cada crédito se calibrará individualmente con sus nodos relevantes dentro del procesamiento
            logger.info("🎯 Estrategia: Calibración individual por crédito con nodos específicos")
            
            # Inicializar diccionarios para simuladores
            # - simuladores_hull_white: para compatibilidad con interfaz (alias)
            # - simuladores_hull_white_por_credito: almacena simuladores específicos por crédito
            self.simuladores_hull_white_por_credito = {
                'base': {},
                'estresado': {}
            }
            
            # IMPORTANTE: La interfaz busca simuladores_hull_white, así que crear alias
            self.simuladores_hull_white = self.simuladores_hull_white_por_credito
            
            # Generar flujos con prepago Hull-White Monte Carlo por crédito
            logger.info("🏦 Generando flujos con prepago Hull-White Monte Carlo...")
            flujos_hull_white_base, flujos_hull_white_estresado = self._generar_flujos_prepago_hull_white_mc(
                df_creditos, 
                flujos_originales, 
                fecha_real_corte, 
                diferencial_prepago,
                n_simulaciones=n_simulaciones
            )
            logger.info(f"✅ Hull-White MC completado: Base={len(flujos_hull_white_base)}, Estresado={len(flujos_hull_white_estresado)} créditos")
            
            # Acumular flujos de Hull-White
            flujos_con_prepago_base.update(flujos_hull_white_base)
            flujos_con_prepago_estresado.update(flujos_hull_white_estresado)
            logger.info(f"📊 Flujos Hull-White acumulados - Base: {len(flujos_con_prepago_base)}, Estresado: {len(flujos_con_prepago_estresado)}")
            
            # NO usar datos sintéticos - las matrices deben ser reales o vacías
            matrices_simuladas_base = {}
            matrices_simuladas_estresadas = {}
            
        else:
            raise ValueError(f"Modelo '{modelo_seleccionado}' no reconocido. Use 'Vasicek' o 'Hull-White'.")

        for id_credito in flujos_originales:
            flujos_originales[id_credito] = asignar_bandas_sfc(flujos_originales[id_credito], fecha_referencia=fecha_real_corte)

        monedas_disponibles = [col for col in ["COP", "USD", "UVR"] if col in df_tasas_lr.columns]
        dict_curvas_base = {
            moneda: df_tasas_lr[["Nodo", "Tiempo", moneda]].rename(columns={moneda: "Tasa"}).assign(Moneda=moneda)
            for moneda in monedas_disponibles
        }
        
        
        
        df_tasas_lr_filtrado = df_tasas_lr[["Nodo", "Tiempo"] + monedas_disponibles].copy()
        dict_curvas_norm = generar_curvas_estresadas_por_moneda(df_tasas_lr_filtrado)

        # Almacenar resultados en la instancia
        self.portafolio_flujos_originales = flujos_originales
        self.portafolio_flujos_analisis = flujos_con_prepago_base
        self.portafolio_flujos_estresados = flujos_con_prepago_estresado
        
        # ✅ DEBUGGING: Verificar contenido de los portafolios
        logger.info(f"📊 PORTAFOLIOS ALMACENADOS:")
        logger.info(f"   🔸 Originales: {len(self.portafolio_flujos_originales)} créditos")
        logger.info(f"   🟢 Base: {len(self.portafolio_flujos_analisis)} créditos = {list(self.portafolio_flujos_analisis.keys())}")
        logger.info(f"   🔴 Estresados: {len(self.portafolio_flujos_estresados)} créditos = {list(self.portafolio_flujos_estresados.keys())}")
        
        # Verificar que los créditos Hull-White efectivamente tienen flujos
        for id_credito, flujos in self.portafolio_flujos_analisis.items():
            if isinstance(flujos, list):
                logger.info(f"   📋 {id_credito} (BASE): {len(flujos)} escenarios de flujos")
            else:
                logger.warning(f"   ⚠️ {id_credito} (BASE): Tipo incorrecto = {type(flujos)}")
        
        for id_credito, flujos in self.portafolio_flujos_estresados.items():
            if isinstance(flujos, list):
                logger.info(f"   📋 {id_credito} (ESTRESADO): {len(flujos)} escenarios de flujos")
            else:
                logger.warning(f"   ⚠️ {id_credito} (ESTRESADO): Tipo incorrecto = {type(flujos)}")
        
        # Resumen de créditos contenidos en los portafolios
        logger.info(f"📊 Resumen de portafolios finales:")
        logger.info(f"   - Originales: {list(flujos_originales.keys())}")
        logger.info(f"   - Base: {list(flujos_con_prepago_base.keys())}")
        logger.info(f"   - Estresado: {list(flujos_con_prepago_estresado.keys())}")
        self.matrices_simuladas = matrices_simuladas_base
        self.matrices_simuladas_estresadas = matrices_simuladas_estresadas
        self.fecha_real_corte = fecha_real_corte
        self.dict_curvas_base = dict_curvas_base
        self.dict_curvas_norm = dict_curvas_norm
        
        logger.info(f"✅ Proceso completo finalizado exitosamente")
        logger.info(f"📊 Resultados: {len(flujos_originales)} flujos originales, {len(flujos_con_prepago_base)} base, {len(flujos_con_prepago_estresado)} estresados")
        logger.info(f"🎲 Matrices simuladas: {len(matrices_simuladas_base)} tipos base, {len(matrices_simuladas_estresadas)} tipos estresados")

        return (
            flujos_originales,
            flujos_con_prepago_base,
            flujos_con_prepago_estresado,
            matrices_simuladas_base,
            matrices_simuladas_estresadas,
            fecha_real_corte,
            dict_curvas_base,
            dict_curvas_norm
        )

    def _generar_flujos_prepago_por_simulacion(
        self,
        df_creditos,
        flujos_originales,
        fecha_real_corte,
        matrices_simuladas,
        diferencial_prepago,
        fecha_de_corte
    ) -> dict:
        import logging
        logger = logging.getLogger(__name__)
        resultado = {}

        for id_credito, df_flujo_completo in flujos_originales.items():
            credito = df_creditos[df_creditos["ID_producto"] == id_credito]
            if credito.empty:
                continue

            tipo = credito["Tipo_producto"].values[0]
            tasa_contractual = credito["Tasa"].values[0]
            fecha_desembolso = pd.to_datetime(credito["Fecha_Desembolso"].values[0])
            moneda_credito = credito["Moneda"].values[0] if "Moneda" in credito.columns else "COP"

            matriz = matrices_simuladas.get(tipo)
            if matriz is None:
                continue

            # Determinar la fecha mínima válida para prepago
            fecha_inicio_valida = max(fecha_de_corte, fecha_desembolso)

            df_futuro = df_flujo_completo[df_flujo_completo["Fecha_Pago"] >= fecha_inicio_valida].copy()
            if df_futuro.empty:
                continue

            # DETECCIÓN AUTOMÁTICA DE CRÉDITOS BULLET Y GENERACIÓN DE FECHAS DE EVALUACIÓN
            tipo_amortizacion = credito["Tipo_Amortizacion"].values[0] if "Tipo_Amortizacion" in credito.columns else "Desconocido"
            
            if tipo_amortizacion.upper() == "BULLET" and len(df_futuro) == 1:
                from dateutil.relativedelta import relativedelta
                
                # Obtener fecha de vencimiento (única fecha del flujo)
                fecha_vencimiento = pd.to_datetime(df_futuro["Fecha_Pago"].iloc[0])
                plazo_anos = (fecha_vencimiento - fecha_de_corte).days / 365.0
                
                logger.info(f"🎯 Vasicek BULLET {id_credito}: Plazo {plazo_anos:.2f} años")
                
                # Generar fechas de evaluación según metodología
                fechas_evaluacion = []
                
                if plazo_anos <= 5.0:
                    # Evaluación mensual para créditos ≤5 años
                    fecha_actual = fecha_de_corte + relativedelta(months=1)
                    while fecha_actual < fecha_vencimiento:
                        fechas_evaluacion.append(fecha_actual)
                        fecha_actual += relativedelta(months=1)
                    metodologia = "MENSUAL"
                else:
                    # Evaluación anual para créditos >5 años
                    fecha_actual = fecha_de_corte + relativedelta(years=1)
                    while fecha_actual < fecha_vencimiento:
                        fechas_evaluacion.append(fecha_actual)
                        fecha_actual += relativedelta(years=1)
                    metodologia = "ANUAL"
                
                # Siempre incluir la fecha de vencimiento
                fechas_evaluacion.append(fecha_vencimiento)
                
                logger.info(f"📅 Vasicek BULLET {id_credito}: {metodologia} - {len(fechas_evaluacion)} puntos de evaluación generados")
                
                # Crear DataFrame expandido con fechas de evaluación para BULLET
                flujo_original = df_futuro.iloc[0]
                capital_total = flujo_original["Capital"]
                tasa_credito = tasa_contractual
                
                df_expandido = []
                
                for fecha_eval in fechas_evaluacion:
                    if fecha_eval == fecha_vencimiento:
                        # En vencimiento: usar flujo original completo
                        df_expandido.append({
                            "Fecha_Pago": fecha_eval,
                            "Capital": flujo_original["Capital"],
                            "Intereses": flujo_original["Intereses"],
                            "Flujo_Total": flujo_original["Flujo_Total"]
                        })
                    else:
                        # En fechas intermedias: solo capital (sin intereses para prepago)
                        # Los intereses se calculan en el momento del prepago según el período transcurrido
                        df_expandido.append({
                            "Fecha_Pago": fecha_eval,
                            "Capital": capital_total,  # Capital completo disponible para prepago
                            "Intereses": 0.0,  # Sin intereses contractuales en fechas intermedias
                            "Flujo_Total": capital_total  # Solo capital para prepago
                        })
                
                df_futuro = pd.DataFrame(df_expandido)
                logger.info(f"✅ BULLET {id_credito}: DataFrame expandido a {len(df_futuro)} fechas de evaluación")

            # INTERPOLACIÓN: matriz contiene tasas EA (ya convertidas desde short rates en simulador)
            modo_interp = getattr(self, "modo_interpolacion_vasicek", "ea")
            logger.info(f"🧮 Interpolación Vasicek en modo='{modo_interp}'")
            tasas_interp = interpolar_tasas_diarias(matriz, fecha_real_corte, df_futuro["Fecha_Pago"], modo=modo_interp)
            fechas_pago = pd.to_datetime(df_futuro["Fecha_Pago"].values)

            flujos_simulacion = []

            for i in range(tasas_interp.shape[0]):
                trayectoria = tasas_interp[i]  # Trayectoria en EA (ya convertida)
                # COMPARACIÓN DIRECTA: tasa_contractual (EA) vs tasa_simulada (EA)
                # Prepago cuando: (tasa_contractual - tasa_simulada) >= diferencial_prepago
                diferencia = tasa_contractual - trayectoria
                indices_validos = np.where(diferencia >= diferencial_prepago)[0]

                if len(indices_validos) == 0:
                    # No hay prepago en esta simulación
                    continue

                idx = indices_validos[0]
                if fechas_pago[idx] < fecha_inicio_valida or idx >= len(df_futuro):
                    continue
  
                prepago_fecha = fechas_pago[idx]
                pago_final = df_futuro.iloc[idx]
                
                # LÓGICA ESPECIAL PARA CRÉDITOS BULLET
                if tipo_amortizacion.upper() == "BULLET":
                    # Calcular intereses devengados hasta la fecha de prepago
                    dias_transcurridos = (prepago_fecha - fecha_desembolso).days
                    anos_transcurridos = dias_transcurridos / 365.0
                    # Capitalización compuesta desde desembolso: V * ((1+EA)^t - 1)
                    intereses_devengados = pago_final["Capital"] * ((1.0 + tasa_contractual) ** anos_transcurridos - 1.0)
                    
                    row_final = {
                        "Fecha_Pago": prepago_fecha,
                        "Capital_Ajustado": pago_final["Capital"],  # Capital completo
                        "Intereses_Ajustados": intereses_devengados,  # Intereses devengados hasta prepago
                        "Prepago_Esperado": pago_final["Capital"],  # Capital prepagado
                        "Flujo_Total_Ajustado": pago_final["Capital"] + intereses_devengados,
                        "Moneda": moneda_credito  # ✅ Agregar moneda
                    }
                    
                    # Para BULLET no hay flujos truncados previos
                    df_resultado = pd.DataFrame([row_final])
                else:
                    # LÓGICA ORIGINAL PARA OTROS TIPOS DE AMORTIZACIÓN
                    flujo_truncado = df_futuro.iloc[:idx].copy()
                    capital_remanente = df_futuro["Capital"].sum() - flujo_truncado["Capital"].sum()

                    row_final = {
                        "Fecha_Pago": prepago_fecha,
                        "Capital_Ajustado": capital_remanente,
                        "Intereses_Ajustados": pago_final["Intereses"],
                        "Prepago_Esperado": capital_remanente,
                        "Flujo_Total_Ajustado": capital_remanente + pago_final["Intereses"],
                        "Moneda": moneda_credito  # ✅ Agregar moneda
                    }

                    df_resultado = pd.concat([
                        flujo_truncado.assign(
                            Capital_Ajustado=flujo_truncado["Capital"],
                            Intereses_Ajustados=flujo_truncado["Intereses"],
                            Prepago_Esperado=0,
                            Flujo_Total_Ajustado=flujo_truncado["Flujo_Total"],
                            Moneda=moneda_credito  # ✅ Agregar moneda
                        ),
                        pd.DataFrame([row_final])
                    ], ignore_index=True)

                df_resultado = asignar_bandas_sfc(df_resultado, fecha_referencia=fecha_real_corte)
                # Anotar identificación de la simulación original (1..N)
                try:
                    df_resultado.attrs['indice_simulacion'] = i + 1
                except Exception:
                    pass
                flujos_simulacion.append(df_resultado)

            resultado[id_credito] = flujos_simulacion

        return resultado
    
    
    def guardar_creditos_fase4(self, df_filtrado: pd.DataFrame):
        """Guarda los créditos filtrados para la fase 4."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"💾 Guardando {len(df_filtrado)} créditos para Fase 4")
        ids_filtrados = set(df_filtrado["ID_producto"].unique())
        
        # Verificar que existen flujos para todos los créditos filtrados
        flujos_base_encontrados = {k: v for k, v in self.portafolio_flujos_analisis.items() if k in ids_filtrados}
        flujos_estresados_encontrados = {k: v for k, v in self.portafolio_flujos_estresados.items() if k in ids_filtrados}
        
        # Log de diagnóstico
        logger.info(f"🔍 Créditos solicitados: {sorted(ids_filtrados)}")
        logger.info(f"🔍 Flujos base disponibles: {sorted(flujos_base_encontrados.keys())}")
        logger.info(f"🔍 Flujos estresados disponibles: {sorted(flujos_estresados_encontrados.keys())}")
        
        # Identificar créditos faltantes
        faltantes_base = ids_filtrados - set(flujos_base_encontrados.keys())
        faltantes_estresados = ids_filtrados - set(flujos_estresados_encontrados.keys())
        
        if faltantes_base:
            logger.warning(f"⚠️ Créditos sin flujos base: {sorted(faltantes_base)}")
        if faltantes_estresados:
            logger.warning(f"⚠️ Créditos sin flujos estresados: {sorted(faltantes_estresados)}")
        
        self.portafolio_flujos_analisis_fase4 = flujos_base_encontrados
        self.portafolio_flujos_estresados_fase4 = flujos_estresados_encontrados
        
        logger.info(f"✅ Guardados {len(self.portafolio_flujos_analisis_fase4)} flujos base y {len(self.portafolio_flujos_estresados_fase4)} estresados para Fase 4")
    
    def calcular_flujos_descuento(self) -> pd.DataFrame:
        """Calcula los flujos de descuento y actualiza df_descuentos."""
        import logging
        from motores.controladores.fase4 import (
            construir_dataframe_flujos_descuentos,
            formatear_curvas_estresadas
        )
        
        logging.info("Iniciando validación de datos para descuentos...")
        
        # Validar que los datos necesarios estén disponibles
        if not self.dict_curvas_base:
            raise ValueError("Debe ejecutar primero la simulación completa para generar las curvas base.")
        
        if not self.dict_curvas_norm:
            raise ValueError("Debe ejecutar primero la simulación completa para generar las curvas normativas.")
        
        logging.info(f"Curvas base disponibles: {list(self.dict_curvas_base.keys())}")
        logging.info(f"Curvas normativas disponibles: {list(self.dict_curvas_norm.keys())}")
        
        # Si no hay datos guardados para fase 4, usar todos los datos disponibles
        portafolio_base = self.portafolio_flujos_analisis_fase4
        portafolio_estresado = self.portafolio_flujos_estresados_fase4
        
        if not portafolio_base:
            logging.warning("⚠️ No hay flujos guardados para Fase 4, usando portafolio completo")
            portafolio_base = self.portafolio_flujos_analisis
            portafolio_estresado = self.portafolio_flujos_estresados
        else:
            logging.info(f"✅ Usando flujos guardados para Fase 4: {len(portafolio_base)} créditos")
        
        if not portafolio_base:
            raise ValueError("No hay flujos de caja disponibles para calcular descuentos. Debe ejecutar primero la simulación completa.")
        
        # Verificación detallada de contenido de portafolios
        logging.info(f"📊 Portafolio base: {len(portafolio_base)} créditos")
        logging.info(f"📊 Portafolio estresado: {len(portafolio_estresado)} créditos")
        
        # Verificar que cada crédito tenga flujos válidos
        creditos_sin_flujos_base = []
        creditos_sin_flujos_estresados = []
        
        for id_credito in portafolio_base.keys():
            flujos_base = portafolio_base.get(id_credito, [])
            if not flujos_base or all(df is None or df.empty for df in flujos_base):
                creditos_sin_flujos_base.append(id_credito)
        
        for id_credito in portafolio_estresado.keys():
            flujos_estresados = portafolio_estresado.get(id_credito, [])
            if not flujos_estresados or all(df is None or df.empty for df in flujos_estresados):
                creditos_sin_flujos_estresados.append(id_credito)
        
        if creditos_sin_flujos_base:
            logging.error(f"❌ Créditos sin flujos base válidos: {creditos_sin_flujos_base}")
        if creditos_sin_flujos_estresados:
            logging.error(f"❌ Créditos sin flujos estresados válidos: {creditos_sin_flujos_estresados}")
        
        logging.info(f"🎯 Iniciando cálculo de descuentos para {len(portafolio_base)} créditos")
        
        try:
            logging.info("Formateando curvas estresadas...")
            curvas_estresadas = {
                moneda: formatear_curvas_estresadas(self.dict_curvas_norm, moneda)
                for moneda in ["COP", "USD", "UVR"]
            }
            logging.info("Curvas estresadas formateadas correctamente")
            
            logging.info("Iniciando construcción de DataFrame de descuentos...")
            self.df_descuentos = construir_dataframe_flujos_descuentos(
                self.dict_curvas_base,
                curvas_estresadas,
                portafolio_base,
                portafolio_estresado,
                self.fecha_real_corte
            )
            logging.info(f"DataFrame de descuentos construido. Shape: {self.df_descuentos.shape}")
            
        except Exception as e:
            logging.error(f"Error durante el cálculo de descuentos: {str(e)}")
            import traceback
            logging.error(f"Traceback completo: {traceback.format_exc()}")
            raise
        
        return self.df_descuentos
    
    def calcular_sensibilidades(self) -> pd.DataFrame:
        """Calcula las sensibilidades (deltas) entre escenarios base y estresados."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("📈 Iniciando cálculo de sensibilidades (deltas)")
        
        if self.df_descuentos.empty:
            logger.error("❌ No hay datos de descuentos para calcular sensibilidades")
            raise ValueError("Debe calcular primero los descuentos.")
        
        # AUDITORÍA: Verificar columnas disponibles
        logger.info(f"🔍 AUDITORÍA - Columnas disponibles en df_descuentos: {list(self.df_descuentos.columns)}")
        
        columnas_choques = [
            "Paralelo_hacia_arriba",
            "Paralelo_hacia_abajo", 
            "Empinamiento",
            "Aplanamiento",
            "Corto_plazo_hacia_arriba",
            "Corto_plazo_hacia_abajo"
        ]

        resultados = []
        for idx, fila in self.df_descuentos.iterrows():
            id_prod = fila["ID_producto"]
            vp_base = fila["VP_base"]
            res = {"ID_producto": id_prod}
            
            # AUDITORÍA: Log detallado para primeros 2 créditos
            if idx < 2:
                logger.info(f"🔍 AUDITORÍA - Crédito {id_prod}:")
                logger.info(f"   VP_base = {vp_base:,.2f}")
            
            for c in columnas_choques:
                col_name = f"VP_est_{c}"
                
                # Verificar que la columna existe
                if col_name not in self.df_descuentos.columns:
                    logger.error(f"❌ COLUMNA FALTANTE: {col_name}")
                    res[f"Δ_{c}"] = 0.0
                    continue
                
                vp_est = fila[col_name]
                delta = vp_est - vp_base
                res[f"Δ_{c}"] = round(delta, 2)
                
                # AUDITORÍA: Log detallado para primeros 2 créditos
                if idx < 2:
                    logger.info(f"   {col_name} = {vp_est:,.2f}")
                    logger.info(f"   Δ_{c} = {vp_est:,.2f} - {vp_base:,.2f} = {delta:,.2f}")
            
            resultados.append(res)

        df_sensibilidades = pd.DataFrame(resultados)
        logger.info(f"✅ Sensibilidades calculadas para {len(df_sensibilidades)} créditos y {len(columnas_choques)} escenarios")
        logger.debug(f"📊 Columnas de sensibilidad: {[col for col in df_sensibilidades.columns if col.startswith('Δ_')]}")
        
        # AUDITORÍA: Mostrar primeras filas del resultado
        logger.info(f"🔍 AUDITORÍA - Primeras sensibilidades calculadas:")
        for idx, row in df_sensibilidades.head(2).iterrows():
            logger.info(f"   {row['ID_producto']}: Δ_Paralelo_abajo = {row['Δ_Paralelo_hacia_abajo']:,.2f}")
        
        return df_sensibilidades
    
    def _asignar_fechas_a_tasas_lr(self, df_tasas_lr: pd.DataFrame, fecha_corte: pd.Timestamp) -> pd.DataFrame:
        """
        Asigna fechas y calcula el tiempo en años a partir del nodo (días desde la fecha de corte).
        Los nodos representan días después de la fecha de corte y las tasas son efectivas anuales.
        
        Args:
            df_tasas_lr: DataFrame con columnas Nodo y tasas por moneda (COP, USD, UVR)
            fecha_corte: Fecha de corte de referencia
            
        Returns:
            DataFrame con columnas 'Fecha' y 'Tiempo' (en años) agregadas
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info("🔧 Asignando fechas y calculando tiempo en años...")
        
        df_resultado = df_tasas_lr.copy()
        
        # Validar que existe la columna Nodo
        if 'Nodo' not in df_resultado.columns:
            raise ValueError("La hoja data_tasasLR debe contener la columna 'Nodo'")
        
        # Validar que existen columnas de monedas
        monedas_disponibles = [col for col in ['COP', 'USD', 'UVR'] if col in df_resultado.columns]
        if not monedas_disponibles:
            raise ValueError("La hoja data_tasasLR debe contener al menos una columna de moneda (COP, USD, UVR)")
        
        logger.info(f"📊 Monedas detectadas en data_tasasLR: {monedas_disponibles}")
        
        # Convertir fecha_corte a datetime si no lo es
        if not isinstance(fecha_corte, pd.Timestamp):
            fecha_corte = pd.to_datetime(fecha_corte)
        
        # Asignar fechas y calcular tiempo en años
        df_resultado['Fecha'] = df_resultado['Nodo'].apply(
            lambda nodo: fecha_corte + pd.Timedelta(days=int(nodo)) if pd.notna(nodo) else pd.NaT
        )
        
        # Calcular tiempo en años (Nodo / 365.0)
        df_resultado['Tiempo'] = df_resultado['Nodo'] / 365.0
        
        # Filtrar registros válidos
        df_resultado = df_resultado.dropna(subset=['Fecha', 'Nodo'])
        
        # Validar que las tasas están en formato decimal (no porcentual)
        for moneda in monedas_disponibles:
            tasas_moneda = df_resultado[moneda].dropna()
            if len(tasas_moneda) > 0:
                tasa_max = tasas_moneda.max()
                if tasa_max > 1.0:
                    logger.warning(f"⚠️ Tasas {moneda} parecen estar en porcentaje (max={tasa_max:.2f}). Convirtiendo a decimal.")
                    df_resultado[moneda] = df_resultado[moneda] / 100.0
                
                logger.info(f"📈 {moneda}: rango tasas {df_resultado[moneda].min():.6f} - {df_resultado[moneda].max():.6f}")
        
        # Ordenar por nodo para mantener secuencia temporal
        df_resultado = df_resultado.sort_values('Nodo').reset_index(drop=True)
        
        logger.info(f"✅ Fechas asignadas: desde {df_resultado['Fecha'].min().strftime('%d/%m/%Y')} hasta {df_resultado['Fecha'].max().strftime('%d/%m/%Y')}")
        logger.info(f"📊 Nodos procesados: {df_resultado['Nodo'].min():.0f} a {df_resultado['Nodo'].max():.0f} días")
        logger.info(f"⏰ Tiempo en años: {df_resultado['Tiempo'].min():.4f} a {df_resultado['Tiempo'].max():.4f}")
        
        return df_resultado
    
    def _generar_flujos_prepago_hull_white_mc(self, df_creditos, flujos_originales, fecha_real_corte, diferencial_prepago, n_simulaciones=100):
        """
        Genera flujos con prepago usando Hull-White Monte Carlo calibrando (a, σ, λ)
        por crédito a partir de `CurvaHW` y simulando en EA para aplicar el criterio
        de prepago: tasa_contractual − EA_sim ≥ diferencial (primera ocurrencia).
        """
        logger = logging.getLogger(__name__)
        logger.info("🏦 HULL-WHITE MC: Inicio por crédito (sin precálculo global)")

        flujos_base = {}
        flujos_estresados = {}
        self.matrices_hull_white = {'base': {}, 'estresado': {}}

        if not hasattr(self, 'df_curva_hw') or self.df_curva_hw is None or self.df_curva_hw.empty:
            raise ValueError("CurvaHW requerida para Hull-White: self.df_curva_hw está vacío")

        total_creditos = len(flujos_originales)

        for idx, (id_credito, df_flujo) in enumerate(flujos_originales.items(), 1):
            try:
                info = df_creditos[df_creditos["ID_producto"] == id_credito]
                if info.empty:
                    continue
                fecha_venc = pd.to_datetime(info["Fecha_Vencimiento"].iloc[0])
                tasa_contractual = info["Tasa"].iloc[0] if "Tasa" in info.columns else None
                fecha_desembolso = pd.to_datetime(info["Fecha_Desembolso"].iloc[0]) if "Fecha_Desembolso" in info.columns else None

                logger.info(f"🎯 [HW] {id_credito}: calibrando con histórico ≤ {fecha_real_corte:%d/%m/%Y} y venc {fecha_venc:%d/%m/%Y}")
                params_base, params_estres = calibrar_hull_white_por_credito(
                    df_curva_hw=self.df_curva_hw,
                    fecha_corte=fecha_real_corte,
                    fecha_vencimiento=fecha_venc,
                )
                
                # GUARDAR PARÁMETROS CALIBRADOS para validación posterior
                if not hasattr(self, 'parametros_hull_white'):
                    self.parametros_hull_white = {}
                    self.parametros_hull_white_estresados = {}
                self.parametros_hull_white[id_credito] = params_base
                self.parametros_hull_white_estresados[id_credito] = params_estres

                logger.info("   💰 Generando flujos con prepago (BASE/ESTRÉS)...")
                lista_base, lista_estresada, r_short_base_viz, r_short_estres_viz = generar_flujos_con_prepago(
                    df_credito=df_flujo,
                    parametros_base=params_base,
                    parametros_estres=params_estres,
                    diferencial_prepago=diferencial_prepago,
                    fecha_corte=fecha_real_corte,
                    tasa_contractual=tasa_contractual,
                    fecha_desembolso=fecha_desembolso,
                    n_simulaciones=n_simulaciones,
                    return_matrices=True,
                )

                # Asignar bandas SFC
                lista_base = [asignar_bandas_sfc(df, fecha_referencia=fecha_real_corte)
                              for df in lista_base if df is not None and not df.empty]
                lista_estresada = [asignar_bandas_sfc(df, fecha_referencia=fecha_real_corte)
                                   for df in lista_estresada if df is not None and not df.empty]

                flujos_base[id_credito] = lista_base
                flujos_estresados[id_credito] = lista_estresada

                self.matrices_hull_white['base'][id_credito] = r_short_base_viz
                self.matrices_hull_white['estresado'][id_credito] = r_short_estres_viz

                logger.info(f"   ✅ {id_credito}: {len(lista_base)} flujos base, {len(lista_estresada)} estresados")

            except Exception as e:
                logger.error(f"❌ Error HW en crédito {id_credito}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue

        logger.info(f"✅ Hull-White MC completado: Base={len(flujos_base)}, Estresado={len(flujos_estresados)}")
        return flujos_base, flujos_estresados
    
    def validar_simulaciones(self, modelo_seleccionado: str) -> dict:
        """
        Valida la CALIBRACIÓN de los modelos calculando R², RMSE y MAE.
        Compara los datos históricos usados vs las predicciones de los parámetros calibrados.
        Incluye sistema de semáforo para interpretación de resultados.
        
        Args:
            modelo_seleccionado: Nombre del modelo a validar
            
        Returns:
            Dict con resultados de validación y semáforo
        """
        from motores.validacion.validador_simulaciones import ValidadorSimulaciones
        logger = logging.getLogger(__name__)
        logger.info(f"🔍 Iniciando validación de CALIBRACIÓN para {modelo_seleccionado}")
        
        validador = ValidadorSimulaciones()
        resultados = {}
        
        # Validar según modelo
        if modelo_seleccionado == "Vasicek":
            # Recuperar parámetros calibrados guardados
            if hasattr(self, 'parametros_vasicek') and self.parametros_vasicek:
                logger.info("📊 Usando parámetros Vasicek guardados")
                resultado_vasicek = validador.validar_vasicek(
                    df_tasas_historicas=self.df_tasas_mercado,
                    parametros_calibrados=self.parametros_vasicek,
                    df_creditos=self.df_creditos
                )
                resultados['Vasicek'] = resultado_vasicek
                logger.info("✅ Validación Vasicek completada")
            else:
                logger.warning("⚠️ No hay parámetros Vasicek calibrados para validar")
        
        elif modelo_seleccionado == "Hull-White":
            # Recuperar parámetros calibrados de Hull-White
            if hasattr(self, 'parametros_hull_white') and self.parametros_hull_white:
                logger.info("📊 Usando parámetros Hull-White guardados")
                resultado_hw = validador.validar_hull_white(
                    df_curva_hw=self.df_curva_hw,
                    parametros_calibrados=self.parametros_hull_white,
                    fecha_corte=self.fecha_real_corte
                )
                resultados['Hull-White'] = resultado_hw
                logger.info("✅ Validación Hull-White completada")
            else:
                logger.warning("⚠️ No hay parámetros Hull-White calibrados para validar")
        
        # Generar reporte consolidado
        if resultados:
            df_reporte = validador.generar_reporte_completo()
            resultados['reporte'] = df_reporte
            
            logger.info(f"✅ Validación completada con {len(resultados)-1} modelos")
        
        return resultados