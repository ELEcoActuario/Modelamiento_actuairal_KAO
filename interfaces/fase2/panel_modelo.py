import tkinter as tk
from tkinter import ttk

class PanelModelo(ttk.Frame):
    """
    Panel para la Fase 2: Selección y definición del modelo actuarial.
    """
    def __init__(self, master, modelos=None, on_confirmar=None):
        super().__init__(master, padding=10)
        self.on_confirmar = on_confirmar

        # Diccionario de definiciones técnicas completas por modelo
        self.definiciones = {
            "Vasicek": (
                "MODELO VASICEK - PROCESO ESTOCÁSTICO CON REVERSIÓN A LA MEDIA\n"
                "═══════════════════════════════════════════════════════════════\n\n"
                "DEFINICIÓN:\n"
                "Modelo de un factor para tasas de interés con reversión a la media hacia un nivel\n"
                "de largo plazo. Implementa proceso de Ornstein-Uhlenbeck para modelar la evolución\n"
                "estocástica de las tasas.\n\n"
                "ECUACIÓN DIFERENCIAL ESTOCÁSTICA:\n"
                "dr(t) = κ(θ - r(t))dt + σ dW(t)\n\n"
                "VARIABLES Y PARÁMETROS:\n"
                "• r(t): Tasa de interés instantánea en el tiempo t\n"
                "• κ (kappa): Velocidad de reversión a la media (κ > 0)\n"
                "• θ (theta): Nivel de largo plazo de la tasa (media de largo plazo)\n"
                "• σ (sigma): Volatilidad instantánea (σ > 0)\n"
                "• dW(t): Proceso de Wiener (movimiento browniano estándar)\n"
                "• dt: Incremento temporal infinitesimal\n\n"
                "CALIBRACIÓN:\n"
                "• Método: Máxima Verosimilitud (MLE) en espacio de short rates r=ln(1+EA), por tipo de crédito\n"
                "• Datos: Series históricas de tasas de mercado semanales (EA → short)\n"
                "• Paso temporal: dt = 7/365 años (base semanal)\n"
                "• Estimación: Parámetros (κ, θ, σ) por tipo (Comercial, Consumo, Vivienda)\n\n"
                "SIMULACIÓN:\n"
                "• Método: Euler-Maruyama con paso semanal Δ = 7/365 años\n"
                "• Trayectorias: N simulaciones Monte Carlo definidas por el usuario (Fase 3)\n"
                "• Espacio: Short rates (ln(1+EA)) → reconvertidos a EA para comparación con tasa contractual\n"
                "• Interpolación: Tasas diarias desde semanales (modo EA por compatibilidad)\n\n"
                "CRITERIO DE PREPAGO:\n"
                "• Umbral: umbral = tasa_contractual - diferencial_prepago\n"
                "• Condición: Prepago cuando tasa_simulada < umbral\n"
                "• Lógica: Si la tasa de mercado baja suficientemente, conviene prepagar\n"
                "ESCENARIO ESTRESADO:\n"
                "• Parámetros base: (κ, θ, σ)\n"
                "• Parámetros estresados: (κ, θ, σ × 1.25)\n"
                "• Incremento de volatilidad del 25% para análisis de estrés\n\n"
                "VALIDACIÓN DE CALIBRACIÓN:\n"
                "• Métricas: R², RMSE, MAE (tasas históricas vs predichas)\n"
                "• Espacio de validación: Short rates con transformación ln(1+EA)\n"
                "• Semáforo: R² ≥ 0.65 (verde), 0.40 ≤ R² < 0.65 (amarillo), R² < 0.40 (rojo)\n\n"
                "APLICACIÓN:\n"
                "Ideal para carteras con datos históricos robustos y análisis de sensibilidad\n"
                "a cambios en volatilidad de tasas de interés."
            ),
            "Hull-White": (
                "MODELO HULL-WHITE DE UN FACTOR - MONTE CARLO\n"
                "═══════════════════════════════════════════════════════════\n\n"
                "DEFINICIÓN:\n"
                "Modelo de tasas de interés de un factor con reversión a la media y función\n"
                "temporal θ(t) que permite ajuste perfecto a la curva de tasas observada.\n"
                "Implementación mediante simulación Monte Carlo con N trayectorias definidas por el usuario.\n\n"
                "ECUACIÓN DIFERENCIAL ESTOCÁSTICA:\n"
                "dr(t) = [θ(t) - a·r(t)]dt + σ dW(t)\n\n"
                "VARIABLES Y PARÁMETROS:\n"
                "• r(t): Tasa de interés instantánea en el tiempo t\n"
                "• a: Parámetro de reversión a la media (velocidad de ajuste)\n"
                "• θ(t): Función temporal de deriva (bajo P: θ(t)=μ_Q(t)+σλ)\n"
                "• σ: Volatilidad constante de la tasa corta\n"
                "• dW(t): Proceso de Wiener estándar\n\n"
                "CALIBRACIÓN:\n"
                "• Método: Calibración MLE específica por crédito usando CurvaHW\n"
                "• Parámetros: (a, σ, λ) calibrados por crédito (no global por moneda)\n"
                "• Función θ(t): θ(t)=μ_Q(t)+σλ sobre malla diaria τ_j=j/365 (ACT/365)\n"
                "• Datos: Curva de tasas libres de riesgo (nodos desde 1) hasta el vencimiento\n\n"
                "SIMULACIÓN:\n"
                "• Tipo: Monte Carlo con N simulaciones definidas por el usuario (base y estresado σ×1.25)\n"
                "• Malla temporal: diaria (τ_j=j/365), ACT/365\n"
                "• Conversión: Short rates → EA para comparación con tasa contractual\n"
                "• Interpolación: Lineal a fechas de pago del crédito\n\n"
                "CRITERIO DE PREPAGO (IGUAL A VASICEK):\n"
                "• Evaluación: En cada fecha de pago del crédito\n"
                "• Condición: (Tasa_Contractual - EA_simulada) ≥ Diferencial_Prepago\n"
                "• Interpretación: Prepago cuando tasa de mercado es suficientemente baja\n"
                "• Restricción: Solo primera ocurrencia por simulación\n"
                "• Bullet: Evaluación mensual (≤5 años) o anual (>5 años)\n\n"
                "ESCENARIO ESTRESADO:\n"
                "• Parámetros base: (a, σ)\n"
                "• Parámetros estresados: (a, σ × 1.25, λ) y θ(t) recalculada\n"
                "• Incremento de volatilidad del 25%\n\n"
                "VALIDACIÓN DE CALIBRACIÓN:\n"
                "• Métricas: R², RMSE, MAE (curva histórica vs curva reconstruida θ(t))\n"
                "• Espacio de validación: Short rates dependientes del tiempo\n"
                "• Semáforo: R² ≥ 0.65 (verde), 0.40 ≤ R² < 0.65 (amarillo), R² < 0.40 (rojo)\n\n"
                "APLICACIÓN:\n"
                "Óptimo para análisis con calibración específica por crédito y criterio\n"
                "de prepago consistente con condiciones de mercado (comparación directa EA)."
            )
        }

        # Modelos disponibles (pueden venir del exterior)
        self.modelos_disponibles = modelos if modelos else list(self.definiciones.keys())

        self._crear_widgets()

    def _crear_widgets(self):
        ttk.Label(self, text="Fase 2: Selección del Modelo Actuarial", font=("Arial", 14, "bold")).pack(pady=(0, 15))

        ttk.Label(self, text="Modelo Actuarial:").pack(anchor="w")
        self.modelo_var = tk.StringVar()
        self.combo_modelos = ttk.Combobox(self, textvariable=self.modelo_var, state="readonly")
        self.combo_modelos['values'] = self.modelos_disponibles
        self.combo_modelos.current(0)
        self.combo_modelos.pack(fill="x", pady=(0, 10))
        self.combo_modelos.bind("<<ComboboxSelected>>", self._actualizar_definicion)

        ttk.Label(self, text="Definición Técnica del Modelo:").pack(anchor="w")
        
        # Frame para el área de texto con scrollbar
        frame_texto = ttk.Frame(self)
        frame_texto.pack(fill="both", expand=True, pady=(0, 10))
        
        self.txt_definicion = tk.Text(frame_texto, height=20, wrap="word", state="normal", 
                                     font=("Consolas", 9), bg="#f8f9fa", fg="#2c3e50")
        scrollbar = ttk.Scrollbar(frame_texto, orient="vertical", command=self.txt_definicion.yview)
        self.txt_definicion.configure(yscrollcommand=scrollbar.set)
        
        self.txt_definicion.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.btn_confirmar = ttk.Button(self, text="Confirmar Modelo", command=self._confirmar_modelo)
        self.btn_confirmar.pack()

        self._actualizar_definicion()

    def _actualizar_definicion(self, event=None):
        modelo = self.modelo_var.get()
        definicion = self.definiciones.get(modelo, "No hay definición disponible.")
        self.txt_definicion.config(state="normal")
        self.txt_definicion.delete("1.0", "end")
        self.txt_definicion.insert("1.0", definicion)
        self.txt_definicion.config(state="disabled")

    def _confirmar_modelo(self):
        if self.on_confirmar:
            self.on_confirmar()

    def get_modelo_seleccionado(self):
        return self.modelo_var.get()

    def get_definicion_modelo(self):
        return self.definiciones.get(self.modelo_var.get(), "")
