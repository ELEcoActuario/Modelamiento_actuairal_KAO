"""
Panel de Fase 6: Validación de Simulaciones
Muestra métricas de bondad de ajuste (R², RMSE, MAE) y gráficos comparativos.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class PanelValidacion(ttk.Frame):
    """Panel para validación de simulaciones con métricas y gráficos."""
    
    def __init__(self, master, calcular_command=None):
        super().__init__(master, padding=10)
        self.calcular_command = calcular_command
        self.resultados_validacion = None
        self.figura_actual = None
        
        self._crear_widgets()
    
    def _crear_widgets(self):
        """Crea la estructura de widgets del panel."""
        # Título
        titulo = ttk.Label(
            self,
            text="Fase 6: Validación de Calibración",
            font=("Arial", 14, "bold")
        )
        titulo.pack(pady=(0, 15))
        
        # Frame de controles
        frame_controles = ttk.Frame(self)
        frame_controles.pack(fill="x", pady=(0, 10))
        
        ttk.Label(
            frame_controles,
            text="Valida la calidad de los parámetros calibrados comparando históricos vs predicciones del modelo (R², RMSE, MAE):"
        ).pack(side="left", padx=(0, 10))
        
        self.btn_validar = ttk.Button(
            frame_controles,
            text="▶ Ejecutar Validación",
            command=self._ejecutar_validacion
        )
        self.btn_validar.pack(side="left")
        
        self.btn_exportar = ttk.Button(
            frame_controles,
            text="📥 Exportar Resultados",
            command=self._exportar_resultados,
            state="disabled"
        )
        self.btn_exportar.pack(side="left", padx=(5, 0))
        
        # Separator
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=10)
        
        # Frame principal con dos columnas
        frame_principal = ttk.Frame(self)
        frame_principal.pack(fill="both", expand=True)
        
        # Columna izquierda: Métricas y tabla
        frame_izquierdo = ttk.Frame(frame_principal)
        frame_izquierdo.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Label de métricas
        ttk.Label(
            frame_izquierdo,
            text="Métricas de Validación por Modelo:",
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(0, 5))
        
        # Tabla de métricas
        frame_tabla = ttk.Frame(frame_izquierdo)
        frame_tabla.pack(fill="both", expand=True)
        
        columnas = ("Modelo", "Entidades", "R²", "RMSE", "MAE")
        self.tree_metricas = ttk.Treeview(
            frame_tabla,
            columns=columnas,
            show="headings",
            height=8
        )
        
        # Configurar columnas
        self.tree_metricas.heading("Modelo", text="Modelo")
        self.tree_metricas.heading("Entidades", text="Entidades")
        self.tree_metricas.heading("R²", text="R²")
        self.tree_metricas.heading("RMSE", text="RMSE")
        self.tree_metricas.heading("MAE", text="MAE")
        
        self.tree_metricas.column("Modelo", width=150, anchor="w")
        self.tree_metricas.column("Entidades", width=80, anchor="center")
        self.tree_metricas.column("R²", width=80, anchor="center")
        self.tree_metricas.column("RMSE", width=80, anchor="center")
        self.tree_metricas.column("MAE", width=80, anchor="center")
        
        # Scrollbars
        scrollbar_v = ttk.Scrollbar(frame_tabla, orient="vertical", command=self.tree_metricas.yview)
        scrollbar_h = ttk.Scrollbar(frame_tabla, orient="horizontal", command=self.tree_metricas.xview)
        self.tree_metricas.configure(yscrollcommand=scrollbar_v.set, xscrollcommand=scrollbar_h.set)
        
        self.tree_metricas.pack(side="left", fill="both", expand=True)
        scrollbar_v.pack(side="right", fill="y")
        scrollbar_h.pack(side="bottom", fill="x")
        
        # Text widget para detalles
        ttk.Label(
            frame_izquierdo,
            text="Detalles de Validación:",
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(10, 5))
        
        frame_detalles = ttk.Frame(frame_izquierdo)
        frame_detalles.pack(fill="both", expand=True)
        
        self.txt_detalles = tk.Text(
            frame_detalles,
            height=10,
            wrap="word",
            font=("Consolas", 9),
            bg="#f8f9fa",
            fg="#2c3e50"
        )
        scrollbar_detalles = ttk.Scrollbar(frame_detalles, orient="vertical", command=self.txt_detalles.yview)
        self.txt_detalles.configure(yscrollcommand=scrollbar_detalles.set)
        
        self.txt_detalles.pack(side="left", fill="both", expand=True)
        scrollbar_detalles.pack(side="right", fill="y")
        
        # Columna derecha: Gráficos
        frame_derecho = ttk.Frame(frame_principal)
        frame_derecho.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        # Label de gráficos
        ttk.Label(
            frame_derecho,
            text="Visualización de Validación:",
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(0, 5))
        
        # Frame para gráficos
        self.frame_graficos = ttk.Frame(frame_derecho)
        self.frame_graficos.pack(fill="both", expand=True)
        
        # Mensaje inicial
        self.lbl_mensaje = ttk.Label(
            self.frame_graficos,
            text="Ejecute la validación para ver gráficos comparativos\n\n"
                 "Los gráficos mostrarán:\n"
                 "• Observado vs Simulado (dispersión)\n"
                 "• Series temporales comparativas\n"
                 "• Distribución de residuos",
            font=("Arial", 10),
            justify="center"
        )
        self.lbl_mensaje.pack(expand=True)
    
    def _ejecutar_validacion(self):
        """Ejecuta el proceso de validación."""
        logger.info("🚀 Iniciando validación desde UI...")
        
        if self.calcular_command:
            try:
                # Deshabilitar botón mientras se ejecuta
                self.btn_validar.config(state="disabled", text="⏳ Validando...")
                self.update_idletasks()
                
                # Ejecutar validación
                resultados = self.calcular_command()
                
                if resultados:
                    self.resultados_validacion = resultados
                    self._mostrar_resultados(resultados)
                    self.btn_exportar.config(state="normal")
                    messagebox.showinfo(
                        "Validación Completada",
                        "La validación de simulaciones se completó exitosamente.\n"
                        "Revise las métricas y gráficos generados."
                    )
                else:
                    messagebox.showwarning(
                        "Sin Resultados",
                        "No se generaron resultados de validación.\n"
                        "Verifique que las simulaciones se hayan ejecutado correctamente."
                    )
                
            except Exception as e:
                logger.error(f"❌ Error en validación: {e}")
                messagebox.showerror(
                    "Error en Validación",
                    f"Ocurrió un error durante la validación:\n{str(e)}"
                )
            finally:
                self.btn_validar.config(state="normal", text="▶ Ejecutar Validación")
        else:
            messagebox.showwarning(
                "Función No Disponible",
                "No se ha configurado la función de validación."
            )
    
    def _mostrar_resultados(self, resultados):
        """Muestra los resultados de validación en la interfaz."""
        logger.info("📊 Mostrando resultados de validación...")
        
        # Limpiar tabla
        for item in self.tree_metricas.get_children():
            self.tree_metricas.delete(item)
        
        # Limpiar detalles
        self.txt_detalles.config(state="normal")
        self.txt_detalles.delete("1.0", "end")
        
        # Llenar tabla con resumen (sin semáforo)
        if 'reporte' in resultados and not resultados['reporte'].empty:
            df_reporte = resultados['reporte']
            
            for _, fila in df_reporte.iterrows():
                modelo_nombre = fila.get('Modelo', '')
                r2_valor = fila.get('R²_Promedio')
                
                # Para Vasicek antes podía ser string, ahora es float; formatear de forma segura
                if isinstance(r2_valor, str):
                    r2_display = r2_valor
                elif pd.notna(r2_valor):
                    r2_display = f"{r2_valor:.4f}"
                else:
                    r2_display = 'N/A'
                
                valores = (
                    f"{modelo_nombre}",
                    fila.get('Entidades_Validadas', ''),
                    r2_display,
                    f"{fila.get('RMSE_Promedio', 0):.6f}" if pd.notna(fila.get('RMSE_Promedio')) else 'N/A',
                    f"{fila.get('MAE_Promedio', 0):.6f}" if pd.notna(fila.get('MAE_Promedio')) else 'N/A'
                )
                self.tree_metricas.insert("", "end", values=valores)
        
        # Mostrar detalles por modelo
        texto_detalles = self._generar_texto_detalles(resultados)
        self.txt_detalles.insert("1.0", texto_detalles)
        self.txt_detalles.config(state="disabled")
        
        # Generar gráficos
        self._generar_graficos(resultados)
    
    def _generar_texto_detalles(self, resultados) -> str:
        """Genera texto detallado de los resultados con semáforo."""
        texto = "REPORTE DETALLADO DE VALIDACIÓN\n"
        texto += "=" * 80 + "\n\n"
        
        for modelo, datos in resultados.items():
            if modelo in ['reporte', 'semaforo']:
                continue
            
            # Encabezado de modelo (sin semáforo)
            texto += f"MODELO: {modelo}\n"
            texto += "-" * 80 + "\n"
            
            if 'metricas_globales' in datos:
                texto += "Métricas Globales:\n"
                if modelo == 'Hull-White':
                    mg = datos['metricas_globales']
                    r2 = mg.get('r_cuadrado_promedio')
                    rmse = mg.get('rmse_promedio')
                    mae = mg.get('mae_promedio')
                    if r2 is not None:
                        texto += f"  • R²: {r2}\n"
                    if rmse is not None:
                        texto += f"  • RMSE: {rmse}\n"
                    if mae is not None:
                        texto += f"  • MAE: {mae}\n"
                elif modelo == 'Vasicek':
                    mg = datos['metricas_globales']
                    r2p = mg.get('r_cuadrado_promedio')
                    rmsep = mg.get('rmse_promedio')
                    maep = mg.get('mae_promedio')
                    if r2p is not None:
                        texto += f"  • R² Promedio: {r2p}\n"
                    if rmsep is not None:
                        texto += f"  • RMSE Promedio: {rmsep}\n"
                    if maep is not None:
                        texto += f"  • MAE Promedio: {maep}\n"
                else:
                    # Ocultar métricas de tests y clasificaciones del resumen global
                    omitir = {"tests_pasados", "tests_totales", "tests_aprobados_pct", "tipos_validos", "tipos_totales", "validacion_general"}
                    for metrica, valor in datos['metricas_globales'].items():
                        if metrica in omitir or valor is None:
                            continue
                        texto += f"  • {metrica}: {valor}\n"
                texto += "\n"
            
            # Detalles por entidad (sin semáforo, evitar duplicados)
            secciones_impresas = set()
            if 'metricas_por_tipo' in datos and 'tipo' not in secciones_impresas:
                texto += "Detalles por Tipo de Crédito:\n"
                for i, (tipo, metricas) in enumerate(list(datos['metricas_por_tipo'].items())):
                    texto += f"  {i+1}. {tipo}:\n"
                    texto += f"     R² = {metricas.get('r_cuadrado', 'N/A')}\n"
                    texto += f"     RMSE = {metricas.get('rmse', 'N/A')}\n"
                    texto += f"     MAE = {metricas.get('mae', 'N/A')}\n"
                    texto += f"     N. observaciones = {metricas.get('n_observaciones', 'N/A')}\n"
                texto += "\n"
                secciones_impresas.add('tipo')
            
            if 'metricas_por_credito' in datos and 'credito' not in secciones_impresas:
                mostrar_credito = True
                # Para Vasicek: nunca listar por crédito (se valida por tipo)
                if modelo == 'Vasicek':
                    mostrar_credito = False
                if 'metricas_por_tipo' in datos:
                    try:
                        metricas_vals = list(datos['metricas_por_credito'].values())
                        tiene_resumen = any(isinstance(m, dict) and 'resumen' in m for m in metricas_vals)
                    except Exception:
                        tiene_resumen = False
                    # Si ya mostramos por tipo y las métricas por crédito no aportan 'resumen', omitir para evitar duplicación
                    if not tiene_resumen:
                        mostrar_credito = False
                if mostrar_credito:
                    if modelo == 'Hull-White':
                        metricas_vals = list(datos['metricas_por_credito'].values())
                        r2 = None
                        rmse = None
                        mae = None
                        nobs = None
                        for m in metricas_vals:
                            if isinstance(m, dict) and 'resumen' not in m:
                                r2 = m.get('r_cuadrado', r2)
                                rmse = m.get('rmse', rmse)
                                mae = m.get('mae', mae)
                                nobs = m.get('n_observaciones', nobs)
                                break
                        texto += "Detalles por Crédito (agrupado):\n"
                        texto += f"  Créditos agrupados: {len(datos['metricas_por_credito'])}\n"
                        texto += f"     R² = {r2 if r2 is not None else 'N/A'}\n"
                        texto += f"     RMSE = {rmse if rmse is not None else 'N/A'}\n"
                        texto += f"     MAE = {mae if mae is not None else 'N/A'}\n"
                        texto += f"     N. observaciones = {nobs if nobs is not None else 'N/A'}\n"
                        texto += "\n"
                        secciones_impresas.add('credito')
                    else:
                        texto += "Detalles por Crédito:\n"
                        creditos_ordenados = list(dict.fromkeys(list(datos['metricas_por_credito'].keys())))
                        for i, credito in enumerate(creditos_ordenados):
                            metricas = datos['metricas_por_credito'][credito]
                            texto += f"  {i+1}. {credito}:\n"
                            if isinstance(metricas, dict):
                                if 'r_cuadrado' in metricas:
                                    texto += f"     R² = {metricas.get('r_cuadrado', 'N/A')}\n"
                                    texto += f"     RMSE = {metricas.get('rmse', 'N/A')}\n"
                                    texto += f"     MAE = {metricas.get('mae', 'N/A')}\n"
                                    texto += f"     N. observaciones = {metricas.get('n_observaciones', 'N/A')}\n"
                                elif 'resumen' in metricas:
                                    resumen = metricas['resumen']
                                    texto += f"     Tests exitosos: {resumen.get('tests_exitosos', 0)}/{resumen.get('tests_totales', 0)}\n"
                        texto += "\n"
                        secciones_impresas.add('credito')
                    texto += "\n"
        
            texto += "\n"
        
        return texto
    
    def _generar_graficos(self, resultados):
        """Genera gráficos de validación."""
        logger.info("📈 Generando gráficos de validación...")
        
        # Limpiar frame de gráficos
        for widget in self.frame_graficos.winfo_children():
            widget.destroy()
        
        # Crear figura con subplots
        fig = Figure(figsize=(10, 8), dpi=80)
        
        # Subplot 1: R² por modelo (barras)
        ax1 = fig.add_subplot(1, 2, 1)
        self._graficar_r2_por_modelo(ax1, resultados)
        
        # Subplot 2: RMSE por modelo (barras)
        ax2 = fig.add_subplot(1, 2, 2)
        self._graficar_rmse_por_modelo(ax2, resultados)
        
        fig.tight_layout()
        
        # Integrar en tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.frame_graficos)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        
        self.figura_actual = fig
        
        logger.info("✅ Gráficos generados exitosamente")
    
    def _graficar_r2_por_modelo(self, ax, resultados):
        """Gráfico de barras de R² por modelo."""
        modelos = []
        r2_valores = []
        
        if 'reporte' in resultados and not resultados['reporte'].empty:
            df = resultados['reporte']
            for _, fila in df.iterrows():
                # Convertir a numérico de forma segura; saltar valores no numéricos (p.ej., '2/3' en Vasicek)
                val = pd.to_numeric(pd.Series([fila.get('R²_Promedio')]), errors='coerce').iloc[0]
                if pd.notna(val):
                    modelos.append(fila['Modelo'])
                    r2_valores.append(float(val))
        
        if modelos:
            colores = ['#3498db', '#2ecc71', '#e74c3c'][:len(modelos)]
            bars = ax.bar(modelos, r2_valores, color=colores, alpha=0.7, edgecolor='black')
            
            # Añadir valores en las barras
            for bar in bars:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.,
                    height,
                    f'{height:.4f}',
                    ha='center',
                    va='bottom',
                    fontsize=9
                )
            
            ax.set_ylabel('R² (Coeficiente de Determinación)', fontsize=10)
            ax.set_title('R² por Modelo', fontsize=11, fontweight='bold')
            ax.set_ylim(0, 1.0)
            ax.axhline(y=0.8, color='green', linestyle='--', alpha=0.5, label='Umbral 0.8')
            ax.axhline(y=0.6, color='orange', linestyle='--', alpha=0.5, label='Umbral 0.6')
            ax.legend(fontsize=8)
            ax.grid(axis='y', alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Sin datos de R²', ha='center', va='center', transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
    
    def _graficar_rmse_por_modelo(self, ax, resultados):
        """Gráfico de barras de RMSE por modelo."""
        modelos = []
        rmse_valores = []
        
        if 'reporte' in resultados and not resultados['reporte'].empty:
            df = resultados['reporte']
            for _, fila in df.iterrows():
                if pd.notna(fila.get('RMSE_Promedio')):
                    modelos.append(fila['Modelo'])
                    rmse_valores.append(fila['RMSE_Promedio'])
        
        if modelos:
            colores = ['#e67e22', '#9b59b6', '#1abc9c'][:len(modelos)]
            bars = ax.bar(modelos, rmse_valores, color=colores, alpha=0.7, edgecolor='black')
            
            # Añadir valores en las barras
            for bar in bars:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.,
                    height,
                    f'{height:.4f}',
                    ha='center',
                    va='bottom',
                    fontsize=9
                )
            
            ax.set_ylabel('RMSE (Error Cuadrático Medio)', fontsize=10)
            ax.set_title('RMSE por Modelo', fontsize=11, fontweight='bold')
            ax.grid(axis='y', alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Sin datos de RMSE', ha='center', va='center', transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
    
    def _graficar_comparacion_metricas(self, ax, resultados):
        """Gráfico de barras agrupadas comparando métricas."""
        if 'reporte' not in resultados or resultados['reporte'].empty:
            ax.text(0.5, 0.5, 'Sin datos', ha='center', va='center', transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            return
        
        df = resultados['reporte']
        modelos = df['Modelo'].tolist()
        
        # Normalizar métricas para comparación visual (coerción a numérico)
        r2_norm = pd.to_numeric(df['R²_Promedio'], errors='coerce').fillna(0).tolist()
        
        x = np.arange(len(modelos))
        width = 0.35
        
        bars = ax.bar(x, r2_norm, width, label='R² (normalizado)', color='#3498db', alpha=0.7)
        
        ax.set_ylabel('Valor Normalizado', fontsize=10)
        ax.set_title('Comparación de Métricas', fontsize=11, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(modelos, rotation=0, ha='center')
        ax.legend(fontsize=9)
        ax.grid(axis='y', alpha=0.3)
    
    def _graficar_resumen_textual(self, ax, resultados):
        """Muestra resumen textual en el subplot."""
        ax.axis('off')
        
        texto_resumen = "RESUMEN DE VALIDACIÓN\n" + "=" * 30 + "\n\n"
        
        if 'reporte' in resultados and not resultados['reporte'].empty:
            df = resultados['reporte']
            
            for _, fila in df.iterrows():
                modelo = fila['Modelo']
                entidades = fila.get('Entidades_Validadas', 0)
                r2 = fila.get('R²_Promedio', 0)
                
                # Resumen sin emojis ni etiquetas
                if pd.notna(r2):
                    texto_resumen += f"{modelo}:\n"
                    texto_resumen += f"  Entidades: {entidades}\n"
                    texto_resumen += f"  R²: {r2:.4f}\n\n"
        else:
            texto_resumen += "No hay datos disponibles"
        
        ax.text(
            0.1, 0.9,
            texto_resumen,
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment='top',
            fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3)
        )
    
    def _exportar_resultados(self):
        """Exporta los resultados de validación a Excel."""
        if not self.resultados_validacion:
            messagebox.showwarning("Sin Datos", "No hay resultados para exportar.")
            return
        
        from tkinter import filedialog
        
        archivo = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            title="Guardar Resultados de Validación"
        )
        
        if archivo:
            try:
                with pd.ExcelWriter(archivo, engine='openpyxl') as writer:
                    # Exportar reporte resumen
                    if 'reporte' in self.resultados_validacion:
                        self.resultados_validacion['reporte'].to_excel(
                            writer,
                            sheet_name='Resumen',
                            index=False
                        )
                    
                    # Exportar detalles por modelo
                    for modelo, datos in self.resultados_validacion.items():
                        if modelo == 'reporte':
                            continue
                        
                        # Crear hoja con nombre corto
                        nombre_hoja = modelo[:31]
                        
                        if 'metricas_por_tipo' in datos:
                            df_detalles = pd.DataFrame(datos['metricas_por_tipo']).T
                            df_detalles.to_excel(writer, sheet_name=nombre_hoja)
                        elif 'metricas_por_credito' in datos:
                            # Simplificar estructura si hay resumen
                            if 'resumen' in list(datos['metricas_por_credito'].values())[0]:
                                resumenes = {
                                    k: v.get('resumen', {})
                                    for k, v in datos['metricas_por_credito'].items()
                                }
                                df_detalles = pd.DataFrame(resumenes).T
                            else:
                                df_detalles = pd.DataFrame(datos['metricas_por_credito']).T
                            df_detalles.to_excel(writer, sheet_name=nombre_hoja)
                
                messagebox.showinfo(
                    "Exportación Exitosa",
                    f"Resultados exportados a:\n{archivo}"
                )
                logger.info(f"✅ Resultados exportados a {archivo}")
                
            except Exception as e:
                logger.error(f"❌ Error exportando resultados: {e}")
                messagebox.showerror(
                    "Error al Exportar",
                    f"No se pudo exportar el archivo:\n{str(e)}"
                )
