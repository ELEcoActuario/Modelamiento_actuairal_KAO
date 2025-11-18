# MODELO HULL-WHITE: MANUAL TEÓRICO-OPERATIVO

## 🎯 FUNDAMENTO TEÓRICO Y PROPÓSITO

### ¿QUÉ ES EL MODELO HULL-WHITE?
El modelo Hull-White es un **modelo de tasa de interés de equilibrio parcial** desarrollado por John Hull y Alan White en 1990. Implementa un proceso estocástico que reproduce la curva de tasas observada en el mercado con condición de no arbitraje.

### ¿POR QUÉ USAMOS HULL-WHITE PARA PREPAGO?
Este modelo es especialmente valioso porque:

1. **Condición de no arbitraje**: Garantiza E[r(t)] = f(0,t) mediante desplazamiento determinístico φ(t) derivado de θ(t)
2. **Árbol trinomial**: Proporciona mayor precisión y estabilidad numérica
3. **Calibración específica**: Parámetros ajustados por crédito individual usando nodos relevantes
4. **Múltiples monedas**: Calibración independiente por moneda (COP, USD, UVR)
5. **Conversión precisa**: Transformaciones rigurosas entre tasas EA y short rates

### ECUACIÓN FUNDAMENTAL
```
dr(t) = [θ(t) - a·r(t)]dt + σ·dW(t)
```

Donde:
- **r(t)**: Tasa corta instantánea (short rate)
- **θ(t)**: Función de drift con condición de no arbitraje:
  θ(t) = ∂f(0,t)/∂t + a·f(0,t) + (σ²/2a)·(1 - e^{-2 a t})
- **φ(t)**: Desplazamiento determinístico que resuelve la ODE
  φ'(t) + a·φ(t) = θ(t), con condición inicial φ(0) = r₀
- **a**: Velocidad de reversión a la media (calibrado típicamente ~0.1)
- **σ**: Volatilidad instantánea calibrada por crédito
- **W(t)**: Proceso de Wiener (movimiento browniano)

### DIFERENCIAS CLAVE CON VASICEK
- **Vasicek**: θ constante, simulación Monte Carlo, parámetros globales por moneda
- **Hull-White**: θ(t) variable, árbol trinomial, calibración específica por crédito

---

## 📊 INFORMACIÓN DE ENTRADA: ¿QUÉ DATOS NECESITAMOS Y POR QUÉ?

### 1. CURVA DE TASAS LIBRES DE RIESGO DIARIA
**¿Qué información contiene?**
- **Nodos temporales**: Días desde fecha de corte (0, 1, 2, ..., n)
- **Tasas por moneda**: COP, USD, UVR (tasas efectivas anuales)
- **Estructura temporal completa**: Desde overnight hasta 30+ años

**¿Por qué es fundamental?**
- **Forward rates f(0,t)**: Se calculan desde precios de bonos cero-cupón: f(0,t) = -∂/∂t ln P(0,t)
- **Función θ(t)**: Garantiza condición de no arbitraje ajustándose a forward rates observadas
- **Mapeo por nodos**: Cada fecha de crédito mapea a un nodo específico (día desde corte)
- **Múltiples monedas**: Calibración independiente por moneda (COP, USD, UVR)

### 2. FLUJOS CONTRACTUALES INDIVIDUALES
**¿Qué representan?**
- **Cronograma detallado**: Fechas y montos de cada pago futuro
- **Componentes separados**: Capital, intereses, saldo pendiente
- **Moneda específica**: Cada crédito tiene su moneda de denominación

**¿Por qué son críticos?**
- **Fechas de evaluación**: Definen cuándo se puede ejercer prepago
- **Valor de ejercicio**: Saldo pendiente determina beneficio del prepago
- **Selección de curva**: La moneda determina qué curva usar

### 3. PARÁMETROS DE CONFIGURACIÓN
**Diferencial de prepago**: Spread mínimo que justifica económicamente el prepago
**Fecha de corte**: Momento desde el cual se proyectan escenarios
**Parámetros de calibración**: a (reversión), σ (volatilidad base y estresada)

---

## 🔬 PROCESO PASO A PASO: METODOLOGÍA ACTUARIAL

### FASE 1: CALIBRACIÓN ESPECÍFICA POR CRÉDITO

#### ¿QUÉ SE CALIBRA?
Para **cada crédito individual** se calibran parámetros específicos:
1. **Parámetro a**: Velocidad de reversión mediante regresión Ornstein-Uhlenbeck
2. **Parámetro σ**: Volatilidad instantánea calibrada con nodos relevantes del crédito
3. **r₀**: Tasa inicial continua: r₀ = f(0, 1día)
4. **Forward rates f(0,t)**: Tasas forward instantáneas desde precios de bonos
5. **Función θ(t)**: Drift que garantiza condición de no arbitraje

#### PROCESO DE CALIBRACIÓN PASO A PASO

**1. Filtración de Nodos Relevantes:**

Cada crédito se analiza mapeando sus fechas de amortización a nodos específicos (días desde fecha de corte) en la curva de tasas. La curva se filtra para incluir únicamente los nodos correspondientes a las fechas de pago del crédito, eliminando información irrelevante que podría introducir ruido en la calibración.

**2. Cálculo de Forward Rates Instantáneas:**

Desde las tasas efectivas anuales EA(t) se calculan los precios de bonos cero-cupón:

```
P(0,t) = (1 + EA(t))^(-t)
```

Las forward rates instantáneas f(0,t) se obtienen mediante el método discreto simplificado:

```
f(0,t) = -ln(P(0,t)) / t
```

Este cálculo se realiza únicamente con los nodos filtrados del crédito.

**3. Calibración Ornstein-Uhlenbeck:**

Los parámetros a y σ se calibran mediante regresión lineal del proceso Ornstein-Uhlenbeck:

```
Δr_t / Δt = -a · r_t + ε_t
```

Donde:
- **a_calibrado**: Pendiente de la regresión (velocidad de reversión)
- **σ_calibrado**: Desviación estándar de los residuos ajustada por tiempo

```
σ = √[Var(residuos) · Δt_promedio]
```

**4. Función θ(t) y desplazamiento φ(t) (No Arbitraje):**

La función θ(t) garantiza que la esperanza de la tasa corta sea igual a la forward rate observada:

```
θ(t) = ∂f(0,t)/∂t + a·f(0,t) + (σ²/2a) · (1 - e^{-2 a t})
```

Con θ(t) se define φ(t) resolviendo φ'(t) + a·φ(t) = θ(t), φ(0) = r₀; usando r(t) = φ(t) + x(t) se garantiza E[r(t)] = f(0,t).

**5. Inicialización r₀:**

La tasa corta inicial r₀ se obtiene como proxy de f(0,0):

```
r₀ = f(0, 1día)
```

Se usa el día 1 en lugar de t=0 para evitar problemas numéricos de división por cero.

#### EJEMPLO COMPARATIVO

**Crédito A (COP, 24 cuotas mensuales):**
- Filtración: 24 nodos específicos de curva COP
- Forward rates: f(0,t) calculadas con esos 24 puntos
- Calibración: (a, σ_A) mediante regresión O-U
- Resultado: θ_A(t) específico para Crédito A

**Crédito B (COP, 60 cuotas mensuales):**
- Filtración: 60 nodos específicos de curva COP
- Forward rates: f(0,t) con esos 60 puntos  
- Calibración: (a, σ_B) con datos filtrados
- Resultado: σ_B ≠ σ_A (diferente estructura temporal)

Ambos créditos en la misma moneda obtienen parámetros distintos debido a sus diferentes estructuras temporales.

#### VENTAJAS DE CALIBRACIÓN ESPECÍFICA
- **Precisión**: Parámetros ajustados a estructura temporal real del crédito
- **Relevancia**: Solo información de nodos relevantes, sin ruido
- **Teoría sólida**: Cada crédito tiene dinámica propia de prepago
- **No arbitraje**: Garantizado mediante función θ(t) calibrada

### FASE 2: CONSTRUCCIÓN DEL ÁRBOL TRINOMIAL

#### ¿QUÉ SE CONSTRUYE?
Un **árbol trinomial recombinante** con condición de no arbitraje:
- **Cada nodo** representa estado del proceso x(t) con r(t) = φ(t) + x(t)
- **Tres ramas** por nodo: subida (up), medio (mid), bajada (down)
- **Recombinación**: Reducción exponencial de nodos mediante convergencia
- **Fechas reales**: Pasos = fechas de amortización del crédito

#### CONSTRUCCIÓN PASO A PASO

**1. Inicialización (t=0):**

El árbol inicia con el proceso x en cero:
```
x₀ = 0
```

La tasa corta inicial se obtiene de la forward rate calibrada:
```
r₀ = f(0, 1día)
```

Se convierte a tasa efectiva anual para referencia:
```
EA₀ = exp(r₀) - 1
```

**2. Iteración por Paso (cada fecha de pago):**

Para cada paso del árbol correspondiente a una fecha de amortización:

Se calcula el tiempo acumulado desde la fecha de corte sumando los intervalos entre cuotas.

Se obtiene el valor de φ(t) para ese tiempo específico usando la función calibrada.

El espaciado trinomial se define como:
```
Δx = σ · √(3 · Δt)
```

Desde cada nodo activo x_actual se generan tres nodos hijos:
```
x_up = x_actual + drift_x + Δx
x_mid = x_actual + drift_x
x_down = x_actual + drift_x - Δx
```

Donde el drift está dado por:
```
drift_x = -a · x_actual · Δt
```

Las tasas cortas en cada nodo hijo incorporan φ(t) para garantizar no arbitraje:
```
r_up = φ(t) + x_up
r_mid = φ(t) + x_mid
r_down = φ(t) + x_down
```

Finalmente, se convierten a tasas efectivas anuales:
```
EA_up = exp(r_up) - 1
EA_mid = exp(r_mid) - 1
EA_down = exp(r_down) - 1
```

**3. Probabilidades Trinomiales:**

El drift normalizado α se calcula y limita al intervalo [-1, 1]:
```
α = drift_x / Δx
α ∈ [-1, 1]
```

Las probabilidades de transición son:
```
p_up = 1/6 + α²/2 + α/2
p_mid = 2/3 - α²
p_down = 1/6 + α²/2 - α/2
```

Estas probabilidades suman 1 y son siempre no negativas cuando α está acotado.

**4. Estructura Resultante:**
```
Paso 0:           (x₀=0, r₀, EA₀)
                      ↙  ↓  ↘
Paso 1:    (x_up, r_up) (x_mid, r_mid) (x_down, r_down)
              ↙ ↓ ↘       ↙ ↓ ↘         ↙ ↓ ↘
Paso 2:   Recombinación de nodos...
```

#### VENTAJAS DEL ÁRBOL TRINOMIAL
- **Precisión superior**: Mejor aproximación numérica
- **Estabilidad numérica**: Probabilidades siempre válidas con α limitado
- **Flexibilidad temporal**: Maneja intervalos variables entre cuotas
- **Eficiencia**: Recombinación reduce crecimiento exponencial

### FASE 3: CONVERSIÓN ENTRE TASAS

#### ¿POR QUÉ ES CRÍTICA?
El modelo Hull-White trabaja internamente con **short rates** (tasas continuas) pero las decisiones de prepago requieren **tasas EA** (efectivas anuales). La conversión precisa garantiza:
- **Equivalencia financiera**: Mismo valor presente bajo ambas tasas
- **Comparabilidad**: Coherencia con tasa contractual del crédito
- **Consistencia**: Idéntica metodología que modelo Vasicek

#### TRANSFORMACIONES IMPLEMENTADAS

**1. Tasa EA → Short Rate:**

La conversión de tasa efectiva anual a tasa continua se realiza mediante transformación logarítmica:

```
r_short = ln(1 + Tasa_EA)
```

**Ejemplo numérico:**
```
EA = 12.50% = 0.1250
r = ln(1.1250) = 0.1178
```

**2. Short Rate → Tasa EA:**

La conversión inversa utiliza la función exponencial directa:

```
Tasa_EA = exp(r_short) - 1
```

**Ejemplo numérico:**
```
r = 0.1178
EA = exp(0.1178) - 1 = 0.1250 = 12.50%
```

#### VERIFICACIÓN DE REVERSIBILIDAD

Las transformaciones son perfectamente reversibles:

```
EA_original = 0.1250
→ r = ln(1.1250) = 0.1178
→ EA_recuperada = exp(0.1178) - 1 = 0.1250 ✓
```

El error numérico es despreciable (< 1e-15), garantizando equivalencia financiera exacta.

#### NOTA TÉCNICA
Se corrigió la fórmula de conversión `Short Rate → EA` para:
- **Consistencia total** con modelo Vasicek
- **Eficiencia computacional**: Fórmula directa sin cálculo de períodos
- **Simplicidad**: Menor complejidad matemática, mismo resultado

### FASE 4: DECISIÓN DE PREPAGO ✅ UNIFICADO CON VASICEK

#### CRITERIO ECONÓMICO (IDÉNTICO A VASICEK)

En cada fecha de pago se evalúa si es económicamente racional prepagar mediante **comparación directa EA vs EA**:

```
Diferencial = Tasa_contractual_EA - Tasa_simulada_EA

Si Diferencial ≥ diferencial_prepago mínimo:
    → PREPAGAR (conviene refinanciar)
Si no:
    → CONTINUAR (tasas aún altas)
```

**🔄 IMPORTANTE - CRITERIO UNIFICADO:**
- **Simulación**: En short rate space (dr = [θ(t) - a·r]dt + σdW)
- **Conversión**: Short Rate → EA mediante `EA = exp(r) - 1`
- **Comparación**: Directa EA vs EA (sin transformaciones adicionales)
- **Consistencia**: Idéntica metodología que modelo Vasicek

#### LÓGICA DE IMPLEMENTACIÓN

**1. Evaluación por Nodo:**

Para cada nodo del árbol trinomial se obtiene la tasa EA simulada y se calcula la diferencia con la tasa contractual del crédito. Si la diferencia supera el umbral mínimo de prepago (diferencial establecido), indica que las tasas de mercado bajaron suficientemente para que convenga refinanciar.

**2. Modificación de Flujos:**

Cuando se decide prepagar, el tratamiento varía según el tipo de crédito:

**Créditos Bullet:**
- Se calculan intereses proporcionales al tiempo transcurrido:
  ```
  factor_tiempo = días_transcurridos / días_totales_crédito
  intereses_acumulados = intereses_totales × factor_tiempo
  flujo_prepago = capital_original + intereses_acumulados
  ```

**Créditos con Amortización Regular:**
- Se usa el saldo pendiente completo:
  ```
  flujo_prepago = saldo_pendiente
  ```

- Los flujos futuros se eliminan del cronograma

**3. Generación de Escenarios:**

**Escenario Base:**
- Utiliza volatilidad σ calibrada específicamente para el crédito
- Refleja comportamiento esperado bajo condiciones normales

**Escenario Estresado:**
- Volatilidad incrementada: σ_estresado = σ × 1.25
- Representa condiciones adversas para análisis de riesgo

**Múltiples Trayectorias:**
- Diferentes caminos del árbol trinomial
- Cada trayectoria representa un escenario posible de evolución de tasas
- Las decisiones de prepago son óptimas en cada nodo según criterio económico

---

## 📈 INTERPRETACIÓN DE RESULTADOS: ¿QUÉ SIGNIFICAN LOS OUTPUTS?

### ESCENARIOS DE PREPAGO POR CRÉDITO

**¿Qué representan?**

Cronogramas de pago modificados que reflejan decisiones racionales de prepago bajo diferentes trayectorias simuladas del árbol trinomial Hull-White.

**Contenido de cada escenario:**

Cada escenario generado incluye la información completa del flujo de caja ajustado:
- **Fecha**: Momento del flujo de caja
- **Capital**: Monto de capital pagado
- **Intereses**: Intereses calculados (proporcionales para bullet)
- **Flujo Total**: Suma de capital más intereses
- **Saldo**: Saldo pendiente remanente
- **Indicador de prepago**: Marca si ocurrió prepago en esa fecha
- **Tasa simulada**: Tasa EA del nodo correspondiente
- **Diferencial**: Diferencia entre tasa contractual y simulada

**Doble Escenario:**

**Escenario Base:** Utiliza volatilidad σ calibrada específicamente para el crédito individual mediante regresión Ornstein-Uhlenbeck con sus nodos relevantes.

**Escenario Estresado:** Aplica volatilidad incrementada (σ × 1.25), representando un factor de estrés regulatorio estándar para análisis de sensibilidad.

**Tratamiento de Créditos Bullet:**

**Cálculo proporcional de intereses:**
```
intereses_acumulados = intereses_totales × (días_transcurridos / días_totales)
```

**Separación correcta:** Capital e intereses se mantienen como componentes independientes sin duplicación.

**Consistencia metodológica:** La lógica de cálculo es idéntica a la implementada en el modelo Vasicek, garantizando comparabilidad de resultados.

### TRAZABILIDAD Y AUDITORÍA

**Logging detallado del proceso:**

Cada crédito genera un registro completo que permite auditar todo el proceso de calibración y simulación:

**Calibración:**
- Número de nodos relevantes utilizados
- Parámetros calibrados (a, σ)
- Rango de tasas EA filtradas
- Verificación de θ(t) en tiempos clave

**Construcción del árbol:**
- Número de pasos (fechas de amortización)
- Tasas EA mapeadas por fecha
- Parámetros efectivos del árbol trinomial

**Decisiones de prepago:**
- Nodo específico donde ocurrió prepago
- Tasa simulada EA en ese nodo
- Tasa contractual del crédito
- Diferencial calculado
- Decisión tomada (PREPAGAR / CONTINUAR)
- Flujos modificados resultantes

### PARÁMETROS CALIBRADOS

**Interpretación de parámetros:**

**Parámetro a (velocidad de reversión):**
- Valores típicos: 0.1 - 0.5
- Indica qué tan rápido las tasas revierten hacia su nivel de largo plazo
- Valores bajos: reversión lenta, mayor persistencia de shocks
- Valores altos: reversión rápida, shocks de corta duración

**Parámetro σ (volatilidad instantánea):**
- Valores típicos: 0.01 - 0.05
- Mide la magnitud de fluctuaciones aleatorias en tasas
- Calibrado específicamente por crédito usando nodos relevantes
- Varía entre créditos aunque tengan la misma moneda

**Función θ(t) (drift con no arbitraje):**
- Refleja estructura temporal de tasas forward observadas
- Garantiza que E[r(t)] = f(0,t)
- Asegura consistencia con precios de mercado
- Variable en el tiempo, no constante

---

## 🎯 APLICACIONES PRÁCTICAS Y CASOS DE USO

### ANÁLISIS MULTI-MONEDA

**Objetivo:** Valorar carteras con créditos en diferentes monedas (COP, USD, UVR)

**Metodología implementada:**

**1. Calibración específica por crédito:**
Cada crédito, independientemente de su moneda, calibra parámetros usando únicamente sus nodos temporales relevantes.

**2. Selección de curva por moneda:**
Se utiliza automáticamente la curva de tasas correspondiente a la moneda de denominación del crédito.

**3. Parámetros individualizados:**
Dos créditos en la misma moneda pueden tener volatilidades diferentes (σ_A ≠ σ_B) debido a sus distintas estructuras temporales.

**4. Procesamiento por crédito:**
Cada crédito se procesa de forma independiente con sus parámetros calibrados específicos.

**5. Consolidación de resultados:**
Los escenarios de prepago de todos los créditos se agregan para obtener visión de portafolio.

### TRATAMIENTO DE CRÉDITOS BULLET

**Desafío:** Los créditos bullet tienen un único pago al vencimiento, sin flujos intermedios que permitan evaluar prepago.

**Solución implementada:**

**Detección automática:** El sistema identifica créditos con un solo flujo de pago.

**Generación de fechas de evaluación:**
- Plazo ≤ 5 años: fechas de evaluación mensuales
- Plazo > 5 años: fechas de evaluación anuales

**Evaluación sintética:** Se permite prepago en fechas intermedias aunque no exista flujo contractual en esas fechas.

**Cálculo proporcional de intereses:**

La fórmula para calcular intereses devengados en caso de prepago anticipado es:

```
factor_tiempo = días_transcurridos / días_totales_crédito
intereses_acumulados = intereses_totales_originales × factor_tiempo
```

**Estructura del flujo de prepago:**
- Capital: Monto de capital original del crédito
- Intereses: Intereses proporcionales al tiempo transcurrido
- Flujo total: Capital + Intereses acumulados

**Consistencia:** Esta metodología es consistente entre Hull-White y Vasicek.

### STRESS TESTING AVANZADO

**Objetivo:** Evaluar sensibilidad de decisiones de prepago ante incrementos en volatilidad del mercado.

**Implementación:**

**Escenario base:**
- Parámetros (a, σ) calibrados mediante regresión Ornstein-Uhlenbeck
- Función θ(t) calculada con σ normal
- Árbol trinomial construido con volatilidad calibrada

**Escenario estresado:**
- Volatilidad incrementada: σ_estresado = σ × 1.25
- Recalculación de θ(t) con nueva volatilidad
- Nuevo árbol trinomial con parámetros estresados

**Análisis comparativo:**
- Diferencias en decisiones de prepago entre escenarios
- Cambios en fechas esperadas de prepago
- Impacto en flujos de caja proyectados
- Evaluación de robustez de decisiones

---

## ⚠️ LIMITACIONES Y CONSIDERACIONES

### SUPUESTOS DEL MODELO

**Supuestos restrictivos inherentes:**

**1. Volatilidad constante:** El parámetro σ permanece fijo durante toda la vida del crédito. En realidad, la volatilidad de tasas puede variar según condiciones de mercado.

**2. Velocidad de reversión constante:** El parámetro a se mantiene invariante. En mercados reales, la velocidad de ajuste puede cambiar con ciclos económicos.

**3. Normalidad de shocks:** Se asume distribución gaussiana para innovaciones. Los mercados pueden experimentar eventos extremos (colas pesadas) no capturados por normalidad.

**4. Independencia de prepago:** Se asume que la decisión de prepago depende solo de tasas. Factores como liquidez del deudor o costos de transacción no se modelan explícitamente.

**Implicaciones prácticas:**

**Recalibración periódica:** Actualizar parámetros regularmente (mensual o trimestralmente) para reflejar condiciones actuales de mercado.

**Validación empírica:** Contrastar decisiones simuladas de prepago con comportamiento histórico observado.

**Análisis de sensibilidad:** Evaluar cómo cambios en parámetros afectan resultados (especialmente σ).

**Uso conjunto de modelos:** Complementar Hull-White con Vasicek para triangular resultados y aumentar confianza.

### CONSIDERACIONES COMPUTACIONALES

**Complejidad del árbol trinomial:**

**Crecimiento exponencial:** Sin recombinación, el número de nodos crece como 3^n, donde n es el número de pasos.

**Requerimientos de memoria:** Créditos con plazos largos (>10 años) y muchas cuotas pueden generar árboles grandes que requieren memoria significativa.

**Balance precisión-eficiencia:** Más pasos del árbol aumentan precisión pero también tiempo de cómputo.

**Optimizaciones implementadas:**

**Recombinación de nodos:** El árbol trinomial permite que diferentes trayectorias converjan en nodos comunes, reduciendo drásticamente el crecimiento. Un árbol de n pasos tiene aproximadamente O(n²) nodos en lugar de O(3^n).

**Calibración específica:** Al usar solo nodos relevantes del crédito, se evita procesar información innecesaria y se reduce ruido en parámetros.

**Conversiones eficientes:** Las transformaciones EA↔short rate usan fórmulas directas (exponencial y logaritmo) sin iteraciones numéricas, optimizando velocidad.

---

## 🔄 INTEGRACIÓN CON OTROS MODELOS

### COMPARACIÓN CON VASICEK

**Hull-White:**
- Función θ(t) variable que garantiza ajuste a forward rates observadas
- Condición de no arbitraje: E[r(t)] = f(0,t)
- Árbol trinomial con recombinación
- Calibración específica por crédito
- Mayor complejidad computacional

**Vasicek:**
- Parámetro θ constante (nivel de largo plazo)
- Simulación Monte Carlo directa
- Calibración global por moneda
- Mayor velocidad de cómputo
- Más simple conceptualmente

### COMPLEMENTARIEDAD Y USO CONJUNTO CON VASICEK

**Triangulación de resultados:** Usar ambos modelos en paralelo permite validar decisiones de prepago. Si Hull-White y Vasicek coinciden en fechas probables de prepago, la confianza aumenta.

**Especialización por caso:**
- **Hull-White**: Óptimo cuando se requiere ajuste preciso a curva de mercado y calibración por crédito
- **Vasicek**: Preferible para análisis rápidos, portafolios grandes y calibración global por tipo

**Validación cruzada:** Comparar escenarios entre modelos para detectar inconsistencias o supuestos problemáticos.

---

## 🔧 CARACTERÍSTICAS DISTINTIVAS DEL MODELO

### 1. CONDICIÓN DE NO ARBITRAJE GARANTIZADA

El modelo Hull-White implementa rigurosa condición de no arbitraje mediante:

**Función θ(t) calibrada:** Asegura que la esperanza de la tasa corta en cualquier momento futuro sea igual a la forward rate observada en el mercado:
```
E[r(t)] = f(0,t)
```

**Cálculo de forward rates:** Desde precios de bonos cero-cupón observados, garantizando consistencia con precios de mercado.

**Recalibración de θ(t) en estrés:** Cuando la volatilidad cambia al escenario estresado, la función θ(t) se recalcula para mantener condición de no arbitraje.

### 2. CALIBRACIÓN ESPECÍFICA POR CRÉDITO

**Filtrado inteligente:** Solo se usan nodos temporales relevantes para cada crédito específico, eliminando ruido de puntos no relacionados.

**Parámetros individualizados:** Dos créditos en la misma moneda obtienen volatilidades diferentes si tienen estructuras temporales distintas.

**Precisión mejorada:** La calibración enfocada produce parámetros más representativos del riesgo real del crédito.

### 3. TRANSFORMACIONES EXACTAS DE TASAS

**EA → Short Rate:**
```
r = ln(1 + EA)
```
Transformación logarítmica de tasa discreta a continua.

**Short Rate → EA:**
```
EA = exp(r) - 1
```
Fórmula directa sin cálculo de períodos, consistente con modelo Vasicek.

**Reversibilidad perfecta:** Las transformaciones son matemáticamente inversas con error numérico despreciable (<1e-15).

### 4. TRATAMIENTO ROBUSTO DE CRÉDITOS BULLET

**Detección automática:** Identifica créditos con un solo flujo de pago.

**Fechas sintéticas:** Genera fechas de evaluación intermedias (mensuales o anuales según plazo).

**Intereses proporcionales:** Calcula intereses devengados al tiempo de prepago mediante factor temporal:
```
intereses = intereses_totales × (días_transcurridos / días_totales)
```

**Sin duplicación:** Capital e intereses se mantienen separados en todas las columnas de salida.

### 5. FLEXIBILIDAD MULTI-MONEDA

**Curvas independientes:** Cada moneda (COP, USD, UVR) tiene su propia curva de tasas libres de riesgo.

**Selección automática:** El sistema usa la curva correspondiente a la moneda de denominación del crédito.

**Procesamiento paralelo:** Múltiples créditos en diferentes monedas se procesan simultáneamente.

---

## 🎯 CONCLUSIÓN

El modelo Hull-White implementado proporciona un **marco matemáticamente riguroso** para análisis de prepago de créditos, combinando:

**Solidez teórica:** Condición de no arbitraje garantizada mediante función θ(t) calibrada con forward rates.

**Precisión:** Calibración específica por crédito usando únicamente nodos temporales relevantes.

**Eficiencia computacional:** Árbol trinomial recombinante que reduce complejidad de O(3^n) a O(n²).

**Flexibilidad operativa:** Manejo de múltiples monedas, créditos bullet, y escenarios estresados.

**Consistencia metodológica:** Transformaciones y cálculos alineados con el modelo Vasicek.

Esta implementación es adecuada para **aplicaciones prácticas** en gestión de riesgo, valoración de carteras, y cumplimiento regulatorio en el sector financiero colombiano.
