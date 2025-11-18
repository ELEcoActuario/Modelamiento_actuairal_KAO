# INTERFACES DE USUARIO: MANUAL TEÓRICO-OPERATIVO

## 🎯 FUNDAMENTO TEÓRICO Y PROPÓSITO

### ¿QUÉ SON LAS INTERFACES DEL SISTEMA?
Las interfaces implementan una **aplicación actuarial profesional** desarrollada en Tkinter que proporciona acceso completo a los modelos estocásticos de valoración de carteras crediticias con análisis de prepago. Están diseñadas bajo principios de **experiencia de usuario (UX)** y **flujo de trabajo actuarial** para guiar al usuario a través de 6 fases secuenciales de análisis.

### ¿POR QUÉ ESTA ARQUITECTURA DE FASES?
El diseño por fases responde a la **metodología actuarial estándar**:

1. **Separación de responsabilidades**: Cada fase tiene un propósito específico y bien definido
2. **Flujo lógico**: Sigue el proceso natural del análisis actuarial
3. **Validación progresiva**: Cada fase valida la anterior antes de continuar
4. **Experiencia guiada**: El usuario no puede perderse en la complejidad
5. **Trazabilidad**: Cada paso es auditable y reproducible

### PRINCIPIO FUNDAMENTAL: INTERFAZ ADAPTATIVA
```
Interfaz = f(Modelo_Seleccionado, Fase_Actual, Estado_Datos)
```

La interfaz se **adapta dinámicamente** según:
- **Modelo estocástico** elegido (Vasicek, Hull-White)
- **Fase actual** del procesamiento (1-6)
- **Estado de los datos** (cargados, procesados, calculados)

---

## 📊 ARQUITECTURA DE FASES: ¿CÓMO FUNCIONA EL FLUJO?

### FASE 1: CARGA Y VALIDACIÓN DE DATOS
**¿Qué hace el usuario?**
- **Selecciona archivo Excel** con datos de créditos y tasas
- **Valida 4 hojas requeridas**: data_credito, data_tasasM, data_tasasLR, CurvaHW
- **Visualiza validaciones** automáticas de estructura
- **Confirma calidad** de datos antes de continuar

**¿Por qué es crítica?**
- **Fundamento sólido**: Todo el análisis depende de datos correctos
- **Detección temprana**: Errores identificados antes del procesamiento
- **Cumplimiento**: Validación de estructura normativa requerida
- **CurvaHW requerida**: Necesaria para calibración Hull-White por crédito

### FASE 2: SELECCIÓN DE MODELO ESTOCÁSTICO
**¿Qué decide el usuario?**
- **Modelo Vasicek**: Para análisis con 100 simulaciones Monte Carlo y calibración por tipo de crédito (Comercial, Consumo, Vivienda)
- **Modelo Hull-White**: Para ajuste perfecto a curva de mercado con 100 simulaciones Monte Carlo y calibración específica por crédito individual

**¿Por qué esta elección es fundamental?**
- **Metodología diferente**: Cada modelo tiene fortalezas específicas
- **Resultados distintos**: Diferentes enfoques para el mismo problema
- **Adaptación de interfaz**: La UI se reconfigura según el modelo elegido
- **Calibración**: Vasicek global por tipo vs Hull-White específica por crédito

### FASE 3: CONFIGURACIÓN Y ANÁLISIS
**¿Qué controla el usuario?**
- **Fecha de corte**: Momento desde el cual se evalúa prepago
- **Diferencial de prepago**: Spread mínimo que incentiva prepago (en puntos porcentuales)
- **Número de simulaciones**: 100 simulaciones por defecto (configurable)
- **Filtros de cartera**: Segmentación por tipo, moneda, amortización
- **Periodicidad de agrupación**: Exacta, Mensual, Trimestral, Semestral, Anual, Bandas SFC
- **Visualización de resultados**: Análisis crédito por crédito con gráficos

**¿Por qué estos parámetros?**
- **Personalización**: Cada análisis tiene contexto específico
- **Sensibilidad**: Pequeños cambios pueden tener gran impacto
- **Exploración**: Permite análisis "what-if" interactivo
- **Guardar para Fase 4**: Selección de créditos específicos para valoración

### FASE 4: VALORACIÓN Y DESCUENTOS
**¿Qué obtiene el usuario?**
- **Valor presente base**: Con curvas libres de riesgo por moneda (COP, USD, UVR)
- **Escenarios estresados**: 6 escenarios normativos SFC
  - Paralelo hacia arriba/abajo
  - Empinamiento/Aplanamiento
  - Corto plazo hacia arriba/abajo
- **Gráficos comparativos**: Curvas de tasas base y estresadas por moneda
- **Tabla de resultados**: VP base y VP estresado por crédito y escenario
- **Transformación normativa**: EA → Short Rate para descuento (FD = exp(-r·t_k))

### FASE 5: ANÁLISIS DE SENSIBILIDAD
**¿Qué analiza el usuario?**
- **Deltas por escenario**: Δ = VP_estresado - VP_base
- **6 escenarios de estrés**: Impacto de cada tipo de shock
- **Ranking de riesgos**: Identificación de mayores exposiciones por crédito
- **Totales consolidados**: Suma de sensibilidades por escenario
- **Exportación**: Resultados para reportes externos

### FASE 6: VALIDACIÓN DE CALIBRACIÓN ⭐ NUEVA
**¿Qué valida el usuario?**
- **Calidad de parámetros calibrados**: R², RMSE, MAE para Vasicek y Hull-White
- **Métricas por modelo**: Validación diferenciada según modelo seleccionado
- **Gráficos comparativos**: Visualización de bondad de ajuste
- **Exportación**: Resultados de validación a Excel

**¿Por qué es fundamental?**
- **Confianza en resultados**: Verificar calidad de calibración MLE
- **Detección de problemas**: Identificar parámetros con mal ajuste
- **Cumplimiento metodológico**: Validación de modelos estocásticos
- **Transparencia**: Auditoría completa del proceso de calibración

---

## 🎯 CARACTERÍSTICAS DISTINTIVAS DEL SISTEMA

### SISTEMA DE CACHÉ INTELIGENTE
**¿Cómo funciona?**
- **Caché por modelo**: Resultados separados para cada modelo estocástico
- **Invalidación automática**: Se limpia cuando cambian parámetros
- **Optimización**: Evita recálculos innecesarios
- **Memoria eficiente**: Gestión automática de recursos

### DETECCIÓN AUTOMÁTICA DE CRÉDITOS BULLET
**¿Qué detecta?**
- **Un solo flujo**: Créditos con pago único al vencimiento
- **Generación de fechas**: Evaluación mensual/anual según plazo
- **Tratamiento especial**: Lógica adaptada para este tipo de crédito

### VALIDACIONES MULTINIVEL
**¿Qué valida?**
- **Estructura de archivos**: Hojas y columnas requeridas
- **Calidad de datos**: Tipos, rangos, consistencia
- **Lógica de negocio**: Fechas coherentes, montos positivos
- **Integridad referencial**: Consistencia entre hojas

### INTERFAZ ADAPTATIVA
**¿Cómo se adapta?**
- **Según modelo**: Diferentes opciones y parámetros
- **Según fase**: Controles relevantes para cada etapa
- **Según datos**: Habilitación/deshabilitación dinámica
- **Según estado**: Feedback visual del progreso

---

## 📈 EXPERIENCIA DE USUARIO: ¿QUÉ VE EL ACTUARIO?

### NAVEGACIÓN INTUITIVA
**Elementos clave:**
- **Barra de progreso**: Visualización clara de la fase actual
- **Botones contextuales**: Solo acciones válidas habilitadas
- **Mensajes informativos**: Guía constante del proceso
- **Validación en tiempo real**: Feedback inmediato de errores

### VISUALIZACIÓN PROFESIONAL
**Componentes:**
- **Tablas interactivas**: Exploración detallada de datos
- **Gráficos dinámicos**: Visualización de resultados y tendencias
- **Paneles de control**: Ajuste de parámetros en tiempo real
- **Reportes integrados**: Síntesis ejecutiva automática

### GESTIÓN DE ESTADO ROBUSTO
**Características:**
- **Persistencia**: Estado mantenido durante toda la sesión
- **Recuperación**: Manejo graceful de errores
- **Logging**: Trazabilidad completa de acciones
- **Auditoría**: Registro de decisiones y parámetros

---

## 🔧 INTEGRACIÓN TÉCNICA

### ARQUITECTURA MVC
**Separación clara:**
- **Modelo**: Lógica de negocio en orquestador y motores
- **Vista**: Interfaces Tkinter especializadas por fase
- **Controlador**: Gestión de eventos y flujo entre fases

### COMUNICACIÓN ENTRE COMPONENTES
**Patrones implementados:**
- **Observer**: Notificación de cambios de estado
- **Command**: Encapsulación de acciones del usuario
- **Strategy**: Diferentes comportamientos según modelo
- **Factory**: Creación dinámica de componentes

### MANEJO DE ERRORES
**Estrategia robusta:**
- **Try-catch comprehensivo**: Captura de excepciones
- **Mensajes informativos**: Explicación clara de errores
- **Recuperación graceful**: Vuelta a estado estable
- **Logging detallado**: Información para diagnóstico

---

## 🎯 VALOR PARA EL ACTUARIO

### PRODUCTIVIDAD
- **Flujo guiado**: Reduce tiempo de aprendizaje
- **Automatización**: Elimina tareas repetitivas
- **Validaciones**: Previene errores costosos
- **Reutilización**: Configuraciones guardadas

### PRECISIÓN
- **Metodologías estándar**: Implementación correcta de modelos
- **Validaciones múltiples**: Verificación en cada paso
- **Trazabilidad**: Auditoría completa del proceso
- **Consistencia**: Resultados reproducibles

### FLEXIBILIDAD
- **Múltiples modelos**: Comparación de enfoques
- **Parametrización**: Adaptación a diferentes contextos
- **Exportación**: Integración con otros sistemas
- **Escalabilidad**: Manejo de carteras grandes

Las interfaces proporcionan una experiencia profesional completa que combina rigor actuarial con usabilidad moderna, permitiendo análisis sofisticados de manera accesible y eficiente.
