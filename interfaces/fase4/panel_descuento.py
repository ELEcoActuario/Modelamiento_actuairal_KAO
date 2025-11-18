import tkinter as tk
from tkinter import ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import itertools
import logging
import numpy as np

class PanelDescuento(ttk.Frame):
    """
    Panel de Fase 4: Muestra tabla con los valores presentes (VP) por crédito
    en escenario base y estresados. También muestra los gráficos de curvas.
    """
    def __init__(self, master):
        super().__init__(master, padding=10)
        self._crear_widgets()
        self.curvas_base_data = None
        self.curvas_estresadas_data = None

    def _crear_widgets(self):
        frame_flujos = ttk.LabelFrame(self, text="Valores Presentes por Crédito y Escenario")
        frame_flujos.pack(fill="both", expand=True, pady=5)

        cols = [
            "ID_producto", "VP_base",
            "VP_est_Paralelo_hacia_arriba",
            "VP_est_Paralelo_hacia_abajo",
            "VP_est_Empinamiento",
            "VP_est_Aplanamiento",
            "VP_est_Corto_plazo_hacia_arriba",
            "VP_est_Corto_plazo_hacia_abajo"
        ]
        self.tabla_flujos = ttk.Treeview(frame_flujos, columns=cols, show="headings", height=14)
        for col in cols:
            display_col = col.replace("VP_est_", "").replace("_", " ").replace("Paralelo hacia", "Paralelo H.C.") \
                            .replace("Corto plazo hacia", "C. Plazo H.C.")
            self.tabla_flujos.heading(col, text=display_col)
            self.tabla_flujos.column(col, width=160 if col == "ID_producto" else 130, anchor="e")
        self.tabla_flujos.pack(fill="both", expand=True)

        self.boton_descuentos = ttk.Button(frame_flujos, text="Calcular Descuentos", command=self._on_calcular_descuentos)
        self.boton_descuentos.pack(pady=5)

        frame_graficos = ttk.LabelFrame(self, text="Gráficos de Curvas de Tasas")
        frame_graficos.pack(fill="both", expand=True, pady=5)

        moneda_frame = ttk.Frame(frame_graficos)
        moneda_frame.pack(fill="x", pady=5)

        ttk.Label(moneda_frame, text="Seleccionar Moneda:").pack(side="left", padx=5)
        self.moneda_var = tk.StringVar(value="COP")
        self.combo_moneda = ttk.Combobox(moneda_frame, values=["COP", "USD", "UVR"], state="readonly", width=10, textvariable=self.moneda_var)
        self.combo_moneda.pack(side="left")
        self.combo_moneda.bind("<<ComboboxSelected>>", self._on_cambio_moneda)

        self.fig, self.ax = plt.subplots(figsize=(8, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame_graficos)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def actualizar_flujos(self, df_flujos_descuento: pd.DataFrame):
        self.tabla_flujos.delete(*self.tabla_flujos.get_children())
        if df_flujos_descuento is None or df_flujos_descuento.empty:
            logging.info("DataFrame de flujos de descuento vacío o nulo. No se actualizará la tabla.")
            return

        columnas_a_mostrar = self.tabla_flujos["columns"]
        df_display = df_flujos_descuento.reindex(columns=columnas_a_mostrar, fill_value=np.nan)

        for _, row in df_display.iterrows():
            valores = []
            for col in columnas_a_mostrar:
                val = row.get(col)
                if pd.isna(val) or val is None:
                    valores.append("0.00" if col != "ID_producto" else "")
                else:
                    valores.append(f"{val:,.2f}" if col != "ID_producto" else str(val))
            self.tabla_flujos.insert("", "end", values=valores)
        logging.info("Tabla de flujos de descuento actualizada.")

    def actualizar_grafico(self, df_tasas_base: dict, dict_curvas_estresadas_consolidadas: dict):
        self.ax.clear()
        moneda = self.moneda_var.get()
        logging.info(f"Actualizando gráfico para moneda: {moneda}")

        self.curvas_base_data = df_tasas_base
        self.curvas_estresadas_data = dict_curvas_estresadas_consolidadas

        all_time_values = []
        all_tasa_values = []

        # --- Graficar Curva Base ---
        df_base_moneda = df_tasas_base.get(moneda)
        if df_base_moneda is not None and not df_base_moneda.empty and \
           {"Tiempo", "Tasa"}.issubset(df_base_moneda.columns):
            df_base_moneda_plot = df_base_moneda.copy()
            df_base_moneda_plot["Tiempo"] = pd.to_numeric(df_base_moneda_plot["Tiempo"], errors='coerce')
            df_base_moneda_plot["Tasa"] = pd.to_numeric(df_base_moneda_plot["Tasa"], errors='coerce')
            df_base_moneda_plot.dropna(subset=["Tiempo", "Tasa"], inplace=True)

            if not df_base_moneda_plot.empty:
                self.ax.plot(df_base_moneda_plot["Tiempo"], df_base_moneda_plot["Tasa"], label="Escenario Base", color="blue", linewidth=2)
                all_time_values.extend(df_base_moneda_plot["Tiempo"].tolist())
                all_tasa_values.extend(df_base_moneda_plot["Tasa"].tolist())
                logging.info(f"Curva base para {moneda} graficada.")
            else:
                logging.warning(f"DataFrame base para {moneda} vacío después de la conversión/limpieza.")
        else:
            logging.warning(f"No se pudieron graficar los datos de la curva base para {moneda}. Datos nulos/vacíos o columnas faltantes.")

        # --- Graficar Curvas Estresadas ---
        color_cycle = itertools.cycle(["red", "orange", "green", "purple", "brown", "cyan", "gray", "magenta"])

        curvas_consolidado_moneda = dict_curvas_estresadas_consolidadas.get(moneda)

        if curvas_consolidado_moneda is not None and not curvas_consolidado_moneda.empty and \
           {"Tiempo", "Tasa", "Choque"}.issubset(curvas_consolidado_moneda.columns):

            curvas_consolidado_moneda_plot = curvas_consolidado_moneda.copy()
            curvas_consolidado_moneda_plot["Tiempo"] = pd.to_numeric(curvas_consolidado_moneda_plot["Tiempo"], errors='coerce')
            curvas_consolidado_moneda_plot["Tasa"] = pd.to_numeric(curvas_consolidado_moneda_plot["Tasa"], errors='coerce')
            curvas_consolidado_moneda_plot.dropna(subset=["Tiempo", "Tasa"], inplace=True)

            if not curvas_consolidado_moneda_plot.empty:
                curvas_consolidado_moneda_plot = curvas_consolidado_moneda_plot.sort_values(by="Tiempo")

                for choque, df_sub in curvas_consolidado_moneda_plot.groupby("Choque"):
                    if not df_sub.empty:
                        self.ax.plot(df_sub["Tiempo"], df_sub["Tasa"], label=choque, color=next(color_cycle), linestyle='--')
                        all_time_values.extend(df_sub["Tiempo"].tolist())
                        all_tasa_values.extend(df_sub["Tasa"].tolist())
                        logging.info(f"Curva estresada '{choque}' para {moneda} graficada.")
                    else:
                        logging.warning(f"DataFrame vacío para el choque '{choque}' en {moneda} después de la conversión/limpieza.")
            else:
                logging.warning(f"El DataFrame consolidado para {moneda} está vacío después de la conversión de tipos y limpieza.")
        else:
            logging.warning(f"No se pudieron graficar las curvas estresadas para {moneda}. Datos nulos/vacíos o columnas faltantes (Tiempo, Tasa, Choque).")

        # --- AJUSTES ESTÉTICOS GENERALES ---
        if not all_time_values or not all_tasa_values:
            self.ax.set_title(f"No hay datos para Curvas de Tasas en {moneda}")
            self.ax.set_xlabel("Tiempo") # Etiqueta genérica si no hay datos
            self.ax.set_ylabel("Tasa de Interés (%)")
            self.canvas.draw()
            logging.warning(f"No hay datos suficientes para graficar en {moneda}.")
            return

        min_time_val = min(all_time_values)
        max_time_val = max(all_time_values)

        # Ajustar el eje X para que no sea tan denso y cubra el rango completo
        # Añadimos un pequeño margen porcentual a los límites para que las curvas no toquen los bordes.
        x_buffer = (max_time_val - min_time_val) * 0.05
        if x_buffer == 0: # Si todos los valores de tiempo son iguales
            x_buffer = 0.01 # Pequeño margen fijo
        self.ax.set_xlim(left=min_time_val - x_buffer, right=max_time_val + x_buffer)

        range_time = max_time_val - min_time_val

        # Calcular el número deseado de ticks (ej. entre 5 y 10)
        num_ticks = 8 # Número preferido de ticks

        if range_time > 0:
            ticks_to_show = np.linspace(min_time_val, max_time_val, num_ticks)
        else: # Si todos los valores de tiempo son iguales, solo mostrar ese valor
            ticks_to_show = np.array([min_time_val])

        # Formatear las etiquetas del eje X a Años o Meses
        # Asumiendo que 'Tiempo' está en años (días / 365)
        x_labels = []
        for t in ticks_to_show:
            if t < 1: # Si el tiempo es menor a 1 año, mostrar en meses
                meses = int(t * 12)
                x_labels.append(f"{meses} m")
            else: # Si es 1 año o más, mostrar en años
                x_labels.append(f"{t:.1f} a") # Mostrar un decimal para años

        self.ax.set_xticks(ticks_to_show)
        self.ax.set_xticklabels(x_labels)
        self.ax.set_xlabel("Tiempo (Años/Meses)") # Etiqueta actualizada para el eje X

        # Ampliar los rangos del eje Y de forma más robusta
        min_tasa = min(all_tasa_values)
        max_tasa = max(all_tasa_values)

        if np.isclose(min_tasa, max_tasa): # Si todas las tasas son las mismas
            min_tasa_adjusted = min_tasa - abs(min_tasa * 0.1) if min_tasa != 0 else -0.01
            max_tasa_adjusted = max_tasa + abs(max_tasa * 0.1) if max_tasa != 0 else 0.01
            if np.isclose(min_tasa_adjusted, max_tasa_adjusted):
                 min_tasa_adjusted = min_tasa - 0.005
                 max_tasa_adjusted = max_tasa + 0.005
        else:
            margen_y = (max_tasa - min_tasa) * 0.20
            min_tasa_adjusted = min_tasa - margen_y
            max_tasa_adjusted = max_tasa + margen_y

        self.ax.set_ylim(min_tasa_adjusted, max_tasa_adjusted)
        logging.info(f"Rango del eje Y ajustado: [{min_tasa_adjusted:.4f}, {max_tasa_adjusted:.4f}]")

        self.ax.set_title(f"Curvas de Tasas para {moneda}")
        self.ax.set_ylabel("Tasa de Interés (%)")
        self.ax.legend(loc='best', fontsize='small')
        self.ax.grid(True)
        self.fig.tight_layout()
        self.canvas.draw()
        logging.info("Gráfico actualizado en canvas.")

    def _on_cambio_moneda(self, event):
        if self.curvas_base_data is not None and self.curvas_estresadas_data is not None:
            logging.info(f"Moneda cambiada a {self.moneda_var.get()}. Redibujando gráfico.")
            self.actualizar_grafico(self.curvas_base_data, self.curvas_estresadas_data)
        else:
            logging.warning("No hay datos de curvas para redibujar al cambiar la moneda. Asegúrese de cargar los datos primero.")

    def _on_calcular_descuentos(self):
        if hasattr(self, "callback_descuentos"):
            logging.info("Botón 'Calcular Descuentos' presionado.")
            self.callback_descuentos()

    def set_callback_actualizar_grafico(self, callback):
        self.callback_actualizar_grafico = callback

    def set_callback_descuentos(self, callback):
        self.callback_descuentos = callback