# BANDAS SFC: MANUAL TEÓRICO-OPERATIVO

## 🎯 FUNDAMENTO TEÓRICO Y PROPÓSITO

### ¿QUÉ SON LAS BANDAS SFC?
Las Bandas SFC son una **metodología normativa** establecida por la Superintendencia Financiera de Colombia en el Anexo 15 del Capítulo 31 del SIAR para la clasificación temporal de flujos de caja en la valoración de carteras crediticias. Definen 19 bandas temporales con factores de tiempo específicos (t_k) para el cálculo de valor presente.

### ¿POR QUÉ SON FUNDAMENTALES?
Este sistema es crítico porque:

1. **Cumplimiento regulatorio**: Obligatorio para entidades vigiladas por la SFC
2. **Estandarización**: Metodología uniforme para toda la industria financiera
3. **Precisión actuarial**: Factores t_k calibrados para el mercado colombiano
4. **Trazabilidad**: Cada flujo tiene asignación auditable y transparente
5. **Consistencia**: Resultados comparables entre entidades

### PRINCIPIO FUNDAMENTAL: FACTOR DE TIEMPO t_k
```
VP = Flujo / (1 + Tasa)^t_k
```

Donde **t_k** es el factor de tiempo normativo que:
- **Refleja la estructura temporal** del mercado colombiano
- **Ajusta por liquidez** según el plazo del flujo
- **Incorpora riesgo de reinversión** implícito
- **Garantiza consistencia** con prácticas supervisoras

---

## 📊 INFORMACIÓN DE ENTRADA: ¿QUÉ DATOS NECESITAMOS Y POR QUÉ?

### FLUJOS DE CAJA CON FECHAS
**¿Qué información se requiere?**
- **DataFrame de flujos**: Cronograma completo de pagos
- **Columna 'Fecha_Pago'**: Fechas específicas de cada flujo
- **Fecha de referencia**: Fecha de corte para cálculo de días

**¿Por qué son críticos estos datos?**
- **Precisión temporal**: Cada día cuenta para la asignación correcta de banda
- **Cumplimiento normativo**: La SFC requiere clasificación exacta por días
- **Consistencia**: Misma metodología para todos los flujos
- **Auditoría**: Trazabilidad completa del proceso de asignación

---

## 🔬 PROCESO PASO A PASO: METODOLOGÍA NORMATIVA

### FASE 1: CÁLCULO DE DÍAS HASTA PAGO

#### ¿QUÉ SE CALCULA?
El **número exacto de días** entre la fecha de referencia y cada fecha de pago.

#### ¿CÓMO SE REALIZA?
```python
dias_hasta_pago = (fecha_pago - fecha_referencia).days
```

#### ¿POR QUÉ ESTA PRECISIÓN?
- **Normativa específica**: La SFC define bandas por días exactos
- **No aproximaciones**: No se usan meses o años aproximados
- **Consistencia temporal**: Mismo criterio para todos los flujos
- **Auditoría**: Cálculo verificable y reproducible

### FASE 2: ASIGNACIÓN DE BANDA SFC

#### ¿QUÉ SE ASIGNA?
Cada flujo se clasifica en una de las **19 bandas normativas** según los días hasta pago.

#### TABLA DE BANDAS SFC (NORMATIVA OFICIAL)
| Banda | Días Inicio | Días Fin | Descripción |
|-------|-------------|----------|-------------|
| 1 | 0 | 1 | Overnight |
| 2 | 2 | 15 | Muy corto plazo |
| 3 | 16 | 61 | Corto plazo |
| 4 | 62 | 137 | Corto-medio plazo |
| 5 | 138 | 228 | Medio plazo |
| 6 | 229 | 295 | Medio-largo plazo |
| 7 | 296 | 457 | Largo plazo |
| 8 | 458 | 640 | Muy largo plazo |
| 9 | 641 | 913 | 2-3 años |
| 10 | 914 | 1278 | 3-4 años |
| 11 | 1279 | 1643 | 4-5 años |
| 12 | 1644 | 2008 | 5-6 años |
| 13 | 2009 | 2373 | 6-7 años |
| 14 | 2374 | 2738 | 7-8 años |
| 15 | 2739 | 3103 | 8-9 años |
| 16 | 3104 | 3468 | 9-10 años |
| 17 | 3469 | 4569 | 10-15 años |
| 18 | 4570 | 6393 | 15-20 años |
| 19 | 6394 | ∞ | Más de 20 años |

#### ¿CÓMO SE IMPLEMENTA?
```python
# Uso de pd.cut para asignación eficiente
df["Banda_SFC"] = pd.cut(
    df["Dias_Hasta_Pago"],
    bins=[-float("inf")] + [1, 15, 61, 137, 228, 295, 457, 640, 913, 1278, 
          1643, 2008, 2373, 2738, 3103, 3468, 4569, 6393, float("inf")],
    labels=list(range(1, 20)),
    right=True
).astype("Int64")
```

### FASE 3: ASIGNACIÓN DE FACTOR t_k

#### ¿QUÉ ES EL FACTOR t_k?
Es el **factor de tiempo normativo** que refleja la estructura temporal del mercado colombiano para cada banda.

#### TABLA DE FACTORES t_k (METODOLOGÍA SFC)
| Días | Factor t_k | Interpretación Económica |
|------|------------|-------------------------|
| ≤ 1 | 0.0028 | Overnight (1/365) |
| ≤ 30 | 0.0417 | 1 mes (1/24) |
| ≤ 90 | 0.1667 | 3 meses (2/12) |
| ≤ 180 | 0.375 | 6 meses (4.5/12) |
| ≤ 270 | 0.625 | 9 meses (7.5/12) |
| ≤ 360 | 0.8075 | 1 año (aprox.) |
| ≤ 540 | 1.25 | 1.5 años |
| ≤ 720 | 1.75 | 2 años |
| ≤ 1080 | 2.5 | 3 años |
| ≤ 1440 | 3.5 | 4 años |
| ≤ 1800 | 4.5 | 5 años |
| ≤ 2160 | 5.5 | 6 años |
| ≤ 2520 | 6.5 | 7 años |
| ≤ 2880 | 7.5 | 8 años |
| ≤ 3240 | 8.5 | 9 años |
| ≤ 3600 | 9.5 | 10 años |
| ≤ 5400 | 12.5 | 15 años |
| ≤ 7200 | 17.5 | 20 años |
| > 7200 | 25.0 | Más de 20 años |

#### ¿POR QUÉ ESTOS FACTORES ESPECÍFICOS?
- **Calibración empírica**: Basados en análisis del mercado colombiano
- **Ajuste por liquidez**: Factores mayores para plazos más largos
- **Riesgo de reinversión**: Incorpora incertidumbre temporal
- **Consistencia internacional**: Alineados con mejores prácticas

---

## 📈 INTERPRETACIÓN DE RESULTADOS: ¿QUÉ SIGNIFICAN LOS OUTPUTS?

### DATAFRAME ENRIQUECIDO
**Columnas agregadas:**
- **Dias_Hasta_Pago**: Número exacto de días hasta el pago
- **Banda_SFC**: Clasificación normativa (1-19)
- **Nodo**: Días hasta pago (equivalente para búsqueda en curvas)
- **t_k**: Factor de tiempo normativo para descuento

### INTERPRETACIÓN DE BANDAS
**Bandas 1-3 (0-61 días)**: 
- **Liquidez alta**: Factores t_k bajos
- **Riesgo mínimo**: Poca incertidumbre temporal
- **Uso**: Flujos de muy corto plazo

**Bandas 4-8 (62-640 días)**:
- **Liquidez media**: Factores t_k intermedios
- **Riesgo moderado**: Incertidumbre creciente
- **Uso**: Flujos de corto a medio plazo

**Bandas 9-19 (641+ días)**:
- **Liquidez baja**: Factores t_k altos
- **Riesgo alto**: Mayor incertidumbre temporal
- **Uso**: Flujos de largo plazo

---

## 🎯 APLICACIONES PRÁCTICAS Y CASOS DE USO

### VALORACIÓN DE CARTERAS
**Proceso integrado:**
1. **Asignación automática** de bandas a todos los flujos
2. **Aplicación de factores t_k** en cálculo de VP
3. **Consolidación** por banda para análisis de concentración
4. **Reporting** regulatorio con clasificación normativa

### ANÁLISIS DE CONCENTRACIÓN TEMPORAL
**Métricas clave:**
- **Distribución por bandas**: % de VP en cada banda
- **Concentración de riesgo**: Identificación de bandas dominantes
- **Diversificación temporal**: Balance de exposiciones
- **Sensibilidad por plazo**: Impacto de movimientos de tasas por banda

### GESTIÓN DE LIQUIDEZ
**Aplicaciones:**
- **Planificación de flujos**: Proyección de ingresos por banda
- **Gestión de gaps**: Identificación de desbalances temporales
- **Optimización**: Rebalanceo de cartera por bandas
- **Stress testing**: Análisis de escenarios por segmento temporal

---

## ⚠️ LIMITACIONES Y CONSIDERACIONES

### SUPUESTOS NORMATIVOS
**Factores fijos**: Los t_k no cambian con condiciones de mercado
**Bandas predefinidas**: No hay flexibilidad en la clasificación
**Mercado colombiano**: Calibración específica para Colombia

### CONSIDERACIONES OPERATIVAS
**Precisión de fechas**: Requiere fechas exactas de pago
**Actualización**: Recálculo necesario con nueva fecha de corte
**Consistencia**: Aplicación uniforme en toda la cartera

---

## 🔧 INTEGRACIÓN CON EL SISTEMA

### APLICACIÓN AUTOMÁTICA
**En motores de amortización**: Asignación post-generación de flujos
**En modelos estocásticos**: Enriquecimiento de flujos con prepago
**En módulo de descuentos**: Uso directo de factores t_k

### CARACTERÍSTICAS TÉCNICAS
**Eficiencia**: Asignación vectorizada con pandas
**Robustez**: Manejo de casos extremos y fechas faltantes
**Trazabilidad**: Logging completo del proceso
**Validación**: Verificación de consistencia normativa

El módulo de Bandas SFC garantiza el cumplimiento normativo exacto y proporciona la base metodológica para valoración consistente con estándares supervisores colombianos.
