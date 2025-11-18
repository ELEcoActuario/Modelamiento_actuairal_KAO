import tkinter as tk
from tkinter import ttk
import pandas as pd

class PanelSensibilidad(tk.Frame):
    def __init__(self, master=None, calcular_command=None):
        super().__init__(master)
        self.df_descuentos = None
        self.df_sensibilidad = None
        self.calcular_command = calcular_command  # Enlazado desde App
        self._crear_widgets()

    def _crear_widgets(self):
        self.label_titulo = tk.Label(self, text="Fase 5 - Análisis de Sensibilidad", font=("Helvetica", 14, "bold"))
        self.label_titulo.pack(pady=10)

        self.btn_calcular = tk.Button(self, text="Calcular sensibilidad", command=self._on_btn_calcular)
        self.btn_calcular.pack(pady=5)

        self.tree = ttk.Treeview(self, columns=(
            "ID_producto",
            "Δ_Paralelo_hacia_arriba",
            "Δ_Paralelo_hacia_abajo",
            "Δ_Empinamiento",
            "Δ_Aplanamiento",
            "Δ_Corto_plazo_hacia_arriba",
            "Δ_Corto_plazo_hacia_abajo"
        ), show="headings", height=20)

        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=170)
        self.tree.pack(pady=10, fill=tk.BOTH, expand=True)

        self.label_total = tk.Label(self, text="", font=("Helvetica", 12, "bold"))
        self.label_total.pack(pady=10)

    def _on_btn_calcular(self):
        if self.calcular_command:
            self.calcular_command()

    def mostrar_resultados(self, df_sensibilidades):
        """
        Método invocado desde App para mostrar los resultados de sensibilidad ya calculados.
        """
        self.df_sensibilidad = df_sensibilidades.copy()
        self._mostrar_tabla()

    def _mostrar_tabla(self):
        self.tree.delete(*self.tree.get_children())

        for _, row in self.df_sensibilidad.iterrows():
            self.tree.insert("", "end", values=list(row.values))

        totales = self.df_sensibilidad.drop(columns="ID_producto").sum(numeric_only=True)
        resumen = "  |  ".join([f"{col}: {totales[col]:,.2f}" for col in totales.index])
        self.label_total.config(text=f"Suma total por escenario:\n{resumen}")
