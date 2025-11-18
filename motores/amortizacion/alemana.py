import pandas as pd
from dateutil.relativedelta import relativedelta
import logging

# Configurar logger para este módulo
logger = logging.getLogger(__name__)

def generar_flujo_aleman(datos_credito: dict) -> pd.DataFrame:
    logger.info(f"🏦 Generando flujo alemán para crédito ID: {datos_credito.get('ID_producto', 'N/A')}")
    """
    Genera los flujos de caja para un crédito bajo el sistema Alemán.
    Cumple con trazabilidad exigida por el Capítulo 31 del SIAR.
    """
    # --- Validación estructural ---
    campos_requeridos = ["Valor", "Tasa", "Numero_Cuotas", "Fecha_Desembolso", "Periodicidad_Pago"]
    for campo in campos_requeridos:
        if campo not in datos_credito or pd.isna(datos_credito[campo]):
            raise ValueError(f"Falta el campo obligatorio: {campo}")

    try:
        monto = float(datos_credito["Valor"])  # Usar "Valor" en lugar de "Monto"
        # Convención del proyecto: 'Tasa' en DECIMAL (p. ej., 0.12 = 12%)
        tasa_anual = float(datos_credito["Tasa"])  # ya en decimal
        fecha_desembolso = pd.to_datetime(datos_credito["Fecha_Desembolso"])
        numero_cuotas = int(datos_credito["Numero_Cuotas"])
        periodicidad = datos_credito["Periodicidad_Pago"]
        
        logger.debug(f"💰 Monto: {monto:,.2f}, Tasa EA: {tasa_anual:.6f} (decimal), Cuotas: {numero_cuotas}, Periodicidad: {periodicidad}")
    except Exception as e:
        raise ValueError(f"Error en los tipos de datos del crédito: {e}")

    if monto <= 0 or tasa_anual < 0 or numero_cuotas <= 0:
        raise ValueError("Monto, tasa y número de cuotas deben ser positivos")

    # --- Conversión de tasa efectiva anual a tasa periódica ---
    if periodicidad == "Quincenal":
        n_periodos = 24
    elif periodicidad == "Mensual":
        n_periodos = 12
    elif periodicidad == "Bimestral":
        n_periodos = 6
    elif periodicidad == "Trimestral":
        n_periodos = 4
    elif periodicidad == "Semestral":
        n_periodos = 2
    elif periodicidad == "Anual":
        n_periodos = 1
    else:
        logger.error(f"❌ Periodicidad no válida: {periodicidad}")
        raise ValueError(f"Periodicidad no válida: {periodicidad}")
    
    logger.debug(f"📊 Períodos por año: {n_periodos}")

    # Conversión efectiva anual -> periódica
    tasa_periodica = (1 + tasa_anual) ** (1 / n_periodos) - 1
    abono_capital_fijo = monto / numero_cuotas
    saldo_pendiente = monto
    fecha_pago = fecha_desembolso
    flujos = []
    
    logger.debug(f"📊 Tasa periódica: {tasa_periodica*100:.4f}%, Abono capital fijo: {abono_capital_fijo:,.2f}")

    for cuota_num in range(1, numero_cuotas + 1):
        intereses = round(saldo_pendiente * tasa_periodica, 2)
        saldo_pendiente -= abono_capital_fijo
        saldo_pendiente = max(0, round(saldo_pendiente, 2))  # Evita valores negativos por redondeo
        
        if cuota_num <= 3 or cuota_num % 10 == 0 or cuota_num > numero_cuotas - 3:
            logger.debug(f"💳 Cuota {cuota_num}: Capital={abono_capital_fijo:,.2f}, Intereses={intereses:,.2f}, Saldo={saldo_pendiente:,.2f}")

        # Ajuste de fecha
        if periodicidad == "Quincenal":
            fecha_pago += relativedelta(days=15)
        else:
            fecha_pago += relativedelta(months=int(12 / n_periodos))

        flujo_total = abono_capital_fijo + intereses

        flujos.append({
            "Fecha_Pago": fecha_pago,
            "Capital": abono_capital_fijo,
            "Intereses": intereses,
            "Flujo_Total": round(flujo_total, 2),
            "Saldo_Pendiente": saldo_pendiente
        })

    df_resultado = pd.DataFrame(flujos)
    logger.info(f"✅ Flujo alemán generado: {len(flujos)} cuotas, Total capital: {monto:,.2f}")
    logger.debug(f"📊 Flujo total acumulado: {df_resultado['Flujo_Total'].sum():,.2f}")
    
    return df_resultado[["Fecha_Pago", "Capital", "Intereses", "Flujo_Total", "Saldo_Pendiente"]]
