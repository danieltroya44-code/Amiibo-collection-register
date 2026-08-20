import streamlit as st
import json
import os
from pathlib import Path

st.set_page_config(
    page_title="Smash Amiibo Vault",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilo para presentación limpia de tarjetas
st.markdown("""
<style>
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }
    div[data-testid="stVerticalBlock"] > div:has(div.stImage) {
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Resolución de rutas absolutas
BASE_DIR = Path(__file__).resolve().parent
LOCAL_CATALOG_FILE = BASE_DIR / "all_amiibos.json"
USER_DATA_FILE = BASE_DIR / "mi_coleccion_smash.json"

# --- PERSISTENCIA DE COLECCIÓN DEL USUARIO ---
def cargar_coleccion_usuario():
    if USER_DATA_FILE.exists():
        try:
            with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def guardar_coleccion_usuario(data):
    with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- PROCESAMIENTO Y FILTRADO DEL JSON LOCAL ---
@st.cache_data
def cargar_amiibos_smash_local():
    if not LOCAL_CATALOG_FILE.exists():
        archivos_en_carpeta = [f.name for f in BASE_DIR.iterdir()]
        st.error(f"❌ No se encontró 'all_amiibos.json'. Archivos visibles: {archivos_en_carpeta}")
        return []

    with open(LOCAL_CATALOG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    amiibos_dict = data.get("amiibos", {})
    game_series_dict = data.get("game_series", {})

    lista_smash = []

    for raw_id, info in amiibos_dict.items():
        clean_id = raw_id.lower().replace("0x", "")
        
        # En el estándar hexadecimal de 16 caracteres:
        # clean_id[12:14] == '00' corresponde a Super Smash Bros.
        if len(clean_id) == 16:
            series_code = clean_id[12:14]
            if series_code == "00":
                head = clean_id[0:8]
                tail = clean_id[8:16]
                
                game_code = f"0x{clean_id[0:3]}"
                game_name = game_series_dict.get(game_code, "Smash Bros.")
                img_url = f"https://raw.githubusercontent.com/N3evin/AmiiboAPI/master/images/icon_{head}-{tail}.png"
                release_date = info.get("release", {}).get("na", "9999-99-99") or "9999-99-99"

                lista_smash.append({
                    "uid": f"{head}-{tail}",
                    "name": info.get("name", "Desconocido"),
                    "gameSeries": game_name,
                    "image": img_url,
                    "release_na": release_date
                })

    return lista_smash

# Inicializar sesión
if "coleccion" not in st.session_state:
    st.session_state.coleccion = cargar_coleccion_usuario()

catalogo_smash = cargar_amiibos_smash_local()
total_catalogo = len(catalogo_smash)

# --- CÁLCULO DE MÉTRICAS ---
obtenidos_count = sum(1 for a in catalogo_smash if st.session_state.coleccion.get(a["uid"]) == "Obtenido")
deseos_count = sum(1 for a in catalogo_smash if st.session_state.coleccion.get(a["uid"]) == "Deseado")
faltantes_count = total_catalogo - obtenidos_count
progreso = (obtenidos_count / total_catalogo * 100) if total_catalogo > 0 else 0

# --- PANEL PRINCIPAL ---
st.title("🏆 Smash Bros. Amiibo Vault")

m1, m2, m3, m4 = st.columns(4)
m1.metric("📦 Catálogo Smash", total_catalogo)
m2.metric("✅ Obtenidos", obtenidos_count)
m3.metric("⭐ Lista de Deseos", deseos_count)
m4.metric("⏳ Faltantes", faltantes_count)

st.progress(progreso / 100)
st.caption(f"Progreso: **{obtenidos_count} / {total_catalogo}** ({progreso:.1f}%)")

# --- CONTROLES Y ORDEN ---
col_search, col_sort, col_order = st.columns([2, 1.5, 1])

with col_search:
    busqueda = st.text_input("🔍 Buscar por personaje o saga...", placeholder="Ej: Mario, Link, Cloud...")

with col_sort:
    criterio = st.selectbox("Ordenar por:", ["Nombre", "Franquicia de origen", "Fecha de lanzamiento"])

with col_order:
    sentido = st.selectbox("Dirección:", ["Ascendente (A-Z)", "Descendente (Z-A)"])

# Aplicación de ordenamiento
reverse_order = sentido.startswith("Descendente")
if criterio == "Nombre":
    catalogo_smash = sorted(catalogo_smash, key=lambda x: x["name"].lower(), reverse=reverse_order)
elif criterio == "Franquicia de origen":
    catalogo_smash = sorted(catalogo_smash, key=lambda x: (x["gameSeries"].lower(), x["name"].lower()), reverse=reverse_order)
elif criterio == "Fecha de lanzamiento":
    catalogo_smash = sorted(catalogo_smash, key=lambda x: x["release_na"], reverse=reverse_order)

# Renderizador de tarjetas en cuadrícula
def render_grid(items):
    if not items:
        st.info("No hay figuras en esta sección.")
        return

    n_cols = 3
    columnas = st.columns(n_cols)

    for idx, amiibo in enumerate(items):
        uid = amiibo["uid"]
        estado_actual = st.session_state.coleccion.get(uid, "Faltante")
        
        with columnas[idx % n_cols]:
            with st.container():
                st.image(amiibo["image"], use_container_width=True)
                st.markdown(f"**{amiibo['name']}**")
                st.caption(f"🎮 {amiibo['gameSeries']}")

                opciones = ["Faltante", "Obtenido", "Deseado"]
                curr_idx = opciones.index(estado_actual) if estado_actual in opciones else 0
                
                nuevo_estado = st.selectbox(
                    "Estado:",
                    options=opciones,
                    index=curr_idx,
                    key=f"sel_{uid}",
                    label_visibility="collapsed"
                )

                if nuevo_estado != estado_actual:
                    if nuevo_estado == "Faltante":
                        st.session_state.coleccion.pop(uid, None)
                    else:
                        st.session_state.coleccion[uid] = nuevo_estado
                    
                    guardar_coleccion_usuario(st.session_state.coleccion)
                    st.rerun()
                
                st.divider()

# Filtrado por búsqueda
def filtrar_items(lista):
    if not busqueda:
        return lista
    q = busqueda.lower()
    return [a for a in lista if q in a["name"].lower() or q in a["gameSeries"].lower()]

filtrados = filtrar_items(catalogo_smash)

# --- PESTAÑAS PRINCIPALES ---
tab_todos, tab_obtenidos, tab_faltantes, tab_deseos = st.tabs([
    f"📚 Todos ({len(filtrados)})",
    f"✅ Obtenidos ({sum(1 for a in filtrados if st.session_state.coleccion.get(a['uid']) == 'Obtenido')})",
    f"⏳ Faltantes ({sum(1 for a in filtrados if st.session_state.coleccion.get(a['uid']) != 'Obtenido')})",
    f"⭐ Lista de Deseos ({sum(1 for a in filtrados if st.session_state.coleccion.get(a['uid']) == 'Deseado')})"
])

with tab_todos:
    render_grid(filtrados)

with tab_obtenidos:
    render_grid([a for a in filtrados if st.session_state.coleccion.get(a["uid"]) == "Obtenido"])

with tab_faltantes:
    render_grid([a for a in filtrados if st.session_state.coleccion.get(a["uid"]) != "Obtenido"])

with tab_deseos:
    render_grid([a for a in filtrados if st.session_state.coleccion.get(a["uid"]) == "Deseado"])