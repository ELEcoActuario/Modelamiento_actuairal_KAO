import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import logging
from utils.logger_config import log_error_detallado, log_inicio_proceso, log_fin_proceso

# Componentes visuales
from .fase1.panel_cargar_archivo import PanelCargarArchivo
from .fase2.panel_modelo import PanelModelo
from .fase3.panel_filtros import PanelFiltros
from .fase3.panel_lista_creditos import PanelListaCreditos
from .fase3.panel_resultados import PanelResultados
from .fase4.panel_descuento import PanelDescuento
from .fase5.panel_sensibilidad import PanelSensibilidad
from .fase6.panel_validacion import PanelValidacion

# Backend
from motores.orquestador import MotorCalculo
from motores.controladores.fase1 import validar_hojas_y_columnas
from motores.controladores.fase3 import aplicar_filtros

class App(tk.Tk):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Modelo KAO MultiMode")
        self.geometry("1200x800")
        self.motor_calculo = None
        self.simulacion_seleccionada_base = 0
        self.simulacion_seleccionada_estresada = 0
        self.logger = logging.getLogger(__name__)
        
        # Cache para evitar recálculos innecesarios
        self._cache_flujos_hull_white = {}  # {id_credito: {'base': lista_flujos, 'estresado': lista_flujos}}
        self._credito_actual = None
        
        self._crear_variables()
        self._crear_layout()
        self._instanciar_componentes()

    def _crear_variables(self):
        # Motor de cálculo directo - eliminamos duplicación innecesaria
        self.motor_calculo = MotorCalculo()
        
        # Variables de interfaz
        self.df_filtrado = pd.DataFrame()
        self.simulacion_seleccionada_base = 0
        self.simulacion_seleccionada_estresada = 0

    def _crear_layout(self):
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)

    def _instanciar_componentes(self):
        self.panel_fase1 = PanelCargarArchivo(self.tabs, self._on_archivo_cargado)
        self.tabs.add(self.panel_fase1, text="Fase 1 - Cargar Archivo")

        self.panel_fase2 = PanelModelo(self.tabs, on_confirmar=self._on_modelo_confirmado)
        self.tabs.add(self.panel_fase2, text="Fase 2 - Modelo Actuarial")

        frame_fase3 = ttk.Frame(self.tabs)
        self.panel_filtros = PanelFiltros(
            frame_fase3,
            aplicar_filtros_command=self.ejecutar_calculos,
            graficar_command=self.graficar_simulacion,
            guardar_fase4_command=self._guardar_creditos_fase4
        )
        self.panel_filtros.pack(side="top", fill="x", padx=5, pady=5)
        self.panel_filtros.set_callback_periodicidad(self._on_periodicidad_cambiada)

        self.panel_lista = PanelListaCreditos(frame_fase3, select_command=self.mostrar_credito_individual)
        self.panel_lista.pack(side="left", fill="y", padx=5, pady=5)

        self.panel_resultados = PanelResultados(frame_fase3, callback_simulacion=self._on_cambio_simulacion)
        self.panel_resultados.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        self.tabs.add(frame_fase3, text="Fase 3 - Resultados")

        self.panel_descuento = PanelDescuento(self.tabs)
        self.panel_descuento.pack(fill="both", expand=True)
        self.tabs.add(self.panel_descuento, text="Fase 4 - Descuentos y Gráficos")
        self.panel_descuento.set_callback_descuentos(self._calcular_flujos_descuento_actualizar_panel)

        # Se pasa el callback a PanelSensibilidad
        self.panel_sensibilidad = PanelSensibilidad(self.tabs, calcular_command=self._calcular_sensibilidad)
        self.panel_sensibilidad.pack(fill="both", expand=True)
        self.tabs.add(self.panel_sensibilidad, text="Fase 5 - Análisis de Sensibilidad")

        # Fase 6: Validación de Calibración
        self.panel_validacion = PanelValidacion(self.tabs, calcular_command=self._calcular_validacion)
        self.panel_validacion.pack(fill="both", expand=True)
        self.tabs.add(self.panel_validacion, text="Fase 6 - Validación de Calibración")

    def _on_archivo_cargado(self, df_creditos, df_tasas_mercado, df_tasas_libres, df_curva_hw):
        try:
            validar_hojas_y_columnas(df_creditos, df_tasas_mercado, df_tasas_libres, df_curva_hw)
            # Almacenar datos en el motor de cálculo
            self.motor_calculo.df_creditos = df_creditos
            self.motor_calculo.df_tasas_mercado = df_tasas_mercado
            self.motor_calculo.df_tasas_libres = df_tasas_libres
            self.motor_calculo.df_curva_hw = df_curva_hw
            self.panel_filtros.habilitar_controles(df_creditos)
            messagebox.showinfo("Archivo Cargado", "Datos cargados y validados correctamente.")
            self.tabs.select(self.panel_fase2)
        except Exception as e:
            messagebox.showerror("Error en Validación", str(e))

    def _on_modelo_confirmado(self):
        modelo = self.panel_fase2.get_modelo_seleccionado()
        modelos_soportados = ["Vasicek", "Hull-White"]
        if modelo not in modelos_soportados:
            messagebox.showerror("Modelo no soportado", f"Modelos soportados: {', '.join(modelos_soportados)}")
            return
        messagebox.showinfo("Modelo Confirmado", f"Modelo seleccionado: {modelo}")
        self.tabs.select(self.panel_filtros.master)

    def ejecutar_calculos(self):
        log_inicio_proceso(self.logger, "Ejecutar Cálculos", {"timestamp": pd.Timestamp.now()})
        
        if self.motor_calculo.df_creditos is None:
            log_error_detallado(self.logger, "No hay datos cargados para ejecutar cálculos")
            messagebox.showwarning("Sin Datos", "Primero debe cargar un archivo con datos.")
            return

        valores = self.panel_filtros.get_valores_filtros()
        self.logger.info(f"📋 Parámetros obtenidos: {valores}")
        
        try:
            fecha_corte = valores["fecha_corte"]
            # El diferencial proviene como porcentaje del usuario (3 = 3%). Convertir a decimal una sola vez.
            diferencial_prepago = valores["diferencial_prepago"] / 100.0
            n_simulaciones = valores.get("n_simulaciones", 100)  # Valor por defecto si no está presente
            self.logger.info(f"📅 Fecha corte: {fecha_corte}, Diferencial prepago: {diferencial_prepago*100:.2f}%")
            self.logger.info(f"🎲 Número de simulaciones: {n_simulaciones}")
            self.logger.info(f"🔍 RASTREO DIFERENCIAL - APP: Recibido del usuario: {valores['diferencial_prepago']}% → Convertido: {diferencial_prepago:.6f}")
        except Exception as e:
            log_error_detallado(self.logger, "Error al procesar parámetros de entrada", e, valores)
            messagebox.showerror("Error de Parámetro", "Fecha de corte, diferencial de prepago o número de simulaciones inválidos.")
            return

        try:
            self.title(f"Ejecutando cálculos a fecha {fecha_corte.strftime('%d/%m/%Y')}...")
            self.update_idletasks()

            # Obtener modelo seleccionado
            modelo_seleccionado = self.panel_fase2.get_modelo_seleccionado()
            self.logger.info(f"🎯 Modelo seleccionado: {modelo_seleccionado}")
            
            # Ejecutar proceso completo usando el motor de cálculo
            log_inicio_proceso(self.logger, "Motor de Cálculo", {
                "modelo": modelo_seleccionado,
                "num_creditos": len(self.motor_calculo.df_creditos),
                "fecha_corte": fecha_corte.strftime('%Y-%m-%d')
            })
            
            self.logger.info(f"🔍 RASTREO DIFERENCIAL - APP: Enviando al orquestador: {diferencial_prepago:.6f}")
            
            self.motor_calculo.ejecutar_proceso_completo(
                df_creditos=self.motor_calculo.df_creditos.copy(),
                df_tasas_mercado=self.motor_calculo.df_tasas_mercado.copy(),
                df_tasas_lr=self.motor_calculo.df_tasas_libres.copy(),
                fecha_de_corte=fecha_corte,
                diferencial_prepago=diferencial_prepago,
                modelo_seleccionado=modelo_seleccionado,
                n_simulaciones=n_simulaciones
            )
            
            log_fin_proceso(self.logger, "Motor de Cálculo", {
                "flujos_originales": len(self.motor_calculo.portafolio_flujos_originales),
                "flujos_base": len(self.motor_calculo.portafolio_flujos_analisis),
                "flujos_estresados": len(self.motor_calculo.portafolio_flujos_estresados)
            })

            # Aplicar filtros y actualizar interfaz
            self.logger.info("🔍 Aplicando filtros...")
            self.df_filtrado = aplicar_filtros(self.motor_calculo.df_creditos, valores)
            self.logger.info(f"📊 Créditos filtrados: {len(self.df_filtrado)}")
            
            self.panel_lista.actualizar_lista(self.df_filtrado["ID_producto"].tolist())
            self.panel_resultados.limpiar_vista()
            
            # Limpiar caché cuando se ejecutan nuevos cálculos
            self._limpiar_cache()

            if not self.df_filtrado.empty:
                self.panel_lista.lista_creditos.selection_set(0)
                self.mostrar_credito_individual()

            # Los gráficos de curvas se generan solo cuando el usuario los solicite en Fase 4
            # No se generan automáticamente al completar los cálculos de Fase 3

            self.title("Modelo KAO MultiMode")
            log_fin_proceso(self.logger, "Ejecutar Cálculos", {"creditos_procesados": len(self.df_filtrado)})
            messagebox.showinfo("Cálculos Completados", "Los cálculos y simulaciones han sido completados.")
            self.tabs.select(self.panel_filtros.master)

        except Exception as e:
            log_error_detallado(self.logger, "Error durante ejecución de cálculos", e, {
                "modelo": modelo_seleccionado if 'modelo_seleccionado' in locals() else "No definido",
                "fecha_corte": fecha_corte.strftime('%Y-%m-%d') if 'fecha_corte' in locals() else "No definida"
            })
            messagebox.showerror("Error en Cálculo", str(e))
            self.title("Modelo KAO MultiMode")

    def mostrar_credito_individual(self, event=None):
        id_sel = self.panel_lista.get_seleccion_actual()
        if id_sel is None:
            return

        # Verificar si ya tenemos datos en caché para este crédito
        modelo_seleccionado = self.panel_fase2.get_modelo_seleccionado()
        cache_disponible = False
        
        if modelo_seleccionado == "Hull-White":
            cache_disponible = self._credito_actual == id_sel and id_sel in self._cache_flujos_hull_white
        
        if cache_disponible:
            # Usar datos del caché sin recalcular
            self._mostrar_desde_cache(id_sel)
            return

        # Obtener modelo seleccionado para decidir qué tipo de visualización usar
        modelo_seleccionado = self.panel_fase2.get_modelo_seleccionado()
        
        valores = self.panel_filtros.get_valores_filtros()
        fecha_corte = valores["fecha_corte"]
        periodicidad = valores["periodicidad"]

        if modelo_seleccionado == "Hull-White":
            # Camino para Hull-White: generar flujos desde simuladores
            df_original = self.motor_calculo.portafolio_flujos_originales.get(id_sel, pd.DataFrame())
            
            # Generar listas de flujos desde simuladores Hull-White con prepago dinámico
            lista_base = self._generar_flujos_desde_hull_white_con_cache(id_sel, 'base')
            lista_estresado = self._generar_flujos_desde_hull_white_con_cache(id_sel, 'estresado')

            self.panel_resultados.mostrar_resultados_flujos(
                df_original,
                lista_base,
                lista_estresado,
                self.simulacion_seleccionada_base,
                self.simulacion_seleccionada_estresada,
                periodicidad,
                fecha_corte
            )
        else:
            # Camino para otros modelos: mostrar flujos tradicionales
            df_original = self.motor_calculo.portafolio_flujos_originales.get(id_sel, pd.DataFrame())
            lista_base = self.motor_calculo.portafolio_flujos_analisis.get(id_sel, [])
            lista_estresado = self.motor_calculo.portafolio_flujos_estresados.get(id_sel, [])

            self.panel_resultados.mostrar_resultados_flujos(
                df_original,
                lista_base,
                lista_estresado,
                self.simulacion_seleccionada_base,
                self.simulacion_seleccionada_estresada,
                periodicidad,
                fecha_corte
            )
        
        # Actualizar crédito actual
        self._credito_actual = id_sel

    def _on_cambio_simulacion(self, idx_base, idx_estresado):
        self.simulacion_seleccionada_base = idx_base
        self.simulacion_seleccionada_estresada = idx_estresado
        self._actualizar_vista_simulacion()

    def _actualizar_vista_simulacion(self):
        """
        Actualiza solo la vista de simulaciones sin recalcular el modelo completo.
        Optimizado para cambios rápidos de filtro de simulación.
        """
        id_sel = self.panel_lista.get_seleccion_actual()
        if not id_sel:
            return
            
        # Solo refrescar las tablas con los datos ya calculados
        self.panel_resultados._refrescar_tablas()
    
    def _mostrar_desde_cache(self, id_credito):
        """Muestra resultados desde caché sin recalcular."""
        valores = self.panel_filtros.get_valores_filtros()
        fecha_corte = valores["fecha_corte"]
        periodicidad = valores["periodicidad"]
        
        modelo_seleccionado = self.panel_fase2.get_modelo_seleccionado()
        df_original = self.motor_calculo.portafolio_flujos_originales.get(id_credito, pd.DataFrame())
        
        # Seleccionar caché apropiado según el modelo
        if modelo_seleccionado == "Hull-White":
            cache_credito = self._cache_flujos_hull_white[id_credito]
        else:
            cache_credito = {}  # Sin cache para otros modelos
        
        self.panel_resultados.mostrar_resultados_flujos(
            df_original,
            cache_credito.get('base', []),
            cache_credito.get('estresado', []),
            self.simulacion_seleccionada_base,
            self.simulacion_seleccionada_estresada,
            periodicidad,
            fecha_corte
        )
    
    def _limpiar_cache(self):
        """Limpia el caché cuando se ejecutan nuevos cálculos."""
        self._cache_flujos_hull_white.clear()
        self._credito_actual = None
    
    def _on_periodicidad_cambiada(self):
        self.mostrar_credito_individual()

    def graficar_simulacion(self):
        """Genera gráficos de simulación según el modelo seleccionado."""
        try:
            modelo_seleccionado = self.panel_fase2.get_modelo_seleccionado()
            
            if modelo_seleccionado == "Vasicek":
                self._graficar_vasicek_interfaz()
            elif modelo_seleccionado == "Hull-White":
                self._graficar_hull_white_interfaz()
            else:
                messagebox.showwarning("Advertencia", f"Funcionalidad no implementada para {modelo_seleccionado}")
                
        except Exception as e:
            self.logger.error(f"Error al generar gráficos: {str(e)}")
            messagebox.showerror("Error", f"Error al generar gráficos: {str(e)}")

    def _graficar_vasicek_interfaz(self):
        """Interfaz para gráficos del modelo Vasicek - obtiene crédito seleccionado."""
        try:
            # Obtener crédito seleccionado
            id_sel = self.panel_lista.get_seleccion_actual()
            if not id_sel:
                messagebox.showwarning("Advertencia", "Seleccione un crédito para ver las simulaciones")
                return
            
            # Llamar al método de graficación específico
            self._graficar_vasicek(id_sel)
            
        except Exception as e:
            self.logger.error(f"Error al graficar Vasicek: {str(e)}")
            messagebox.showerror("Error", f"Error al graficar Vasicek: {str(e)}")




    def _generar_flujos_desde_hull_white_con_cache(self, id_credito, escenario_tipo):
        """Genera flujos Hull-White con sistema de caché integrado."""
        # Verificar si ya están en caché
        if id_credito in self._cache_flujos_hull_white:
            if escenario_tipo in self._cache_flujos_hull_white[id_credito]:
                return self._cache_flujos_hull_white[id_credito][escenario_tipo]
        
        # Generar flujos (solo si no están en caché)
        flujos = self._generar_flujos_desde_hull_white(id_credito, escenario_tipo)
        
        # Guardar en caché
        if id_credito not in self._cache_flujos_hull_white:
            self._cache_flujos_hull_white[id_credito] = {}
        self._cache_flujos_hull_white[id_credito][escenario_tipo] = flujos
        
        return flujos
    
    def _generar_flujos_desde_hull_white(self, id_credito, escenario_tipo):
        """Método interno para generar flujos Hull-White sin caché."""
        try:
            # ✅ DEBUG COMPLETO: Mostrar todos los portafolios disponibles
            self.logger.info(f"🔍 DIAGNÓSTICO HULL-WHITE {id_credito} ({escenario_tipo}):")
            
            # Listar todos los portafolios disponibles
            if hasattr(self.motor_calculo, 'portafolio_flujos_analisis'):
                creditos_analisis = list(self.motor_calculo.portafolio_flujos_analisis.keys())
                self.logger.info(f"   📊 portafolio_flujos_analisis: {len(creditos_analisis)} créditos = {creditos_analisis}")
            else:
                self.logger.info(f"   ❌ NO EXISTE portafolio_flujos_analisis")
                
            if hasattr(self.motor_calculo, 'portafolio_flujos_estresados'):
                creditos_estresados = list(self.motor_calculo.portafolio_flujos_estresados.keys())
                self.logger.info(f"   📊 portafolio_flujos_estresados: {len(creditos_estresados)} créditos = {creditos_estresados}")
            else:
                self.logger.info(f"   ❌ NO EXISTE portafolio_flujos_estresados")
            
            # CORRECCIÓN CRÍTICA: Primero verificar si los flujos ya están generados
            # Los flujos se generan durante el proceso principal y se guardan en portafolio
            if escenario_tipo == 'base':
                # Flujos base están en portafolio_flujos_analisis
                if hasattr(self.motor_calculo, 'portafolio_flujos_analisis'):
                    flujos_generados = self.motor_calculo.portafolio_flujos_analisis.get(id_credito, [])
                    if flujos_generados:
                        self.logger.info(f"✅ Usando flujos Hull-White BASE ya generados para {id_credito}: {len(flujos_generados)} escenarios")
                        return flujos_generados
                    else:
                        self.logger.warning(f"⚠️ {id_credito} NO encontrado en portafolio_flujos_analisis")
            else:
                # Flujos estresados están en portafolio_flujos_estresados
                if hasattr(self.motor_calculo, 'portafolio_flujos_estresados'):
                    flujos_generados = self.motor_calculo.portafolio_flujos_estresados.get(id_credito, [])
                    if flujos_generados:
                        self.logger.info(f"✅ Usando flujos Hull-White ESTRESADO ya generados para {id_credito}: {len(flujos_generados)} escenarios")
                        return flujos_generados
                    else:
                        self.logger.warning(f"⚠️ {id_credito} NO encontrado en portafolio_flujos_estresados")
            
            # Si no hay flujos generados, verificar simuladores
            if not hasattr(self.motor_calculo, 'simuladores_hull_white') or not self.motor_calculo.simuladores_hull_white:
                self.logger.warning(f"No hay simuladores Hull-White disponibles para {id_credito}")
                return []
            
            self.logger.info(f"Simuladores Hull-White disponibles: {list(self.motor_calculo.simuladores_hull_white.keys())}")
            
            # Obtener simuladores del tipo especificado
            simuladores = self.motor_calculo.simuladores_hull_white.get(escenario_tipo, {})
            
            if not simuladores:
                self.logger.warning(f"No hay simuladores Hull-White {escenario_tipo} para {id_credito}")
                self.logger.info(f"Tipos disponibles: {list(self.motor_calculo.simuladores_hull_white.keys())}")
                return []
            
            self.logger.info(f"Simuladores {escenario_tipo}: {list(simuladores.keys())}")
            
            # CORRECCIÓN: Los simuladores están almacenados por id_credito, no por moneda
            # Buscar simulador específico para este crédito
            simulador = simuladores.get(id_credito)
            
            if simulador is None:
                self.logger.warning(f"No hay simulador Hull-White {escenario_tipo} para crédito {id_credito}")
                self.logger.info(f"Simuladores disponibles: {list(simuladores.keys())}")
                return []
            
            # Obtener información del crédito para logs
            if hasattr(self.motor_calculo, 'df_creditos') and self.motor_calculo.df_creditos is not None:
                credito_info = self.motor_calculo.df_creditos[self.motor_calculo.df_creditos["ID_producto"] == id_credito]
                if not credito_info.empty:
                    moneda_credito = credito_info["Moneda"].values[0] if "Moneda" in credito_info.columns else "COP"
                    self.logger.info(f"✅ Simulador encontrado para crédito {id_credito}, moneda: {moneda_credito}")
                else:
                    moneda_credito = "COP"
            else:
                moneda_credito = "COP"
            
            # Obtener flujos futuros del crédito
            flujos_futuros = self.motor_calculo.portafolio_flujos_originales.get(id_credito)
            if flujos_futuros is None or flujos_futuros.empty:
                self.logger.warning(f"No hay flujos futuros para crédito {id_credito}")
                return []
            
            # Obtener parámetros de filtros
            valores = self.panel_filtros.get_valores_filtros()
            fecha_corte = valores["fecha_corte"]
            
            # Asegurar que diferencial_prepago sea float
            try:
                diferencial_prepago = float(valores.get("diferencial_prepago", 0.0)) / 100.0
            except (ValueError, TypeError):
                diferencial_prepago = 0.0
            
            # Generar escenarios de prepago desde Hull-White
            self.logger.info(f"Generando escenarios para {id_credito} con diferencial {diferencial_prepago:.4f}")
            escenarios = simulador.generar_escenarios_prepago(flujos_futuros, diferencial_prepago, moneda=moneda_credito, fecha_corte=fecha_corte)
            
            if not escenarios:
                self.logger.warning(f"No se generaron escenarios Hull-White para crédito {id_credito}")
                return []
            
            self.logger.info(f"{len(escenarios)} escenarios generados para {id_credito}")
            
            # Convertir escenarios a formato compatible con interfaz
            lista_flujos = []
            for i, escenario in enumerate(escenarios):
                # FILTRAR ESCENARIO PARA MOSTRAR SOLO FLUJOS POST FECHA DE CORTE
                df_filtrado = escenario.copy()
                if 'Fecha_Pago' in df_filtrado.columns:
                    df_filtrado['Fecha_Pago'] = pd.to_datetime(df_filtrado['Fecha_Pago'])
                    fecha_corte_dt = pd.to_datetime(fecha_corte)
                    # Solo flujos posteriores a fecha de corte
                    df_filtrado = df_filtrado[df_filtrado['Fecha_Pago'] > fecha_corte_dt].reset_index(drop=True)
                elif 'Fecha' in df_filtrado.columns:
                    df_filtrado['Fecha'] = pd.to_datetime(df_filtrado['Fecha'])
                    fecha_corte_dt = pd.to_datetime(fecha_corte)
                    # Solo flujos posteriores a fecha de corte
                    df_filtrado = df_filtrado[df_filtrado['Fecha'] > fecha_corte_dt].reset_index(drop=True)
                
                # Solo procesar si quedan flujos después del filtrado
                if not df_filtrado.empty:
                    # Crear DataFrame compatible con formato esperado por interfaz
                    df_compatible = df_filtrado.copy()
                    
                    # Asegurar que tenga las columnas necesarias para interfaz
                    if 'Capital_Ajustado' not in df_compatible.columns:
                        df_compatible['Capital_Ajustado'] = df_compatible.get('Capital', 0)
                    if 'Intereses_Ajustados' not in df_compatible.columns:
                        df_compatible['Intereses_Ajustados'] = df_compatible.get('Intereses', 0)
                    if 'Flujo_Total_Ajustado' not in df_compatible.columns:
                        df_compatible['Flujo_Total_Ajustado'] = df_compatible.get('Flujo_Total', 0)
                    
                    # Agregar metadatos para identificación en selector
                    paso_prepago = escenario.attrs.get('paso_prepago', i)
                    tiempo_prepago_raw = escenario.attrs.get('tiempo_prepago', 'N/A')
                    optimizado = escenario.attrs.get('optimizado', False)
                    sin_prepago = escenario.attrs.get('sin_prepago', False)
                    es_bullet = escenario.attrs.get('es_bullet', False)
                    
                    # CORRECCIÓN CRÍTICA: Validar tiempo_prepago antes de formatear
                    try:
                        tiempo_prepago = float(tiempo_prepago_raw)
                        tiempo_str = f"{tiempo_prepago:.2f}años"
                    except (ValueError, TypeError):
                        tiempo_str = str(tiempo_prepago_raw)
                    
                    # Crear nombre descriptivo para el selector (consistente con otros créditos)
                    if sin_prepago:
                        nombre_escenario = f"Sin Prepago - Flujo Original"
                    else:
                        nombre_escenario = f"Prepago Paso {paso_prepago} - t={tiempo_str}"
                    
                    df_compatible.attrs['nombre_simulacion'] = nombre_escenario
                    df_compatible.attrs['indice_simulacion'] = i
                    df_compatible.attrs['es_prepago'] = not sin_prepago
                    df_compatible.attrs['paso_prepago'] = paso_prepago
                    
                    lista_flujos.append(df_compatible)
            
            self.logger.info(f"Generados {len(lista_flujos)} flujos desde Hull-White {escenario_tipo} para {id_credito} (moneda: {moneda_credito})")
            
            # Registrar atributos de los flujos generados (nivel debug)
            for i, flujo in enumerate(lista_flujos):
                attrs_info = getattr(flujo, 'attrs', {})
                nombre = attrs_info.get('nombre_simulacion', 'SIN NOMBRE')
                self.logger.debug(f"Flujo {i}: {nombre}")
            
            return lista_flujos
            
        except Exception as e:
            self.logger.error(f"Error generando flujos desde Hull-White: {str(e)}")
            return []


    def mostrar_auditoria_hull_white(self):
        """Muestra tabla de auditoría para Hull-White."""
        try:
            # Obtener crédito seleccionado
            id_sel = self.panel_lista.get_seleccion_actual()
            if not id_sel:
                messagebox.showwarning("Advertencia", "Seleccione un crédito para ver auditoría.")
                return
            
            # CORRECCIÓN: Verificar si hay simuladores específicos por crédito primero
            simuladores_base = {}
            simuladores_estresado = {}
            
            # Priorizar simuladores específicos por crédito
            if hasattr(self.motor_calculo, 'simuladores_hull_white_por_credito') and self.motor_calculo.simuladores_hull_white_por_credito:
                simuladores_base_credito = self.motor_calculo.simuladores_hull_white_por_credito.get('base', {})
                simuladores_estresado_credito = self.motor_calculo.simuladores_hull_white_por_credito.get('estresado', {})
                
                # Si existe simulador específico para este crédito, usarlo
                if id_sel in simuladores_base_credito:
                    simuladores_base = {id_sel: simuladores_base_credito[id_sel]}
                    simuladores_estresado = {id_sel: simuladores_estresado_credito.get(id_sel)}
                    usar_simulador_especifico = True
                else:
                    usar_simulador_especifico = False
            else:
                usar_simulador_especifico = False
            
            # Fallback a simuladores globales por moneda
            if not simuladores_base and hasattr(self.motor_calculo, 'simuladores_hull_white') and self.motor_calculo.simuladores_hull_white:
                simuladores_base = self.motor_calculo.simuladores_hull_white.get('base', {})
                simuladores_estresado = self.motor_calculo.simuladores_hull_white.get('estresado', {})
                usar_simulador_especifico = False
            
            if not simuladores_base and not simuladores_estresado:
                messagebox.showwarning("Sin datos", "No hay simulaciones Hull-White disponibles.\nEjecute el modelo primero.")
                return
            
            # Obtener información del crédito
            credito_info = None
            if hasattr(self.motor_calculo, 'df_creditos') and self.motor_calculo.df_creditos is not None:
                credito_info = self.motor_calculo.df_creditos[self.motor_calculo.df_creditos["ID_producto"] == id_sel]
            
            if credito_info is None or credito_info.empty:
                messagebox.showwarning("Sin datos", f"No se encontró información del crédito {id_sel}.")
                return
            
            moneda_credito = credito_info["Moneda"].values[0] if "Moneda" in credito_info.columns else "COP"
            
            # Validar disponibilidad según el tipo de simulador
            if usar_simulador_especifico:
                # Para simuladores específicos, verificar que existan para este crédito
                if id_sel not in simuladores_base:
                    messagebox.showwarning("Sin datos", f"No hay simulador Hull-White específico para el crédito {id_sel}.\nEjecute el modelo primero.")
                    return
            else:
                # Para simuladores globales, verificar por moneda
                if moneda_credito not in simuladores_base and moneda_credito not in simuladores_estresado:
                    messagebox.showwarning("Sin datos", f"No hay simulaciones Hull-White para la moneda {moneda_credito} del crédito {id_sel}.\nEjecute el modelo primero.")
                    return
            
            # Crear ventana de auditoría
            self._crear_ventana_auditoria_hull_white(id_sel, simuladores_base, simuladores_estresado, moneda_credito, usar_simulador_especifico)
            
        except Exception as e:
            self.logger.error(f"Error al mostrar auditoría Hull-White: {str(e)}")
            messagebox.showerror("Error", f"Error al mostrar auditoría Hull-White: {str(e)}")
    
    def _crear_ventana_auditoria_hull_white(self, id_credito, simuladores_base, simuladores_estresado, moneda_credito, usar_simulador_especifico=False):
        """Crea ventana con tabla de auditoría Hull-White."""
        import tkinter as tk
        from tkinter import ttk
        
        # Crear ventana
        ventana = tk.Toplevel(self)
        ventana.title(f"Auditoría Hull-White - Crédito {id_credito}")
        ventana.geometry("1200x700")
        
        # Frame principal
        frame_principal = ttk.Frame(ventana)
        frame_principal.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Título
        titulo = ttk.Label(frame_principal, text=f"Auditoría de Simulación Hull-White - Crédito: {id_credito}", 
                          font=("Arial", 14, "bold"))
        titulo.pack(pady=(0, 10))
        
        # Frame para controles
        frame_controles = ttk.Frame(frame_principal)
        frame_controles.pack(fill="x", pady=(0, 10))
        
        # Selector de escenario
        ttk.Label(frame_controles, text="Escenario:").pack(side="left", padx=(0, 5))
        combo_escenario = ttk.Combobox(frame_controles, values=["base", "estresado"], state="readonly", width=15)
        combo_escenario.set("base")
        combo_escenario.pack(side="left", padx=(0, 20))
        
        # Información de optimización
        info_label = ttk.Label(frame_controles, text="", font=("Arial", 10))
        info_label.pack(side="left")
        
        # Frame para tabla
        frame_tabla = ttk.Frame(frame_principal)
        frame_tabla.pack(fill="both", expand=True)
        
        # Crear Treeview con columnas simplificadas
        columnas = ("Nodo", "Tasa_Simulada", "Tasa_Nodo_Anterior", "Diferencial", "Prepago")
        
        tree = ttk.Treeview(frame_tabla, columns=columnas, show="headings", height=20)
        
        # Configurar columnas
        anchos = {"Nodo": 80, "Tasa_Simulada": 120, "Tasa_Nodo_Anterior": 150, 
                 "Diferencial": 100, "Prepago": 80}
        
        for col in columnas:
            tree.heading(col, text=col.replace("_", " "))
            tree.column(col, width=anchos.get(col, 100), anchor="center")
        
        # Scrollbars
        scrollbar_v = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree.yview)
        scrollbar_h = ttk.Scrollbar(frame_tabla, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=scrollbar_v.set, xscrollcommand=scrollbar_h.set)
        
        # Empaquetar tabla y scrollbars
        tree.pack(side="left", fill="both", expand=True)
        scrollbar_v.pack(side="right", fill="y")
        scrollbar_h.pack(side="bottom", fill="x")
        
        def actualizar_tabla():
            """Actualiza la tabla según el escenario seleccionado."""
            # Limpiar tabla
            for item in tree.get_children():
                tree.delete(item)
            
            escenario = combo_escenario.get()
            simuladores = simuladores_base if escenario == "base" else simuladores_estresado
            
            # CORRECCIÓN: Manejar simuladores específicos vs globales
            if usar_simulador_especifico:
                # Para simuladores específicos, usar el ID del crédito
                if id_credito not in simuladores:
                    info_label.config(text=f"No hay simulador específico para crédito {id_credito} en escenario {escenario}")
                    return
                simulador = simuladores[id_credito]
            else:
                # Para simuladores globales, usar la moneda del crédito
                if moneda_credito not in simuladores:
                    info_label.config(text=f"No hay datos para escenario {escenario} en moneda {moneda_credito}")
                    return
                simulador = simuladores[moneda_credito]
            
            # Obtener datos de auditoría del simulador
            try:
                # Buscar datos de auditoría en el simulador
                auditoria_data = getattr(simulador, 'auditoria_data', None)
                
                # ✅ FALLBACK: Si no hay auditoría en el simulador, buscar en el orquestador
                if auditoria_data is None or len(auditoria_data) == 0:
                    self.logger.info(f"🔍 No hay auditoría en simulador, buscando en orquestador...")
                    if hasattr(self.motor_calculo, 'auditoria_hull_white'):
                        auditoria_orquestador = self.motor_calculo.auditoria_hull_white.get(escenario, {})
                        if id_credito in auditoria_orquestador:
                            auditoria_data = auditoria_orquestador[id_credito].get('auditoria_data', [])
                            self.logger.info(f"✅ Auditoría encontrada en orquestador: {len(auditoria_data)} registros")
                
                if auditoria_data is None or len(auditoria_data) == 0:
                    info_label.config(text="No hay datos de auditoría disponibles")
                    return
                
                # Obtener información de optimización
                prepagos_por_paso = getattr(simulador, 'prepagos_por_paso', np.array([]))
                pasos_con_prepago = getattr(simulador, 'pasos_con_prepago', np.array([]))
                
                total_pasos = len(auditoria_data)
                pasos_optimizados = len(pasos_con_prepago)
                
                # Obtener el diferencial real del simulador
                prepagos_detectados = 0
                diferencial_prepago_raw = getattr(simulador, 'tasa_diferencial_prepago', 0.02)
                
                # Asegurar que sea float
                try:
                    diferencial_prepago = float(diferencial_prepago_raw)
                except (ValueError, TypeError):
                    diferencial_prepago = 0.02
                    
                self.logger.info(f"🔍 Diferencial de prepago obtenido: {diferencial_prepago:.4f}")
                
                # Usar la lógica de prepago del simulador
                for fila in auditoria_data:
                    hay_prepago = fila.get('prepago', False)
                    if hay_prepago:
                        prepagos_detectados += 1
                
                # Mostrar estadísticas que coincidan con la tabla
                porcentaje_prepago = (prepagos_detectados / total_pasos * 100) if total_pasos > 0 else 0
                info_label.config(text=f"Total nodos: {total_pasos} | Prepagos detectados: {prepagos_detectados} ({porcentaje_prepago:.1f}%) | Diferencial mínimo: {diferencial_prepago:.2%}")
                
                # Llenar tabla con datos del simulador
                for i, fila in enumerate(auditoria_data):
                    # DEBUG: Verificar contenido de fila
                    if i < 5:  # Solo primeras 5 filas
                        self.logger.info(f"🔍 INTERFAZ AUDITORÍA - Fila {i}: {fila}")
                    
                    # Asegurar que todos los valores sean numéricos
                    try:
                        # ✅ CORRECCIÓN: Usar nombres correctos del simulador
                        tasa_simulada = float(fila.get('ea_actual', 0))  # Nombre correcto del simulador
                        tasa_nodo_anterior = float(fila.get('ea_anterior', tasa_simulada))  # Nombre correcto del simulador
                        diferencial = float(fila.get('diferencia', 0))
                        
                        # DEBUG: Verificar valores extraídos
                        if i < 5:
                            self.logger.info(f"🔍 INTERFAZ AUDITORÍA - Valores extraídos: tasa_sim={tasa_simulada:.6f}, tasa_ant={tasa_nodo_anterior:.6f}, dif={diferencial:.6f}")
                    except (ValueError, TypeError):
                        tasa_simulada = 0.0
                        tasa_nodo_anterior = 0.0
                        diferencial = 0.0
                    
                    hay_prepago = fila.get('prepago', False)
                    prepago_texto = "SÍ" if hay_prepago else "NO"
                    
                    # Formatear valores
                    valores = (
                        str(i),
                        f"{tasa_simulada:.4f}",
                        f"{tasa_nodo_anterior:.4f}",
                        f"{diferencial:.4f}",
                        prepago_texto
                    )
                    
                    # Insertar fila con color según prepago
                    item = tree.insert("", "end", values=valores)
                    if hay_prepago:
                        # Marcar visualmente las filas con prepago
                        tree.item(item, tags=("prepago",))
                    
                    # Actualizar tasa anterior para el siguiente nodo
                    tasa_anterior = tasa_simulada
                
                # Configurar colores para filas con prepago
                tree.tag_configure("prepago", background="#ffe6e6")
                
            except Exception as e:
                self.logger.error(f"Error al cargar datos de auditoría: {str(e)}")
                info_label.config(text=f"Error al cargar datos: {str(e)}")
        
        # Conectar evento de cambio de escenario
        combo_escenario.bind("<<ComboboxSelected>>", lambda e: actualizar_tabla())
        
        # Cargar datos iniciales
        actualizar_tabla()
        
        # Frame para estadísticas
        frame_stats = ttk.LabelFrame(frame_principal, text="Estadísticas de Optimización", padding=10)
        frame_stats.pack(fill="x", pady=(10, 0))
        
        def actualizar_estadisticas():
            """Actualiza las estadísticas mostradas."""
            escenario = combo_escenario.get()
            simuladores = simuladores_base if escenario == "base" else simuladores_estresado
            
            if moneda_credito in simuladores:
                simulador = simuladores[moneda_credito]
                auditoria_data = getattr(simulador, 'auditoria_data', [])
                # CORRECCIÓN: Usar el mismo atributo que en actualizar_tabla()
                diferencial_prepago_raw = getattr(simulador, 'tasa_diferencial_prepago', 0.02)
                try:
                    diferencial_prepago = float(diferencial_prepago_raw)
                except (ValueError, TypeError):
                    diferencial_prepago = 0.02
                
                # CORRECCIÓN CRÍTICA: Usar la misma lógica que la tabla de auditoría
                total_nodos = len(auditoria_data)
                prepagos_detectados = 0
                
                # Contar prepagos usando la misma lógica que actualizar_tabla()
                for fila in auditoria_data:
                    hay_prepago = fila.get('prepago', False)
                    if hay_prepago:
                        prepagos_detectados += 1
                
                porcentaje_prepago = (prepagos_detectados / total_nodos * 100) if total_nodos > 0 else 0
                
                stats_text = f"Escenario: {escenario.upper()} | Total nodos: {total_nodos} | "
                stats_text += f"Prepagos detectados: {prepagos_detectados} ({porcentaje_prepago:.1f}%) | "
                stats_text += f"Diferencial mínimo: {diferencial_prepago:.1%}"
                
                # Limpiar frame de estadísticas antes de agregar nueva etiqueta
                for widget in frame_stats.winfo_children():
                    widget.destroy()
                
                stats_label = ttk.Label(frame_stats, text=stats_text)
                stats_label.pack()
        
        # Conectar actualización de estadísticas
        combo_escenario.bind("<<ComboboxSelected>>", lambda e: [actualizar_tabla(), actualizar_estadisticas()])
        
        # Mostrar estadísticas iniciales
        actualizar_estadisticas()
    

    def _graficar_vasicek(self, id_sel):
        """Grafica las simulaciones del modelo Vasicek (método original)."""
        
        # Limpiar cualquier figura previa
        plt.close('all')
        
        tipo = self.motor_calculo.df_creditos.loc[self.motor_calculo.df_creditos["ID_producto"] == id_sel, "Tipo_producto"].values[0]
        matriz_base = self.motor_calculo.matrices_simuladas.get(tipo)
        matriz_est = self.motor_calculo.matrices_simuladas_estresadas.get(tipo)

        if matriz_base is None or matriz_est is None:
            messagebox.showerror("Sin Datos", f"No se encontraron matrices simuladas para el tipo: {tipo}")
            return

        fila = self.motor_calculo.df_creditos[self.motor_calculo.df_creditos["ID_producto"] == id_sel]
        if fila.empty:
            messagebox.showerror("Error", "No se encontró información del crédito seleccionado.")
            return

        tasa_contractual = fila["Tasa"].values[0]
        diferencial_prepago = self.panel_filtros.get_valores_filtros()["diferencial_prepago"] / 100.0
        umbral = tasa_contractual - diferencial_prepago

        semanas = range(matriz_base.shape[0])

        plt.figure(figsize=(10, 4))
        for fila in matriz_base.T:
            plt.plot(semanas, fila, color='blue', alpha=0.2, linewidth=0.8)
        plt.axhline(y=tasa_contractual, color='blue', linestyle='--', linewidth=1.2, label='Tasa Contractual')
        plt.axhline(y=umbral, color='green', linestyle='-.', linewidth=1.2, label='Umbral Prepago')
        plt.title(f"Simulaciones Vasicek Base - {tipo}")
        plt.xlabel("Semanas")
        plt.ylabel("Tasa")
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.show()

        plt.figure(figsize=(10, 4))
        for fila in matriz_est.T:
            plt.plot(semanas, fila, color='red', alpha=0.2, linewidth=0.8)
        plt.axhline(y=tasa_contractual, color='blue', linestyle='--', linewidth=1.2, label='Tasa Contractual')
        plt.axhline(y=umbral, color='green', linestyle='-.', linewidth=1.2, label='Umbral Prepago')
        plt.title(f"Simulaciones Vasicek Estresadas - {tipo}")
        plt.xlabel("Semanas")
        plt.ylabel("Tasa")
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.show()

    def _graficar_hull_white_interfaz(self):
        """Interfaz para gráficos del modelo Hull-White Monte Carlo."""
        try:
            # Obtener crédito seleccionado
            id_sel = self.panel_lista.get_seleccion_actual()
            if not id_sel:
                messagebox.showwarning("Advertencia", "Seleccione un crédito para ver las simulaciones")
                return
            
            # Llamar al método de graficación específico
            self._graficar_hull_white_mc(id_sel)
            
        except Exception as e:
            self.logger.error(f"Error al graficar Hull-White MC: {str(e)}")
            messagebox.showerror("Error", f"Error al graficar Hull-White MC: {str(e)}")
    
    def _graficar_hull_white_mc(self, id_sel):
        """Grafica las simulaciones Monte Carlo del modelo Hull-White con criterio de prepago correcto."""
        
        # Limpiar cualquier figura previa
        plt.close('all')
        
        # Obtener matrices simuladas para el crédito
        matrices_hw = getattr(self.motor_calculo, 'matrices_hull_white', None)
        if matrices_hw is None:
            messagebox.showerror("Sin Datos", "No se encontraron matrices Hull-White. Ejecute el modelo primero.")
            return
        
        matriz_base = matrices_hw.get('base', {}).get(id_sel)
        matriz_est = matrices_hw.get('estresado', {}).get(id_sel)
        
        if matriz_base is None or matriz_est is None:
            messagebox.showerror("Sin Datos", f"No se encontraron matrices simuladas para el crédito: {id_sel}")
            return
        
        # Obtener información del crédito
        fila = self.motor_calculo.df_creditos[self.motor_calculo.df_creditos["ID_producto"] == id_sel]
        if fila.empty:
            messagebox.showerror("Error", "No se encontró información del crédito seleccionado.")
            return
        
        tasa_contractual = fila["Tasa"].values[0]
        moneda = fila["Moneda"].values[0] if "Moneda" in fila.columns else "COP"
        diferencial_prepago = self.panel_filtros.get_valores_filtros()["diferencial_prepago"] / 100.0
        umbral_prepago = tasa_contractual - diferencial_prepago
        
        # Eje temporal (días desde fecha de corte)
        n_pasos = matriz_base.shape[0]
        dias = range(n_pasos)
        
        # GRÁFICO 1: Escenario Base
        plt.figure(figsize=(12, 5))
        for sim in range(matriz_base.shape[1]):
            plt.plot(dias, matriz_base[:, sim], color='blue', alpha=0.2, linewidth=0.8)
        
        # Líneas de referencia
        plt.axhline(y=tasa_contractual, color='darkblue', linestyle='--', linewidth=1.5, 
                   label=f'Tasa Contractual ({tasa_contractual*100:.2f}%)')
        plt.axhline(y=umbral_prepago, color='green', linestyle='-.', linewidth=1.5, 
                   label=f'Umbral Prepago ({umbral_prepago*100:.2f}%)')
        
        # Nota explicativa del criterio de prepago
        texto_criterio = (f"Criterio prepago: Tasa_Contractual - EA_simulada ≥ {diferencial_prepago*100:.2f}%\n"
                         f"Prepago cuando tasa simulada ≤ {umbral_prepago*100:.2f}%")
        plt.text(0.02, 0.98, texto_criterio, transform=plt.gca().transAxes, 
                fontsize=9, verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.title(f"Simulaciones Hull-White MC Base - {id_sel} ({moneda})\n100 trayectorias de Tasas EA simuladas")
        plt.xlabel("Días desde fecha de corte")
        plt.ylabel("Tasa EA")
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.legend(loc='upper right')
        plt.tight_layout()
        plt.show()
        
        # GRÁFICO 2: Escenario Estresado
        plt.figure(figsize=(12, 5))
        for sim in range(matriz_est.shape[1]):
            plt.plot(dias, matriz_est[:, sim], color='red', alpha=0.2, linewidth=0.8)
        
        # Líneas de referencia
        plt.axhline(y=tasa_contractual, color='darkblue', linestyle='--', linewidth=1.5, 
                   label=f'Tasa Contractual ({tasa_contractual*100:.2f}%)')
        plt.axhline(y=umbral_prepago, color='green', linestyle='-.', linewidth=1.5, 
                   label=f'Umbral Prepago ({umbral_prepago*100:.2f}%)')
        
        # Nota explicativa del criterio de prepago
        plt.text(0.02, 0.98, texto_criterio, transform=plt.gca().transAxes, 
                fontsize=9, verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.title(f"Simulaciones Hull-White MC Estresadas - {id_sel} ({moneda})\n100 trayectorias de Tasas EA simuladas (σ × 1.25)")
        plt.xlabel("Días desde fecha de corte")
        plt.ylabel("Tasa EA")
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.legend(loc='upper right')
        plt.tight_layout()
        plt.show()

    def _graficar_hull_white(self, id_sel):
        """DEPRECADO: Grafica las trayectorias de tasas del modelo Hull-White (árbol trinomial)."""
        # Obtener flujos del crédito seleccionado
        flujos_base = self.motor_calculo.portafolio_flujos_analisis.get(id_sel)
        flujos_estresados = self.motor_calculo.portafolio_flujos_estresados.get(id_sel)

        if not flujos_base or not flujos_estresados:
            messagebox.showerror("Sin Datos", f"No se encontraron simulaciones Hull-White para el crédito: {id_sel}")
            return

        # Obtener información del crédito
        fila = self.motor_calculo.df_creditos[self.motor_calculo.df_creditos["ID_producto"] == id_sel]
        if fila.empty:
            messagebox.showerror("Error", "No se encontró información del crédito seleccionado.")
            return

        tasa_contractual = fila["Tasa"].values[0]
        diferencial_prepago = self.panel_filtros.get_valores_filtros()["diferencial_prepago"] / 100.0
        umbral = tasa_contractual - diferencial_prepago

        # Determinar moneda y simuladores Hull-White
        moneda = fila["Moneda"].values[0] if "Moneda" in fila.columns else "COP"
        simuladores_hw = getattr(self.motor_calculo, 'simuladores_hull_white', None)
        if not simuladores_hw:
            messagebox.showwarning("Simuladores no disponibles", "No se encontraron simuladores Hull-White guardados.")
            return

        simulador_base = simuladores_hw.get('base', {}).get(moneda)
        simulador_est = simuladores_hw.get('estresado', {}).get(moneda)
        if simulador_base is None or simulador_est is None:
            messagebox.showwarning("Simulador no disponible", f"No se encontró simulador Hull-White para la moneda {moneda}.")
            return

        # Fechas objetivo: usar las fechas de pago del primer escenario como referencia
        # (todas las simulaciones generadas comparten el mismo calendario de pagos)
        if flujos_base[0].empty or 'Fecha_Pago' not in flujos_base[0].columns:
            messagebox.showerror("Sin Fechas", "No se encontraron fechas de pago en los flujos base.")
            return
        fechas_objetivo = pd.to_datetime(flujos_base[0]['Fecha_Pago']).tolist()

        # Simular TODAS las trayectorias reales en las fechas objetivo
        tasas_base = simulador_base.simular_trayectorias(fechas_objetivo, n_simulaciones=100)
        tasas_est = simulador_est.simular_trayectorias(fechas_objetivo, n_simulaciones=100)

        # Graficar: todas las trayectorias reales
        plt.figure(figsize=(12, 5))

        # Escenario Base
        plt.subplot(1, 2, 1)
        for sim_idx in range(tasas_base.shape[0]):
            plt.plot(fechas_objetivo, tasas_base[sim_idx, :], alpha=0.15, linewidth=0.6, color='blue')
        plt.axhline(y=tasa_contractual, color='red', linestyle='--', linewidth=1.2, label='Tasa Contractual')
        plt.axhline(y=umbral, color='green', linestyle='-.', linewidth=1.2, label='Umbral Prepago')
        plt.title(f"Hull-White Base - {id_sel}")
        plt.xlabel("Fecha")
        plt.ylabel("Tasa")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.xticks(rotation=45)

        # Escenario Estresado
        plt.subplot(1, 2, 2)
        for sim_idx in range(tasas_est.shape[0]):
            plt.plot(fechas_objetivo, tasas_est[sim_idx, :], alpha=0.15, linewidth=0.6, color='red')
        plt.axhline(y=tasa_contractual, color='red', linestyle='--', linewidth=1.2, label='Tasa Contractual')
        plt.axhline(y=umbral, color='green', linestyle='-.', linewidth=1.2, label='Umbral Prepago')
        plt.title(f"Hull-White Estresado (σ×1.25) - {id_sel}")
        plt.xlabel("Fecha")
        plt.ylabel("Tasa")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.xticks(rotation=45)

        plt.tight_layout()
        plt.show()

        # Gráfico adicional: Comparación de flujos totales
        self._graficar_comparacion_flujos_hull_white(id_sel, flujos_base, flujos_estresados)
    
    def _graficar_comparacion_flujos_hull_white(self, id_sel, flujos_base, flujos_estresados):
        """Gráfico adicional comparando flujos totales Hull-White."""
        
        plt.figure(figsize=(10, 6))
        
        # Calcular flujos promedio por fecha
        if flujos_base and flujos_estresados:
            # Tomar primer escenario como referencia para fechas
            if flujos_base[0].empty or flujos_estresados[0].empty:
                return
                
            fechas_ref = pd.to_datetime(flujos_base[0]['Fecha_Pago'])
            
            # Calcular flujos promedio base
            flujos_prom_base = []
            for fecha in fechas_ref:
                flujos_fecha = []
                for escenario in flujos_base[:50]:  # Usar más escenarios para promedio
                    if not escenario.empty:
                        flujo_fecha = escenario[escenario['Fecha_Pago'] == fecha]['Flujo_Total'].sum()
                        if flujo_fecha > 0:
                            flujos_fecha.append(flujo_fecha)
                flujos_prom_base.append(np.mean(flujos_fecha) if flujos_fecha else 0)
            
            # Calcular flujos promedio estresados
            flujos_prom_estresados = []
            for fecha in fechas_ref:
                flujos_fecha = []
                for escenario in flujos_estresados[:50]:
                    if not escenario.empty:
                        flujo_fecha = escenario[escenario['Fecha_Pago'] == fecha]['Flujo_Total'].sum()
                        if flujo_fecha > 0:
                            flujos_fecha.append(flujo_fecha)
                flujos_prom_estresados.append(np.mean(flujos_fecha) if flujos_fecha else 0)
            
            plt.plot(fechas_ref, flujos_prom_base, 'b-', linewidth=2, label='Base (promedio)', marker='o')
            plt.plot(fechas_ref, flujos_prom_estresados, 'r-', linewidth=2, label='Estresado (promedio)', marker='s')
            
            plt.title(f"Comparación Flujos Hull-White - {id_sel}")
            plt.xlabel("Fecha")
            plt.ylabel("Flujo Total Promedio")
            plt.grid(True, alpha=0.3)
            plt.legend()
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.show()

    def _guardar_creditos_fase4(self):
        try:
            self.motor_calculo.guardar_creditos_fase4(self.df_filtrado)
            messagebox.showinfo("Guardado", "Créditos y flujos seleccionados guardados para la Fase 4.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron guardar los créditos para la Fase 4: {str(e)}")

    def _calcular_flujos_descuento_actualizar_panel(self):
        try:
            import logging
            logging.info("Iniciando cálculo de flujos de descuento...")
            df_descuentos = self.motor_calculo.calcular_flujos_descuento()
            logging.info(f"Descuentos calculados. Shape: {df_descuentos.shape}")
            self.panel_descuento.actualizar_flujos(df_descuentos)
            
            # Generar gráficos de curvas de descuento por moneda en Fase 4
            if hasattr(self.motor_calculo, 'dict_curvas_base') and hasattr(self.motor_calculo, 'dict_curvas_norm'):
                logging.info("Generando gráficos de curvas de descuento en Fase 4...")
                self.panel_descuento.actualizar_grafico(
                    self.motor_calculo.dict_curvas_base,
                    self.motor_calculo.dict_curvas_norm
                )
                logging.info("✅ Gráficos de curvas generados correctamente")
            else:
                logging.warning("⚠️ No se encontraron datos de curvas para generar gráficos")
            
            messagebox.showinfo("Descuentos Calculados", "Los valores presentes han sido calculados correctamente.")
        except Exception as e:
            import traceback
            logging.error(f"Error en cálculo de descuentos: {str(e)}")
            logging.error(traceback.format_exc())
            messagebox.showerror("Error", f"Error al calcular descuentos: {str(e)}")

    def _calcular_sensibilidad(self):
        try:
            df_sensibilidades = self.motor_calculo.calcular_sensibilidades()
            self.panel_sensibilidad.mostrar_resultados(df_sensibilidades)
        except Exception as e:
            messagebox.showerror("Error", f"Error al calcular sensibilidad: {str(e)}")
    
    def _calcular_validacion(self):
        """
        Ejecuta validación llamando al orquestador.
        """
        try:
            # Verificar que se han ejecutado simulaciones
            if not hasattr(self.motor_calculo, 'matrices_simuladas'):
                messagebox.showwarning(
                    "Sin Simulaciones",
                    "Debe ejecutar primero las simulaciones en Fase 3 antes de validar."
                )
                return None
            
            # Obtener modelo seleccionado
            modelo_seleccionado = self.panel_fase2.get_modelo_seleccionado()
            
            # Llamar al orquestador
            self.logger.info(f"🎯 Llamando validación para modelo: {modelo_seleccionado}")
            resultados = self.motor_calculo.validar_simulaciones(modelo_seleccionado)
            
            if resultados:
                self.logger.info("✅ Validación completada exitosamente")
            else:
                self.logger.warning("⚠️ No se generaron resultados de validación")
            
            return resultados
            
        except Exception as e:
            log_error_detallado(self.logger, "Error en validación de simulaciones", e)
            messagebox.showerror(
                "Error en Validación",
                f"Ocurrió un error durante la validación:\n{str(e)}"
            )
            return None

    


