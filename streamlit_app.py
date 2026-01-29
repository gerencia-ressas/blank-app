import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def apply_custom_styles():
    st.markdown("""
        <style>
        <style>
        /* Ocultar la barra de estado de Streamlit (Deploy, etc) */
        header {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Ajustar el padding superior para que no quede un hueco blanco */
        .block-container {
            padding-top: 2rem;
        }
        /* Importar la fuente Outfit */
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

        html, body, [class*="css"], .stMarkdown, p, span {
            font-family: 'Outfit', sans-serif !important;
        }

        /* Estilizar las tarjetas de métricas */
        [data-testid="stMetric"] {
            background-color: white;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 10px 25px -5px rgba(234, 179, 8, 0.1);
        }

        /* Botones con color azul corporativo */
        .stButton>button {
            background-color: #2563EB;
            color: white;
            border-radius: 8px;
            border: none;
            padding: 0.5rem 1rem;
            transition: all 0.3s ease;
        }
        
        .stButton>button:hover {
            background-color: #1E3A8A;
            box-shadow: 0 10px 25px -5px rgba(234, 179, 8, 0.3);
            transform: translateY(-2px);
        }

        /* Estilo para los inputs */
        .stNumberInput, .stSlider {
            border-radius: 8px;
        }
        </style>
    """, unsafe_allow_html=True)

# Configuración de página al inicio absoluto
st.set_page_config(page_title="Simulador AGPE - CREG 174 (2021)", layout="wide")
apply_custom_styles()

HOUR_LABELS = [f"{h}:00" for h in range(24)]

def hourly_consumption_profile(monthly_consumption_kwh: float) -> np.ndarray:
    base = monthly_consumption_kwh / 30.0 / 24.0
    multipliers = np.zeros(24)
    for h in range(24):
        if 0 <= h <= 7: multipliers[h] = 0.35
        elif 8 <= h <= 10: multipliers[h] = 1.15
        elif 11 <= h <= 16: multipliers[h] = 1.65
        elif 17 <= h <= 21: multipliers[h] = 1.30
        elif 22 <= h <= 23: multipliers[h] = 0.55
    
    ruido = np.random.uniform(0.8, 1.2, 24)
    profile = (base * multipliers) * ruido
    if profile.sum() > 0:
        scale = (monthly_consumption_kwh / 30.0) / profile.sum()
        profile = profile * scale
    return profile

def solar_generation_profile(monthly_consumption_kwh: float, percent_comp: float) -> np.ndarray:
    hours = np.arange(24)
    raw = np.sin(np.pi * (hours - 6) / 12.0)
    raw = np.clip(raw, 0, None)
    daily_raw_sum = raw.sum()
    if daily_raw_sum == 0 or percent_comp <= 0:
        return np.zeros(24)
    target_monthly_gen = monthly_consumption_kwh * (percent_comp / 100.0)
    scale = target_monthly_gen / (daily_raw_sum * 30.0)
    gen = raw * scale
    return gen

def settle_hourly(demand: np.ndarray, generation: np.ndarray) -> dict:
    autoconsumo = np.minimum(generation, demand)
    excedente = np.maximum(generation - demand, 0.0)
    importada = np.maximum(demand - generation, 0.0)
    return {
        "demand": demand, "generation": generation,
        "autoconsumo": autoconsumo, "excedente": excedente, "importada": importada,
    }

def billing(monthly_consumption_kwh: float, hourly: dict, CU: float, C: float) -> dict:
    cost_without = monthly_consumption_kwh * CU
    imported_monthly = hourly["importada"].sum() * 30.0
    excedente_monthly = hourly["excedente"].sum() * 30.0
    cost_with = (imported_monthly * CU) - (excedente_monthly * (CU - C))
    ahorro = cost_without - cost_with
    ahorro_pct = (ahorro / cost_without * 100.0) if cost_without > 0 else 0.0
    return {
        "cost_without": cost_without, "cost_with": cost_with,
        "ahorro": ahorro, "ahorro_pct": ahorro_pct,
        "imported_monthly": imported_monthly, "excedente_monthly": excedente_monthly,
        "autoconsumido_monthly": hourly["autoconsumo"].sum() * 30.0,
    }

def render_detailed_billing(bill_data: dict, CU: float, C: float, precio_bolsa: float, hourly_data: dict):
    total_consumo_mensual = bill_data["imported_monthly"] + bill_data["autoconsumido_monthly"]
    total_excedentes_mensual = hourly_data["excedente"].sum() * 30.0
    
    # Excedentes Tipo 1 (hasta el límite de la energía importada)
    excedentes_tipo1 = min(total_excedentes_mensual, bill_data["imported_monthly"])
    # Excedentes Tipo 2 (el remanente)
    excedentes_tipo2 = max(0.0, total_excedentes_mensual - excedentes_tipo1)

    st.markdown("## Resumen Económico Detallado")
    col_empresa, col_cliente = st.columns(2)

    with col_empresa:
        st.markdown("### Empresa de Energía (Lo que aparece en el recibo)")
        imp_red = bill_data["imported_monthly"] * CU
        costo_intercambio_tipo1 = excedentes_tipo1 * C
        credito_excedentes_tipo1 = excedentes_tipo1 * (-CU)
        venta_tipo2 = excedentes_tipo2 * (-precio_bolsa)
        total_factura_empresa = imp_red + costo_intercambio_tipo1 + credito_excedentes_tipo1 + venta_tipo2

        st.markdown(f"- Importación desde la Red: **{imp_red:,.0f} COP**")
        st.markdown(f"- Costo Intercambio Tipo 1: **{costo_intercambio_tipo1:,.0f} COP**")
        st.markdown(f"- Crédito Excedentes Tipo 1: **{credito_excedentes_tipo1:,.0f} COP**")
        st.markdown(f"- Venta Tipo 2: **{venta_tipo2:,.0f} COP**")
        st.markdown(f"**Total Factura:** **{total_factura_empresa:,.0f} COP**")

    with col_cliente:
        st.markdown("### Beneficio Cliente (Valor real generado)")
        ahorro_autoconsumo = bill_data["autoconsumido_monthly"] * CU
        ingreso_excedentes = (excedentes_tipo1 * CU) + (excedentes_tipo2 * precio_bolsa)
        total_beneficio_mensual = ahorro_autoconsumo + ingreso_excedentes - (excedentes_tipo1 * C)

        st.markdown(f"- Ahorro por Autoconsumo: **{ahorro_autoconsumo:,.0f} COP**")
        st.markdown(f"- Ingreso/Ahorro por Excedentes: **{ingreso_excedentes:,.0f} COP**")
        st.markdown(f"**Total Beneficio Mensual:** **{total_beneficio_mensual:,.0f} COP**")


def plot_profiles(df: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["hora"], y=df["consumo_kwh"], name="Consumo (kWh/h)", fill="tozeroy",
        line=dict(color="firebrick"), mode="lines", opacity=0.6
    ))
    fig.add_trace(go.Scatter(
        x=df["hora"], y=df["generacion_kwh"], name="Generación Solar (kWh/h)", fill="tozeroy",
        line=dict(color="goldenrod"), mode="lines", opacity=0.6
    ))
    fig.update_layout(
        title=dict(text="Perfil horario: Consumo vs Generación", x=0.02, y=0.95),
        xaxis_title="Hora",
        yaxis_title="kWh por hora",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=450,
        margin=dict(t=100, b=50, l=50, r=20),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)
def plot_monthly_comparison(df: pd.DataFrame):
    # Cálculos mensuales acumulados
    total_consumo = df["consumo_kwh"].sum() * 30
    total_autoconsumo = df["autoconsumo_kwh"].sum() * 30
    total_excedentes = df["excedente_kwh"].sum() * 30
    
    # Lógica de Excedentes Tipo 1 y Tipo 2 (Simplificada para el gráfico)
    # Tipo 1: Excedentes hasta cubrir el consumo importado
    # Tipo 2: Generación que sobra después de cubrir todo el consumo
    excedente_tipo1 = min(total_excedentes, total_consumo - total_autoconsumo)
    excedente_tipo2 = max(0, total_excedentes - excedente_tipo1)

    fig_monthly = go.Figure()

    # Barra de Consumo (Referencia al lado)
    fig_monthly.add_trace(go.Bar(
        x=["Consumo", "Generación"],
        y=[total_consumo, 0],
        name="Consumo Total",
        marker_color='firebrick',
        offsetgroup=0
    ))

    # Barras Apiladas de Generación
    # 1. Autoconsumo
    fig_monthly.add_trace(go.Bar(
        x=["Consumo", "Generación"],
        y=[0, total_autoconsumo],
        name="Autoconsumo",
        marker_color='#22C55E', # Verde
        offsetgroup=1
    ))

    # 2. Excedentes Tipo 1
    fig_monthly.add_trace(go.Bar(
        x=["Consumo", "Generación"],
        y=[0, excedente_tipo1],
        name="Excedente Tipo 1",
        marker_color='goldenrod',
        offsetgroup=1
    ))

    # 3. Excedentes Tipo 2
    fig_monthly.add_trace(go.Bar(
        x=["Consumo", "Generación"],
        y=[0, excedente_tipo2],
        name="Excedente Tipo 2",
        marker_color='#F59E0B', # Naranja oscuro
        offsetgroup=1
    ))

    fig_monthly.update_layout(
        barmode='stack',
        bargap=0.2,
        title=dict(text="Análisis de Energía Mensual", x=0.02, y=0.95),
        yaxis_title="kWh por mes",
        height=450,
        margin=dict(t=100, b=50, l=50, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_monthly, use_container_width=True)

def main():
    st.markdown('<h1 style="color: #1E3A8A; text-align: center;">Simulador de Facturación de Energía Solar</h1>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([1.2, 1.0, 1.0, 1.0])
    with col1:
        consumo = st.number_input("Consumo mensual (kWh)", min_value=0.0, value=1200.0, format="%.2f")
    with col2:
        percent = st.slider("Compensación solar (%)", 0, 200, 30)
    with col3:
        CU = st.number_input("Tarifa CU (COP/kWh)", min_value=0.0, value=700.0)
    with col4:
        C = st.number_input("Comercialización C (COP/kWh)", min_value=0.0, value=50.0)
    with col4:
        precio_bolsa = st.number_input("Precio de Bolsa (COP/kWh)", min_value=0.0, value=210.0)

    st.divider()

    demand = hourly_consumption_profile(consumo)
    generation = solar_generation_profile(consumo, percent)
    hourly = settle_hourly(demand, generation)
    bill = billing(consumo, hourly, CU, C)
    df = pd.DataFrame({
        "hora": HOUR_LABELS, "consumo_kwh": hourly["demand"],
        "generacion_kwh": hourly["generation"], "autoconsumo_kwh": hourly["autoconsumo"],
        "excedente_kwh": hourly["excedente"], "importada_kwh": hourly["importada"],
    })

    # Sección de Gráficos alineados
    st.subheader("Análisis de Comportamiento")
    col_hourly, col_monthly = st.columns([3, 1], vertical_alignment="top") 

    with col_hourly:
        plot_profiles(df)

    with col_monthly:
        plot_monthly_comparison(df)

    st.divider()

    render_detailed_billing(bill, CU, C, precio_bolsa, hourly)

    st.divider()
    with st.expander("Ver detalle horario"):
        st.subheader("Detalle horario (promedio diario)")
    st.dataframe(df.style.format({
        "consumo_kwh": "{:.3f}",
        "generacion_kwh": "{:.3f}",
        "autoconsumo_kwh": "{:.3f}",
        "excedente_kwh": "{:.3f}",
        "importada_kwh": "{:.3f}",
    }), use_container_width=True)

if __name__ == "__main__":
    main()