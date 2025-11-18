import tkinter as tk
from tkinter import ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from motores.utils.agrupacion_flujos import agrupar_flujos_originales, agrupar_flujos_ajustados

class PanelResultados(ttk.Frame):
    def __init__(self, master, callback_simulacion=None):
        super().__init__(master, padding=10)
        self.callback_simulacion = callback_simulacion
        self.agrupacion_actual = "Exacta"
        self._crear_widgets()

    def _crear_widgets(self):
        lbl_info = ttk.Label(
            self,
            text=(
                "📌 Este panel muestra los flujos futuros del crédito seleccionado.\n"
                "Puede cambiar entre simulaciones de prepago base y estresado usando las listas desplegables.\n"
                "Los flujos están agrupados según la periodicidad seleccionada en los filtros."
            ),
            foreground="blue", justify="left"
        )
        lbl_info.pack(anchor="w", pady=(0, 10))

        self.configs = {
            "orig": {
                "label": "Flujo Contractual Futuro",
                "cols": ("Periodo", "Capital", "Intereses", "Flujo_Total")
            },
            "base": {
                "label": "Flujos con Prepago (Base)",
                "cols": ("Periodo", "Capital_Ajustado", "Intereses_Ajustados", "Flujo_Total_Ajustado")
            },
            "est": {
                "label": "Flujos con Prepago (Estresado)",
                "cols": ("Periodo", "Capital_Ajustado", "Intereses_Ajustados", "Flujo_Total_Ajustado")
            }
        }

        self.tablas = {}
        self.sim_selectores = {}

        for key, cfg in self.configs.items():
            frame = ttk.LabelFrame(self, text=cfg["label"])
            frame.pack(fill="both", expand=True, pady=5)

            if key in ["base", "est"]:
                selector = ttk.Combobox(frame, state="readonly")
                selector.pack(anchor="w")
                selector.bind("<<ComboboxSelected>>", lambda e, k=key: self._on_selector_changed(k))
                self.sim_selectores[key] = selector

            tree = ttk.Treeview(frame, columns=cfg["cols"], show="headings", height=8)
            for col in cfg["cols"]:
                tree.heading(col, text=col)
            tree.pack(fill="both", expand=True)
            self.tablas[key] = tree

        resumen_frame = ttk.LabelFrame(self, text="Resumen Comparativo (a Fecha de Corte)")
        resumen_frame.pack(fill="x", pady=5)
        self.label_resumen = ttk.Label(resumen_frame, text="Seleccione un crédito para ver detalles.", justify="left")
        self.label_resumen.pack(anchor="w")
        
        # Frame para resultados de valoración
        self.frame_vp = ttk.LabelFrame(self, text="Valoración del Modelo")
        
        # Frame para valores numéricos
        frame_valores = ttk.Frame(self.frame_vp)
        frame_valores.pack(fill="x", pady=5)
        
        # Labels para VP Base
        frame_vp_base = ttk.Frame(frame_valores)
        frame_vp_base.pack(fill="x", pady=2)
        ttk.Label(frame_vp_base, text="Valor Presente (Base):").pack(side="left")
        self.lbl_vp_base_valor = ttk.Label(frame_vp_base, text="$0.00", font=("Arial", 10, "bold"), foreground="blue")
        self.lbl_vp_base_valor.pack(side="right")
        
        # Labels para VP Estresado
        frame_vp_estresado = ttk.Frame(frame_valores)
        frame_vp_estresado.pack(fill="x", pady=2)
        ttk.Label(frame_vp_estresado, text="Valor Presente (Estresado):").pack(side="left")
        self.lbl_vp_estresado_valor = ttk.Label(frame_vp_estresado, text="$0.00", font=("Arial", 10, "bold"), foreground="red")
        self.lbl_vp_estresado_valor.pack(side="right")
        
        # Labels para diferencia
        frame_diferencia = ttk.Frame(frame_valores)
        frame_diferencia.pack(fill="x", pady=2)
        ttk.Label(frame_diferencia, text="Impacto del Estrés:").pack(side="left")
        self.lbl_diferencia_valor = ttk.Label(frame_diferencia, text="$0.00 (0.00%)", font=("Arial", 10, "bold"), foreground="darkgreen")
        self.lbl_diferencia_valor.pack(side="right")
        
        # Frame para gráfico de comparación
        self.frame_grafico_vp = ttk.Frame(self.frame_vp)
        self.frame_grafico_vp.pack(fill="both", expand=True, pady=5)
        
        # Ocultar frame de VPs por defecto
        self.frame_vp.pack_forget()
        
        # Guardar referencias a frames de flujos para mostrar/ocultar
        self.frames_flujos = []
        for key, cfg in self.configs.items():
            # Buscar el frame correspondiente en los widgets ya creados
            for widget in self.winfo_children():
                if isinstance(widget, ttk.LabelFrame) and widget.cget("text") == cfg["label"]:
                    self.frames_flujos.append(widget)
                    break
        self.frames_flujos.append(resumen_frame)  # Incluir frame de resumen

    def limpiar_vista(self):
        for tabla in self.tablas.values():
            tabla.delete(*tabla.get_children())
        for selector in self.sim_selectores.values():
            selector.set("")
            selector["values"] = []
        self.label_resumen.config(text="Seleccione un crédito o vea los totales agrupados.")

    def mostrar_resultados_flujos(self, df_orig, lista_base, lista_est, idx_base, idx_est, agrupacion: str, fecha_corte: pd.Timestamp):
        # Ocultar frame de VPs y mostrar frames de flujos
        self.frame_vp.pack_forget()
        for frame in self.frames_flujos:
            frame.pack(fill="both" if "Resumen" not in frame.cget("text") else "x", expand=True if "Resumen" not in frame.cget("text") else False, pady=5)
        
        self.agrupacion_actual = agrupacion
        self.limpiar_vista()

        if df_orig is None or df_orig.empty or 'Fecha_Pago' not in df_orig.columns:
            self.label_resumen.config(text="No hay datos para mostrar.")
            return

        df_orig = df_orig[pd.to_datetime(df_orig['Fecha_Pago']) >= pd.to_datetime(fecha_corte)].copy()
        if df_orig.empty:
            self.label_resumen.config(text="No hay flujos futuros a partir de la fecha de corte.")
            return

        # Filtrar solo simulaciones con prepago
        self.lista_base = [df for df in (lista_base or []) if self._tiene_prepago(df)]
        self.lista_est = [df for df in (lista_est or []) if self._tiene_prepago(df)]
        self.df_orig = df_orig

        # Mostrar simulaciones disponibles
        self.sim_selectores["base"]["values"] = [self._obtener_nombre_simulacion(df, i+1) for i, df in enumerate(self.lista_base)]
        self.sim_selectores["est"]["values"] = [self._obtener_nombre_simulacion(df, i+1) for i, df in enumerate(self.lista_est)]

        if self.lista_base:
            idx_base_safe = max(0, min(idx_base, len(self.lista_base) - 1))
            self.sim_selectores["base"].current(idx_base_safe)
        else:
            self.sim_selectores["base"].set("")
        if self.lista_est:
            idx_est_safe = max(0, min(idx_est, len(self.lista_est) - 1))
            self.sim_selectores["est"].current(idx_est_safe)
        else:
            self.sim_selectores["est"].set("")

        if not self.lista_base and not self.lista_est:
            self.label_resumen.config(text="No hay simulaciones con prepago para mostrar.")

        df_orig_agr = agrupar_flujos_originales(df_orig, agrupacion, fecha_corte)
        self._llenar_tabla(self.tablas["orig"], df_orig_agr, self.configs["orig"]["cols"], agrupacion)
        self._refrescar_tablas()
        self._actualizar_resumen()

    def _on_selector_changed(self, key):
        idx_base = self.sim_selectores["base"].current()
        idx_est = self.sim_selectores["est"].current()

        if self.callback_simulacion:
            self.callback_simulacion(idx_base, idx_est)

    def _indices_simulacion(self, lista_df):
        return [df.attrs.get("indice_simulacion", i) for i, df in enumerate(lista_df)]

    def _tiene_prepago(self, df):
        try:
            if df is None or df.empty:
                return False
            if "Prepago_Esperado" in df.columns:
                return bool((df["Prepago_Esperado"].fillna(0) > 0).any())
            return False
        except Exception:
            return False

    def _refrescar_tablas(self):
        agrupacion = self.agrupacion_actual

        idx_base = self.sim_selectores["base"].current()
        idx_est = self.sim_selectores["est"].current()

        df_base = self.lista_base[idx_base] if 0 <= idx_base < len(self.lista_base) else pd.DataFrame()
        df_est = self.lista_est[idx_est] if 0 <= idx_est < len(self.lista_est) else pd.DataFrame()

        df_base_agr, df_est_agr = agrupar_flujos_ajustados(df_base, df_est, agrupacion)

        self._llenar_tabla(self.tablas["base"], df_base_agr, self.configs["base"]["cols"], agrupacion)
        self._llenar_tabla(self.tablas["est"], df_est_agr, self.configs["est"]["cols"], agrupacion)
        self._actualizar_resumen()

    def _llenar_tabla(self, treeview, df, columnas, agrupacion):
        treeview.delete(*treeview.get_children())
        if df is None or df.empty:
            return

        for _, row in df.iterrows():
            values = [str(row.get("Periodo", ""))]
            for col in columnas[1:]:
                values.append(f"{row.get(col, 0):,.2f}")
            treeview.insert("", "end", values=values)

    def _actualizar_resumen(self):
        idx_base = self.sim_selectores["base"].current()
        idx_est = self.sim_selectores["est"].current()

        df_base = self.lista_base[idx_base] if 0 <= idx_base < len(self.lista_base) else pd.DataFrame()
        df_est = self.lista_est[idx_est] if 0 <= idx_est < len(self.lista_est) else pd.DataFrame()

        resumen = (
            f"Total Flujo Contractual Futuro: {self._sumar_col(self.df_orig, 'Flujo_Total'):,.2f}\n"
            f"Total Flujo Base (Prepago):      {self._sumar_col(df_base, 'Flujo_Total_Ajustado'):,.2f}\n"
            f"Total Flujo Estresado:           {self._sumar_col(df_est, 'Flujo_Total_Ajustado'):,.2f}"
        )
        self.label_resumen.config(text=resumen)

    def _sumar_col(self, df, columna):
        if df is None or columna not in df.columns:
            return 0
        return round(df[columna].sum(), 2)
    
    def _obtener_nombre_simulacion(self, df, indice):
        """Obtiene nombre descriptivo para simulación."""
        if hasattr(df, 'attrs'):
            # Identificador original de la simulación (1..N)
            if 'indice_simulacion' in df.attrs:
                try:
                    return f"Simulación #{int(df.attrs['indice_simulacion'])}"
                except Exception:
                    return f"Simulación #{df.attrs['indice_simulacion']}"
            # Usar cuota evaluada si está disponible
            elif 'cuota_evaluada' in df.attrs:
                return f"Simulación {indice} - Cuota {df.attrs['cuota_evaluada']}"
        
        # Fallback genérico
        return f"Simulación {indice}"
    
    def _obtener_cuota_evaluada(self, df, indice):
        if hasattr(df, 'attrs') and 'cuota_evaluada' in df.attrs:
            return df.attrs['cuota_evaluada']
        return indice
    
    def mostrar_resultados_vp(self, vp_base: float, vp_estresado: float):
        """
        Muestra los resultados de Valores Presentes del modelo.
        
        Args:
            vp_base: Valor Presente en escenario base
            vp_estresado: Valor Presente en escenario estresado
        """
        # Ocultar frames de flujos y mostrar frame de VPs
        for frame in self.frames_flujos:
            frame.pack_forget()
        
        self.frame_vp.pack(fill="both", expand=True, pady=10)
        
        # Calcular diferencia e impacto
        diferencia = vp_estresado - vp_base
        porcentaje_impacto = (diferencia / vp_base * 100) if vp_base != 0 else 0
        
        # Actualizar valores con formato de moneda
        self.lbl_vp_base_valor.config(text=f"${vp_base:,.2f}")
        self.lbl_vp_estresado_valor.config(text=f"${vp_estresado:,.2f}")
        
        # Actualizar diferencia con color según el impacto
        color_diferencia = "red" if diferencia < 0 else "green"
        signo = "-" if diferencia < 0 else "+"
        self.lbl_diferencia_valor.config(
            text=f"{signo}${abs(diferencia):,.2f} ({porcentaje_impacto:+.2f}%)",
            foreground=color_diferencia
        )
        
        # Crear gráfico de comparación
        self._crear_grafico_comparacion_vp(vp_base, vp_estresado)
    
    def _crear_grafico_comparacion_vp(self, vp_base: float, vp_estresado: float):
        """
        Crea un gráfico de barras comparando VP_base vs VP_estresado.
        
        Args:
            vp_base: Valor Presente en escenario base
            vp_estresado: Valor Presente en escenario estresado
        """
        # Limpiar frame anterior
        for widget in self.frame_grafico_vp.winfo_children():
            widget.destroy()
        
        # Crear figura
        fig, ax = plt.subplots(figsize=(8, 4))
        
        # Datos para el gráfico
        escenarios = ['Base\n(σ normal)', 'Estresado\n(σ × 1.25)']
        valores = [vp_base, vp_estresado]
        colores = ['steelblue', 'coral']
        
        # Crear gráfico de barras
        barras = ax.bar(escenarios, valores, color=colores, alpha=0.7, edgecolor='black', linewidth=1)
        
        # Añadir valores en las barras
        for i, (barra, valor) in enumerate(zip(barras, valores)):
            altura = barra.get_height()
            ax.text(barra.get_x() + barra.get_width()/2., altura + max(valores)*0.01,
                   f'${valor:,.0f}', ha='center', va='bottom', fontweight='bold', fontsize=10)
        
        # Calcular y mostrar diferencia
        diferencia = vp_estresado - vp_base
        porcentaje = (diferencia / vp_base * 100) if vp_base != 0 else 0
        
        # Añadir línea de diferencia
        if diferencia != 0:
            ax.annotate('', xy=(1, vp_estresado), xytext=(1, vp_base),
                       arrowprops=dict(arrowstyle='<->', color='red', lw=2))
            
            # Texto de diferencia
            y_medio = (vp_base + vp_estresado) / 2
            signo = "-" if diferencia < 0 else "+"
            ax.text(1.1, y_medio, f'{signo}${abs(diferencia):,.0f}\n({porcentaje:+.1f}%)', 
                   ha='left', va='center', fontweight='bold', fontsize=9,
                   bbox=dict(boxstyle="round,pad=0.3", facecolor='yellow', alpha=0.8))
        
        # Configuración del gráfico
        ax.set_title('Comparación de Valores Presentes\n(Impacto del Estrés de Volatilidad)', 
                    fontweight='bold', fontsize=12)
        ax.set_ylabel('Valor Presente ($)', fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        
        # Formatear eje Y con separadores de miles
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        # Ajustar layout
        plt.tight_layout()
        
        # Integrar en tkinter
        canvas = FigureCanvasTkAgg(fig, self.frame_grafico_vp)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Cerrar figura para liberar memoria
        plt.close(fig)
    
    def mostrar_frontera_prepago(self, datos_auditoria: list, n_periodos: int, volatilidad: float):
        """
        Muestra la frontera de prepago: un gráfico 2D que muestra cuándo es óptimo prepagar.
        
        Args:
            datos_auditoria: Lista de datos de auditoría del modelo
            n_periodos: Número de períodos del árbol
            volatilidad: Volatilidad usada en el modelo
        """
        # Ocultar frames de flujos y mostrar frame de VPs
        for frame in self.frames_flujos:
            frame.pack_forget()
        
        self.frame_vp.pack(fill="both", expand=True, pady=10)
        
        # Limpiar frame anterior
        for widget in self.frame_grafico_vp.winfo_children():
            widget.destroy()
        
        # Crear figura para frontera de prepago
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Extraer datos de auditoría para crear la frontera
        nodos_prepago = []
        nodos_continuar = []
        
        for dato in datos_auditoria:
            if 'Nodo' in dato and 'Tasa_Descuento' in dato and 'Decision' in dato:
                try:
                    # Parsear nodo (i,j)
                    nodo_str = str(dato['Nodo']).strip('()')
                    if ',' in nodo_str:
                        i, j = map(int, nodo_str.split(','))
                        tasa = float(dato.get('Tasa_Descuento', 0))
                        decision = str(dato.get('Decision', '')).upper()
                        
                        if decision == 'PREPAGO':
                            nodos_prepago.append((i, j, tasa))
                        else:
                            nodos_continuar.append((i, j, tasa))
                except (ValueError, TypeError):
                    continue
        
        # Dibujar nodos de prepago y continuar
        if nodos_prepago:
            periodos_prep = [nodo[0] for nodo in nodos_prepago]
            tasas_prep = [nodo[2] for nodo in nodos_prepago]
            ax.scatter(periodos_prep, tasas_prep, c='red', s=60, alpha=0.7, 
                      label='Prepago Óptimo', marker='s')
        
        if nodos_continuar:
            periodos_cont = [nodo[0] for nodo in nodos_continuar]
            tasas_cont = [nodo[2] for nodo in nodos_continuar]
            ax.scatter(periodos_cont, tasas_cont, c='green', s=60, alpha=0.7, 
                      label='Continuar Óptimo', marker='o')
        
        # Intentar dibujar la frontera de prepago
        if nodos_prepago and nodos_continuar:
            self._dibujar_linea_frontera(ax, nodos_prepago, nodos_continuar, n_periodos)
        
        # Configuración del gráfico
        ax.set_title('Frontera de Prepago\n(Condiciones Óptimas de Ejercicio de la Opción)', 
                    fontweight='bold', fontsize=12)
        ax.set_xlabel('Período de Tiempo', fontsize=10)
        ax.set_ylabel('Tasa de Interés', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Formatear eje Y como porcentajes
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1%}'))
        
        # Añadir información explicativa
        info_text = (
            f'Interpretación:\n'
            f'• Zona Roja: Prepago es óptimo\n'
            f'• Zona Verde: Continuar es óptimo\n'
            f'• Volatilidad: {volatilidad:.4f}\n'
            f'• Nodos analizados: {len(datos_auditoria)}'
        )
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes, 
               verticalalignment='top', fontsize=9,
               bbox=dict(boxstyle="round", facecolor='lightyellow', alpha=0.9))
        
        # Ajustar layout
        plt.tight_layout()
        
        # Integrar en tkinter
        canvas = FigureCanvasTkAgg(fig, self.frame_grafico_vp)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Cerrar figura para liberar memoria
        plt.close(fig)
    
    def _dibujar_linea_frontera(self, ax, nodos_prepago, nodos_continuar, n_periodos):
        """
        Intenta dibujar una línea que separe la zona de prepago de la de continuar.
        
        Args:
            ax: Axes de matplotlib
            nodos_prepago: Lista de nodos donde es óptimo prepagar
            nodos_continuar: Lista de nodos donde es óptimo continuar
            n_periodos: Número total de períodos
        """
        try:
            # Agrupar por período para encontrar la frontera
            frontera_puntos = []
            
            for periodo in range(n_periodos + 1):
                tasas_prepago_periodo = [nodo[2] for nodo in nodos_prepago if nodo[0] == periodo]
                tasas_continuar_periodo = [nodo[2] for nodo in nodos_continuar if nodo[0] == periodo]
                
                if tasas_prepago_periodo and tasas_continuar_periodo:
                    # La frontera está aproximadamente entre la tasa más baja de prepago
                    # y la tasa más alta de continuar
                    tasa_frontera = (min(tasas_prepago_periodo) + max(tasas_continuar_periodo)) / 2
                    frontera_puntos.append((periodo, tasa_frontera))
            
            # Dibujar línea de frontera si hay suficientes puntos
            if len(frontera_puntos) >= 2:
                periodos_frontera = [p[0] for p in frontera_puntos]
                tasas_frontera = [p[1] for p in frontera_puntos]
                ax.plot(periodos_frontera, tasas_frontera, 'b--', linewidth=2, 
                       label='Frontera Aproximada', alpha=0.8)
                
        except Exception as e:
            # Si falla el cálculo de frontera, no dibujar nada
            pass
    
    def _obtener_cuota_evaluada(self, df, numero_simulacion):
        """
        Obtiene el número de cuota evaluada en una simulación.
        
        Args:
            df: DataFrame de la simulación
            numero_simulacion: Número de simulación como fallback
            
        Returns:
            Número de cuota evaluada
        """
        if 'Cuota_Evaluada' in df.columns:
            cuota_evaluada = df['Cuota_Evaluada'].iloc[0] if not df.empty else numero_simulacion
            return cuota_evaluada
        else:
            return numero_simulacion

