import pandas as pd
from typing import List, Optional, Dict
from motores.bandas.utils_bandas import asignar_bandas_sfc

def aplicar_filtros(df_creditos, valores_filtro):
    """
    Aplica los filtros de amortización, producto y moneda sobre los créditos.
    """
    df_filtrado = df_creditos.copy()
    if valores_filtro["amortizacion"] != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Tipo_Amortizacion"] == valores_filtro["amortizacion"]]
    if valores_filtro["producto"] != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Tipo_producto"] == valores_filtro["producto"]]
    if valores_filtro["moneda"] != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Moneda"] == valores_filtro["moneda"]]
    return df_filtrado

def combinar_flujos_por_ids(portafolios: Dict[str, pd.DataFrame], ids: List[str]) -> pd.DataFrame:
    """
    Une los DataFrames de flujos asociados a los IDs seleccionados.
    """
    return pd.concat(
        [portafolios[id_] for id_ in ids if id_ in portafolios and portafolios[id_] is not None],
        ignore_index=True
    )

def extraer_flujos_individuales(
    portafolios: Dict[str, Dict[str, Optional[pd.DataFrame]]],
    id_producto: str,
    fecha_corte: Optional[pd.Timestamp] = None,
    fecha_corte_modelo: Optional[pd.Timestamp] = None
) -> tuple[
    Optional[pd.DataFrame],
    List[pd.DataFrame],
    List[pd.DataFrame]
]:
    """
    Extrae los flujos asociados a un producto individual:
    - flujo contractual (único)
    - lista de flujos base con prepago
    - lista de flujos estresados con prepago

    También aplica bandas SFC si se proporciona la fecha de corte.
    Filtra los flujos de prepago base y estresado desde la fecha de corte.
    """
    flujo_original = portafolios.get("originales", {}).get(id_producto)
    lista_base = portafolios.get("analisis", {}).get(id_producto, [])
    lista_estresado = portafolios.get("estresados", {}).get(id_producto, [])

    if fecha_corte is not None:
        fecha_corte = pd.to_datetime(fecha_corte)
        
        # Usar fecha_corte_modelo para bandas SFC si está disponible, sino usar fecha_corte
        fecha_bandas = fecha_corte_modelo if fecha_corte_modelo is not None else fecha_corte

        if isinstance(flujo_original, pd.DataFrame):
            flujo_original = flujo_original[flujo_original["Fecha_Pago"] >= fecha_corte].copy()
            flujo_original = asignar_bandas_sfc(flujo_original, fecha_bandas)

        lista_base = [
            asignar_bandas_sfc(df[df["Fecha_Pago"] >= fecha_corte].copy(), fecha_bandas)
            for df in lista_base if isinstance(df, pd.DataFrame) and not df.empty
        ]

        lista_estresado = [
            asignar_bandas_sfc(df[df["Fecha_Pago"] >= fecha_corte].copy(), fecha_bandas)
            for df in lista_estresado if isinstance(df, pd.DataFrame) and not df.empty
        ]

    return flujo_original, lista_base, lista_estresado