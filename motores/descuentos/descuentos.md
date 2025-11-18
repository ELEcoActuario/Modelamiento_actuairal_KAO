# MÓDULO DE DESCUENTOS: MANUAL TEÓRICO-OPERATIVO

## 🎯 FUNDAMENTO TEÓRICO Y PROPÓSITO

### ¿QUÉ ES EL MÓDULO DE DESCUENTOS?
El módulo de descuentos implementa las **metodologías supervisoras de valoración** establecidas por la Superintendencia Financiera de Colombia (SFC) para el cálculo de valor presente de carteras crediticias. Aplica tanto curvas base como escenarios normativos de estrés para cumplir con requerimientos regulatorios.

### ¿POR QUÉ ES FUNDAMENTAL EN ANÁLISIS ACTUARIAL?
Este módulo es crítico porque:

1. **Cumplimiento normativo**: Implementa metodologías SIAR Capítulo 31
2. **Valoración de carteras**: Calcula valor presente ajustado por riesgo de prepago
3. **Análisis de sensibilidad**: Evalúa impacto de 6 escenarios de estrés normativos
4. **Gestión de riesgo**: Cuantifica exposición a movimientos de tasas de interés
5. **Provisiones**: Base para cálculo de provisiones por riesgo de mercado

### PRINCIPIO FUNDAMENTAL: VALOR PRESENTE AJUSTADO
```
VP_ajustado = Σ [Flujo_con_prepago(t) × Factor_descuento(t) × Factor_banda_SFC(t)]
```

Donde cada componente refleja:
- **Flujo_con_prepago**: Cronograma modificado por decisiones de prepago
- **Factor_descuento**: Curva libre de riesgo por moneda
- **Factor_banda_SFC**: Metodología normativa de factores t_k

---

## 📊 INFORMACIÓN DE ENTRADA: ¿QUÉ DATOS NECESITAMOS Y POR QUÉ?

### 1. FLUJOS AJUSTADOS POR PREPAGO
**¿Qué información contiene?**
- **Cronogramas modificados**: Flujos resultantes de modelos estocásticos (Vasicek, Hull-White)
- **Múltiples simulaciones**: 100+ escenarios por crédito
- **Componentes detallados**: Capital_Ajustado, Intereses_Ajustados, Prepago_Esperado
- **Bandas SFC**: Factores t_k asignados según metodología normativa

**¿Por qué son fundamentales?**
- **Realismo**: Reflejan decisiones racionales de prepago
- **Diversidad de escenarios**: Capturan incertidumbre de comportamiento
- **Base regulatoria**: Cumplen metodologías supervisoras
- **Trazabilidad**: Permiten auditoría completa del proceso

### 2. CURVAS DE DESCUENTO BASE
**¿Qué representan?**
- **Tasas libres de riesgo**: Por moneda (COP, USD, UVR)
- **Estructura temporal**: Desde overnight hasta 30+ años
- **Nodos diarios**: Granularidad para coincidencia exacta con fechas de pago

**¿Por qué son críticas?**
- **Valoración neutral al riesgo**: Base teórica para descuento
- **Diferenciación por moneda**: Reconoce riesgo específico de cada divisa
- **Actualización de mercado**: Reflejan condiciones actuales de tasas

### 3. CURVAS NORMATIVAS ESTRESADAS
**¿Qué escenarios incluyen?**
1. **Paralelo hacia arriba**: +100 pb en toda la curva
2. **Paralelo hacia abajo**: -100 pb en toda la curva
3. **Empinamiento**: Corto +50pb, Largo +150pb
4. **Aplanamiento**: Corto +150pb, Largo +50pb
5. **Corto plazo hacia arriba**: ≤2 años +100pb
6. **Corto plazo hacia abajo**: ≤2 años -100pb

**¿Por qué estos escenarios específicos?**
- **Normativa SFC**: Cumplimiento de requerimientos regulatorios
- **Cobertura completa**: Evalúan diferentes tipos de riesgo de tasa
- **Stress testing**: Identifican vulnerabilidades de la cartera
- **Gestión de capital**: Base para cálculo de capital regulatorio

---

## 🔬 PROCESO PASO A PASO: METODOLOGÍA ACTUARIAL

### FASE 1: CÁLCULO DE VALOR PRESENTE BASE

#### ¿QUÉ SE CALCULA?
El **valor presente promedio** de cada crédito usando curvas base y flujos ajustados por prepago.

#### ¿CÓMO SE REALIZA?
**Metodología por crédito:**
1. **Identificación de moneda**: Detección automática desde datos del crédito
2. **Selección de curva**: Curva base correspondiente a la moneda
3. **Promediación de simulaciones**: VP promedio de todas las simulaciones del crédito
4. **Aplicación de bandas SFC**: Uso de factores t_k normativos

**Fórmula aplicada:**
```
VP_base = (1/n) × Σ[i=1 to n] Σ[t] [Flujo_i(t) / (1 + Tasa_base(nodo_t))^t_k(t)]
```

#### ¿POR QUÉ ESTA METODOLOGÍA?
- **Consistencia normativa**: Sigue exactamente metodología SIAR
- **Búsqueda exacta**: Coincidencia precisa de nodos temporales
- **Promediación robusta**: Reduce ruido de simulaciones individuales
- **Trazabilidad**: Cada cálculo es auditable

### FASE 2: CÁLCULO DE VALORES PRESENTES ESTRESADOS

#### ¿QUÉ SE CALCULA?
El **valor presente promedio** bajo cada uno de los 6 escenarios normativos de estrés.

#### ¿CÓMO SE IMPLEMENTA?
**Proceso por escenario:**
1. **Aplicación de shock**: Modificación de curva base según escenario
2. **Recálculo de VP**: Mismo proceso que VP base con curva estresada
3. **Consolidación**: Agregación de resultados por escenario
4. **Validación**: Verificación de consistencia matemática

**Ejemplo de aplicación de shocks:**
```python
# Escenario: Paralelo hacia arriba
Tasa_estresada(t) = Tasa_base(t) + 0.01

# Escenario: Empinamiento  
Tasa_estresada(t) = Tasa_base(t) + 0.005 + 0.001 × Tiempo(t)
```

#### ¿POR QUÉ ESTOS CÁLCULOS?
- **Análisis de sensibilidad**: Cuantifica impacto de movimientos de tasas
- **Identificación de riesgos**: Detecta vulnerabilidades específicas
- **Cumplimiento regulatorio**: Satisface requerimientos de stress testing
- **Gestión proactiva**: Permite toma de decisiones informadas

### FASE 3: CÁLCULO DE SENSIBILIDADES (DELTAS)

#### ¿QUÉ SE CALCULA?
Las **diferencias** entre valor presente base y cada escenario estresado.

#### ¿CÓMO SE IMPLEMENTA?
**Cálculo de deltas:**
```
Δ_escenario = VP_estresado_escenario - VP_base
```

**Interpretación de resultados:**
- **Δ > 0**: El escenario beneficia el valor de la cartera
- **Δ < 0**: El escenario perjudica el valor de la cartera
- **|Δ| grande**: Alta sensibilidad a ese tipo de movimiento

#### ¿POR QUÉ SON IMPORTANTES LOS DELTAS?
- **Medida de riesgo**: Cuantifican exposición a diferentes tipos de shock
- **Comparabilidad**: Permiten ranking de riesgos por magnitud
- **Gestión de cobertura**: Guían estrategias de hedging
- **Reporting**: Base para reportes regulatorios y gerenciales

---

## 📈 INTERPRETACIÓN DE RESULTADOS: ¿QUÉ SIGNIFICAN LOS OUTPUTS?

### DATAFRAME CONSOLIDADO DE DESCUENTOS
**Estructura del output:**
- **VP_base**: Valor presente con curvas base
- **VP_est_Paralelo_hacia_arriba**: VP con shock paralelo +100pb
- **VP_est_Paralelo_hacia_abajo**: VP con shock paralelo -100pb
- **VP_est_Empinamiento**: VP con empinamiento de curva
- **VP_est_Aplanamiento**: VP con aplanamiento de curva
- **VP_est_Corto_plazo_hacia_arriba**: VP con shock corto +100pb
- **VP_est_Corto_plazo_hacia_abajo**: VP con shock corto -100pb

### MÉTRICAS DE SENSIBILIDAD
**Deltas por escenario:**
- **Δ_Paralelo_hacia_arriba**: Impacto de alza general de tasas
- **Δ_Paralelo_hacia_abajo**: Impacto de baja general de tasas
- **Δ_Empinamiento**: Sensibilidad a cambios de pendiente (steepening)
- **Δ_Aplanamiento**: Sensibilidad a aplanamiento de curva (flattening)
- **Δ_Corto_plazo_hacia_arriba**: Exposición a alzas de corto plazo
- **Δ_Corto_plazo_hacia_abajo**: Exposición a bajas de corto plazo

### INTERPRETACIÓN ECONÓMICA
**Signos de los deltas:**
- **Δ negativo en alzas**: Normal para activos de tasa fija
- **Δ positivo en bajas**: Beneficio por reducción de tasas de descuento
- **Magnitud relativa**: Indica qué tipo de movimiento genera mayor impacto

---

## 🎯 APLICACIONES PRÁCTICAS Y CASOS DE USO

### GESTIÓN DE RIESGO DE TASA DE INTERÉS
**Identificación de exposiciones:**
- **Riesgo paralelo**: Sensibilidad a movimientos generales de tasas
- **Riesgo de forma**: Exposición a cambios en la forma de la curva
- **Riesgo de plazo**: Concentración de sensibilidad en segmentos específicos

### CÁLCULO DE PROVISIONES
**Metodología regulatoria:**
1. **Identificar** el escenario más adverso para cada crédito
2. **Calcular** la pérdida máxima esperada
3. **Aplicar** factores de provisión según normativa
4. **Consolidar** a nivel de cartera

### OPTIMIZACIÓN DE CARTERAS
**Estrategias basadas en sensibilidades:**
- **Diversificación temporal**: Balancear exposiciones por plazo
- **Cobertura selectiva**: Hedging de riesgos más significativos
- **Rebalanceo**: Ajuste de composición según tolerancia al riesgo

---

## ⚠️ LIMITACIONES Y CONSIDERACIONES

### SUPUESTOS NORMATIVOS
**Escenarios predefinidos**: Los 6 escenarios pueden no capturar todos los riesgos posibles
**Magnitud de shocks**: Los movimientos de 100pb pueden ser insuficientes en crisis
**Independencia**: No considera correlaciones entre diferentes tipos de shock

### CONSIDERACIONES OPERATIVAS
**Calidad de curvas**: Resultados dependen de la calidad de curvas base
**Frecuencia de actualización**: Necesidad de recalcular con nueva información de mercado
**Agregación**: Pérdida de información al promediar simulaciones

---

## 🔧 INTEGRACIÓN CON FASE 6: VALIDACIÓN

El módulo de descuentos se complementa con la **Fase 6 de Validación** que verifica la calidad de los flujos ajustados mediante:

### VERIFICACIÓN DE ESTRUCTURA
**Antes del descuento:**
- Validación de columnas críticas: `Capital_Ajustado`, `Intereses_Ajustados`, `Flujo_Total_Ajustado`, `Prepago_Esperado`
- Detección de DataFrames vacíos o inconsistentes
- Logging detallado de problemas encontrados

### AUDITORÍA DE CÁLCULOS
**Durante el proceso:**
- Logging de primeros créditos procesados (verificación manual)
- Seguimiento de VPs calculados por moneda
- Validación de curvas estresadas por escenario
- Verificación de nombres de columnas finales

### TRAZABILIDAD COMPLETA
**Información registrada:**
- Estado inicial de portafolios (base y estresado)
- Curvas disponibles por moneda
- VPs calculados por crédito y escenario
- Deltas de sensibilidad finales

El módulo de descuentos proporciona una base sólida y normativamente compliant para la valoración y análisis de riesgo de carteras crediticias, implementando estándares supervisores con precisión técnica y eficiencia operativa.
