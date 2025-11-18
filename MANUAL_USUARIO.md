# MANUAL DE USUARIO - SISTEMA DE VALORACIÓN ACTUARIAL

## 📘 GUÍA PASO A PASO PARA USUARIOS

Este manual le guiará en el uso del sistema de valoración de carteras crediticias con análisis de prepago.

---

## 🎯 ANTES DE COMENZAR

### Requisitos del Sistema

**Software necesario:**
- Python 3.8 o superior instalado
- Librerías Python (instalar con el comando indicado más abajo)
- Microsoft Excel o compatible para preparar datos de entrada
- Windows, macOS o Linux

**Instalación de dependencias:**
```bash
pip install pandas numpy scipy matplotlib tkcalendar openpyxl statsmodels
```

---

## 📊 PREPARACIÓN DE DATOS DE ENTRADA

### Archivo Excel Requerido

Debe preparar **un único archivo Excel (.xlsx)** que contenga **4 hojas obligatorias** con nombres exactos:

#### 1️⃣ HOJA: `data_credito`

**Contiene:** Información de cada crédito de su cartera

**Columnas obligatorias:**

| Columna | Tipo | Descripción | Ejemplo |
|---------|------|-------------|---------|
| `ID_producto` | Texto | Identificador único del crédito | "CRE-001", "12345" |
| `Tipo_Amortizacion` | Texto | Sistema de amortización | "Francesa", "Alemana", "Americana", "Bullet" |
| `Tipo_producto` | Texto | Tipo de crédito | "Comercial", "Consumo", "Vivienda" |
| `Valor` | Número | Monto del crédito | 10000000 |
| `Tasa` | Decimal | Tasa efectiva anual | 0.12 (para 12%) |
| `Numero_Cuotas` | Entero | Cantidad de cuotas | 24, 36, 60 |
| `Fecha_Desembolso` | Fecha | Fecha de inicio | 2023-01-15 |
| `Fecha_Vencimiento` | Fecha | Fecha de vencimiento | 2025-01-15 |
| `Moneda` | Texto | Moneda del crédito | "COP", "USD", "UVR" |
| `Periodicidad_Pago` | Texto | Frecuencia de pago | "Mensual", "Quincenal", "Trimestral", "Semestral", "Anual" |

**⚠️ IMPORTANTE:**
- Las **tasas deben estar en decimal** (12% = 0.12, no 12)
- Las **fechas** deben estar en formato fecha de Excel
- Los **montos** sin separadores de miles (10000000, no 10.000.000)

**Ejemplo de fila:**
```
ID_producto: CRE-001
Tipo_Amortizacion: Francesa
Tipo_producto: Comercial
Valor: 50000000
Tasa: 0.125
Numero_Cuotas: 36
Fecha_Desembolso: 2023-06-01
Fecha_Vencimiento: 2026-06-01
Moneda: COP
Periodicidad_Pago: Mensual
```

---

#### 2️⃣ HOJA: `data_tasasM`

**Contiene:** Serie histórica de tasas de mercado **por tipo de crédito**

**Columnas obligatorias:**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `Fecha` | Fecha | Fecha de observación (semanal o mensual) |
| `Comercial` | Decimal | Tasa EA para créditos comerciales |
| `Consumo` | Decimal | Tasa EA para créditos de consumo |
| `Vivienda` | Decimal | Tasa EA para créditos de vivienda |

**⚠️ IMPORTANTE:**
- **Mínimo 2-3 años** de datos históricos
- Frecuencia **semanal o mensual** recomendada
- Tasas en **decimal** (12% = 0.12)
- Ordenar por fecha (más antigua primero)

**Ejemplo:**
```
Fecha        | Comercial | Consumo | Vivienda
2021-01-07   | 0.0850    | 0.1650  | 0.0950
2021-01-14   | 0.0855    | 0.1655  | 0.0952
2021-01-21   | 0.0860    | 0.1660  | 0.0955
...
```

---

#### 3️⃣ HOJA: `data_tasasLR`

**Contiene:** Curva de tasas libres de riesgo (cero cupón) **por moneda**

**Columnas obligatorias:**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `Nodo` | Entero | Días desde hoy (0, 1, 7, 30, 90, 180, 360, 540, 720, ...) |
| `Tiempo` | Decimal | Tiempo en años (Nodo/365) |
| `COP` | Decimal | Tasa EA en pesos colombianos |
| `USD` | Decimal | Tasa EA en dólares |
| `UVR` | Decimal | Tasa EA en UVR |

**⚠️ IMPORTANTE:**
- Incluir **nodos clave**: 1, 7, 30, 90, 180, 360, 540, 720, 1080, 1440, 1800, 2160, 2520, 2880, 3240, 3600, 5400, 7200, 10800
- `Tiempo = Nodo / 365`
- Tasas en **decimal**
- Si no tiene datos de alguna moneda, poner 0 o dejar vacío

**Ejemplo:**
```
Nodo  | Tiempo  | COP    | USD    | UVR
1     | 0.0027  | 0.0450 | 0.0200 | 0.0380
7     | 0.0192  | 0.0455 | 0.0205 | 0.0382
30    | 0.0822  | 0.0465 | 0.0215 | 0.0390
90    | 0.2466  | 0.0480 | 0.0230 | 0.0400
180   | 0.4932  | 0.0500 | 0.0250 | 0.0420
360   | 0.9863  | 0.0550 | 0.0300 | 0.0450
...
```

---

#### 4️⃣ HOJA: `CurvaHW`

**Contiene:** Serie histórica de curvas de tasas completas (para modelo Hull-White)

**Estructura:**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `Fecha` | Fecha | Fecha de observación de la curva |
| `1` | Decimal | Tasa EA a 1 día |
| `7` | Decimal | Tasa EA a 7 días |
| `30` | Decimal | Tasa EA a 30 días |
| `90` | Decimal | Tasa EA a 90 días |
| `180` | Decimal | Tasa EA a 180 días |
| `360` | Decimal | Tasa EA a 360 días |
| `540` | Decimal | Tasa EA a 540 días |
| `720` | Decimal | Tasa EA a 720 días |
| ... | ... | (tantos nodos como tenga disponibles) |

**⚠️ IMPORTANTE:**
- **Mínimo 6 meses** de datos históricos de curvas
- Los nombres de columnas deben ser **números** (1, 7, 30, 90, ...)
- Cada fila es una observación completa de la curva en una fecha
- Tasas en **decimal**

**Ejemplo:**
```
Fecha       | 1      | 7      | 30     | 90     | 180    | 360    | 720
2023-01-05  | 0.0450 | 0.0455 | 0.0465 | 0.0480 | 0.0500 | 0.0550 | 0.0600
2023-01-12  | 0.0452 | 0.0457 | 0.0467 | 0.0482 | 0.0502 | 0.0552 | 0.0602
2023-01-19  | 0.0455 | 0.0460 | 0.0470 | 0.0485 | 0.0505 | 0.0555 | 0.0605
...
```

---

### ✅ CHECKLIST DE VALIDACIÓN DE DATOS

Antes de usar el archivo, verifique:

- [ ] El archivo tiene extensión `.xlsx`
- [ ] Tiene exactamente 4 hojas con nombres: `data_credito`, `data_tasasM`, `data_tasasLR`, `CurvaHW`
- [ ] Todas las columnas obligatorias están presentes
- [ ] Las tasas están en **decimal** (0.12, no 12)
- [ ] Las fechas están en formato fecha de Excel
- [ ] No hay celdas vacías en columnas obligatorias
- [ ] `data_tasasM` tiene al menos 100 observaciones
- [ ] `CurvaHW` tiene al menos 26 observaciones (6 meses semanales)
- [ ] Los tipos de crédito coinciden entre `data_credito` y `data_tasasM`

---

## 🚀 EJECUCIÓN DEL SISTEMA

### Paso 1: Abrir Terminal/Consola

**Windows:**
- Presione `Win + R`
- Escriba `cmd` y presione Enter

**macOS/Linux:**
- Abra la aplicación Terminal

### Paso 2: Navegar a la Carpeta del Proyecto

```bash
cd "C:\Users\Pc\Documents\Proyectos\Proyectos Alfa\Modelo tesis"
```

(Ajuste la ruta según donde tenga el proyecto)

### Paso 3: Ejecutar el Sistema

```bash
python main.py
```

### Paso 4: Esperar a que Cargue la Interfaz

Verá mensajes en consola indicando la carga de módulos. Después de unos segundos aparecerá la ventana del sistema.

---

## 🖥️ GUÍA DE USO DE LA INTERFAZ

La interfaz tiene **6 pestañas** (fases) que debe seguir en orden:

---

### 📁 FASE 1: CARGAR Y VALIDAR ARCHIVO

**Qué hacer:**

1. **Click en "Cargar Archivo Excel (.xlsx)"**
   - Se abrirá un explorador de archivos
   - Seleccione su archivo Excel preparado
   - Click en "Abrir"

2. **Esperar validación automática**
   - El sistema verificará:
     - ✓ Que existan las 4 hojas requeridas
     - ✓ Que todas las columnas obligatorias estén presentes
     - ✓ Que los tipos de datos sean correctos
     - ✓ Que `CurvaHW` tenga columnas numéricas

3. **Revisar mensaje de confirmación**
   - ✅ **Verde:** "Archivo cargado y validado correctamente"
     - Puede continuar a Fase 2
   - ❌ **Rojo:** Mensaje de error específico
     - Corrija el archivo según el error indicado
     - Vuelva a cargar

**⚠️ Errores comunes:**
- "Faltan hojas requeridas": Verifique nombres exactos de hojas
- "Columna faltante": Agregue la columna indicada
- "No es tipo fecha": Convierta la columna a formato fecha en Excel

---

### 🎲 FASE 2: SELECCIÓN DE MODELO

**Qué hacer:**

1. **Leer definición técnica del modelo**
   - El panel muestra explicación completa de cada modelo
   - Use el scroll para leer todo el contenido

2. **Seleccionar modelo estocástico:**

   **Modelo Vasicek** - Elija si:
   - Tiene muchos créditos del mismo tipo
   - Quiere análisis más rápido
   - Prefiere calibración por tipo de crédito (Comercial/Consumo/Vivienda)
   - Necesita interpretación directa de parámetros

   **Modelo Hull-White** - Elija si:
   - Necesita máxima precisión
   - Tiene datos históricos de curvas completas (CurvaHW)
   - Quiere calibración específica por cada crédito
   - Requiere ajuste perfecto a curva de mercado

3. **Click en "Confirmar Modelo"**
   - El sistema pasará automáticamente a Fase 3

---

### ⚙️ FASE 3: CONFIGURACIÓN Y ANÁLISIS

Esta es la fase principal donde se ejecutan las simulaciones.

**Controles disponibles:**

#### 1. Parámetros de Simulación

**Fecha de Corte:**
- Seleccione la fecha desde la cual evaluar prepago
- Típicamente: fecha actual o fecha de análisis
- Solo se analizarán flujos **después** de esta fecha

**Tasa Diferencial Prepago (%):**
- Ingrese el spread mínimo para prepago
- Ejemplo: Si ingresa `2`, significa que el crédito se prepaga cuando:
  - `Tasa_Contractual - Tasa_Simulada ≥ 2%`
- Valores típicos: 0.5% a 3%

**Número de Simulaciones:**
- Por defecto: 100
- Puede modificarlo (mínimo 10, máximo 1000)
- Más simulaciones = mayor precisión, más tiempo de cálculo

#### 2. Filtros de Cartera

**Amortización:**
- Filtre por tipo: Francesa, Alemana, Americana, Bullet, o "Todos"

**Producto:**
- Filtre por tipo: Comercial, Consumo, Vivienda, o "Todos"

**Moneda:**
- Filtre por moneda: COP, USD, UVR, o "Todos"

**Periodicidad:**
- Seleccione cómo agrupar los resultados:
  - **Exacta**: Fecha por fecha (sin agrupar)
  - **Mensual**: Suma mensual de flujos
  - **Trimestral**: Suma trimestral
  - **Semestral**: Suma semestral
  - **Anual**: Suma anual
  - **Bandas SFC**: Agrupación normativa (para reportes regulatorios)

#### 3. Ejecutar Cálculos

1. **Click en "Aplicar Filtros y Calcular"**
   - El sistema comenzará a procesar
   - Verá la barra de progreso
   - Puede tardar de 30 segundos a varios minutos según:
     - Número de créditos
     - Modelo seleccionado
     - Número de simulaciones

2. **Esperar mensaje de confirmación**
   - "Proceso completado exitosamente"

#### 4. Visualizar Resultados

**Panel izquierdo: Lista de Créditos**
- Aparecerán todos los créditos filtrados
- Click en un crédito para ver sus detalles

**Panel derecho: Detalles del Crédito**

Cuando selecciona un crédito, verá 3 tablas:

1. **Flujo Contractual Futuro**
   - Fechas y montos según contrato original
   - Sin considerar prepago

2. **Flujos con Prepago (Base)**
   - Selector desplegable: elija simulación
   - Flujos modificados por decisiones de prepago
   - Escenario con volatilidad normal

3. **Flujos con Prepago (Estresado)**
   - Selector desplegable: elija simulación
   - Flujos con volatilidad incrementada (+25%)
   - Escenario de estrés

**Resumen Comparativo:**
- Total de cada tipo de flujo
- Compare impacto del prepago

#### 5. Ver Gráficos

**Click en "Ver Gráficos"**
- Se abrirá ventana con visualizaciones:
  - Trayectorias de tasas simuladas
  - Evolución de flujos
  - Comparación base vs estresado

#### 6. Guardar Selección para Fase 4

Si quiere valorar solo algunos créditos:

1. Seleccione los créditos en la lista (Ctrl+Click para múltiples)
2. **Click en "Guardar créditos para Fase 4"**
3. Confirme la selección
4. Estos créditos se usarán en la valoración

---

### 💰 FASE 4: VALORACIÓN Y DESCUENTOS

**Qué hace:**
- Calcula el **Valor Presente** de los flujos con prepago
- Aplica curvas libres de riesgo por moneda
- Genera 6 escenarios de estrés normativos

**Pasos:**

1. **Click en "Calcular Descuentos"**
   - El sistema calculará VPs automáticamente
   - Verá tabla con resultados

2. **Revisar Tabla de Resultados**

Columnas mostradas:
- `ID_producto`: Identificador del crédito
- `VP_base`: Valor presente con curva base
- `VP_est_Paralelo hacia arriba`: VP con todas las tasas +100pb
- `VP_est_Paralelo hacia abajo`: VP con todas las tasas -100pb
- `VP_est_Empinamiento`: VP con empinamiento de curva
- `VP_est_Aplanamiento`: VP con aplanamiento de curva
- `VP_est_Corto plazo hacia arriba`: VP con corto plazo +100pb
- `VP_est_Corto plazo hacia abajo`: VP con corto plazo -100pb

3. **Ver Gráficos de Curvas**

**Selector "Seleccionar Moneda":**
- Elija: COP, USD o UVR
- El gráfico mostrará:
  - Curva base (línea azul sólida)
  - 6 curvas estresadas (líneas punteadas de colores)

**Interpretación:**
- Curvas más altas → VPs más bajos
- Curvas más bajas → VPs más altos
- Compare cómo cada escenario modifica la curva

---

### 📊 FASE 5: ANÁLISIS DE SENSIBILIDAD

**Qué hace:**
- Calcula **deltas** (diferencias) entre VP base y VP estresado
- Identifica exposiciones a cada tipo de riesgo

**Pasos:**

1. **Click en "Calcular sensibilidad"**
   - El sistema calculará automáticamente

2. **Revisar Tabla de Sensibilidades**

Columnas:
- `ID_producto`: Identificador del crédito
- `Δ_Paralelo_hacia_arriba`: Cambio en VP si tasas suben 100pb
- `Δ_Paralelo_hacia_abajo`: Cambio en VP si tasas bajan 100pb
- `Δ_Empinamiento`: Cambio en VP con empinamiento
- `Δ_Aplanamiento`: Cambio en VP con aplanamiento
- `Δ_Corto_plazo_hacia_arriba`: Cambio en VP con corto plazo +100pb
- `Δ_Corto_plazo_hacia_abajo`: Cambio en VP con corto plazo -100pb

**Interpretación de deltas:**
- **Δ negativo grande**: El crédito pierde mucho valor en ese escenario (RIESGO ALTO)
- **Δ positivo**: El crédito gana valor en ese escenario
- **Δ cercano a cero**: Poco sensible a ese tipo de movimiento

3. **Revisar Totales**

Al final de la tabla verá:
- **Suma total por escenario**: Exposición total de la cartera
- Use para identificar el escenario más adverso

**Ejemplo de interpretación:**
```
Suma total Δ_Paralelo_hacia_arriba: -5,234,567
```
Si las tasas suben 100pb en todos los plazos, la cartera perdería $5,234,567 de valor presente.

---

### ✅ FASE 6: VALIDACIÓN DE CALIBRACIÓN

**Qué hace:**
- Valida la **calidad** de los parámetros calibrados
- Calcula métricas de bondad de ajuste: R², RMSE, MAE

**Pasos:**

1. **Click en "▶ Ejecutar Validación"**
   - El sistema validará automáticamente
   - Tarda unos segundos

2. **Revisar Tabla de Métricas**

Columnas:
- `Modelo`: Vasicek o Hull-White
- `Entidades`: Número de entidades validadas
- `R²`: Coeficiente de determinación (0 a 1)
  - **Más cercano a 1 = Mejor ajuste**
  - Valores típicos: >0.65 muy bueno, >0.40 aceptable
- `RMSE`: Error cuadrático medio (menor es mejor)
- `MAE`: Error absoluto medio (menor es mejor)

3. **Revisar Detalles de Validación**

- **Métricas por tipo/crédito**:
  - R², RMSE, MAE por tipo (Vasicek) o por crédito (Hull-White)
  - Número de observaciones usadas en la validación

4. **Ver Gráficos de Validación**

El sistema genera automáticamente:
- Gráfico de R² por modelo
- Gráfico de RMSE por modelo
- Líneas de referencia (umbrales de calidad)

5. **Exportar Resultados (Opcional)**

**Click en "📥 Exportar Resultados"**
- Seleccione ubicación y nombre de archivo
- Se guardará Excel con:
  - Hoja "Resumen": métricas globales
  - Hojas por modelo: detalles completos

### Solución de Problemas Comunes

**Error: "Faltan columnas requeridas"**
- Solución: Revise nombres exactos de columnas en Excel
- Las columnas deben escribirse exactamente como se indica

**Error: "CurvaHW está vacía"**
- Solución: Verifique que la hoja `CurvaHW` tenga datos
- Debe tener columna `Fecha` y al menos una columna numérica

**La ejecución es muy lenta**
- Reduzca número de simulaciones a 50
- Filtre menos créditos
- Use modelo Vasicek (más rápido que Hull-White)

**Los VPs parecen incorrectos**
- Verifique que las tasas estén en decimal (0.12, no 12)
- Revise coherencia de curvas de tasas libres de riesgo
- Compare con valoraciones anteriores

**Error: "No hay datos históricos"**
- Solución: Asegúrese de que `data_tasasM` tenga suficientes datos
- Mínimo 100 observaciones para calibración robusta


## ✅ CHECKLIST DE PROCESO COMPLETO

Use esta lista para verificar que completó todos los pasos:

- [ ] ✅ Preparé archivo Excel con 4 hojas
- [ ] ✅ Validé estructura de datos (tasas en decimal, fechas correctas)
- [ ] ✅ Ejecuté `python main.py`
- [ ] ✅ **Fase 1**: Cargué y validé archivo (mensaje verde)
- [ ] ✅ **Fase 2**: Seleccioné modelo (Vasicek o Hull-White)
- [ ] ✅ **Fase 3**: Configuré parámetros (fecha corte, diferencial, simulaciones)
- [ ] ✅ **Fase 3**: Ejecuté cálculos (proceso completado)
- [ ] ✅ **Fase 3**: Revisé flujos de créditos individuales
- [ ] ✅ **Fase 3**: Guardé selección para Fase 4 (si aplica)
- [ ] ✅ **Fase 4**: Calculé descuentos
- [ ] ✅ **Fase 4**: Revisé tabla de VPs por escenario
- [ ] ✅ **Fase 4**: Analicé gráficos de curvas
- [ ] ✅ **Fase 5**: Calculé sensibilidades
- [ ] ✅ **Fase 5**: Identifiqué escenarios más adversos
- [ ] ✅ **Fase 6**: Ejecuté validación de calibración
- [ ] ✅ **Fase 6**: Revisé métricas de calidad (R², RMSE, MAE)
- [ ] ✅ Exporté o capturé resultados de interés

---

## 🎓 GLOSARIO DE TÉRMINOS

**Valor Presente (VP)**: Valor actual de flujos futuros descontados a una tasa

**Prepago**: Pago anticipado del crédito antes de su vencimiento contractual

**Tasa EA**: Tasa Efectiva Anual

**Short Rate**: Tasa instantánea continua (usada internamente en modelos)

**Diferencial de prepago**: Spread mínimo necesario para que sea económicamente racional prepagar

**Simulación Monte Carlo**: Técnica que genera múltiples escenarios aleatorios

**Calibración**: Estimación de parámetros del modelo usando datos históricos

**R²**: Coeficiente de determinación, mide calidad del ajuste (0 a 1)

**RMSE**: Error cuadrático medio, mide precisión de predicciones

**Bandas SFC**: Clasificación temporal normativa de la Superintendencia Financiera de Colombia

**Escenarios de estrés**: Situaciones adversas para evaluar riesgo (ej: tasas +100pb)

**Δ (Delta)**: Cambio en valor presente ante un escenario de estrés

---
