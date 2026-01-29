import streamlit as st

def apply_custom_styles():
    st.markdown("""
        <style>
        /* Importar la fuente Outfit */
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

        html, body, [class*="css"], .stMarkdown, p, span {
            font-family: 'Outfit', sans-serif !important;
        }

        /* Estilizar las tarjetas de métricas para que parezcan Shadcn Cards */
        [data-testid="stMetric"] {
            background-color: white;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 10px 25px -5px rgba(234, 179, 8, 0.1); /* solar shadow suave */
        }

        /* Botones con tu color solar.blue */
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

# Llamar a la función al inicio
apply_custom_styles()

import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Simulador AGPE - CREG 174 (2021)", layout="wide")

HOUR_LABELS = [f"{h}:00" for h in range(24)]

def hourly_consumption_profile(monthly_consumption_kwh: float) -> np.ndarray:
    """Genera un perfil horario de consumo (kWh) a partir del consumo mensual."""
    base = monthly_consumption_kwh / 30.0 / 24.0
    multipliers = np.zeros(24)
    for h in range(24):
        if 0 <= h <= 7:
            multipliers[h] = 0.35
        elif 8 <= h <= 10:
            multipliers[h] = 1.15
        elif 11 <= h <= 16:
            multipliers[h] = 1.65
        elif 17 <= h <= 21:
            multipliers[h] = 1.30
        elif 22 <= h <= 23:
            multipliers[h] = 0.55
   # --- CAMBIO AQUÍ: Generar ruido entre 0.8 y 1.2 para las 24 horas ---
    ruido = np.random.uniform(0.8, 1.2, 24)
    profile = (base * multipliers) * ruido
    # ---
    # Ajuste para que la suma diaria coincida con monthly/30
    if profile.sum() > 0:
        scale = (monthly_consumption_kwh / 30.0) / profile.sum()
        profile = profile * scale
    return profile

def solar_generation_profile(monthly_consumption_kwh: float, percent_comp: float) -> np.ndarray:
    """Simula curva solar diaria (kWh por hora) escalada para lograr el % de compensación solicitado."""
    hours = np.arange(24)
    raw = np.sin(np.pi * (hours - 6) / 12.0)  # seno desde 6 hasta 18h
    raw = np.clip(raw, 0, None)
    daily_raw_sum = raw.sum()
    if daily_raw_sum == 0 or percent_comp <= 0:
        return np.zeros(24)
    # Queremos que la energía mensual generada == percent_comp% * consumo mensual
    target_monthly_gen = monthly_consumption_kwh * (percent_comp / 100.0)
    # factor que convierte raw (unidad arbitraria por día) en kWh por hora
    scale = target_monthly_gen / (daily_raw_sum * 30.0)
    gen = raw * scale
    return gen

def settle_hourly(demand: np.ndarray, generation: np.ndarray) -> dict:
    """Calcula autoconsumo, excedentes e importaciones por hora."""
    autoconsumo = np.minimum(generation, demand)
    excedente = np.maximum(generation - demand, 0.0)
    importada = np.maximum(demand - generation, 0.0)
    return {
        "demand": demand,
        "generation": generation,
        "autoconsumo": autoconsumo,
        "excedente": excedente,
        "importada": importada,
    }

def billing(monthly_consumption_kwh: float, hourly: dict, CU: float, C: float) -> dict:
    """Calcula la facturación según la fórmula provista."""
    cost_without = monthly_consumption_kwh * CU
    imported_monthly = hourly["importada"].sum() * 30.0
    excedente_monthly = hourly["excedente"].sum() * 30.0
    cost_with = (imported_monthly * CU) - (excedente_monthly * (CU - C))
    ahorro = cost_without - cost_with
    ahorro_pct = (ahorro / cost_without * 100.0) if cost_without > 0 else 0.0
    return {
        "cost_without": cost_without,
        "cost_with": cost_with,
        "ahorro": ahorro,
        "ahorro_pct": ahorro_pct,
        "imported_monthly": imported_monthly,
        "excedente_monthly": excedente_monthly,
        "autoconsumido_monthly": hourly["autoconsumo"].sum() * 30.0,
    }

def make_dataframe(hourly: dict) -> pd.DataFrame:
    df = pd.DataFrame({
        "hora": HOUR_LABELS,
        "consumo_kwh": hourly["demand"],
        "generacion_kwh": hourly["generation"],
        "autoconsumo_kwh": hourly["autoconsumo"],
        "excedente_kwh": hourly["excedente"],
        "importada_kwh": hourly["importada"],
    })
    return df

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
        title="Perfil horario: Consumo vs Generación (promedio diario)",
        xaxis_title="Hora",
        yaxis_title="kWh por hora",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_monthly_comparison(df: pd.DataFrame):
    fig_monthly = go.Figure()

    fig_monthly.add_trace(go.Bar(
        x=df["hora"],
        y=df["consumo_kwh"] * 30,
        name="Consumo Mensual (kWh)",
        marker_color='firebrick',
        opacity=0.7
    ))

    fig_monthly.add_trace(go.Bar(
        x=df["hora"],
        y=df["generacion_kwh"] * 30,
        name="Generación Mensual (kWh)",
        marker_color='goldenrod',
        opacity=0.7
    ))

    fig_monthly.update_layout(
        barmode='overlay',
        title="Comportamiento Mensual: Consumo vs Generación",
        xaxis_title="Hora",
        yaxis_title="kWh por mes",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_monthly, use_container_width=True)

def main():
    st.markdown('<h1 style="color: #1E3A8A; text-align: center;">Simulador de Energía Solar</h1>', unsafe_allow_html=True)
    st.title("Simulador AGPE — Resolución CREG 174 (2021)")
    st.markdown("Simula facturación hora a hora para un sistema de autogeneración a pequeña escala (AGPE).")

    col1, col2, col3, col4 = st.columns([1.2, 1.0, 1.0, 1.0])
    with col1:
        consumo = st.number_input("Consumo mensual (kWh)", min_value=0.0, value=1200.0, step=10.0, format="%.2f")
    with col2:
        percent = st.slider("Porcentaje de compensación solar (%)", min_value=0, max_value=200, value=30, step=1)
    with col3:
        CU = st.number_input("Tarifa Costo Unitario (COP/kWh)", min_value=0.0, value=700.0, step=10.0, format="%.2f")
    with col4:
        C = st.number_input("Costo Comercialización C (COP/kWh)", min_value=0.0, value=50.0, step=1.0, format="%.2f")

    st.divider()

    demand = hourly_consumption_profile(consumo)
    generation = solar_generation_profile(consumo, percent)
    hourly = settle_hourly(demand, generation)
    bill = billing(consumo, hourly, CU, C)
    df = make_dataframe(hourly)

    # Visualizaciones y métricas
    left, right = st.columns([2, 1])
    with left:
        plot_profiles(df)
    with right:
        st.subheader("Resumen económico")
        st.metric("Costo sin proyecto (COP/mes)", f"{bill['cost_without']:,.0f}")
        st.metric("Costo con proyecto (COP/mes)", f"{bill['cost_with']:,.0f}")
        st.metric("Ahorro (COP/mes)", f"{bill['ahorro']:,.0f}", delta=f"{bill['ahorro_pct']:.2f}%")
        st.markdown("### Energía (kWh / mes)")
        st.write(f"- Autoconsumida: {bill['autoconsumido_monthly']:.2f} kWh")
        st.write(f"- Exportada (excedentes): {bill['excedente_monthly']:.2f} kWh")
        st.write(f"- Importada: {bill['imported_monthly']:.2f} kWh")

    st.divider()
    st.subheader("Comportamiento Mensual Detallado")
    plot_monthly_comparison(df)

    st.divider()
    st.subheader("Detalle horario (promedio diario)")
    st.dataframe(df.style.format({
        "consumo_kwh": "{:.3f}",
        "generacion_kwh": "{:.3f}",
        "autoconsumo_kwh": "{:.3f}",
        "excedente_kwh": "{:.3f}",
        "importada_kwh": "{:.3f}",
    }), use_container_width=True)

    st.caption("Notas: La generación solar es una curva seno simplificada entre 6:00 y 18:00, escalada para alcanzar el porcentaje de compensación mensual indicado. La liquidación horaria respeta la lógica de autoconsumo (min) y excedentes (+).")

if __name__ == "__main__":
    main()

