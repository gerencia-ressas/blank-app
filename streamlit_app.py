import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from PIL import Image
import os
import base64
# ... imports ...
try:
    import numpy_financial as npf
except ImportError:
    npf = None

def calculate_irr(values):
    """Calcula la Tasa Interna de Retorno (IRR)."""
    if npf:
        return npf.irr(values)
    
    # Fallback básico si numpy_financial no está instalado (usando numpy < 1.24 si tiene irr, o aproximación)
    # Numpy 1.24+ eliminó np.irr.
    try:
        return np.irr(values)
    except AttributeError:
        # Implementación simple de Newton-Raphson para IRR
        res = 0.1
        for _ in range(20):
            npv = 0
            d_npv = 0
            for t, val in enumerate(values):
                npv += val / ((1 + res) ** t)
                d_npv -= t * val / ((1 + res) ** (t + 1))
            if abs(d_npv) < 1e-6:
                return res
            res = res - npv / d_npv
            if abs(npv) < 1e-6:
                return res
        return res

def calculate_npv(rate, values):
    """Calcula el Valor Presente Neto (NPV)."""
    if npf:
        return npf.npv(rate, values)
    try:
        return np.npv(rate, values)
    except AttributeError:
        values = np.asarray(values)
        t = np.arange(len(values))
        return (values / (1 + rate) ** t).sum()

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA (Debe ser la primera línea de Streamlit)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Simulador AGPE - CREG 174 (2021)", layout="wide")



# -----------------------------------------------------------------------------
# 2. ESTILOS CSS
# -----------------------------------------------------------------------------


def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def get_plotly_uri(path):
    #Convierte una ruta de archivo en un Data URI para Plotly.
    if os.path.exists(path):
        encoded = get_base64_of_bin_file(path)
        return f"data:image/jpg;base64,{encoded}"
    return None


def apply_custom_styles():
    # Cargar imagen de fondo del proyecto 
    #Marcas de Agua para los Graficos en modo fullscreen
    current_dir = os.path.dirname(__file__)
    logo_path = os.path.join(current_dir, "assets", "logo ressas 572x197.jpg")  
    logotxt_path = os.path.join(current_dir, "assets", "Icono ressas.jpg")
    watermark_path = os.path.join(current_dir, "assets", "Text RESsas.jpg")
    
    bin_str_logo = ""
    bin_str_bg = ""
    bin_str_watermark = ""
    # 2. Convertir imagen a base64
    if os.path.exists(logo_path):
        bin_str_logo = get_base64_of_bin_file(logo_path)
    if os.path.exists(logotxt_path):
        bin_str_bg = get_base64_of_bin_file(logotxt_path)
    
    if os.path.exists(watermark_path):
        bin_str_watermark = get_base64_of_bin_file(watermark_path)  

    uri_fondo = get_plotly_uri(logotxt_path)
    uri_marca_agua = get_plotly_uri(watermark_path)


    st.markdown(f"""
        <style>
        /* 1. Capa de fondo ajustada al contenido principal */
            .stApp::before {{
                content: "";
                background-image: url("data:image/jpg;base64,{bin_str_bg}");
                background-repeat: no-repeat;
                background-attachment: fixed;
                background-position: center; /* Centra la imagen dentro de su contenedor */
                background-size: 40%; /* Tamaño de la marca de agua */
                
                position: fixed;
                top: 0;
                /* El truco: dejar que el flexbox de Streamlit maneje el margen izquierdo */
                left: 0; 
                right: 0;
                bottom: 0;
                
                /* Margen para compensar el sidebar de Streamlit (aprox 21rem o 336px) */
                margin-left: auto; 
                margin-right: auto;
                
                opacity: 0.08;
                z-index: -1;
                pointer-events: none; /* Evita que el fondo interfiera con clicks */
            }}
         /* CAPA 2: Logo Inferior Derecha (Usando ::after) */
            .stApp::after {{
                content: "";
                background-image: url("data:image/jpg;base64,{bin_str_logo}");
                background-repeat: no-repeat;
                background-position: bottom right;
                background-size: 200px; /* Ajusta el tamaño deseado */
                
                position: fixed;
                bottom: 20px; /* Margen desde abajo */
                right: 20px;  /* Margen desde la derecha */
                width: 200px; /* Debe ser igual o mayor a background-size */
                height: 100px;
                
                opacity: 0.4; /* Un poco más visible que el fondo */
                z-index: 1;   /* Por encima del fondo central */
                pointer-events: none;
            }}
            
            /* Ajuste para que el fondo ignore el sidebar visualmente */
            @media (min-width: 992px) {{
                .stApp::before {{ margin-left: 336px; }}
            }}   
            /* 2. LOGO SOLO EN LOS GRAFICOS*/

            [data-testid="stFullScreenFrame"]::after {{
                content: "";
                background-image: url("data:image/jpg;base64,{bin_str_watermark}");
                background-repeat: no-repeat;
                background-position: center;
                background-size: contain;
                
                /* Posicionamiento centrado */
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                
                /* Tamaño y Opacidad */
                width: 50%; 
                height: 50%;
                opacity: 0.10; /* Sutil para no estorbar la lectura */
                
                z-index: 99; /* Suficiente para estar sobre el gráfico pero bajo los tooltips */
                pointer-events: none;
            }}

            /* 2. Aseguramos que el contenedor principal sea transparente */
            .stApp {{
                background-color: rgba(0,0,0,0);
            }}
        /* Ocultar elementos default
        
        header {{visibility: hidden;}} 
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}*/
       
        
        /* --- ESTILO PARA MÉTRICAS NORMALES --- */
        [data-testid="stMetric"] {{
            background-color: rgba(0,0,0,0); /* Mantener fondo blanco para legibilidad */
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        

        /* --- AJUSTE PARA LOS INPUTS DEL SIDEBAR --- */
         /* --- ALINEACIÓN HORIZONTAL EN SIDEBAR --- */
            /* Forzamos al contenedor del widget a ser una fila */
            [data-testid="stSidebar"] .stNumberInput {{
                display: flex;
                flex-direction: row;
                align-items: center;
                justify-content: space-between;
                gap: 10px;
                margin-bottom: 10px;
            }}

            /* Ajustamos el label (texto) para que no ocupe todo el ancho */
            [data-testid="stSidebar"] .stNumberInput label {{
                display: flex;
                margin-bottom: 0 !important; /* Quita el espacio de abajo del texto */
                flex: 1 1 auto;
                min-width: 150px; /* Asegura espacio para el nombre */
            }}

            /* Ajustamos el cuadro de entrada de número */
            [data-testid="stSidebar"] .stNumberInput div[data-baseweb="input"] {{
                width: 120px !important; /* Ancho fijo para los cuadritos de números */
                flex: 0 0 auto;
            }}

            /* Opcional: Hacer la fuente un poco más pequeña para que quepa mejor */
            [data-testid="stSidebar"] label p {{
                font-size: 14px !important;
            }}  
        /* --- AJUSTE PARA LOS INPUTS DEL SIDEBAR --- */
            /* --- MOVER LOGO AL FINAL DEL SIDEBAR --- */
        /* Convertimos el contenedor de widgets del sidebar en un Flexbox vertical */
        [data-testid="stSidebarUserContent"] {{
            display: flex;
            flex-direction: column;
            height: 90vh; /* Ajusta la altura para que ocupe casi toda la pantalla */
        }} 

        /* Buscamos el contenedor de la imagen y le damos un margen superior automático */
        /* Esto empuja la imagen hacia el fondo del contenedor flex */
        [data-testid="stSidebarUserContent"] .stImage {{
            margin-top: auto !important;
            padding-bottom: 20px;
        }} 

        </style>
        
    """, unsafe_allow_html=True)
    return uri_marca_agua, uri_fondo

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

def billing(monthly_consumption_kwh: float, hourly: dict, CU: float, C: float, precio_bolsa: float, factor_contribucion:float,) -> dict:
    autoconsumo_mes = hourly["autoconsumo"].sum() * 30.0
    excedente_total_mes = hourly["excedente"].sum() * 30.0
    importada_mes = hourly["importada"].sum() * 30.0
    
    exc_tipo1 = min(excedente_total_mes, importada_mes)
    exc_tipo2 = max(0, excedente_total_mes - importada_mes)

    # --- LÓGICA DE CONTRIBUCIÓN CORREGIDA ---
    # La contribución se cobra sobre los kWh netos (Importados - Compensados T1)
    kwh_netos_a_pagar = max(0, importada_mes - exc_tipo1)
    # El valor base es la tarifa CU por esos kWh netos
    valor_base_contribucion = kwh_netos_a_pagar * CU
    contribucion = valor_base_contribucion * (factor_contribucion / 100)
    # ----------------------------------------
    
    costo_sin_proyecto = monthly_consumption_kwh * CU*(1+(factor_contribucion/100))
    
    valor_importada = importada_mes * CU
    
    costo_intercambio_t1 = exc_tipo1 * C
    credito_t1 = exc_tipo1 * -CU
    credito_t2 = exc_tipo2 * -precio_bolsa

    # Ahorro de contribución por Autoconsumo (Energía que no pasó por el medidor)
    ahorro_contrib_auto = (autoconsumo_mes * CU) * (factor_contribucion / 100)
    
    # Ahorro de contribución por Excedentes T1 (Energía compensada 1 a 1)
    ahorro_contrib_t1 = (exc_tipo1 * CU) * (factor_contribucion / 100)
    
    # Total ahorro en contribución
    total_ahorro_contribucion = ahorro_contrib_auto + ahorro_contrib_t1
    
    costo_con_proyecto = valor_importada + contribucion+costo_intercambio_t1 + credito_t1 + credito_t2
    
    ahorro_autoconsumo = autoconsumo_mes * CU
    beneficio_neto_excedentes = abs(credito_t1 + credito_t2) - costo_intercambio_t1
    
    return {
        "autoconsumo_mes": autoconsumo_mes,
        "importada_mes": importada_mes,
        "v_contribucion":contribucion,
        "exc_tipo1": exc_tipo1,
        "exc_tipo2": exc_tipo2,
        "costo_sin": costo_sin_proyecto,
        "costo_con": costo_con_proyecto,
        "v_importada": valor_importada,
        "v_intercambio": costo_intercambio_t1,
        "v_credito_t1": credito_t1,
        "v_credito_t2": credito_t2,
        "v_ahorro_auto": ahorro_autoconsumo,
        "v_ahorro_contribucion": total_ahorro_contribucion,
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
        v_contribucion= bill_data["v_contribucion"]
        v_intercambio = bill_data["v_intercambio"]
        v_credito_t1 = bill_data["v_credito_t1"]
        v_credito_t2 = bill_data["v_credito_t2"]
        total_factura = bill_data["costo_con"]

        st.write(f"➕ **Importación (Red):** $ {v_importada:,.0f}")
        st.write(f"➕ **Contribucion (Red):** $ {v_contribucion:,.0f}")
        st.write(f"➕ **Costo Intercambio T1:** $ {v_intercambio:,.0f}")
        st.write(f"➖ **Crédito Excedentes T1:** $ {abs(v_credito_t1):,.0f}")
        st.write(f"➖ **Venta Excedentes T2:** $ {abs(v_credito_t2):,.0f}")
        st.markdown(f"### **Total Factura:** \n# $ {total_factura:,.0f}")

    with col_cliente:
        st.markdown("### 👤 Beneficio Cliente")
        st.caption("Valor real generado por tu sistema")
        
        v_ahorro_auto = bill_data["v_ahorro_auto"]
        v_intercambio = bill_data["v_intercambio"]
        v_ahorro_impuestos = bill_data["v_ahorro_contribucion"]
        beneficio_neto_exc = (abs(bill_data["v_credito_t1"]) + abs(bill_data["v_credito_t2"])) - v_intercambio
        total_beneficio = v_ahorro_auto + beneficio_neto_exc+v_ahorro_impuestos

        st.write(f"💡 **Ahorro Autoconsumo:** $ {v_ahorro_auto:,.0f}")
        st.write(f"☀️ **Ahorro Excedentes T1:** $ {abs(bill_data['v_credito_t1']):,.0f}")
        st.write(f"💰 **Venta Excedentes T2:** $ {abs(bill_data['v_credito_t2']):,.0f}")
        st.write(f"⚠️ **Menos Costo Intercambio:** -$ {v_intercambio:,.0f}")
        st.write(f"📉 **Ahorro Contribución (20%):** $ {v_ahorro_impuestos:,.0f}")
        st.markdown(f"### **Total Ahorro Real:** \n# $ {total_beneficio:,.0f}")

def plot_profiles(df: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["hora"], y=df["consumo_kwh"], name="Consumo (kWh/h)", fill="tozeroy", line=dict(color="firebrick"), opacity=0.6))
    fig.add_trace(go.Scatter(x=df["hora"], y=df["generacion_kwh"], name="Generación Solar (kWh/h)", fill="tozeroy", line=dict(color="goldenrod"), opacity=0.6))

    fig.update_layout(
    title=dict(text="Perfil horario: Consumo vs Generación", x=0.5, y=0.05, xanchor='center', yanchor='top'),
    xaxis_title="Hora", yaxis_title="kWh por hora",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
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
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# 4. FUNCIÓN MAIN
# -----------------------------------------------------------------------------
def main():
    
    uri_marca_agua, uri_background = apply_custom_styles()
    # 001. Definir la ruta al logo dentro de assets
    # 'os.path.dirname(__file__)' ayuda a encontrar la carpeta raíz del proyecto
    current_dir = os.path.dirname(__file__)
    logotxt_path = os.path.join(current_dir, "assets", "logo ressas 572x197.jpg") # <-- Asegúrate que el nombre coincida

    # 1. INPUTS (SIDEBAR)
    with st.sidebar:
        st.header("Parámetros de Simulación")
        consumo = st.number_input("Consumo mensual (kWh)", min_value=0.0, value=1200.0, format="%.2f")
        CU = st.number_input("Tarifa CU (COP/kWh)", min_value=0.0, value=720.0)
        factor_contribucion= st.number_input("Contribucion (%/kWh)", min_value=0.0, value=20.0)
        C = st.number_input("Comercialización C (COP/kWh)", min_value=0.0, value=56.71)
        precio_bolsa = st.number_input("Precio de Bolsa (COP/kWh)", min_value=0.0, value=210.0)
        hsp=st.number_input("Horas Solar Pico", min_value=0.0, value=3.5)
        
        st.header("Ajustes de Compensación")
        percent = st.slider("Porcentaje de compensación solar (%)", 0, 200, 100, key='percent_slider_sidebar')
        
        st.header("Parámetros Financieros (Ley 1715)")
        tasa_renta = st.number_input("Tasa de Renta (%)", min_value=0.0, max_value=100.0, value=35.0, step=1.0)
     # 002. Insertar Logo en el sidebar
     # with st.sidebar:
     #   if os.path.exists(logotxt_path):
     #       st.image(logotxt_path, use_container_width=True)
     #   else:
     #       # Esto te avisará si el nombre del archivo o carpeta está mal escrito
     #       st.warning(f"No se encontró el logo en: {logotxt_path}")

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
    bill = billing(consumo, hourly, CU, C, precio_bolsa, factor_contribucion)
    
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

    # -----------------------------------------------------------------------------
    # 4.1. IMPACTO AMBIENTAL Y SOSTENIBILIDAD
    # -----------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("## 🍃 Impacto Ambiental y Sostenibilidad")

    # A. Constantes y Cálculos
    factor_emision = 0.1643 # tCO2e / MWh (UPME/XM)
    factor_arboles = 50     # árboles / tCO2
    horizonte_amb = 25      # años

    # Generación anual en MWh
    gen_anual_mwh = (gen_obj * 12) / 1000 
    
    # Impactos
    co2_anual = gen_anual_mwh * factor_emision
    co2_total_25 = co2_anual * horizonte_amb
    
    arboles_anual = co2_anual * factor_arboles
    arboles_total = co2_total_25 * factor_arboles
    
    # Equivalencia Vehicular
    factor_auto_km = 0.00018  # 180 gCO2/km = 0.00018 tCO2/km
    km_evitados_anual = co2_anual / factor_auto_km
    km_evitados_total = co2_total_25 / factor_auto_km

    # B. Interfaz de Resumen
    st.info(f"Tu proyecto contribuye a la mitigación del impacto ambiental al evitar la emisión de **{co2_total_25:.2f} toneladas de CO₂** en {horizonte_amb} años, equivalente a plantar **{arboles_total:.0f} árboles** o dejar de recorrer **{km_evitados_total:,.0f} kilómetros** en un vehículo de combustión.")

    col_amb1, col_amb2, col_amb3 = st.columns(3)
    
    col_amb1.metric(
        "Toneladas CO₂ / Año", 
        f"{co2_anual:.2f} t", 
        delta="☁️",
        help="Calculado usando el Factor de Emisión del SIN (UPME/XM) de 0.1643 tCO2e/MWh. Referencia: Res. UPME 135 de 2025."
    )
    
    col_amb2.metric(
        "Árboles equivalentes / Año", 
        f"{arboles_anual:.0f} árboles", 
        delta="🌳",
        help="Basado en una absorción promedio de 20kg de CO2 por árbol joven al año en el trópico. Referencia: Guía IDEAM/IPCC."
    )
    
    col_amb3.metric(
        "Km Evitados en Carro", 
        f"{km_evitados_anual:,.0f} km", 
        delta="🚗",
        help="Equivalencia basada en un vehículo de combustión promedio con emisión de 180g CO2/km."
    )

    # C. Gráfico de Proyección Ambiental
    anios_amb = list(range(1, horizonte_amb + 1))
    acumulado_co2 = [co2_anual * a for a in anios_amb]

    with st.expander("🍃 Ver Proyección de Impacto Ambiental"):
        fig_amb = go.Figure()
        fig_amb.add_trace(go.Bar(
            x=anios_amb,
            y=acumulado_co2,
            name="CO₂ Evitado Acumulado",
            marker_color='#10B981',
            opacity=0.8
        ))
        
        fig_amb.update_layout(
            title="Acumulación de CO₂ evitado (25 años)",
            xaxis_title="Años",
            yaxis_title="Toneladas CO₂e",
            height=350,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            hovermode="x unified"
        )
        st.plotly_chart(fig_amb, use_container_width=True)

    st.caption("📜 *Marco Normativo: Ley 2169 de 2021 (Acción Climática) y Resolución UPME 135 de 2025.*")

    # -----------------------------------------------------------------------------
    # 4.2. INCENTIVOS TRIBUTARIOS (LEY 1715)
    # -----------------------------------------------------------------------------
    st.markdown("---")
    st.header("🎁 Beneficios e Incentivos Tributarios (Ley 1715)")

    # A. Cálculos
    inversion_cop_total = inversion * 1_000_000
    tasa_renta_dec = tasa_renta / 100.0
    
    # 1. Deducción Especial de Renta (50% Inversión)
    base_deduccion_renta = inversion_cop_total * 0.50
    ahorro_deduccion_renta = base_deduccion_renta * tasa_renta_dec
    
    # 2. Depreciación Acelerada (100% Inversión - Beneficio de flujo)
    # El ahorro real es el escudo fiscal generado por depreciar el activo
    base_depreciacion = inversion_cop_total
    ahorro_depreciacion = base_depreciacion * tasa_renta_dec
    
    # Totales
    total_incentivo = ahorro_deduccion_renta + ahorro_depreciacion
    porcentaje_sobre_inversion = (total_incentivo / inversion_cop_total) * 100 if inversion_cop_total > 0 else 0

    # B. Tarjetas Resumen
    c_tax1, c_tax2, c_tax3 = st.columns(3)
    c_tax1.metric("Ahorro por Deducción Renta", f"$ {ahorro_deduccion_renta:,.0f}",help="Incentivo de renta (Ley 2099 de 2021, Artículo 8)")
    c_tax2.metric("Ahorro Depreciación Acelerada", f"$ {ahorro_depreciacion:,.0f}",help="Depreciación acelerada (Ley 2099 de 2021, Artículo 11)")
    c_tax3.metric("Total Incentivo Fiscal", f"$ {total_incentivo:,.0f}", delta=f"{porcentaje_sobre_inversion:.1f}% Inv.")

    # C. Tabla Detallada
    # Creamos un DataFrame para mostrar la lógica como en la imagen
    datos_tabla = [
        {
            "Concepto": "Deducción de Renta (50%)",
            "Inversión Base": f"$ {inversion_cop_total:,.0f}",
            "% Base Deducible": "50%",
            "Valor a Deducir": f"$ {base_deduccion_renta:,.0f}",
            "Tasa Renta": f"{tasa_renta}%",
            "Ahorro Final": f"$ {ahorro_deduccion_renta:,.0f}"
        },
        {
            "Concepto": "Depreciación Acelerada",
            "Inversión Base": f"$ {inversion_cop_total:,.0f}",
            "% Base Deducible": "100%",
            "Valor a Deducir": f"$ {base_depreciacion:,.0f}",
            "Tasa Renta": f"{tasa_renta}%",
            "Ahorro Final": f"$ {ahorro_depreciacion:,.0f}"
        },
        {
            "Concepto": "TOTAL BENEFICIOS",
            "Inversión Base": "-",
            "% Base Deducible": "-",
            "Valor a Deducir": "-",
            "Tasa Renta": "-",
            "Ahorro Final": f"$ {total_incentivo:,.0f}"
        }
    ]
    df_tax = pd.DataFrame(datos_tabla)
    st.table(df_tax)

    # D. Notas Legales
    with st.expander("ℹ️ Información Legal - Ley 1715 de 2014"):
        st.write("""
        *   **Certificado UPME Res 319 de 2022 & Res 464 de 2021** se requiere tramitar la certificación de beneficios tributarios por la UPME. El certificado se expedirá al haber acreditado el pago según la tarifa (Res 464/2021).
        *   **Deducción Especial de Renta:** Deducción sobre el impuesto de renta del 50% del valor de la inversión realizada. La deducción podrá ser tomada en un periodo no mayor a 15 años contados a partir del año gravable siguiente al año de entrada en operación.
        *   **Depreciación Acelerada:**  Será aplicable a maquinarias, equipos y obras civiles necesarias para la preinversión, inversión y operación de los proyectos. La tasa anual de depreciación será de hasta el 33.33% como tasa global anual. Esta tasa puede ser variada anualmente por el titular del proyecto, previa comunicación a la DIAN, sin exceder dicho límite.
        *   **Los siguientes beneficios tributarios, ya estan considerados en la oferta,puesto que son un menor valor en equipos, materiales y servicios:**
        *   **Exención de IVA:** Exención del impuesto sobre las ventas (IVA) para la adquisición de equipos, maquinaria y equipos nuevos o usados, siempre que estos sean necesarios para la producción de energía a partir de fuentes renovables y no sean considerados bienes o servicios de carácter suntuario.
        *   **Exención de Aranceles:** Exención del impuesto de arancel para la importación de equipos, maquinaria y equipos nuevos o usados, siempre que estos sean necesarios para la producción de energía a partir de fuentes renovables y no sean considerados bienes o servicios de carácter suntuario.        
        """)

    # -----------------------------------------------------------------------------
    # 5. ANÁLISIS FINANCIERO
    # -----------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("## 💰 Análisis Financiero")

    # A. Preparar Datos
    # Recalcular el beneficio mensual total para usarlo de base
    # (Misma lógica que en render_detailed_billing)
    v_ahorro_auto = bill["v_ahorro_auto"]
    v_intercambio = bill["v_intercambio"]
    v_credito_t1 = bill["v_credito_t1"]
    v_credito_t2 = bill["v_credito_t2"]
    v_ahorro_impuestos = bill["v_ahorro_contribucion"]
    
    beneficio_neto_exc = (abs(v_credito_t1) + abs(v_credito_t2)) - v_intercambio
    total_beneficio = v_ahorro_auto + beneficio_neto_exc + v_ahorro_impuestos
    
    ahorro_mensual_base = total_beneficio
    inversion_cop = inversion * 1_000_000
    
    # Parámetros Financieros
    tio_anual = 0.10      # 10% E.A.
    ipc_anual = 0.05      # 5% Anual
    horizonte_anios = 30
    
    # B. Construcción del Flujo de Caja y Datos Comparativos
    flujos = [-inversion_cop] # Año 0 (Cash Flow Project)
    flujos_acumulados = [-inversion_cop]
    
    # Datos para Comparativa (VPN)
    costo_mensual_sin = bill["costo_sin"]
    costo_mensual_con = bill["costo_con"]
    
    vpn_sin_proyecto = [0] # Año 0
    vpn_con_proyecto = [inversion_cop] # Año 0 (El proyecto empieza con la inversión)
    
    acumulado_sin_vpn = 0
    acumulado_con_vpn = inversion_cop
    
    for anio in range(1, horizonte_anios + 1):
        # Factores Comunes
        factor_inflacion = (1 + ipc_anual) ** anio
        factor_vpn = 1 / ((1 + tio_anual) ** anio)
        
        # 1. Flujo de Caja (Retorno de Inversión)
        # Nota: El usuario pidió explícitamente (ahorro_mensual_base * 12) * (1.05 ** año)
        ahorro_anio = (ahorro_mensual_base * 12) * factor_inflacion
        flujos.append(ahorro_anio)
        
        nuevo_acumulado = flujos_acumulados[-1] + ahorro_anio
        flujos_acumulados.append(nuevo_acumulado)
        
        # 2. Gasto Comparativo (VPN)
        # Gasto Sin Proyecto
        gasto_anio_sin = (costo_mensual_sin * 12) * factor_inflacion
        acumulado_sin_vpn += (gasto_anio_sin * factor_vpn)
        vpn_sin_proyecto.append(acumulado_sin_vpn)
        
        # Gasto Con Proyecto
        gasto_anio_con = (costo_mensual_con * 12) * factor_inflacion
        acumulado_con_vpn += (gasto_anio_con * factor_vpn)
        vpn_con_proyecto.append(acumulado_con_vpn)

    # C. Cálculos de Indicadores
    van = calculate_npv(tio_anual, flujos)
    
    # TIR: Manejo de errores
    try:
        tir = calculate_irr(flujos)
        if tir is None or np.isnan(tir):
            tir = 0.0
    except:
        tir = 0.0
        
    # Payback
    payback_anios = 0
    encontro_payback = False
    for i, val in enumerate(flujos_acumulados):
        if val >= 0:
            payback_anios = i
            encontro_payback = True
            break
            
    # D. Renderizado de Métricas
    met1, met2, met3 = st.columns(3)
    
    van_color = "normal" if van > 0 else "off"
    met1.metric("VAN (Premio a la Inversión)", f"$ {van:,.0f} COP", delta_color=van_color)
    
    tir_str = f"{tir*100:.2f} %" if encontro_payback else "N/A"
    met2.metric("TIR (Rentabilidad)", tir_str)
    
    payback_str = f"{payback_anios} Años" if encontro_payback else "> 30 Años"
    met3.metric("Payback (Retorno)", payback_str)

    # E. Gráficas
    eje_x = list(range(horizonte_anios + 1))
    
    # E.1 Gráfica Comparativa de Gasto (VPN) FIRST
    # E.1 Gráfica Comparativa de Gasto (VPN) FIRST
    with st.expander("📉 Comparativa de Gasto Acumulado (VPN)", expanded=True):
        fig_comp = go.Figure()
        
        fig_comp.add_trace(go.Scatter(
            x=eje_x, 
            y=vpn_sin_proyecto,
            mode='lines',
            name='Gasto Acumulado SIN Proyecto (VPN)',
            line=dict(color='#EF4444', width=3, dash='dash')
        ))
        
        fig_comp.add_trace(go.Scatter(
            x=eje_x, 
            y=vpn_con_proyecto,
            mode='lines',
            name='Gasto Acumulado CON Proyecto (VPN)',
            line=dict(color='#3B82F6', width=3),
            fill='tonexty',
            fillcolor='rgba(59, 130, 246, 0.1)'
        ))
        
        fig_comp.update_layout(
            title="Comparativa de Gasto Acumulado (VPN @ 10%)",
            xaxis_title="Años",
            yaxis_title="COP (Valor Presente)",
            height=450,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
        )
        
        # Anotación del Ahorro Total (VPN)
        ahorro_total_vpn = vpn_sin_proyecto[-1] - vpn_con_proyecto[-1]
        mid_y = (vpn_sin_proyecto[-1] + vpn_con_proyecto[-1]) / 2
        
        fig_comp.add_annotation(
            x=horizonte_anios,
            y=mid_y,
            text=f"<b>Ahorro Neto (VPN):<br>$ {ahorro_total_vpn:,.0f}</b>",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor="#10B981",
            ax=-60,
            ay=0,
            bgcolor="rgba(255, 255, 255, 0.9)",
            bordercolor="#10B981",
            borderwidth=2,
            borderpad=4,
            font=dict(size=12, color="#065F46")
        )
        
        st.plotly_chart(fig_comp, use_container_width=True)
    
    # E.2 Gráfica de Flujo de Caja Acumulado (Retorno) SECOND
    with st.expander("📈 Retorno de Inversión"):
        fig_fin = go.Figure()
        
        fig_fin.add_trace(go.Scatter(
            x=eje_x, 
            y=flujos_acumulados,
            mode='lines+markers',
            name='Flujo Acumulado',
            line=dict(color='#10B981', width=3),
            fill='tozeroy'
        ))
        
        fig_fin.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Punto de Equilibrio")
        
        fig_fin.update_layout(
            title="Flujo de Caja Acumulado",
            xaxis_title="Años",
            yaxis_title="COP Acumulados",
            height=400,
            hovermode="x unified",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig_fin, use_container_width=True)


if __name__ == "__main__":
    main()