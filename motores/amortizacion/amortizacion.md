# SISTEMAS DE AMORTIZACIÓN: MANUAL TEÓRICO-OPERATIVO

## 🎯 FUNDAMENTO TEÓRICO Y PROPÓSITO

### ¿QUÉ SON LOS SISTEMAS DE AMORTIZACIÓN?
Los sistemas de amortización son **metodologías matemáticas** que determinan cómo se distribuyen los pagos de capital e intereses a lo largo de la vida de un crédito. Cada sistema responde a diferentes necesidades económicas, perfiles de riesgo y estrategias comerciales de las entidades financieras.

### ¿POR QUÉ SON FUNDAMENTALES EN EL ANÁLISIS ACTUARIAL?
En el contexto de análisis de prepago y valoración de carteras, los sistemas de amortización son críticos porque:

1. **Definen el cronograma base**: Establecen las fechas y montos contractuales sobre los cuales se evalúan las decisiones de prepago
2. **Determinan el perfil de riesgo**: Diferentes sistemas concentran el riesgo de prepago en distintos momentos
3. **Impactan la valoración**: El patrón de amortización afecta directamente el valor presente y la duración de los activos
4. **Influyen en el comportamiento del deudor**: Cada sistema crea incentivos diferentes para el prepago

### PRINCIPIOS MATEMÁTICOS FUNDAMENTALES
Todos los sistemas se basan en la **ecuación fundamental del valor del dinero en el tiempo**:
```
VP = Σ [Flujo(t) / (1 + r)^t]
```

Donde cada sistema distribuye diferentemente:
- **Capital**: Monto principal a amortizar
- **Intereses**: Costo financiero del saldo pendiente
- **Tiempo**: Periodicidad y plazo de los pagos

---

## 📊 INFORMACIÓN DE ENTRADA: ¿QUÉ DATOS NECESITAMOS Y POR QUÉ?

### DATOS CONTRACTUALES BÁSICOS
**¿Qué información se requiere?**
- **Monto del crédito (Valor)**: Capital inicial a financiar
- **Tasa efectiva anual**: Costo financiero del crédito
- **Número de cuotas**: Cantidad total de pagos programados
- **Fechas**: Desembolso y vencimiento contractual
- **Periodicidad**: Frecuencia de pagos (mensual, quincenal, etc.)

**¿Por qué cada dato es crítico?**
- **Monto**: Define la base sobre la cual se calculan intereses y amortización
- **Tasa**: Determina el costo financiero y la distribución entre capital e intereses
- **Plazo**: Establece el horizonte temporal y la velocidad de amortización
- **Periodicidad**: Afecta la tasa periódica y el número total de flujos

### CONVERSIÓN DE TASA EFECTIVA ANUAL A PERIÓDICA
**¿Por qué es necesaria esta conversión?**
La tasa contractual se expresa como **Efectiva Anual (EA)**, pero los pagos son periódicos. La conversión correcta es fundamental para:
- **Precisión matemática**: Mantener equivalencia financiera
- **Cumplimiento normativo**: Seguir estándares de cálculo actuarial
- **Consistencia**: Garantizar resultados comparables entre productos

**Fórmula de conversión:**
```
Tasa_periódica = (1 + Tasa_EA)^(1/frecuencia) - 1
```

**Mapeo de frecuencias:**
- Quincenal: 24 períodos/año
- Mensual: 12 períodos/año  
- Bimestral: 6 períodos/año
- Trimestral: 4 períodos/año
- Semestral: 2 períodos/año
- Anual: 1 período/año

---

## 🔬 PROCESO PASO A PASO: METODOLOGÍA ACTUARIAL COMÚN

### FASE 1: VALIDACIÓN Y PREPARACIÓN DE DATOS

#### ¿QUÉ SE VALIDA?
1. **Existencia de campos obligatorios**: Verificar que todos los datos requeridos estén presentes
2. **Tipos de datos**: Convertir strings a números y fechas según corresponda
3. **Coherencia lógica**: Validar que fecha de vencimiento > fecha de desembolso
4. **Rangos válidos**: Montos positivos, tasas no negativas, cuotas > 0

#### ¿POR QUÉ ESTAS VALIDACIONES?
- **Prevenir errores**: Detectar problemas antes del cálculo
- **Garantizar calidad**: Asegurar consistencia en los resultados
- **Cumplir normativa**: Seguir estándares de validación actuarial
- **Facilitar auditoría**: Crear trazabilidad de los procesos

### FASE 2: CONVERSIÓN DE PARÁMETROS

#### ¿QUÉ SE CONVIERTE?
- **Tasa EA a periódica**: Aplicar fórmula de equivalencia financiera
- **Fechas a períodos**: Calcular número exacto de períodos entre fechas
- **Periodicidad a incrementos**: Determinar saltos temporales entre pagos

#### ¿CÓMO SE REALIZA LA CONVERSIÓN?
```
# Ejemplo para periodicidad mensual:
frecuencia_anual = 12
tasa_periodica = (1 + 0.12)^(1/12) - 1 = 0.009489
```

### FASE 3: GENERACIÓN DE CRONOGRAMA

#### ¿QUÉ SE GENERA?
Un **DataFrame estandarizado** con la estructura:
- **Fecha_Pago**: Fecha específica de cada pago
- **Capital**: Abono a capital en cada período
- **Intereses**: Intereses causados sobre saldo pendiente
- **Flujo_Total**: Suma de capital + intereses
- **Saldo_Pendiente**: Capital remanente después del pago

#### ¿POR QUÉ ESTA ESTRUCTURA?
- **Estandarización**: Formato uniforme para todos los sistemas
- **Compatibilidad**: Integración directa con modelos estocásticos
- **Trazabilidad**: Seguimiento detallado de cada componente
- **Flexibilidad**: Fácil manipulación para análisis posteriores

---

## 🏦 SISTEMA FRANCÉS: CUOTAS FIJAS

### ¿QUÉ ES EL SISTEMA FRANCÉS?
El sistema francés, también conocido como **sistema de cuotas fijas**, es el método de amortización más utilizado mundialmente. Se caracteriza por mantener un **pago constante** durante toda la vida del crédito, donde la proporción entre capital e intereses varía en cada período.

### ¿POR QUÉ SE USA ESTE SISTEMA?
**Ventajas para el deudor:**
- **Predictibilidad**: Cuota fija facilita la planificación financiera
- **Accesibilidad inicial**: Cuotas menores al inicio vs sistema alemán
- **Estabilidad**: No hay sorpresas en el monto a pagar

**Ventajas para el acreedor:**
- **Flujo constante**: Ingresos predecibles para gestión de liquidez
- **Menor riesgo de incumplimiento**: Cuotas estables reducen default
- **Estandarización**: Facilita la comercialización y comparación

### METODOLOGÍA MATEMÁTICA

#### FÓRMULA FUNDAMENTAL
La cuota fija se calcula usando la **fórmula de anualidades**:
```
Cuota = Valor × [r × (1+r)^n] / [(1+r)^n - 1]
```

Donde:
- **Valor**: Monto del crédito
- **r**: Tasa periódica
- **n**: Número de cuotas

#### ¿POR QUÉ ESTA FÓRMULA?
Esta ecuación garantiza que el **valor presente** de todas las cuotas sea exactamente igual al monto del crédito:
```
VP = Cuota/(1+r)¹ + Cuota/(1+r)² + ... + Cuota/(1+r)ⁿ = Valor
```

#### DISTRIBUCIÓN PERÍODO A PERÍODO
En cada período t:
1. **Intereses(t) = Saldo_pendiente(t-1) × tasa_periódica**
2. **Capital(t) = Cuota_fija - Intereses(t)**
3. **Saldo_pendiente(t) = Saldo_pendiente(t-1) - Capital(t)**

### CARACTERÍSTICAS DEL PERFIL DE AMORTIZACIÓN

#### EVOLUCIÓN TEMPORAL
- **Períodos iniciales**: Mayor proporción de intereses, menor de capital
- **Períodos medios**: Proporción equilibrada entre capital e intereses  
- **Períodos finales**: Mayor proporción de capital, menor de intereses

#### IMPLICACIONES PARA PREPAGO
- **Alto riesgo inicial**: Saldos altos hacen atractivo el prepago temprano
- **Incentivo decreciente**: A medida que avanza el tiempo, menor beneficio del prepago
- **Punto de inflexión**: Momento donde capital > intereses (aprox. 60% del plazo)

---

## 🏛️ SISTEMA ALEMÁN: CAPITAL FIJO

### ¿QUÉ ES EL SISTEMA ALEMÁN?
El sistema alemán se caracteriza por **amortizar capital constante** en cada período, mientras que los intereses se calculan sobre el saldo pendiente decreciente. Esto resulta en **cuotas decrecientes** a lo largo del tiempo.

### ¿CUÁNDO SE UTILIZA?
**Aplicaciones típicas:**
- **Créditos comerciales**: Empresas con flujos crecientes en el tiempo
- **Créditos de inversión**: Proyectos con rentabilidad creciente
- **Deudores sofisticados**: Que prefieren mayor amortización inicial

### METODOLOGÍA MATEMÁTICA

#### FÓRMULA FUNDAMENTAL
```
Capital_fijo = Valor / Número_cuotas
Intereses(t) = Saldo_pendiente(t-1) × tasa_periódica
Cuota(t) = Capital_fijo + Intereses(t)
```

#### EVOLUCIÓN DEL SALDO
```
Saldo_pendiente(t) = Valor - (t × Capital_fijo)
```

### CARACTERÍSTICAS DEL PERFIL

#### VENTAJAS
- **Amortización acelerada**: Reduce más rápidamente el riesgo crediticio
- **Menor costo total**: Menos intereses pagados vs sistema francés
- **Transparencia**: Fácil comprensión de la estructura

#### DESVENTAJAS
- **Cuotas iniciales altas**: Mayor carga financiera al inicio
- **Menor accesibilidad**: Requiere mayor capacidad de pago inicial
- **Flujo decreciente**: Puede no ajustarse al perfil de ingresos del deudor

---

## 🇺🇸 SISTEMA AMERICANO: INTERESES PERIÓDICOS

### ¿QUÉ ES EL SISTEMA AMERICANO?
En el sistema americano, el deudor paga **solo intereses** durante la vida del crédito, y **todo el capital** se paga al vencimiento. Es común en productos corporativos y de inversión.

### ¿CUÁNDO ES APROPIADO?
**Casos de uso:**
- **Créditos puente**: Financiación temporal hasta obtener recursos permanentes
- **Proyectos de inversión**: Donde los retornos se concentran al final
- **Gestión de flujo**: Cuando se requiere minimizar pagos periódicos

### METODOLOGÍA MATEMÁTICA

#### FÓRMULAS
```
Intereses_periódicos = Valor × tasa_periódica
Pago_final = Valor + Intereses_periódicos
```

#### PERFIL DE RIESGO
- **Riesgo concentrado**: Todo el capital se recupera al final
- **Riesgo de refinanciación**: El deudor debe conseguir recursos para el pago final
- **Sensibilidad a prepago**: Muy sensible a cambios en tasas de mercado

---

## 🎯 SISTEMA BULLET: PAGO ÚNICO

### ¿QUÉ ES EL SISTEMA BULLET?
El sistema bullet implica un **pago único** al vencimiento que incluye capital e intereses capitalizados. No hay pagos intermedios.

### ¿CUÁNDO SE UTILIZA?
**Aplicaciones específicas:**
- **Inversiones de corto plazo**: CDT, bonos cupón cero
- **Financiación especializada**: Operaciones estructuradas
- **Gestión de liquidez**: Cuando no se requieren flujos intermedios

### METODOLOGÍA MATEMÁTICA

#### CAPITALIZACIÓN COMPUESTA
```
Monto_final = Valor × (1 + tasa_EA)^(plazo_años)
Intereses_totales = Monto_final - Valor
```

#### CARACTERÍSTICAS ESPECIALES
- **Sin flujos intermedios**: Toda la evaluación se concentra al vencimiento
- **Capitalización completa**: Los intereses generan intereses
- **Riesgo binario**: O se paga completo o hay incumplimiento total

---

## 📊 COMPARACIÓN ENTRE SISTEMAS

### IMPACTO EN VALOR PRESENTE
Todos los sistemas, **matemáticamente**, tienen el mismo valor presente cuando se descuentan a la tasa contractual. Sin embargo, difieren en:

#### PERFIL DE RIESGO DE PREPAGO
1. **Francés**: Riesgo alto inicial, decreciente en el tiempo
2. **Alemán**: Riesgo moderado, más estable
3. **Americano**: Riesgo muy alto, constante
4. **Bullet**: Riesgo concentrado al vencimiento

#### DURACIÓN FINANCIERA
- **Francés**: Duración intermedia
- **Alemán**: Menor duración (pagos más tempranos)
- **Americano**: Mayor duración (capital al final)
- **Bullet**: Duración = plazo del crédito

### SELECCIÓN DEL SISTEMA APROPIADO

#### FACTORES DE DECISIÓN
1. **Perfil del deudor**: Capacidad de pago y flujos esperados
2. **Tipo de crédito**: Consumo, comercial, vivienda, inversión
3. **Estrategia del acreedor**: Gestión de riesgo y liquidez
4. **Condiciones de mercado**: Tasas, volatilidad, competencia

#### RECOMENDACIONES ACTUARIALES
- **Créditos masivos**: Sistema francés por estandarización
- **Créditos corporativos**: Sistema alemán o americano según flujos
- **Productos de inversión**: Sistema bullet para simplicidad
- **Gestión de riesgo**: Diversificar sistemas en la cartera

---

## 🔧 INTEGRACIÓN CON ANÁLISIS DE PREPAGO

### ¿CÓMO SE CONECTAN CON LOS MODELOS ESTOCÁSTICOS?
Los flujos generados por cada sistema de amortización son la **base contractual** sobre la cual operan los modelos de prepago:

1. **Input para modelos**: Los cronogramas son la referencia para evaluar prepago
2. **Fechas de evaluación**: Cada fecha de pago es un momento de decisión potencial
3. **Magnitud del incentivo**: El saldo pendiente determina el beneficio del prepago
4. **Perfil temporal**: La distribución de flujos afecta la probabilidad de prepago

### CONSIDERACIONES ESPECIALES POR SISTEMA

#### SISTEMA FRANCÉS
- **Prepago más probable**: En los primeros años por saldos altos
- **Evaluación continua**: En cada fecha de pago
- **Impacto significativo**: Gran diferencia entre flujos originales y ajustados

#### SISTEMA ALEMÁN  
- **Prepago menos probable**: Amortización acelerada reduce incentivos
- **Ventana temporal**: Principalmente en el primer tercio del plazo
- **Impacto moderado**: Menor diferencia vs flujos originales

#### SISTEMA AMERICANO
- **Prepago muy probable**: Saldo constante mantiene incentivo
- **Evaluación crítica**: Especialmente sensible a caídas de tasas
- **Impacto máximo**: Diferencia total entre flujos con y sin prepago

#### SISTEMA BULLET
- **Evaluación especial**: Se generan fechas intermedias artificiales
- **Decisión binaria**: Prepago total o continuación hasta vencimiento
- **Modelado complejo**: Requiere tratamiento especial en simulaciones

Los sistemas de amortización constituyen la base fundamental sobre la cual se construye todo el análisis actuarial de prepago, determinando no solo los flujos contractuales sino también los incentivos económicos que guían las decisiones de los deudores.
