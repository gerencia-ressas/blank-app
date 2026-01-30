import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from PIL import Image
import os

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA (Debe ser la primera línea de Streamlit)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Simulador AGPE - CREG 174 (2021)", layout="wide")

# -----------------------------------------------------------------------------
# 2. ESTILOS CSS
# -----------------------------------------------------------------------------
def apply_custom_styles():
    st.markdown("""
        <style>
     
        /* Ocultar elementos default */
        header {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        .block-container {
            padding-top: 0rem;
            max-width: 1200px;
        }

        /* --- ESTILO PARA MÉTRICAS NORMALES (Abajo en el reporte) --- */
        /* Estas seguirán siendo blancas con texto negro */
        [data-testid="stMetric"] {
            background-color: white;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
}
        </style>
    """, unsafe_allow_html=True)

apply_custom_styles()

# -----------------------------------------------------------------------------
# 3. LÓGICA DE CÁLCULO
# -----------------------------------------------------------------------------
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

def billing(monthly_consumption_kwh: float, hourly: dict, CU: float, C: float, precio_bolsa: float) -> dict:
    autoconsumo_mes = hourly["autoconsumo"].sum() * 30.0
    excedente_total_mes = hourly["excedente"].sum() * 30.0
    importada_mes = hourly["importada"].sum() * 30.0
    
    exc_tipo1 = min(excedente_total_mes, importada_mes)
    exc_tipo2 = max(0, excedente_total_mes - importada_mes)
    
    costo_sin_proyecto = monthly_consumption_kwh * CU
    
    valor_importada = importada_mes * CU
    costo_intercambio_t1 = exc_tipo1 * C
    credito_t1 = exc_tipo1 * -CU
    credito_t2 = exc_tipo2 * -precio_bolsa
    
    costo_con_proyecto = valor_importada + costo_intercambio_t1 + credito_t1 + credito_t2
    
    ahorro_autoconsumo = autoconsumo_mes * CU
    beneficio_neto_excedentes = abs(credito_t1 + credito_t2) - costo_intercambio_t1
    
    return {
        "autoconsumo_mes": autoconsumo_mes,
        "importada_mes": importada_mes,
        "exc_tipo1": exc_tipo1,
        "exc_tipo2": exc_tipo2,
        "costo_sin": costo_sin_proyecto,
        "costo_con": costo_con_proyecto,
        "v_importada": valor_importada,
        "v_intercambio": costo_intercambio_t1,
        "v_credito_t1": credito_t1,
        "v_credito_t2": credito_t2,
        "v_ahorro_auto": ahorro_autoconsumo,
        "v_beneficio_exc": beneficio_neto_excedentes
    }

def render_detailed_billing(bill_data: dict, CU: float, C: float, precio_bolsa: float, hourly_data: dict, consumo_mensual: float):
    st.markdown("## 📊 Como se comporta la Factura de Energia")
    costo_actual = bill_data["costo_sin"]
    st.info(f"**Costo Actual de Energía (Sin Proyecto):** $ {costo_actual:,.0f} COP/mes")

    col_empresa, col_cliente = st.columns(2)

    with col_empresa:
        st.markdown("### 🏢 Empresa de Energía")
        st.caption("Cálculo de la factura mensual (lo que pagarás)")
        
        v_importada = bill_data["v_importada"]
        v_intercambio = bill_data["v_intercambio"]
        v_credito_t1 = bill_data["v_credito_t1"]
        v_credito_t2 = bill_data["v_credito_t2"]
        total_factura = bill_data["costo_con"]

        st.write(f"➕ **Importación (Red):** $ {v_importada:,.0f}")
        st.write(f"➕ **Costo Intercambio T1:** $ {v_intercambio:,.0f}")
        st.write(f"➖ **Crédito Excedentes T1:** $ {abs(v_credito_t1):,.0f}")
        st.write(f"➖ **Venta Excedentes T2:** $ {abs(v_credito_t2):,.0f}")
        st.markdown(f"### **Total Factura:** \n# $ {total_factura:,.0f}")

    with col_cliente:
        st.markdown("### 👤 Beneficio Cliente")
        st.caption("Valor real generado por tu sistema")
        
        v_ahorro_auto = bill_data["v_ahorro_auto"]
        v_intercambio = bill_data["v_intercambio"]
        beneficio_neto_exc = (abs(bill_data["v_credito_t1"]) + abs(bill_data["v_credito_t2"])) - v_intercambio
        total_beneficio = v_ahorro_auto + beneficio_neto_exc

        st.write(f"💡 **Ahorro Autoconsumo:** $ {v_ahorro_auto:,.0f}")
        st.write(f"☀️ **Ahorro Excedentes T1:** $ {abs(bill_data['v_credito_t1']):,.0f}")
        st.write(f"💰 **Venta Excedentes T2:** $ {abs(bill_data['v_credito_t2']):,.0f}")
        st.write(f"⚠️ **Menos Costo Intercambio:** -$ {v_intercambio:,.0f}")
        st.markdown(f"### **Total Ahorro Real:** \n# $ {total_beneficio:,.0f}")

def plot_profiles(df: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["hora"], y=df["consumo_kwh"], name="Consumo (kWh/h)", fill="tozeroy", line=dict(color="firebrick"), opacity=0.6))
    fig.add_trace(go.Scatter(x=df["hora"], y=df["generacion_kwh"], name="Generación Solar (kWh/h)", fill="tozeroy", line=dict(color="goldenrod"), opacity=0.6))
    fig.update_layout(
        title=dict(text="Perfil horario: Consumo vs Generación", x=0.5, y=0.05, xanchor='center', yanchor='top'),
        xaxis_title="Hora", yaxis_title="kWh por hora",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=450, margin=dict(t=50, b=80, l=50, r=20), hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_monthly_comparison(df: pd.DataFrame):
    total_consumo = df["consumo_kwh"].sum() * 30
    total_autoconsumo = df["autoconsumo_kwh"].sum() * 30
    total_excedentes = df["excedente_kwh"].sum() * 30
    excedente_tipo1 = min(total_excedentes, total_consumo - total_autoconsumo)
    excedente_tipo2 = max(0, total_excedentes - excedente_tipo1)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=["Consumo", "Generación"], y=[total_consumo, 0], name="Consumo Total", marker_color='firebrick'))
    fig.add_trace(go.Bar(x=["Consumo", "Generación"], y=[0, total_autoconsumo], name="Autoconsumo", marker_color='#22C55E'))
    fig.add_trace(go.Bar(x=["Consumo", "Generación"], y=[0, excedente_tipo1], name="Excedente Tipo 1", marker_color='goldenrod'))
    fig.add_trace(go.Bar(x=["Consumo", "Generación"], y=[0, excedente_tipo2], name="Excedente Tipo 2", marker_color='#F59E0B'))

    fig.update_layout(
        barmode='stack', bargap=0.2,
        title=dict(text="Energía Mes Típico", x=0.5, y=0.05, xanchor='center', yanchor='top'),
        yaxis_title="kWh por mes", height=450, margin=dict(t=50, b=80, l=50, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# 4. FUNCIÓN MAIN
# -----------------------------------------------------------------------------
def main():
    # 001. Definir la ruta al logo dentro de assets
    # 'os.path.dirname(__file__)' ayuda a encontrar la carpeta raíz del proyecto
    current_dir = os.path.dirname(__file__)
    logo_path = os.path.join(current_dir, "assets", "logo ressas 572x197.jpg") # <-- Asegúrate que el nombre coincida

    # 002. Insertar en el sidebar
    with st.sidebar:
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
        else:
            # Esto te avisará si el nombre del archivo o carpeta está mal escrito
            st.warning(f"No se encontró el logo en: {logo_path}")

    # 1. INPUTS (SIDEBAR)
    with st.sidebar:
        st.header("Parámetros de Simulación")
        consumo = st.number_input("Consumo mensual (kWh)", min_value=0.0, value=1200.0, format="%.2f")
        CU = st.number_input("Tarifa CU (COP/kWh)", min_value=0.0, value=720.0)
        C = st.number_input("Comercialización C (COP/kWh)", min_value=0.0, value=56.71)
        precio_bolsa = st.number_input("Precio de Bolsa (COP/kWh)", min_value=0.0, value=210.0)
        hsp=st.number_input("Horas Solar Pico", min_value=0.0, value=3.5)
        
        st.header("Ajustes de Compensación")
        percent = st.slider("Porcentaje de compensación solar (%)", 0, 200, 100, key='percent_slider_sidebar')

    # 2. CÁLCULOS DEL PROYECTO (Deben hacerse antes de renderizar el header)
   
    kWp = (consumo * (percent / 100)) / (30 * hsp) if (30 * hsp) > 0 else 0
    costo_kwp = 5500000 if kWp <= 10 else 3300000
    inversion = (kWp * costo_kwp) / 1_000_000
    gen_obj = consumo * (percent / 100)

    # 3. inicio renderizacion  
    st.markdown('<h2>🏗️ Dimensionamiento y Presupuesto</h2>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Tamaño del Proyecto", f"{kWp:.2f} kWp")
    with c2:
        st.metric("Inversión Estimada", f"$ {inversion:,.2f} M COP")
    with c3:
        st.metric("Generación Objetivo", f"{gen_obj:,.0f} kWh/mes")

   
    demand = hourly_consumption_profile(consumo)
    generation = solar_generation_profile(consumo, percent)
    hourly = settle_hourly(demand, generation)
    bill = billing(consumo, hourly, CU, C, precio_bolsa)
    
    df = pd.DataFrame({
        "hora": HOUR_LABELS, "consumo_kwh": hourly["demand"],
        "generacion_kwh": hourly["generation"], "autoconsumo_kwh": hourly["autoconsumo"],
        "excedente_kwh": hourly["excedente"], "importada_kwh": hourly["importada"],
    })

    with st.expander("Ver detalle horario"):
        st.subheader("Detalle horario (promedio diario)")
        st.dataframe(df.style.format({
            "consumo_kwh": "{:.3f}",
            "generacion_kwh": "{:.3f}",
            "autoconsumo_kwh": "{:.3f}",
            "excedente_kwh": "{:.3f}",
            "importada_kwh": "{:.3f}",
        }), use_container_width=True)

    # Sección de Gráficos
    with st.expander("Graficos Comportamiento Generacion Vs Consumo"):
        st.subheader("Análisis de Comportamiento")
        col_hourly, col_monthly = st.columns([3, 1], vertical_alignment="top") 
    with col_hourly:
        plot_profiles(df)
    with col_monthly:
        plot_monthly_comparison(df)

    render_detailed_billing(bill, CU, C, precio_bolsa, hourly, consumo)
if __name__ == "__main__":
    main()