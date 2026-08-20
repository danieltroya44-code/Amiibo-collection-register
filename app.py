import streamlit as st
import requests
import json
import os

st.set_page_config(
    page_title="Smash Amiibo Vault",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilo CSS para tarjetas limpias y responsivas
st.markdown("""
<style>
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem;
    }
    .amiibo-card {
        background-color: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 10px;
        text-align: center;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

DB_FILE = "coleccion_smash.json"

# --- PERSISTENCIA LOCAL ---
def cargar_datos():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def guardar_datos(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@st.cache_data(show_spinner=False)
def obtener_amiibos_smash():
    # 1. Intentar descargar directamente el dump oficial desde GitHub (100% estable)
    github_raw = "https://raw.githubusercontent.com/N3evin/AmiiboAPI/master/database/amiibo.json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        res = requests.get(github_raw, headers=headers, timeout=12)
        if res.status_code == 200:
            datos_raw = res.json().get("amiibos", {})
            
            # ID de la serie Super Smash Bros en la base de datos es '0x00' (los dos primeros dígitos del head/tail)
            lista = []
            for k, v in datos_raw.items():
                head, tail = k.split("-")
                # Las figuras de Smash Bros tienen serie de colección 0x00
                if head[0:2].lower() == "00":
                    img_url = f"https://raw.githubusercontent.com/N3evin/AmiiboAPI/master/images/icon_{k}.png"
                    lista.append({
                        "uid": k,
                        "name": v.get("name", "Desconocido"),
                        "gameSeries": v.get("gameSeries", "Smash Bros."),
                        "image": img_url,
                        "release_na": v.get("release", {}).get("na", "9999-99-99") or "9999-99-99"
                    })
            
            if lista:
                return lista
    except Exception:
        pass

    # 2. Fallback a la API clásica con User-Agent
    try:
        url = "https://www.amiiboapi.com/api/amiibo/?amiiboSeries=Super%20Smash%20Bros."
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            datos = res.json().get("amiibo", [])
            unicos = {}
            for item in datos:
                uid = item["head"] + "-" + item["tail"]
                if uid not in unicos:
                    unicos[uid] = {
                        "uid": uid,
                        "name": item["name"],
                        "gameSeries": item.get("gameSeries", "Otros"),
                        "image": item["image"],
                        "release_na": item.get("release", {}).get("na", "9999-99-99") or "9999-99-99"
                    }
            return list(unicos.values())
    except Exception as e:
        st.error(f"Error al conectar con el catálogo: {e}")
        
    return []

# Inicializar sesión
if "coleccion" not in st.session_state:
    st.session_state.coleccion = cargar_datos()

lista_amiibos = obtener_amiibos_smash()
total_catalogo = len(lista_amiibos)

# --- CÁLCULO DE MÉTRICAS ---
obtenidos_count = sum(1 for a in lista_amiibos if st.session_state.coleccion.get(a["uid"]) == "Obtenido")
deseos_count = sum(1 for a in lista_amiibos if st.session_state.coleccion.get(a["uid"]) == "Deseado")
faltantes_count = total_catalogo - obtenidos_count
porcentaje = (obtenidos_count / total_catalogo * 100) if total_catalogo > 0 else 0

# --- HEADER Y ESTADÍSTICAS ---
st.title("🏆 Smash Bros. Amiibo Vault")

m1, m2, m3, m4 = st.columns(4)
m1.metric("📦 Catálogo Total", total_catalogo)
m2.metric("✅ Obtenidos", obtenidos_count)
m3.metric("⭐ En Lista de Deseos", deseos_count)
m4.metric("⏳ Faltantes", faltantes_count)

st.progress(porcentaje / 100)
st.caption(f"Progreso de colección: **{porcentaje:.1f}% completado**")

# --- BARRA DE CONTROL (BÚSQUEDA Y ORDENAMIENTO) ---
col_search, col_sort, col_order = st.columns([2, 1.5, 1])

with col_search:
    busqueda = st.text_input("🔍 Buscar por personaje o saga...", placeholder="Ej: Mario, Link, Pokémon...")

with col_sort:
    criterio_orden = st.selectbox(
        "Ordenar por:",
        ["Nombre del personaje", "Franquicia de origen", "Fecha de lanzamiento"]
    )

with col_order:
    direccion = st.selectbox("Dirección:", ["Ascendente (A-Z)", "Descendente (Z-A)"])

# Aplicar ordenamiento
reverse_flag = direccion.startswith("Descendente")
if criterio_orden == "Nombre del personaje":
    lista_amiibos = sorted(lista_amiibos, key=lambda x: x["name"].lower(), reverse=reverse_flag)
elif criterio_orden == "Franquicia de origen":
    lista_amiibos = sorted(lista_amiibos, key=lambda x: (x["gameSeries"].lower(), x["name"].lower()), reverse=reverse_flag)
elif criterio_orden == "Fecha de lanzamiento":
    lista_amiibos = sorted(lista_amiibos, key=lambda x: x["release_na"], reverse=reverse_flag)

# --- RENDERIZADOR DE TARJETAS EN GRID ---
def renderizar_catalogo(items_a_mostrar):
    if not items_a_mostrar:
        st.info("No se encontraron figuras en esta sección.")
        return

    # Cuadrícula responsive de 3 columnas (óptimo en móviles y desktop)
    n_cols = 3
    columnas = st.columns(n_cols)

    for idx, amiibo in enumerate(items_a_mostrar):
        uid = amiibo["uid"]
        estado_actual = st.session_state.coleccion.get(uid, "Faltante")
        
        with columnas[idx % n_cols]:
            with st.container():
                st.image(amiibo["image"], use_container_width=True)
                st.markdown(f"**{amiibo['name']}**")
                st.caption(f"🎮 {amiibo['gameSeries']}")

                opciones = ["Faltante", "Obtenido", "Deseado"]
                index_val = opciones.index(estado_actual) if estado_actual in opciones else 0
                
                nuevo_estado = st.selectbox(
                    "Estado:",
                    options=opciones,
                    index=index_val,
                    key=f"sel_{uid}",
                    label_visibility="collapsed"
                )

                if nuevo_estado != estado_actual:
                    if nuevo_estado == "Faltante":
                        st.session_state.coleccion.pop(uid, None)
                    else:
                        st.session_state.coleccion[uid] = nuevo_estado
                    
                    guardar_datos(st.session_state.coleccion)
                    st.rerun()
                
                st.divider()

# --- FILTRADO POR TEXTO ---
def filtrar_por_busqueda(lista):
    if not busqueda:
        return lista
    q = busqueda.lower()
    return [
        a for a in lista 
        if q in a["name"].lower() or q in a["gameSeries"].lower()
    ]

amiibos_filtrados = filtrar_por_busqueda(lista_amiibos)

# --- PESTAÑAS PRINCIPALES ---
tab_todos, tab_obtenidos, tab_faltantes, tab_deseos = st.tabs([
    f"📚 Todos ({len(amiibos_filtrados)})",
    f"✅ Obtenidos ({sum(1 for a in amiibos_filtrados if st.session_state.coleccion.get(a['uid']) == 'Obtenido')})",
    f"⏳ Faltantes ({sum(1 for a in amiibos_filtrados if st.session_state.coleccion.get(a['uid']) != 'Obtenido')})",
    f"⭐ Lista de Deseos ({sum(1 for a in amiibos_filtrados if st.session_state.coleccion.get(a['uid']) == 'Deseado')})"
])

with tab_todos:
    renderizar_catalogo(amiibos_filtrados)

with tab_obtenidos:
    solo_obtenidos = [a for a in amiibos_filtrados if st.session_state.coleccion.get(a["uid"]) == "Obtenido"]
    renderizar_catalogo(solo_obtenidos)

with tab_faltantes:
    solo_faltantes = [a for a in amiibos_filtrados if st.session_state.coleccion.get(a["uid"]) != "Obtenido"]
    renderizar_catalogo(solo_faltantes)

with tab_deseos:
    solo_deseos = [a for a in amiibos_filtrados if st.session_state.coleccion.get(a["uid"]) == "Deseado"]
    renderizar_catalogo(solo_deseos)