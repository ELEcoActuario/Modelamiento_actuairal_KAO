# MODELO VASICEK: MANUAL TEÓRICO-OPERATIVO

## 🎯 FUNDAMENTO TEÓRICO Y PROPÓSITO

### ¿QUÉ ES EL MODELO VASICEK?
El modelo Vasicek es un **modelo estocástico de equilibrio** desarrollado por Oldrich Vasicek en 1977 para modelar la evolución temporal de tasas de interés de corto plazo. Su importancia radica en ser el primer modelo que incorpora **reversión a la media**, un fenómeno empíricamente observado donde las tasas tienden a regresar hacia un nivel de largo plazo.

### ¿POR QUÉ USAMOS VASICEK PARA PREPAGO?
En el contexto actuarial de prepago, el modelo Vasicek nos permite:

1. **Simular escenarios futuros de tasas**: Generar múltiples trayectorias posibles de tasas de mercado
2. **Evaluar decisiones racionales**: Un deudor prepagará cuando las tasas de mercado sean significativamente menores a su tasa contractual
3. **Cuantificar riesgo de prepago**: Estimar la probabilidad y timing de prepagos bajo diferentes escenarios económicos
4. **Cumplir normativa**: Implementar metodologías supervisoras para valoración de carteras crediticias

### ECUACIÓN FUNDAMENTAL ✅ ACTUALIZADA
```
dr(t) = κ[θ - r(t)]dt + σdW(t)
```

**🔄 CORRECCIÓN IMPLEMENTADA (2025-09-29):**
El modelo ahora implementa correctamente la teoría estocástica trabajando con **tasas cortas/instantáneas** en lugar de tasas efectivas anuales directamente.

Donde:
- **r(t)**: **Tasa corta/instantánea** en el tiempo t (SHORT RATE SPACE)
- **κ (kappa)**: Velocidad de reversión a la media (>0)
- **θ (theta)**: Nivel de largo plazo en SHORT RATE SPACE
- **σ (sigma)**: Volatilidad instantánea en SHORT RATE SPACE
- **dW(t)**: Proceso de Wiener (movimiento browniano)

**Transformación Fundamental:**
- **EA → Short Rate**: `short_rate = ln(1 + tasa_ea)`
- **Short Rate → EA**: `tasa_ea = exp(short_rate) - 1`

---

## 📊 INFORMACIÓN DE ENTRADA: ¿QUÉ DATOS NECESITAMOS Y POR QUÉ?

### 1. SERIES HISTÓRICAS DE TASAS DE MERCADO ✅ ACTUALIZADA
**¿Qué información contiene?**
- **Fechas**: Serie temporal de observaciones (mínimo 2-3 años)
- **Tasas por segmento**: Comercial, Consumo, Vivienda (tasas efectivas anuales)
- **Frecuencia**: Datos semanales o mensuales para capturar dinámica

**¿Por qué necesitamos esta información?**
- **Calibración de parámetros**: Los parámetros κ, θ, σ se estiman usando MLE **en SHORT RATE SPACE** después de transformar las tasas EA
- **Diferenciación por segmento**: Cada tipo de crédito tiene dinámicas de tasas diferentes
- **Captura de régimen**: Los datos históricos reflejan el régimen económico y monetario actual

**🔄 PROCESO CORREGIDO:**
1. **Input**: Tasas efectivas anuales históricas
2. **Transformación**: EA → `ln(1 + tasa_ea)` → Short Rates
3. **Calibración**: MLE en SHORT RATE SPACE
4. **Output**: Parámetros (κ, θ, σ) en SHORT RATE SPACE

**¿Qué características debe tener?**
- **Suficiencia estadística**: Mínimo 100-150 observaciones para estimación robusta
- **Representatividad**: Debe incluir diferentes ciclos económicos
- **Calidad**: Sin datos faltantes o outliers extremos

### 2. FLUJOS CONTRACTUALES ORIGINALES
**¿Qué representan?**
- **Cronograma de pagos**: Fechas y montos de capital e intereses según contrato original
- **Sin modificaciones**: Flujos "puros" sin considerar prepago u otras contingencias
- **Base de comparación**: Referencia para evaluar el impacto del prepago

**¿Por qué son fundamentales?**
- **Valor de referencia**: Representan el valor contractual sin riesgo de prepago
- **Timing de evaluación**: Definen las fechas donde se puede ejercer la opción de prepago
- **Magnitud del riesgo**: Permiten cuantificar el impacto económico del prepago

### 3. PARÁMETROS DE CONFIGURACIÓN
**Fecha de corte**: Momento desde el cual se proyectan escenarios futuros
**Diferencial de prepago**: Spread mínimo que incentiva la decisión de prepago
**Horizonte de simulación**: Período de proyección (hasta vencimiento de créditos)

---

## 🔬 PROCESO PASO A PASO: METODOLOGÍA ACTUARIAL

### FASE 1: CALIBRACIÓN DE PARÁMETROS (MLE) ✅ CORREGIDA

#### ¿QUÉ SE HACE?
Se estiman los parámetros κ, θ, σ para cada tipo de crédito usando **Maximum Likelihood Estimation** **en SHORT RATE SPACE** después de transformar las series históricas.

#### ¿CÓMO SE REALIZA? (PROCESO CORREGIDO)
1. **Transformación crítica**: EA históricas → `ln(1 + tasa_ea)` → Short Rates
2. **Preparación de datos**: Conversión a frecuencia uniforme y cálculo de incrementos Δr en short rates
3. **Discretización del modelo**: Transformación de la ecuación continua a forma discreta en SHORT RATE SPACE
4. **Función de verosimilitud**: Construcción de la función L(κ,θ,σ) basada en distribución normal de short rates
5. **Optimización numérica**: Maximización de log-verosimilitud usando algoritmos de gradiente
6. **Validación**: Umbrales ajustados para short rates (σ < 0.5, |θ| < 0.5)

#### ¿POR QUÉ ESTE MÉTODO?
- **Eficiencia estadística**: MLE produce estimadores con mínima varianza asintótica
- **Consistencia**: Los estimadores convergen al valor verdadero con muestras grandes
- **Flexibilidad**: Permite incorporar restricciones económicas (κ>0, σ>0)

#### RESULTADO OBTENIDO (CORREGIDO)
**Parámetros base calibrados** por tipo de crédito **EN SHORT RATE SPACE**:
- **κ**: Típicamente entre 0.1-0.5 (velocidad de reversión)
- **θ**: Nivel promedio de short rates por segmento
- **σ**: Volatilidad de short rates observada

**Conversión para referencia**: θ se convierte a EA equivalente para logging: `θ_EA = exp(θ_short) - 1`

**Parámetros estresados**: σ incrementado en 25% para análisis de sensibilidad

### FASE 2: SIMULACIÓN MONTE CARLO ✅ CORREGIDA

#### ¿QUÉ SE HACE?
Se generan **100 trayectorias** (configurable) semanales de tasas futuras para cada tipo de crédito usando los parámetros calibrados **en SHORT RATE SPACE** y se retransforman automáticamente a EA.

#### ¿CÓMO SE REALIZA? (PROCESO CORREGIDO)
1. **Input**: Parámetros (κ, θ, σ) en SHORT RATE SPACE, r₀ en EA
2. **Transformación r₀**: `r0_short = ln(1 + r0_ea)`
3. **Discretización temporal**: División del horizonte en pasos semanales (Δt = 7/365)
4. **Generación de shocks**: 100 secuencias de números aleatorios normales independientes
5. **Evolución estocástica**: Aplicación iterativa en SHORT RATE SPACE
6. **Retransformación**: `tasa_ea = exp(short_rate) - 1`
7. **Output**: Matrices en EA para compatibilidad

**Ecuación discretizada (SHORT RATE SPACE):**
```
r_short(t+Δt) = r_short(t) + κ[θ_short - r_short(t)]Δt + σ_short√Δt × ε(t)
```

#### ¿POR QUÉ SIMULACIÓN MONTE CARLO?
- **Captura de incertidumbre**: Refleja la naturaleza estocástica de las tasas
- **Múltiples escenarios**: Permite evaluar prepago bajo diferentes condiciones
- **Distribución completa**: No solo valor esperado, sino toda la distribución de resultados
- **Flexibilidad**: Fácil incorporación de restricciones adicionales

#### RESULTADO OBTENIDO (CORREGIDO)
**Matrices de simulación** [tiempo × simulaciones] conteniendo **tasas en EA** (ya retransformadas):
- **Escenario base**: 100 trayectorias con volatilidad calibrada en short rates
- **Escenario estresado**: 100 trayectorias con volatilidad incrementada 25% en short rates
- **Horizonte completo**: Desde fecha de corte hasta vencimiento del último crédito
- **Compatibilidad**: Matrices en EA para comparación directa con tasas contractuales

### FASE 3: EVALUACIÓN DE PREPAGO ✅ CORREGIDA

#### ¿QUÉ SE HACE?
Para cada crédito y cada simulación, se evalúa en cada fecha de pago si es **económicamente racional** ejercer el prepago usando **comparación directa EA vs EA**.

#### ¿CÓMO SE REALIZA? (FLUJO CORREGIDO)
1. **Interpolación de tasas**: Mapeo de tasas semanales **ya en EA** a fechas específicas de pago
2. **Comparación directa**: Tasa contractual (EA) vs Tasa simulada (EA)
3. **Criterio corregido**: `(tasa_contractual_ea - tasa_simulada_ea) >= diferencial_prepago`
4. **Construcción de flujos**: Modificación de cronograma según decisión de prepago
5. **Créditos bullet**: Cálculo proporcional de intereses según tiempo transcurrido

#### ¿POR QUÉ ESTE CRITERIO CORREGIDO?
- **Teóricamente correcto**: Simulación en short rates según teoría estocástica
- **Prácticamente compatible**: Comparación en EA para consistencia
- **Matemáticamente preciso**: Calibración más realista en short rates
- **Racionalidad económica**: Un deudor refinanciará cuando ahorre costos significativos
- **Diferencial de prepago**: Incorpora costos de transacción y fricción del mercado

#### RESULTADO OBTENIDO (CORREGIDO)
**Flujos ajustados por prepago** para cada crédito:
- **100 escenarios base**: Cronogramas modificados según decisiones de prepago EA vs EA
- **100 escenarios estresados**: Misma lógica con mayor volatilidad en short rates
- **Trazabilidad completa**: Registro de fechas y razones de prepago
- **Créditos bullet**: Intereses calculados proporcionalmente sin duplicación
- **Columnas ajustadas**: Capital_Ajustado, Intereses_Ajustados, Prepago_Esperado, Flujo_Total_Ajustado

---

## 📈 INTERPRETACIÓN DE RESULTADOS: ¿QUÉ SIGNIFICAN LOS OUTPUTS?

### PARÁMETROS CALIBRADOS: INTERPRETACIÓN ECONÓMICA

#### KAPPA (κ) - VELOCIDAD DE REVERSIÓN
**¿Qué mide?**
- **Velocidad de ajuste**: Qué tan rápido las tasas regresan a su nivel de largo plazo
- **Rango típico**: 0.1 - 0.5 anual

**Interpretación práctica:**
- **κ = 0.1**: Las tasas tardan ~10 años en cerrar la mitad de la brecha hacia θ
- **κ = 0.5**: Las tasas tardan ~1.4 años en cerrar la mitad de la brecha hacia θ
- **κ alto**: Mayor estabilidad, menor persistencia de shocks
- **κ bajo**: Mayor persistencia, shocks duran más tiempo

#### THETA (θ) - NIVEL DE LARGO PLAZO
**¿Qué representa?**
- **Tasa de equilibrio**: Nivel hacia el cual convergen las tasas en el largo plazo
- **Interpretación**: Refleja condiciones estructurales de la economía

**Factores que lo determinan:**
- **Política monetaria**: Objetivo de inflación del banco central
- **Prima de riesgo**: Diferencial por tipo de crédito
- **Condiciones macroeconómicas**: Crecimiento, inflación esperada

#### SIGMA (σ) - VOLATILIDAD
**¿Qué captura?**
- **Incertidumbre**: Magnitud de fluctuaciones aleatorias de las tasas
- **Riesgo**: Mayor σ implica mayor riesgo de prepago

**Impacto en prepago:**
- **σ alto**: Mayor probabilidad de que tasas caigan significativamente
- **σ bajo**: Menor variabilidad, prepagos más predecibles

### MATRICES DE SIMULACIÓN: ANÁLISIS DE ESCENARIOS

#### DISTRIBUCIÓN DE TRAYECTORIAS
**¿Qué observar?**
- **Tendencia central**: Convergencia hacia θ en el largo plazo
- **Dispersión**: Amplitud del cono de incertidumbre
- **Percentiles**: P10, P50, P90 para análisis de riesgo

#### ESCENARIOS EXTREMOS
**Escenario optimista (percentil 10)**: Tasas bajas sostenidas → Alto riesgo de prepago
**Escenario pesimista (percentil 90)**: Tasas altas sostenidas → Bajo riesgo de prepago
**Escenario central (mediana)**: Trayectoria más probable

### FLUJOS CON PREPAGO: IMPACTO ECONÓMICO

#### MÉTRICAS CLAVE
**Probabilidad de prepago**: % de simulaciones donde ocurre prepago
**Timing promedio**: Fecha esperada de prepago cuando ocurre
**Impacto en duración**: Reducción en vida promedio del crédito
**Pérdida de ingresos**: Diferencia entre flujos originales vs ajustados

---

## 🎯 APLICACIONES PRÁCTICAS Y CASOS DE USO

### GESTIÓN DE RIESGO DE PREPAGO

#### ANÁLISIS DE SENSIBILIDAD
**Pregunta clave**: ¿Cómo cambia el riesgo de prepago ante diferentes escenarios?

**Metodología:**
1. **Calibrar** con diferentes períodos históricos
2. **Comparar** parámetros obtenidos
3. **Evaluar** estabilidad de resultados
4. **Identificar** períodos de régimen diferente

#### STRESS TESTING
**Objetivo**: Evaluar impacto de escenarios adversos

**Implementación:**
- **Escenario base**: Parámetros calibrados con datos históricos
- **Escenario estresado**: σ incrementado 25% (mayor volatilidad)
- **Comparación**: Diferencias en probabilidades y timing de prepago

### VALORACIÓN DE CARTERAS

#### VALOR PRESENTE AJUSTADO POR RIESGO
**Fórmula conceptual:**
```
VP_ajustado = Σ [P(no prepago en t) × Flujo(t) × Factor_descuento(t)]
```

**Donde:**
- **P(no prepago en t)**: Probabilidad de supervivencia hasta fecha t
- **Flujo(t)**: Flujo contractual en fecha t
- **Factor_descuento(t)**: Factor de descuento libre de riesgo

#### PROVISIONES POR RIESGO DE PREPAGO
**Cálculo**: Diferencia entre VP contractual y VP ajustado por prepago
**Interpretación**: Pérdida esperada por ejercicio de opción de prepago
**Uso regulatorio**: Cumplimiento de normativas de provisiones

### PRICING DE PRODUCTOS

#### INCORPORACIÓN DE PRIMA POR RIESGO DE PREPAGO
**Metodología:**
1. **Estimar** probabilidad de prepago usando Vasicek
2. **Calcular** pérdida esperada por prepago
3. **Incorporar** prima en tasa ofrecida al cliente
4. **Ajustar** según perfil de riesgo del deudor

#### DISEÑO DE PRODUCTOS
**Cláusulas de prepago**: Penalidades que desincentiven prepago temprano
**Tasas variables**: Productos que se ajusten automáticamente con el mercado
**Opciones de refinanciación**: Productos que permitan ajustes internos

---

## ⚠️ LIMITACIONES Y CONSIDERACIONES

### SUPUESTOS DEL MODELO

#### SUPUESTOS RESTRICTIVOS
1. **Tasas no pueden ser negativas**: En la práctica, pueden ocurrir tasas negativas
2. **Un solo factor de riesgo**: Ignora otros factores como spread de crédito
3. **Parámetros constantes**: En realidad pueden cambiar con el tiempo
4. **Normalidad de shocks**: Distribución real puede tener colas pesadas

#### IMPLICACIONES PRÁCTICAS
- **Calibración frecuente**: Necesidad de recalibrar periódicamente
- **Validación empírica**: Comparar predicciones con realizaciones
- **Modelos complementarios**: Usar junto con otros enfoques
- **Análisis de sensibilidad**: Evaluar robustez de resultados

### CONSIDERACIONES OPERATIVAS

#### CALIDAD DE DATOS
**Requisitos mínimos:**
- **Longitud**: Mínimo 2-3 años de datos históricos
- **Frecuencia**: Datos semanales o mensuales
- **Consistencia**: Metodología uniforme de cálculo de tasas
- **Representatividad**: Incluir diferentes ciclos económicos

#### INTERPRETACIÓN DE RESULTADOS
**Precauciones:**
- **No es predicción exacta**: Es un modelo probabilístico
- **Sensible a parámetros**: Pequeños cambios pueden tener gran impacto
- **Contexto económico**: Considerar cambios estructurales en la economía
- **Validación cruzada**: Comparar con otros modelos y experiencia histórica

---

## 🔄 INTEGRACIÓN CON OTROS MODELOS

### COMPARACIÓN CON HULL-WHITE
**Vasicek**: Parámetros constantes, más simple, interpretación directa
**Hull-White**: Ajuste perfecto a curva inicial, mayor complejidad computacional

### COMPLEMENTARIEDAD
**Uso conjunto**: Vasicek para análisis de sensibilidad, Hull-White para valoración precisa
**Validación cruzada**: Comparar resultados entre modelos para mayor robustez
**Especialización**: Cada modelo óptimo para diferentes tipos de análisis

El modelo Vasicek proporciona una base sólida y teóricamente fundamentada para el análisis de riesgo de prepago, combinando simplicidad conceptual con rigor matemático para aplicaciones prácticas en gestión de riesgo y valoración de carteras crediticias.
