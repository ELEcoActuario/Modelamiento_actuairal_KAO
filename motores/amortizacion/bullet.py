import pandas as pd
import logging

# Configurar logger para este módulo
logger = logging.getLogger(__name__)

def generar_flujo_bullet(datos_credito: dict) -> pd.DataFrame:
    logger.info(f"🎯 Generando flujo bullet para crédito ID: {datos_credito.get('ID_producto', 'N/A')}")
    """
    Genera los flujos de caja para un producto tipo Bullet.
    Capital e intereses se pagan en una sola cuota al vencimiento.
    Cumple con trazabilidad exigida por el Capítulo 31 del SIAR.
    """
    # --- Validación estructural ---
    campos_requeridos = ["Valor", "Tasa", "Fecha_Desembolso", "Fecha_Vencimiento"]
    for campo in campos_requeridos:
        if campo not in datos_credito or pd.isna(datos_credito[campo]):
            logger.error(f"❌ Campo obligatorio faltante: {campo}")
            raise ValueError(f"Falta el campo obligatorio: {campo}")

    try:
        valor = float(datos_credito["Valor"])
        tasa_ea = float(datos_credito["Tasa"])
        fecha_desembolso = pd.to_datetime(datos_credito["Fecha_Desembolso"], format='%d/%m/%Y')
        fecha_vencimiento = pd.to_datetime(datos_credito["Fecha_Vencimiento"], format='%d/%m/%Y')
        logger.debug(f"💰 Valor: {valor:,.2f}, Tasa: {tasa_ea:.2f}%, Desembolso: {fecha_desembolso.strftime('%d/%m/%Y')}, Vencimiento: {fecha_vencimiento.strftime('%d/%m/%Y')}")
    except Exception as e:
        logger.error(f"❌ Error en tipos de datos: {e}")
        raise ValueError(f"Error en los tipos de datos del crédito: {e}")

    if valor <= 0 or tasa_ea < 0:
        logger.error(f"❌ Valores inválidos: Valor={valor}, Tasa={tasa_ea}")
        raise ValueError("El valor del crédito debe ser positivo y la tasa no negativa.")

    if fecha_vencimiento <= fecha_desembolso:
        logger.error(f"❌ Fechas inválidas: Vencimiento {fecha_vencimiento} <= Desembolso {fecha_desembolso}")
        raise ValueError("La fecha de vencimiento debe ser posterior a la fecha de desembolso.")

    # --- Cálculo del plazo y monto final ---
    plazo_dias = (fecha_vencimiento - fecha_desembolso).days
    plazo_anos = plazo_dias / 365.0
    monto_final = valor * (1 + tasa_ea)**plazo_anos
    intereses_totales = monto_final - valor
    logger.debug(f"📊 Plazo: {plazo_dias} días ({plazo_anos:.2f} años), Monto final: {monto_final:,.2f}, Intereses: {intereses_totales:,.2f}")

    # --- Generar flujo único ---
    flujos = [{
        "Fecha_Pago": fecha_vencimiento,
        "Capital": round(valor, 2),
        "Intereses": round(intereses_totales, 2),
        "Flujo_Total": round(monto_final, 2),
        "Saldo_Pendiente": 0.00
    }]

    df_resultado = pd.DataFrame(flujos)
    logger.info(f"✅ Flujo bullet generado: Pago único de {monto_final:,.2f} el {fecha_vencimiento.strftime('%d/%m/%Y')}")
    return df_resultado[["Fecha_Pago", "Capital", "Intereses", "Flujo_Total", "Saldo_Pendiente"]]
