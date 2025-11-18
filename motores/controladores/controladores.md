# CONTROLADORES: MANUAL TEÓRICO-OPERATIVO

## ℹ️ NOTA IMPORTANTE

Este directorio contiene **solo 3 controladores especializados** (`fase1.py`, `fase3.py`, `fase4.py`) que implementan lógica de negocio específica para fases críticas que requieren procesamiento complejo de datos.

**¿Dónde está la lógica de las otras fases?**
- **Fase 2**: Lógica en `interfaces/fase2/panel_modelo.py` (selección de modelo)
- **Fase 5**: Lógica en `motores/orquestador.py` (método `calcular_sensibilidades()`)
- **Fase 6**: Lógica en `motores/validacion/validador_simulaciones.py` y `motores/orquestador.py` (método `validar_simulaciones()` - calcula R², RMSE, MAE)

---

## 🎯 FUNDAMENTO TEÓRICO Y PROPÓSITO

### ¿QUÉ SON LOS CONTROLADORES?
Los controladores implementan el **patrón MVC (Modelo-Vista-Controlador)** actuando como la capa de lógica de negocio que coordina las interacciones entre las interfaces de usuario y los motores de cálculo especializados. Cada controlador encapsula las reglas de negocio específicas para una fase del procesamiento actuarial.

### ¿POR QUÉ ESTA ARQUITECTURA?
La separación en controladores responde a principios de **ingeniería de software**:

1. **Separación de responsabilidades**: Cada controlador maneja una fase específica
2. **Reutilización**: Lógica de negocio independiente de la interfaz
3. **Testabilidad**: Cada controlador puede probarse de forma aislada
4. **Mantenibilidad**: Cambios localizados sin afectar otros componentes
5. **Escalabilidad**: Fácil adición de nuevas funcionalidades

### PRINCIPIO FUNDAMENTAL: ORQUESTACIÓN
```
Resultado = Controlador(Datos_Entrada, Reglas_Negocio, Motores_Especializados)
```

Cada controlador:
- **Valida** datos de entrada según reglas de negocio
- **Transforma** información al formato requerido
- **Orquesta** llamadas a motores especializados
- **Consolida** resultados para la interfaz

---

## 📊 CONTROLADORES IMPLEMENTADOS: ¿QUÉ CÓDIGO EXISTE?

Este directorio contiene **3 controladores especializados** que implementan lógica de negocio específica para fases críticas del procesamiento:

### CONTROLADOR FASE 1: VALIDACIÓN DE DATOS
**Archivo:** `fase1.py`  
**Función principal:** `validar_hojas_y_columnas()`

**¿Qué valida?**
- **Estructura de archivos**: 4 hojas requeridas (data_credito, data_tasasM, data_tasasLR, CurvaHW)
- **Columnas obligatorias**: Campos críticos para cada hoja
- **Tipos de datos**: Conversión y validación de formatos
- **Normalización de compatibilidad**: Renombra columnas alternativas (Periodisidad_Pago, Monto)
- **Validación de CurvaHW**: Verifica columnas numéricas con tasas de mercado

**¿Por qué es crítico?**
- **Fundamento sólido**: Todo el análisis depende de datos correctos
- **Detección temprana**: Errores identificados antes del procesamiento costoso
- **Cumplimiento**: Validación de estructura normativa requerida
- **Compatibilidad**: Maneja variaciones en nombres de columnas

**Funcionalidad clave:**
```python
# Validación de columnas mínimas requeridas
columnas_creditos = ['ID_producto', 'Tipo_Amortizacion', 'Tipo_producto', 
                     'Valor', 'Tasa', 'Numero_Cuotas', 'Fecha_Desembolso', 
                     'Fecha_Vencimiento', 'Moneda', 'Periodicidad_Pago']

columnas_tasasM = ['Fecha']
columnas_tasasLR = ['Nodo', 'Tiempo', 'COP', 'USD', 'UVR']

# CurvaHW: Validación de columnas numéricas
if df_curva_hw is not None:
    columnas_numericas = df_curva_hw.select_dtypes(include=['float64', 'int64']).columns
    if len(columnas_numericas) == 0:
        raise ValueError("CurvaHW: No se encontraron columnas numéricas")
```

---

### CONTROLADOR FASE 3: FILTRADO Y EXTRACCIÓN DE FLUJOS
**Archivo:** `fase3.py`  
**Funciones principales:** `aplicar_filtros()`, `combinar_flujos_por_ids()`, `extraer_flujos_individuales()`

**¿Qué orquesta?**
- **Aplicación de filtros**: Por amortización, producto y moneda
- **Combinación de flujos**: Agrega DataFrames de flujos por IDs seleccionados
- **Extracción individual**: Obtiene flujo contractual + listas base/estresadas por crédito
- **Aplicación de bandas SFC**: Asigna factores t_k a flujos filtrados
- **Filtrado temporal**: Mantiene solo flujos posteriores a fecha de corte

**¿Cómo maneja la complejidad?**
- **Filtrado incremental**: Aplica filtros secuencialmente según selección del usuario
- **Manejo de múltiples simulaciones**: Trabaja con listas de DataFrames (base y estresadas)
- **Bandas dinámicas**: Asigna automáticamente según fecha de corte o fecha de corte del modelo
- **Validaciones robustas**: Verifica existencia de datos antes de procesar

**Funcionalidad clave:**
```python
def aplicar_filtros(df_creditos, valores_filtro):
    """Aplica filtros de amortización, producto y moneda"""
    df_filtrado = df_creditos.copy()
    if valores_filtro["amortizacion"] != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Tipo_Amortizacion"] == valores_filtro["amortizacion"]]
    if valores_filtro["producto"] != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Tipo_producto"] == valores_filtro["producto"]]
    if valores_filtro["moneda"] != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Moneda"] == valores_filtro["moneda"]]
    return df_filtrado

def extraer_flujos_individuales(portafolios, id_producto, fecha_corte, fecha_corte_modelo):
    """
    Extrae:
    - flujo contractual (único)
    - lista de flujos base con prepago
    - lista de flujos estresados con prepago
    
    Aplica bandas SFC y filtra por fecha de corte
    """
```

---

### CONTROLADOR FASE 4: CONSTRUCCIÓN DE DESCUENTOS
**Archivo:** `fase4.py`  
**Funciones principales:** `construir_dataframe_flujos_descuentos()`, `formatear_curva_base()`, `formatear_curvas_estresadas()`

**¿Qué calcula?**
- **Valor presente base**: Promedio de VPs sobre todas las simulaciones por crédito
- **Escenarios estresados**: VP para 6 escenarios normativos SFC
- **Transformación de curvas**: EA → Short Rate mediante `ln(1 + EA)`
- **Consolidación**: DataFrame unificado con todas las columnas de VP
- **Validación de estructura**: Verifica columnas críticas antes de calcular

**¿Cómo implementa la metodología normativa?**
- **Búsqueda exacta de nodos**: Coincidencia precisa de días hasta pago
- **Transformación rigurosa**: Tasas EA → short rates para descuento
- **Fórmula normativa**: `FD(t_k) = exp(-r·t_k)`
- **Auditoría completa**: Logging detallado de cada paso del proceso
- **Validación multinivel**: Verifica estructura antes, durante y después del cálculo

**Funcionalidad clave:**
```python
def validar_estructura_flujos(portafolio, nombre_portafolio):
    """
    Valida que todos los flujos tengan columnas requeridas:
    - Capital_Ajustado
    - Intereses_Ajustados
    - Flujo_Total_Ajustado
    - Prepago_Esperado
    """

def formatear_curva_base(df_tasas_libres, moneda):
    """
    Formatea curva base y TRANSFORMA tasas EA a short rates:
    r = ln(1 + EA)
    
    Necesario para aplicar fórmula de descuento: FD(t_k) = exp(-r·t_k)
    """

# Escenarios de estrés normativos
ESCENARIOS_ESTRES = [
    "Paralelo_hacia_arriba",
    "Paralelo_hacia_abajo",
    "Empinamiento",
    "Aplanamiento",
    "Corto_plazo_hacia_arriba",
    "Corto_plazo_hacia_abajo"
]
```

**Auditoría implementada:**
- Logging de estado inicial (número de créditos, curvas disponibles)
- Validación de estructura de portafolios antes del procesamiento
- Seguimiento de VPs calculados por crédito
- Verificación de nombres de columnas finales
- Registro de primeros valores para verificación manual

---

## 🔬 METODOLOGÍA DE ORQUESTACIÓN

### PATRÓN DE PROCESAMIENTO
**Secuencia estándar:**
1. **Validación**: Verificar precondiciones
2. **Preparación**: Transformar datos al formato requerido
3. **Ejecución**: Llamar motores especializados
4. **Consolidación**: Agregar y formatear resultados
5. **Validación**: Verificar postcondiciones

### MANEJO DE ERRORES
**Estrategia por capas:**
- **Validación temprana**: Fallar rápido con errores claros
- **Aislamiento**: Errores en un crédito no afectan otros
- **Recuperación**: Intentos de corrección automática
- **Logging**: Trazabilidad completa para diagnóstico

### OPTIMIZACIÓN DE RENDIMIENTO
**Técnicas aplicadas:**
- **Caché inteligente**: Evitar recálculos innecesarios
- **Procesamiento paralelo**: Cuando los datos lo permiten
- **Validación incremental**: Solo verificar cambios
- **Gestión de memoria**: Liberación proactiva de recursos

---

## 🎯 INTEGRACIÓN CON EL SISTEMA

### COMUNICACIÓN CON INTERFACES
**Patrón Observer:**
- **Notificaciones**: Cambios de estado a la interfaz
- **Callbacks**: Actualización de progreso
- **Eventos**: Comunicación asíncrona
- **Estado**: Sincronización entre componentes

### COORDINACIÓN CON MOTORES
**Patrón Strategy:**
- **Selección dinámica**: Motor según modelo elegido
- **Configuración**: Parámetros específicos por motor
- **Resultados**: Formato estandarizado de salida
- **Errores**: Manejo uniforme de excepciones

### GESTIÓN DE DATOS
**Flujo de información:**
- **Entrada**: Validación y normalización
- **Procesamiento**: Transformaciones requeridas
- **Salida**: Formato estándar para interfaces
- **Persistencia**: Estado mantenido durante sesión

---

## ⚠️ CONSIDERACIONES OPERATIVAS

### ESCALABILIDAD
**Diseño para crecimiento:**
- **Modularidad**: Fácil adición de nuevos controladores
- **Configurabilidad**: Parámetros ajustables sin código
- **Extensibilidad**: Interfaces bien definidas
- **Reutilización**: Componentes compartidos

### MANTENIBILIDAD
**Código sostenible:**
- **Separación clara**: Responsabilidades bien definidas
- **Documentación**: Código autodocumentado
- **Pruebas**: Cobertura de casos críticos
- **Refactoring**: Estructura que facilita cambios

### ROBUSTEZ
**Operación confiable:**
- **Validaciones**: Múltiples niveles de verificación
- **Recuperación**: Manejo graceful de errores
- **Logging**: Información suficiente para diagnóstico
- **Monitoreo**: Métricas de rendimiento y salud

---

## 🎯 CONCLUSIÓN

Los **3 controladores especializados** (`fase1.py`, `fase3.py`, `fase4.py`) proporcionan funcionalidad crítica para:

1. **Validación de entrada** (Fase 1): Garantiza calidad de datos antes del procesamiento
2. **Filtrado y extracción** (Fase 3): Maneja la complejidad de múltiples simulaciones y flujos
3. **Construcción de descuentos** (Fase 4): Implementa metodología normativa SFC con auditoría completa

Estos controladores trabajan en conjunto con:
- **Orquestador** (`motores/orquestador.py`): Lógica principal de Fases 2, 5 y 6
- **Interfaces** (`interfaces/`): Gestión de interacción con usuario
- **Motores especializados**: Amortización, Vasicek, Hull-White, descuentos, validación

La arquitectura modular permite **mantenimiento focalizado** donde cada componente tiene responsabilidades claramente definidas, facilitando el desarrollo, testing y evolución del sistema de valoración actuarial.
