import pandas as pd
from dateutil.relativedelta import relativedelta
import logging

# Configurar logger para este módulo
logger = logging.getLogger(__name__)

def generar_flujo_americano(datos_credito: dict) -> pd.DataFrame:
    logger.info(f"🇺🇸 Generando flujo americano para crédito ID: {datos_credito.get('ID_producto', 'N/A')}")
    """
    Genera los flujos de caja para un crédito tipo Americano.
    Capital se paga completamente al vencimiento. Intereses son constantes.
    Cumple con trazabilidad del Capítulo 31 del SIAR.
    """
    # --- Validación estructural ---
    campos_requeridos = ["Valor", "Tasa", "Numero_Cuotas", "Fecha_Desembolso", "Fecha_Vencimiento", "Periodicidad_Pago"]
    for campo in campos_requeridos:
        if campo not in datos_credito or pd.isna(datos_credito[campo]):
            raise ValueError(f"Falta el campo obligatorio: {campo}")

    try:
        monto = float(datos_credito["Valor"])  # Usar "Valor" como monto
        # Convención del proyecto: 'Tasa' en DECIMAL (p. ej., 0.12 = 12%)
        tasa_anual = float(datos_credito["Tasa"])  # ya en decimal
        fecha_desembolso = pd.to_datetime(datos_credito["Fecha_Desembolso"])
        numero_cuotas = int(datos_credito["Numero_Cuotas"])
        periodicidad = datos_credito["Periodicidad_Pago"]
        
        logger.debug(f"💰 Monto: {monto:,.2f}, Tasa EA: {tasa_anual:.6f} (decimal), Cuotas: {numero_cuotas}, Periodicidad: {periodicidad}")
    except Exception as e:
        raise ValueError(f"Error en los tipos de datos del crédito: {e}")

    if monto <= 0 or tasa_anual < 0 or numero_cuotas <= 0:
        raise ValueError("Valor, tasa y número de cuotas deben ser positivos")

    # --- Cálculo de tasa periódica ---
    periodos_map = {
        "Quincenal": 24, "Mensual": 12, "Bimestral": 6,
        "Trimestral": 4, "Semestral": 2, "Anual": 1
    }

    if periodicidad not in periodos_map:
        logger.error(f"❌ Periodicidad no válida: {periodicidad}")
        raise ValueError(f"Periodicidad no válida: {periodicidad}")

    n_periodos = periodos_map[periodicidad]
    # Conversión efectiva anual -> periódica
    tasa_periodica = (1 + tasa_anual) ** (1 / n_periodos) - 1
    intereses_constantes = round(monto * tasa_periodica, 2)
    saldo_pendiente = monto
    fecha_pago = fecha_desembolso
    flujos = []
    
    logger.debug(f"📊 Tasa periódica: {tasa_periodica*100:.4f}%, Intereses constantes: {intereses_constantes:,.2f}")

    for i in range(numero_cuotas):
        cuota_num = i + 1
        if periodicidad == "Quincenal":
            fecha_pago += relativedelta(days=15)
        else:
            fecha_pago += relativedelta(months=int(12 / n_periodos))

        if i == numero_cuotas - 1:  # Última cuota
            capital = monto
            flujo_total = capital + intereses_constantes
            logger.debug(f"💳 Cuota final {cuota_num}: Capital={capital:,.2f}, Intereses={intereses_constantes:,.2f}")
        else:
            capital = 0
            flujo_total = intereses_constantes
            if cuota_num <= 3 or cuota_num % 10 == 0:
                logger.debug(f"💳 Cuota {cuota_num}: Solo intereses={intereses_constantes:,.2f}")

        flujos.append({
            "Fecha_Pago": fecha_pago,
            "Capital": round(capital, 2),
            "Intereses": intereses_constantes,
            "Flujo_Total": round(flujo_total, 2),
            "Saldo_Pendiente": round(saldo_pendiente, 2) if i < numero_cuotas - 1 else 0.00
        })

    df_resultado = pd.DataFrame(flujos)
    logger.info(f"✅ Flujo americano generado: {len(flujos)} cuotas, Capital final: {monto:,.2f}")
    logger.debug(f"📊 Total intereses: {intereses_constantes * numero_cuotas:,.2f}")
    
    return df_resultado[["Fecha_Pago", "Capital", "Intereses", "Flujo_Total", "Saldo_Pendiente"]]
