import pandas as pd
from dateutil.relativedelta import relativedelta
import logging

# Configurar logger para este módulo
logger = logging.getLogger(__name__)

def generar_flujo_frances(datos_credito: dict) -> pd.DataFrame:
    logger.info(f"🇫🇷 Generando flujo francés para crédito ID: {datos_credito.get('ID_producto', 'N/A')}")
    """
    Genera los flujos de caja para un crédito bajo el sistema Francés.
    Cuotas fijas, con abono creciente a capital y decreciente en intereses.
    Cumple con trazabilidad exigida por el Capítulo 31 del SIAR.
    """
    # --- Validación estructural ---
    campos_requeridos = ["Valor", "Tasa", "Numero_Cuotas", "Fecha_Desembolso", "Periodicidad_Pago"]
    for campo in campos_requeridos:
        if campo not in datos_credito or pd.isna(datos_credito[campo]):
            logger.error(f"❌ Campo obligatorio faltante: {campo}")
            raise ValueError(f"Falta el campo obligatorio: {campo}")

    try:
        valor = float(datos_credito["Valor"])
        tasa_ea = float(datos_credito["Tasa"])
        numero_cuotas = int(datos_credito["Numero_Cuotas"])
        fecha_inicio = pd.to_datetime(datos_credito["Fecha_Desembolso"], format='%d/%m/%Y')
        periodicidad = datos_credito["Periodicidad_Pago"]
        logger.debug(f"💰 Valor: {valor:,.2f}, Tasa: {tasa_ea:.2f}%, Cuotas: {numero_cuotas}, Periodicidad: {periodicidad}")
    except Exception as e:
        logger.error(f"❌ Error en tipos de datos: {e}")
        raise ValueError(f"Error en los tipos de datos del crédito: {e}")

    if valor <= 0 or tasa_ea < 0 or numero_cuotas <= 0:
        logger.error(f"❌ Valores inválidos: Valor={valor}, Tasa={tasa_ea}, Cuotas={numero_cuotas}")
        raise ValueError("Valor, tasa y número de cuotas deben ser positivos.")

    # --- Conversión de tasa efectiva anual a tasa periódica ---
    periodos_map = {
        "Quincenal": 24, "Mensual": 12, "Bimestral": 6,
        "Trimestral": 4, "Semestral": 2, "Anual": 1
    }
    if periodicidad not in periodos_map:
        logger.error(f"❌ Periodicidad no válida: {periodicidad}")
        raise ValueError(f"Periodicidad no válida: {periodicidad}")

    frecuencia = periodos_map[periodicidad]
    meses_por_periodo = 12 // frecuencia if periodicidad != "Quincenal" else 0.5
    tasa_periodica = (1 + tasa_ea)**(1 / frecuencia) - 1
    logger.debug(f"📊 Tasa periódica: {tasa_periodica*100:.4f}%")

    # --- Cálculo de cuota fija ---
    cuota_fija = valor * (tasa_periodica * (1 + tasa_periodica)**numero_cuotas) / ((1 + tasa_periodica)**numero_cuotas - 1)
    logger.debug(f"💳 Cuota fija calculada: {cuota_fija:,.2f}")

    # --- Simulación de flujo ---
    flujos = []
    saldo_pendiente = valor
    fecha_pago = fecha_inicio

    for _ in range(numero_cuotas):
        intereses = saldo_pendiente * tasa_periodica
        abono_capital = cuota_fija - intereses
        saldo_pendiente -= abono_capital

        if periodicidad == "Quincenal":
            fecha_pago += relativedelta(days=15)
        else:
            fecha_pago += relativedelta(months=meses_por_periodo)

        flujos.append({
            "Fecha_Pago": fecha_pago,
            "Capital": round(abono_capital, 2),
            "Intereses": round(intereses, 2),
            "Flujo_Total": round(cuota_fija, 2),
            "Saldo_Pendiente": round(max(saldo_pendiente, 0), 2)
        })

    # --- Resultado final ---
    df_resultado = pd.DataFrame(flujos)
    logger.info(f"✅ Flujo francés generado: {len(flujos)} cuotas, Cuota fija: {cuota_fija:,.2f}")
    logger.debug(f"📊 Total capital: {valor:,.2f}, Total intereses: {sum(f['Intereses'] for f in flujos):,.2f}")
    return df_resultado[["Fecha_Pago", "Capital", "Intereses", "Flujo_Total", "Saldo_Pendiente"]]
