# 🏦 Sistema de Valoración Actuarial con Análisis de Prepago

Sistema profesional de valoración de carteras crediticias implementando modelos estocásticos Vasicek y Hull-White para análisis de riesgo de prepago.

## 📋 Características Principales

- **Modelos Estocásticos**: Vasicek y Hull-White
- **6 Fases de Análisis**: Desde carga de datos hasta validación de calibración
- **Cumplimiento Normativo**: Escenarios SFC (Superintendencia Financiera de Colombia)
- **Validación**: Métricas R², RMSE, MAE
- **Interfaz GUI**: Tkinter profesional

## 🚀 Instalación

```bash
# Clonar repositorio
git clone https://github.com/ELEcoActuario/Modelamiento_actuairal_KAO.git

# Instalar dependencias
pip install pandas numpy scipy matplotlib tkcalendar openpyxl

# Ejecutar
python main.py
```

## 📖 Documentación

- [Manual de Usuario](MANUAL_USUARIO.md) - Guía completa paso a paso
- [Arquitectura de Interfaces](interfaces/interfaces.md) - 6 fases del sistema
- [Controladores](motores/controladores/controladores.md) - Lógica de negocio

## 🎯 Estructura del Proyecto

```
proyecto/
├── main.py                    # Punto de entrada
├── interfaces/                # GUI (6 fases)
├── motores/                   # Lógica de cálculo
│   ├── vasicek/              # Modelo Vasicek
│   ├── hull_white/           # Modelo Hull-White
│   ├── amortizacion/         # 4 sistemas de amortización
│   ├── descuentos/           # Valoración y escenarios SFC
│   └── validacion/           # Validación de calibración
└── utils/                    # Utilidades comunes
```

## 💡 Uso Básico

1. **Fase 1**: Cargar archivo Excel con datos de créditos
2. **Fase 2**: Seleccionar modelo (Vasicek o Hull-White)
3. **Fase 3**: Configurar simulación y analizar resultados
4. **Fase 4**: Calcular valores presentes (base + 6 escenarios SFC)
5. **Fase 5**: Análisis de sensibilidad (deltas)
6. **Fase 6**: Validar calibración (R², RMSE, MAE)

## 📊 Modelos Implementados

### Vasicek
- Calibración MLE por tipo de crédito
- 100 simulaciones Monte Carlo
- Reversión a la media

### Hull-White
- Calibración específica por crédito
- Ajuste perfecto a curva de mercado
- Función θ(t) dependiente del tiempo

## 🔬 Validación

Sistema de validación con métricas estándar:
- **R²**: Coeficiente de determinación
- **RMSE**: Error cuadrático medio
- **MAE**: Error absoluto medio

## 📧 Contacto

Para consultas o colaboraciones, contactar al autor.

---

**Desarrollado por ELEcoActuario** | Python 3.8+ | 2024
