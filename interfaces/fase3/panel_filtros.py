import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry

class PanelFiltros(ttk.LabelFrame):
    def __init__(self, master, aplicar_filtros_command, graficar_command, guardar_fase4_command=None):
        super().__init__(master, text="Controles de Cálculo y Filtros", padding=10)

        self.aplicar_filtros_command = aplicar_filtros_command
        self.graficar_command = graficar_command
        self.guardar_fase4_command = guardar_fase4_command

        self._crear_widgets()

    def _crear_widgets(self):
        frame_superior = ttk.Frame(self)
        frame_superior.pack(fill="x", pady=5)

        # Texto de ayuda
        lbl_info = ttk.Label(
            frame_superior,
            text=(
                "💡 Ingrese la Tasa Diferencial de Prepago en puntos porcentuales.\n"
                "Criterio de prepago: Tasa_Contractual - Tasa_Simulada ≥ Diferencial\n"
                "(Prepago cuando la tasa de mercado es suficientemente más baja que la contractual)"
            ),
            foreground="blue", justify="left"
        )
        lbl_info.grid(row=0, column=0, columnspan=4, sticky="w", padx=5, pady=(0, 5))

        # Fecha de corte
        ttk.Label(frame_superior, text="Fecha de Corte:").grid(row=1, column=0, sticky="w", padx=5)
        self.fecha_corte = DateEntry(frame_superior, date_pattern='yyyy-mm-dd')
        self.fecha_corte.grid(row=1, column=1, padx=5)

        # Diferencial prepago
        ttk.Label(frame_superior, text="Tasa Diferencial Prepago (%):").grid(row=1, column=2, sticky="w", padx=5)
        self.dif_prepago = ttk.Entry(frame_superior, width=10)
        self.dif_prepago.grid(row=1, column=3, padx=5)

        # Número de simulaciones
        ttk.Label(frame_superior, text="Número de Simulaciones:").grid(row=2, column=0, sticky="w", padx=5)
        self.n_simulaciones = ttk.Entry(frame_superior, width=10)
        self.n_simulaciones.insert(0, "100")  # Valor por defecto
        self.n_simulaciones.grid(row=2, column=1, padx=5)

        # Filtros
        frame_filtros = ttk.Frame(self)
        frame_filtros.pack(fill="x", pady=5)

        ttk.Label(frame_filtros, text="Amortización:").grid(row=0, column=0, padx=5)
        self.filtro_amort = ttk.Combobox(frame_filtros, state="readonly")
        self.filtro_amort.grid(row=0, column=1, padx=5)

        ttk.Label(frame_filtros, text="Producto:").grid(row=0, column=2, padx=5)
        self.filtro_producto = ttk.Combobox(frame_filtros, state="readonly")
        self.filtro_producto.grid(row=0, column=3, padx=5)

        ttk.Label(frame_filtros, text="Moneda:").grid(row=0, column=4, padx=5)
        self.filtro_moneda = ttk.Combobox(frame_filtros, state="readonly")
        self.filtro_moneda.grid(row=0, column=5, padx=5)

        ttk.Label(frame_filtros, text="Periodicidad:").grid(row=0, column=6, padx=5)
        self.filtro_periodicidad = ttk.Combobox(frame_filtros, state="readonly")
        self.filtro_periodicidad['values'] = ["Exacta", "Mensual", "Trimestral", "Semestral", "Anual", "Bandas SFC"]
        self.filtro_periodicidad.current(0)
        self.filtro_periodicidad.grid(row=0, column=7, padx=5)
        self.filtro_periodicidad.bind("<<ComboboxSelected>>", lambda e: self._on_periodicidad_cambiada())

        # Botones de acción
        frame_botones = ttk.Frame(self)
        frame_botones.pack(fill="x", pady=10)

        ttk.Button(frame_botones, text="Aplicar Filtros y Calcular", command=self.aplicar_filtros_command).pack(side="left", padx=10)
        ttk.Button(frame_botones, text="Ver Gráficos", command=self.graficar_command).pack(side="left", padx=10)

        if self.guardar_fase4_command:
            ttk.Button(frame_botones, text="Guardar créditos para Fase 4", command=self.guardar_fase4_command).pack(side="left", padx=10)

    def habilitar_controles(self, df_creditos):
        # Amortización
        valores_amort = sorted(df_creditos["Tipo_Amortizacion"].dropna().unique().tolist())
        valores_amort.insert(0, "Todos")
        self.filtro_amort['values'] = valores_amort
        self.filtro_amort.set("Todos")

        # Producto
        valores_producto = sorted(df_creditos["Tipo_producto"].dropna().unique().tolist())
        valores_producto.insert(0, "Todos")
        self.filtro_producto['values'] = valores_producto
        self.filtro_producto.set("Todos")

        # Moneda
        valores_moneda = sorted(df_creditos["Moneda"].dropna().unique().tolist())
        valores_moneda.insert(0, "Todos")
        self.filtro_moneda['values'] = valores_moneda
        self.filtro_moneda.set("Todos")

    def get_valores_filtros(self):
        try:
            diferencial = float(self.dif_prepago.get())
        except ValueError:
            diferencial = 0.0  # valor por defecto si el usuario escribe algo inválido

        try:
            n_sims = int(self.n_simulaciones.get())
            if n_sims < 1:
                n_sims = 100  # valor por defecto si es inválido
        except ValueError:
            n_sims = 100  # valor por defecto si el usuario escribe algo inválido

        return {
            "fecha_corte": self.fecha_corte.get_date(),
            "diferencial_prepago": diferencial,
            "n_simulaciones": n_sims,
            "amortizacion": self.filtro_amort.get(),
            "producto": self.filtro_producto.get(),
            "moneda": self.filtro_moneda.get(),
            "periodicidad": self.filtro_periodicidad.get()
        }

    def set_callback_periodicidad(self, callback):
        self._callback_periodicidad = callback

    def _on_periodicidad_cambiada(self):
        if hasattr(self, "_callback_periodicidad"):
            self._callback_periodicidad()
