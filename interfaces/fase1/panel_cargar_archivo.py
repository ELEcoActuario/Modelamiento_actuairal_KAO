import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd

class PanelCargarArchivo(ttk.Frame):
    """
    Panel para la Fase 1: Cargar y validar archivo Excel con las 3 hojas requeridas.
    """
    def __init__(self, master, on_carga_exitosa):
        super().__init__(master, padding=10)
        self.on_carga_exitosa = on_carga_exitosa
        self.df_creditos = None
        self.df_tasas_mercado = None
        self.df_tasas_libres = None
        self.df_curva_hw = None
        self._crear_widgets()

    def _crear_widgets(self):
        ttk.Label(self, text="Fase 1: Cargar y Validar Archivo Excel", font=("Arial", 14, "bold")).pack(pady=(0, 15))
        self.btn_cargar = ttk.Button(self, text="Cargar Archivo Excel (.xlsx)", command=self._cargar_archivo)
        self.btn_cargar.pack(pady=10)
        self.lbl_estado = ttk.Label(self, text="", foreground="red")
        self.lbl_estado.pack(pady=5)

    def _mostrar_mensaje(self, mensaje, tipo="error"):
        color = "green" if tipo == "exito" else "red"
        self.lbl_estado.config(text=mensaje, foreground=color)

    def _validar_columnas(self, df, requeridas, hoja):
        faltantes = [col for col in requeridas if col not in df.columns]
        if faltantes:
            return f"Faltan columnas en '{hoja}': {', '.join(faltantes)}"
        return None

    def _validar_tipos(self, df, hoja):
        errores = []
        if hoja == 'data_credito':
            if not pd.api.types.is_numeric_dtype(df["Tasa"]):
                errores.append(f"'Tasa' en {hoja} no es numérica.")
            if "Valor" in df.columns and not pd.api.types.is_numeric_dtype(df["Valor"]):
                errores.append(f"'Valor' en {hoja} no es numérica.")
            if not pd.api.types.is_integer_dtype(df["Numero_Cuotas"]):
                errores.append(f"'Numero_Cuotas' en {hoja} no es entero.")
            for col in ["Fecha_Desembolso", "Fecha_Vencimiento"]:
                if not pd.api.types.is_datetime64_any_dtype(df[col]):
                    errores.append(f"'{col}' en {hoja} no es tipo fecha.")
        return errores

    def _cargar_archivo(self):
        filepath = filedialog.askopenfilename(
            title="Seleccione el archivo de parámetros",
            filetypes=[("Archivos de Excel", "*.xlsx")]
        )
        if not filepath:
            return

        try:
            xls = pd.ExcelFile(filepath)
            hojas_requeridas = ['data_credito', 'data_tasasM', 'data_tasasLR', 'CurvaHW']
            faltantes = [hoja for hoja in hojas_requeridas if hoja not in xls.sheet_names]
            if faltantes:
                self._mostrar_mensaje(f"Error: Faltan hojas requeridas: {', '.join(faltantes)}")
                return

            # Leer hojas
            df_creditos = pd.read_excel(xls, sheet_name='data_credito', decimal=',')
            df_tasasM = pd.read_excel(xls, sheet_name='data_tasasM', decimal=',')
            df_tasasLR = pd.read_excel(xls, sheet_name='data_tasasLR', decimal=',')
            df_curvaHW = pd.read_excel(xls, sheet_name='CurvaHW', decimal=',')

            # Conversión explícita de fechas
            df_creditos["Fecha_Desembolso"] = pd.to_datetime(df_creditos["Fecha_Desembolso"], dayfirst=True, errors="coerce")
            df_creditos["Fecha_Vencimiento"] = pd.to_datetime(df_creditos["Fecha_Vencimiento"], dayfirst=True, errors="coerce")
            if "Fecha" in df_tasasM.columns:
                df_tasasM["Fecha"] = pd.to_datetime(df_tasasM["Fecha"], dayfirst=True, errors="coerce")

            # Normalización de columnas (alias y compatibilidad)
            if "Periodisidad_Pago" in df_creditos.columns and "Periodicidad_Pago" not in df_creditos.columns:
                df_creditos = df_creditos.rename(columns={"Periodisidad_Pago": "Periodicidad_Pago"})
            if "Monto" in df_creditos.columns and "Valor" not in df_creditos.columns:
                df_creditos = df_creditos.rename(columns={"Monto": "Valor"})

            # Validar columnas
            errores = []
            errores.append(self._validar_columnas(df_creditos, [
                'ID_producto', 'Tipo_Amortizacion', 'Tipo_producto', 'Valor', 'Tasa', 'Numero_Cuotas',
                'Fecha_Desembolso', 'Fecha_Vencimiento', 'Moneda', 'Periodicidad_Pago'
            ], 'data_credito'))
            errores.append(self._validar_columnas(df_tasasM, ['Fecha'], 'data_tasasM'))
            errores.append(self._validar_columnas(df_tasasLR, [
                'Nodo', 'Tiempo', 'COP', 'USD', 'UVR'
            ], 'data_tasasLR'))
            
            # Validar CurvaHW - debe tener al menos una columna de tasas
            if df_curvaHW.empty:
                errores.append("CurvaHW: La hoja está vacía")
            elif df_curvaHW.shape[1] == 0:
                errores.append("CurvaHW: No se encontraron columnas de tasas")
            else:
                # Validar que tiene datos numéricos
                columnas_numericas = df_curvaHW.select_dtypes(include=['float64', 'int64']).columns
                if len(columnas_numericas) == 0:
                    errores.append("CurvaHW: No se encontraron columnas numéricas con tasas de mercado")

            # Validar tipos
            errores.extend(self._validar_tipos(df_creditos, 'data_credito'))
            errores = [e for e in errores if e]

            if errores:
                self._mostrar_mensaje("\n".join(errores))
                return

            # Guardar
            self.df_creditos = df_creditos
            self.df_tasas_mercado = df_tasasM
            self.df_tasas_libres = df_tasasLR
            self.df_curva_hw = df_curvaHW

            self._mostrar_mensaje("✅ Archivo cargado y validado correctamente (incluye CurvaHW).", tipo="exito")

            if self.on_carga_exitosa:
                self.on_carga_exitosa(self.df_creditos, self.df_tasas_mercado, self.df_tasas_libres, self.df_curva_hw)

                # Transición automática a Fase 2
                self.master.master.select(1)

        except FileNotFoundError:
            self._mostrar_mensaje("Archivo no encontrado.")
        except ValueError as e:
            self._mostrar_mensaje(f"Error de lectura: {e}")
        except Exception as e:
            self._mostrar_mensaje(f"Error inesperado: {e}")
