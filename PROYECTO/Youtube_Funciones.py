import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
from typing import Optional, Dict, Any, List

import Variables
import Alertas
import Botones_Funciones
from Database import Database
from Downloader_Engine import DownloaderEngine, format_seconds, format_bytes, parse_time_str

current_analyzed_info: Optional[Dict[str, Any]] = None

# Controles de interfaz
entry_url = None
lbl_preview_title = None
lbl_preview_meta = None
lbl_preview_thumb = None
combo_formato = None
combo_calidad = None
combo_velocidad = None
combo_cookies = None
combo_paralelo = None

# Variables de checkboxes
chk_metadata_var = None
chk_subtitles_var = None
chk_trim_var = None
chk_notify_var = None
chk_open_finish_var = None
chk_suspend_finish_var = None

# Recorte de tiempo
frame_trim_inputs = None
entry_trim_start = None
entry_trim_end = None

# Progreso
frame_progreso = None
pbar = None
lbl_progreso_pct = None
lbl_progreso_detalles = None
lbl_progreso_titulo = None
btn_cancelar = None

carpeta_salida_actual = Variables.carpeta_descargas_default

def Centro_youtube(parent_frame):
    """Construye la vista moderna, responsiva y completa con todas las herramientas élite."""
    global entry_url, lbl_preview_title, lbl_preview_meta, lbl_preview_thumb
    global combo_formato, combo_calidad, combo_velocidad, combo_cookies, combo_paralelo
    global chk_metadata_var, chk_subtitles_var, chk_trim_var, chk_notify_var, chk_open_finish_var, chk_suspend_finish_var
    global frame_trim_inputs, entry_trim_start, entry_trim_end
    global frame_progreso, pbar, lbl_progreso_pct, lbl_progreso_detalles, lbl_progreso_titulo, btn_cancelar

    container = ttk.Frame(parent_frame, padding=(10, 6))
    container.pack(fill="both", expand=True)

    # ==========================================
    # 1. TARJETA DE BÚSQUEDA Y URL
    # ==========================================
    card_busqueda = ttk.LabelFrame(container, text=" Enlace de Video, Playlist o Búsqueda Directa ", padding=(8, 6))
    card_busqueda.pack(fill="x", pady=(0, 5))

    frame_input = ttk.Frame(card_busqueda)
    frame_input.pack(fill="x")

    placeholder = "Pega una URL o escribe para buscar en YouTube (ej: música para programar)..."
    url_var = tk.StringVar(value="")

    entry_url = ttk.Entry(frame_input, textvariable=url_var, font=("Helvetica", 10))
    entry_url.pack(side="left", fill="x", expand=True, padx=(0, 6), ipady=3)
    entry_url.insert(0, placeholder)

    def on_entry_focus_in(event):
        if entry_url.get() == placeholder:
            entry_url.delete(0, tk.END)

    def on_entry_focus_out(event):
        if not entry_url.get().strip():
            entry_url.insert(0, placeholder)

    entry_url.bind("<FocusIn>", on_entry_focus_in)
    entry_url.bind("<FocusOut>", on_entry_focus_out)
    entry_url.bind("<Return>", lambda event: accion_analizar_o_buscar())

    btn_pegar = ttk.Button(frame_input, text="📋 Pegar", width=8, command=accion_pegar_portapapeles)
    btn_pegar.pack(side="left", padx=(0, 4))

    btn_analizar = ttk.Button(frame_input, text="🔍 Analizar", width=9, style="Accent.TButton", command=accion_analizar_o_buscar)
    btn_analizar.pack(side="left", padx=(0, 4))

    btn_buscar_popup = ttk.Button(frame_input, text="🔎 Buscador", width=10, command=lambda: abrir_modal_buscador(entry_url.get()))
    btn_buscar_popup.pack(side="left", padx=(0, 4))

    btn_web = ttk.Button(frame_input, text="🌐 YouTube", width=10, command=accion_abrir_youtube)
    btn_web.pack(side="left")

    # ==========================================
    # 2. TARJETA DE VISTA PREVIA Y HERRAMIENTAS ÉLITE
    # ==========================================
    card_preview = ttk.LabelFrame(container, text=" Previsualización y Configuración Avanzada ", padding=(8, 6))
    card_preview.pack(fill="x", pady=(0, 5))

    frame_prev_inner = ttk.Frame(card_preview)
    frame_prev_inner.pack(fill="x")

    # Miniatura
    frame_thumb = ttk.Frame(frame_prev_inner, width=155, height=88)
    frame_thumb.pack(side="left", padx=(0, 10))
    frame_thumb.pack_propagate(False)

    lbl_preview_thumb = ttk.Label(frame_thumb, text="Sin vista previa", anchor="center")
    lbl_preview_thumb.pack(fill="both", expand=True)

    # Detalles
    frame_detalles = ttk.Frame(frame_prev_inner)
    frame_detalles.pack(side="left", fill="both", expand=True)

    lbl_preview_title = ttk.Label(
        frame_detalles,
        text="Introduce un enlace o término y pulsa 'Analizar' para ver detalles",
        font=("Helvetica", 10, "bold"),
        wraplength=500
    )
    lbl_preview_title.pack(anchor="w", pady=(0, 2))

    def _ajustar_wrap(event):
        nuevo_wrap = max(250, event.width - 20)
        lbl_preview_title.config(wraplength=nuevo_wrap)

    frame_detalles.bind("<Configure>", _ajustar_wrap)

    lbl_preview_meta = ttk.Label(
        frame_detalles,
        text="Canal: -- | Duración: --:-- | Calidad: 1080p",
        font=("Helvetica", 8),
        foreground="#94a3b8"
    )
    lbl_preview_meta.pack(anchor="w", pady=(0, 4))

    # Fila 1 de opciones: Formato, Calidad, Límite de Velocidad y Cookies
    frame_combos = ttk.Frame(frame_detalles)
    frame_combos.pack(anchor="w", pady=(0, 3))

    ttk.Label(frame_combos, text="Formato:").pack(side="left", padx=(0, 3))
    formatos = ["MP4 (Video)", "MP3 (Audio)", "M4A (Audio)", "WAV", "FLAC"]
    formato_var = tk.StringVar(value="MP4 (Video)")
    combo_formato = ttk.Combobox(frame_combos, textvariable=formato_var, values=formatos, state="readonly", width=11)
    combo_formato.pack(side="left", padx=(0, 8))

    ttk.Label(frame_combos, text="Calidad:").pack(side="left", padx=(0, 3))
    calidades_video = ["Mejor", "2160p (4K)", "1440p (2K)", "1080p", "720p", "480p", "360p"]
    calidades_audio = ["320 kbps (Máx)", "256 kbps (Alta)", "192 kbps (Estándar)", "128 kbps (Básica)"]
    calidad_var = tk.StringVar(value="1080p")
    combo_calidad = ttk.Combobox(frame_combos, textvariable=calidad_var, values=calidades_video, state="readonly", width=13)
    combo_calidad.pack(side="left", padx=(0, 8))

    def on_formato_changed(event):
        fmt = formato_var.get()
        if "MP4" in fmt:
            combo_calidad.config(values=calidades_video)
            combo_calidad.set("1080p")
        else:
            combo_calidad.config(values=calidades_audio)
            combo_calidad.set("320 kbps (Máx)")

    combo_formato.bind("<<ComboboxSelected>>", on_formato_changed)

    ttk.Label(frame_combos, text="Velocidad:").pack(side="left", padx=(0, 3))
    velocidades = ["Ilimitada", "10 MB/s", "5 MB/s", "2 MB/s", "1 MB/s"]
    vel_var = tk.StringVar(value="Ilimitada")
    combo_velocidad = ttk.Combobox(frame_combos, textvariable=vel_var, values=velocidades, state="readonly", width=10)
    combo_velocidad.pack(side="left", padx=(0, 8))

    ttk.Label(frame_combos, text="Cookies:").pack(side="left", padx=(0, 3))
    cookies_opts = ["Ninguno", "Firefox", "Chrome", "Brave", "Edge", "Chromium"]
    cookies_var = tk.StringVar(value="Ninguno")
    combo_cookies = ttk.Combobox(frame_combos, textvariable=cookies_var, values=cookies_opts, state="readonly", width=9)
    combo_cookies.pack(side="left")

    # Fila 2 de opciones: Checkboxes con Recorte, Notificaciones y Auto-Abrir
    frame_checks = ttk.Frame(frame_detalles)
    frame_checks.pack(anchor="w", pady=(0, 3))

    chk_metadata_var = tk.BooleanVar(value=True)
    chk_subtitles_var = tk.BooleanVar(value=False)
    chk_trim_var = tk.BooleanVar(value=False)
    chk_notify_var = tk.BooleanVar(value=True)
    chk_open_finish_var = tk.BooleanVar(value=False)

    ttk.Checkbutton(frame_checks, text="Carátula / ID3", variable=chk_metadata_var).pack(side="left", padx=(0, 6))
    ttk.Checkbutton(frame_checks, text="Subtítulos", variable=chk_subtitles_var).pack(side="left", padx=(0, 6))

    def on_toggle_trim():
        if chk_trim_var.get():
            frame_trim_inputs.pack(side="left", padx=(6, 0))
        else:
            frame_trim_inputs.pack_forget()

    chk_trim = ttk.Checkbutton(frame_checks, text="✂️ Recortar", variable=chk_trim_var, command=on_toggle_trim)
    chk_trim.pack(side="left", padx=(0, 6))

    # Entradas de tiempo de recorte
    frame_trim_inputs = ttk.Frame(frame_checks)
    ttk.Label(frame_trim_inputs, text="De:").pack(side="left", padx=(2, 2))
    entry_trim_start = ttk.Entry(frame_trim_inputs, width=5)
    entry_trim_start.insert(0, "00:00")
    entry_trim_start.pack(side="left", padx=(0, 4))
    ttk.Label(frame_trim_inputs, text="A:").pack(side="left", padx=(2, 2))
    entry_trim_end = ttk.Entry(frame_trim_inputs, width=5)
    entry_trim_end.insert(0, "01:30")
    entry_trim_end.pack(side="left", padx=(0, 6))

    ttk.Checkbutton(frame_checks, text="🔔 Notificar", variable=chk_notify_var).pack(side="left", padx=(0, 6))
    ttk.Checkbutton(frame_checks, text="📂 Abrir al terminar", variable=chk_open_finish_var).pack(side="left")

    # Fila 3: Botones de acción principales
    frame_action_btns = ttk.Frame(frame_detalles)
    frame_action_btns.pack(anchor="w", pady=(2, 0))

    btn_descargar_ahora = ttk.Button(
        frame_action_btns,
        text="⬇️ Descargar Ahora",
        style="Accent.TButton",
        command=accion_descargar_inmediato
    )
    btn_descargar_ahora.pack(side="left", padx=(0, 6))

    btn_agregar_cola = ttk.Button(
        frame_action_btns,
        text="➕ A la Cola",
        command=accion_agregar_a_cola
    )
    btn_agregar_cola.pack(side="left", padx=(0, 6))

    btn_carpeta = ttk.Button(
        frame_action_btns,
        text="📁 Carpeta Destino",
        command=accion_cambiar_carpeta
    )
    btn_carpeta.pack(side="left", padx=(0, 6))

    btn_play_quick = ttk.Button(
        frame_action_btns,
        text="▶ Reproducir Sel.",
        command=Botones_Funciones.reproducir_seleccionado
    )
    btn_play_quick.pack(side="left")

    # ==========================================
    # 3. TARJETA DE PROGRESO DE DESCARGA
    # ==========================================
    frame_progreso = ttk.LabelFrame(container, text=" Progreso de Descarga en Vivo ", padding=(8, 4))
    frame_progreso.pack(fill="x", pady=(0, 5))

    frame_pbar_row = ttk.Frame(frame_progreso)
    frame_pbar_row.pack(fill="x", pady=(1, 3))

    pbar = ttk.Progressbar(frame_pbar_row, mode="determinate", maximum=100)
    pbar.pack(side="left", fill="x", expand=True, padx=(0, 6))

    lbl_progreso_pct = ttk.Label(frame_pbar_row, text="0%", font=("Helvetica", 9, "bold"), width=6, anchor="center")
    lbl_progreso_pct.pack(side="left", padx=(0, 6))

    btn_cancelar = ttk.Button(frame_pbar_row, text="⏹️ Cancelar", width=10, command=Botones_Funciones.cancelar_descarga)
    btn_cancelar.pack(side="left")

    frame_pbar_meta = ttk.Frame(frame_progreso)
    frame_pbar_meta.pack(fill="x")

    lbl_progreso_titulo = ttk.Label(frame_pbar_meta, text="En espera de descarga...", font=("Helvetica", 8))
    lbl_progreso_titulo.pack(side="left", fill="x", expand=True)

    lbl_progreso_detalles = ttk.Label(
        frame_pbar_meta,
        text="Velocidad: -- | Restante: --:-- | 0 MB / 0 MB",
        font=("Helvetica", 8),
        foreground="#94a3b8"
    )
    lbl_progreso_detalles.pack(side="right")

    # ==========================================
    # 4. COLA DE DESCARGAS E HISTORIAL
    # ==========================================
    card_cola = ttk.LabelFrame(container, text=" Cola de Descargas e Historial ", padding=(8, 5))
    card_cola.pack(fill="both", expand=True)

    # Treeview
    Botones_Funciones.crear_treeview(card_cola)

    # Barra inferior con control de descargas paralelas
    frame_cola_btns = ttk.Frame(card_cola)
    frame_cola_btns.pack(fill="x", pady=(5, 0))

    frame_btns_left = ttk.Frame(frame_cola_btns)
    frame_btns_left.pack(side="left")

    btn_descargar_sel = ttk.Button(
        frame_btns_left,
        text="⬇️ Descargar Sel.",
        style="Accent.TButton",
        command=accion_descargar_seleccionado_cola
    )
    btn_descargar_sel.pack(side="left", padx=(0, 4))

    btn_descargar_todo = ttk.Button(
        frame_btns_left,
        text="⚡ Descargar Todo",
        command=accion_descargar_todo_cola
    )
    btn_descargar_todo.pack(side="left", padx=(0, 6))

    ttk.Label(frame_btns_left, text="Paralelo:").pack(side="left", padx=(2, 2))
    paralelo_var = tk.StringVar(value="2")
    combo_paralelo = ttk.Combobox(frame_btns_left, textvariable=paralelo_var, values=["1", "2", "3", "4"], state="readonly", width=3)
    combo_paralelo.pack(side="left", padx=(0, 6))

    btn_abrir_destino = ttk.Button(
        frame_btns_left,
        text="📂 Abrir Carpeta",
        command=lambda: Botones_Funciones.abrir_carpeta(carpeta_salida_actual)
    )
    btn_abrir_destino.pack(side="left")

    # Checkbox suspender al terminar la cola
    chk_suspend_finish_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(frame_btns_left, text="💤 Suspender al terminar", variable=chk_suspend_finish_var).pack(side="left", padx=(8, 0))

    frame_btns_right = ttk.Frame(frame_cola_btns)
    frame_btns_right.pack(side="right")

    btn_eliminar = ttk.Button(
        frame_btns_right,
        text="🗑️ Quitar",
        command=Botones_Funciones.eliminar_seleccionado
    )
    btn_eliminar.pack(side="left", padx=(0, 4))

    btn_limpiar = ttk.Button(
        frame_btns_right,
        text="🧹 Limpiar Cola",
        command=Botones_Funciones.clear
    )
    btn_limpiar.pack(side="left")

    return container

# ==========================================
# BUSCADOR INTERACTIVO INTEGRADO DE YOUTUBE
# ==========================================

def abrir_modal_buscador(query_inicial: str = ""):
    """Abre una ventana emergente para buscar videos en YouTube sin usar el navegador."""
    modal = tk.Toplevel(Variables.root)
    modal.title("🔍 Buscador de YouTube Integrado")
    modal.geometry("750x450")
    modal.minsize(600, 350)
    modal.transient(Variables.root)
    modal.grab_set()

    frame_m_top = ttk.Frame(modal, padding=10)
    frame_m_top.pack(fill="x")

    clean_q = query_inicial if ("http" not in query_inicial and "Pega una URL" not in query_inicial) else ""
    m_var = tk.StringVar(value=clean_q)

    ent_busqueda = ttk.Entry(frame_m_top, textvariable=m_var, font=("Helvetica", 10))
    ent_busqueda.pack(side="left", fill="x", expand=True, padx=(0, 6), ipady=3)

    lbl_estado = ttk.Label(modal, text="Escribe una búsqueda y pulsa 'Buscar'...", font=("Helvetica", 9), foreground="#94a3b8")
    lbl_estado.pack(anchor="w", padx=12, pady=(0, 4))

    # Treeview de resultados
    frame_m_results = ttk.Frame(modal, padding=(10, 0))
    frame_m_results.pack(fill="both", expand=True)

    cols = ("index", "title", "uploader", "duration")
    tv_res = ttk.Treeview(frame_m_results, columns=cols, show="headings", selectmode="browse")
    tv_res.heading("index", text="#")
    tv_res.heading("title", text="Título")
    tv_res.heading("uploader", text="Canal")
    tv_res.heading("duration", text="Duración")

    tv_res.column("index", width=35, anchor="center")
    tv_res.column("title", width=380, anchor="w")
    tv_res.column("uploader", width=140, anchor="w")
    tv_res.column("duration", width=70, anchor="center")

    scroll_m = ttk.Scrollbar(frame_m_results, orient="vertical", command=tv_res.yview)
    tv_res.configure(yscrollcommand=scroll_m.set)
    scroll_m.pack(side="right", fill="y")
    tv_res.pack(side="left", fill="both", expand=True)

    resultados_cache: List[Dict[str, Any]] = []

    def ejecutar_busqueda():
        q = ent_busqueda.get().strip()
        if not q:
            return
        lbl_estado.config(text=f"Buscando '{q}' en YouTube... Por favor espera.")
        tv_res.delete(*tv_res.get_children())

        def _worker():
            nonlocal resultados_cache
            try:
                resultados_cache = DownloaderEngine.search_youtube(q, max_results=8)
                modal.after(0, _poblar_resultados)
            except Exception as e:
                modal.after(0, lambda: lbl_estado.config(text=f"Error en búsqueda: {e}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _poblar_resultados():
        nonlocal resultados_cache
        lbl_estado.config(text=f"Se encontraron {len(resultados_cache)} resultados. Selecciona uno:")
        for idx, r in enumerate(resultados_cache):
            tv_res.insert("", "end", iid=str(idx), values=(idx + 1, r['title'], r['uploader'], r['duration_str']))

    btn_search_m = ttk.Button(frame_m_top, text="🔍 Buscar", style="Accent.TButton", command=ejecutar_busqueda)
    btn_search_m.pack(side="left")
    ent_busqueda.bind("<Return>", lambda e: ejecutar_busqueda())

    def cargar_seleccionado():
        sel = tv_res.selection()
        if not sel:
            Alertas.alerta_Amarilla(Variables.titulo, "Selección", "Selecciona un video de la lista.")
            return
        idx = int(sel[0])
        elegido = resultados_cache[idx]
        entry_url.delete(0, tk.END)
        entry_url.insert(0, elegido['url'])
        modal.destroy()
        iniciar_analisis()

    frame_m_bottom = ttk.Frame(modal, padding=10)
    frame_m_bottom.pack(fill="x")

    btn_cargar = ttk.Button(frame_m_bottom, text="✅ Cargar en la App", style="Accent.TButton", command=cargar_seleccionado)
    btn_cargar.pack(side="left", padx=(0, 6))

    btn_cancel_m = ttk.Button(frame_m_bottom, text="Cerrar", command=modal.destroy)
    btn_cancel_m.pack(side="right")

    if clean_q:
        ejecutar_busqueda()

# ==========================================
# ACCIONES Y CONTROLADORES
# ==========================================

def parsear_limite_velocidad() -> Optional[int]:
    """Obtiene los bytes por segundo a partir del combobox de velocidad."""
    val = combo_velocidad.get() if combo_velocidad else "Ilimitada"
    if "10 MB" in val:
        return 10 * 1024 * 1024
    elif "5 MB" in val:
        return 5 * 1024 * 1024
    elif "2 MB" in val:
        return 2 * 1024 * 1024
    elif "1 MB" in val:
        return 1 * 1024 * 1024
    return None

def parsear_recorte_tiempo() -> Optional[tuple]:
    """Obtiene el rango de tiempo de inicio y fin en segundos si el recorte está activado."""
    if not chk_trim_var.get():
        return None
    s_start = entry_trim_start.get().strip() if entry_trim_start else ""
    s_end = entry_trim_end.get().strip() if entry_trim_end else ""
    t_start = parse_time_str(s_start) or 0
    t_end = parse_time_str(s_end)
    if t_end is not None and t_end > t_start:
        return (t_start, t_end)
    return None

def accion_pegar_portapapeles():
    try:
        texto = Variables.root.clipboard_get().strip()
        if texto:
            entry_url.delete(0, tk.END)
            entry_url.insert(0, texto)
            if texto.startswith("http://") or texto.startswith("https://"):
                iniciar_analisis()
    except Exception:
        pass

def accion_abrir_youtube():
    query = entry_url.get().strip()
    placeholder = "Pega una URL"
    if not query or placeholder in query:
        Botones_Funciones.abrir_link("https://www.youtube.com")
    else:
        Botones_Funciones.abrir_link(query)

def accion_analizar_o_buscar():
    texto = entry_url.get().strip()
    if not texto or "Pega una URL" in texto:
        Alertas.alerta_Amarilla(Variables.titulo, "Campo vacío", "Introduce una URL o término de búsqueda.")
        return

    if texto.startswith("http://") or texto.startswith("https://"):
        iniciar_analisis()
    else:
        abrir_modal_buscador(texto)

def accion_cambiar_carpeta():
    global carpeta_salida_actual
    nueva = filedialog.askdirectory(initialdir=carpeta_salida_actual, title="Seleccionar Carpeta de Descargas")
    if nueva:
        carpeta_salida_actual = nueva
        Alertas.alerta_ok(Variables.titulo, "Carpeta Actualizada", f"Las descargas se guardarán en:\n{carpeta_salida_actual}")

def iniciar_analisis():
    url = entry_url.get().strip()
    if not url or "Pega una URL" in url:
        Alertas.alerta_Amarilla(Variables.titulo, "Campo vacío", "Introduce una URL válida para analizar.")
        return

    cookies_browser = combo_cookies.get() if combo_cookies else "Ninguno"
    lbl_preview_title.config(text="🔍 Analizando enlace con yt-dlp... Por favor espera.")
    lbl_preview_meta.config(text="Obteniendo metadatos, calidades y miniaturas...")

    def _worker():
        try:
            info = DownloaderEngine.extract_info(url, cookies_browser=cookies_browser)
            Variables.root.after(0, lambda: _mostrar_resultado_analisis(info))
        except Exception as e:
            err = str(e)
            Variables.root.after(0, lambda: _mostrar_error_analisis(err))

    threading.Thread(target=_worker, daemon=True).start()

def _mostrar_resultado_analisis(info: Dict[str, Any]):
    global current_analyzed_info
    current_analyzed_info = info

    if info.get('is_playlist'):
        titulo = info.get('title', 'Lista de reproducción')
        conteo = info.get('count', 0)
        lbl_preview_title.config(text=f"📋 Playlist: {titulo} ({conteo} videos)")
        lbl_preview_meta.config(text=f"Canal/Creador: {info.get('uploader')} | Total videos: {conteo}")
        lbl_preview_thumb.config(text="📋 Playlist", image="")

        res = Alertas.alerta_aceptar(
            Variables.titulo,
            "Playlist Detectada",
            f"Se encontraron {conteo} videos en la lista:\n'{titulo}'.\n\n¿Deseas agregarlos todos a la cola de descargas?"
        )
        if res == 1:
            Database.add_batch(info.get('entries', []))
            Botones_Funciones.actualizar_treeview()
            Alertas.alerta_ok(Variables.titulo, "Lista Agregada", f"{conteo} videos han sido agregados a la cola.")
    else:
        titulo = info.get('title', 'Sin título')
        duracion = info.get('duration_str', '--:--')
        uploader = info.get('uploader', 'Desconocido')
        vistas = info.get('views', 0)
        vistas_str = f"{vistas:,}" if vistas else "N/A"

        lbl_preview_title.config(text=titulo)
        lbl_preview_meta.config(text=f"Canal: {uploader} | Duración: {duracion} | Vistas: {vistas_str}")

        thumb_url = info.get('thumbnail')
        if thumb_url:
            Botones_Funciones.descargar_miniatura_async(thumb_url, _actualizar_miniatura_ui)

        resoluciones = info.get('resolutions', [])
        if resoluciones and "MP4" in combo_formato.get():
            combo_calidad.config(values=["Mejor"] + resoluciones)
            combo_calidad.set(resoluciones[0] if resoluciones else "1080p")

def _actualizar_miniatura_ui(photo):
    if photo:
        lbl_preview_thumb.config(image=photo, text="")
        lbl_preview_thumb.image = photo
    else:
        lbl_preview_thumb.config(text="▶ Video", image="")

def _mostrar_error_analisis(err_msg: str):
    lbl_preview_title.config(text="❌ Error al analizar el enlace")
    lbl_preview_meta.config(text="Verifica tu conexión o que la URL sea válida.")
    Alertas.alerta_error(Variables.titulo, "Error de Análisis", f"No se pudo extraer información del enlace:\n\n{err_msg}")

def accion_agregar_a_cola():
    global current_analyzed_info
    if not current_analyzed_info:
        url = entry_url.get().strip()
        if url and not "Pega una URL" in url:
            iniciar_analisis()
        else:
            Alertas.alerta_Amarilla(Variables.titulo, "Aviso", "Primero analiza un enlace válido antes de agregarlo.")
        return

    if current_analyzed_info.get('is_playlist'):
        Database.add_batch(current_analyzed_info.get('entries', []))
    else:
        Database.add_video(
            title=current_analyzed_info.get('title', 'Video'),
            duration=current_analyzed_info.get('duration_str', '00:00'),
            status=Variables.Pendiente,
            link=current_analyzed_info.get('url', ''),
            thumbnail=current_analyzed_info.get('thumbnail', ''),
            uploader=current_analyzed_info.get('uploader', '')
        )
    Botones_Funciones.actualizar_treeview()
    Alertas.alerta_ok(Variables.titulo, "Cola Actualizada", "El elemento ha sido agregado a la cola con éxito.")

def _progreso_callback(d: Dict[str, Any]):
    percent = d.get('percent', 0.0)
    pbar['value'] = percent
    lbl_progreso_pct.config(text=d.get('percent_str', f"{percent:.1f}%"))

    speed = d.get('speed_str', '--')
    eta = d.get('eta_str', '--')
    dl_str = d.get('downloaded_str', '')
    total_str = d.get('total_str', '')
    fname = d.get('filename') or d.get('title', '')

    if fname:
        lbl_progreso_titulo.config(text=f"Descargando: {fname}")
    lbl_progreso_detalles.config(text=f"Velocidad: {speed} | Restante: {eta} | {dl_str} / {total_str}")

def accion_descargar_inmediato():
    global current_analyzed_info, carpeta_salida_actual
    if not current_analyzed_info:
        url = entry_url.get().strip()
        if url and "http" in url:
            iniciar_analisis()
            return
        Alertas.alerta_Amarilla(Variables.titulo, "Aviso", "Introduce y analiza un video antes de descargar.")
        return

    url = current_analyzed_info.get('url')
    formato_raw = combo_formato.get().split()[0]
    calidad = combo_calidad.get()
    meta = chk_metadata_var.get()
    subs = chk_subtitles_var.get()
    t_range = parsear_recorte_tiempo()
    ratelimit = parsear_limite_velocidad()
    cookies_browser = combo_cookies.get()
    open_on_finish = chk_open_finish_var.get()
    notify_on_finish = chk_notify_var.get()

    Database.add_video(
        title=current_analyzed_info.get('title', 'Video'),
        duration=current_analyzed_info.get('duration_str', '00:00'),
        status=Variables.Descargando,
        link=url,
        thumbnail=current_analyzed_info.get('thumbnail', ''),
        uploader=current_analyzed_info.get('uploader', '')
    )
    Botones_Funciones.actualizar_treeview()

    pbar['value'] = 0
    lbl_progreso_pct.config(text="0%")
    lbl_progreso_titulo.config(text=f"Iniciando descarga: {current_analyzed_info.get('title')}")

    def on_complete(success: bool, msg: str, final_path: str):
        if success:
            pbar['value'] = 100
            lbl_progreso_pct.config(text="100%")
            lbl_progreso_titulo.config(text="✅ Descarga completada")
            lbl_progreso_detalles.config(text="Archivo procesado con éxito.")
            Alertas.alerta_ok(Variables.titulo, "Descarga Finalizada", msg)
        else:
            lbl_progreso_titulo.config(text="❌ Descarga no completada")
            Alertas.alerta_error(Variables.titulo, "Aviso de Descarga", msg)

    Botones_Funciones.ejecutar_descarga(
        url=url,
        output_dir=carpeta_salida_actual,
        format_type=formato_raw,
        quality=calidad,
        embed_metadata=meta,
        embed_thumbnail=meta,
        download_subtitles=subs,
        time_range=t_range,
        rate_limit_bytes=ratelimit,
        cookies_browser=cookies_browser,
        open_on_finish=open_on_finish,
        notify_on_finish=notify_on_finish,
        on_progress=_progreso_callback,
        on_complete=on_complete
    )

def accion_descargar_seleccionado_cola():
    if not Botones_Funciones.treeview_ref:
        return
    seleccion = Botones_Funciones.treeview_ref.selection()
    if not seleccion:
        Alertas.alerta_Amarilla(Variables.titulo, "Selección", "Selecciona un elemento de la lista para descargar.")
        return

    item_id = int(seleccion[0])
    registros = Database.get_all()
    target = next((r for r in registros if r[0] == item_id), None)
    if not target:
        return

    url = target[4]
    title = target[1]
    formato_raw = combo_formato.get().split()[0]
    calidad = combo_calidad.get()
    meta = chk_metadata_var.get()
    subs = chk_subtitles_var.get()
    t_range = parsear_recorte_tiempo()
    ratelimit = parsear_limite_velocidad()
    cookies_browser = combo_cookies.get()
    open_on_finish = chk_open_finish_var.get()
    notify_on_finish = chk_notify_var.get()

    pbar['value'] = 0
    lbl_progreso_pct.config(text="0%")
    lbl_progreso_titulo.config(text=f"Descargando de cola: {title}")

    def on_complete(success: bool, msg: str, final_path: str):
        if success:
            pbar['value'] = 100
            lbl_progreso_pct.config(text="100%")
            lbl_progreso_titulo.config(text=f"✅ Descarga completada: {title}")
            Alertas.alerta_ok(Variables.titulo, "Descarga Finalizada", msg)
        else:
            lbl_progreso_titulo.config(text="❌ Error en la descarga")
            Alertas.alerta_error(Variables.titulo, "Aviso de Descarga", msg)

    Botones_Funciones.ejecutar_descarga(
        url=url,
        output_dir=carpeta_salida_actual,
        format_type=formato_raw,
        quality=calidad,
        embed_metadata=meta,
        embed_thumbnail=meta,
        download_subtitles=subs,
        time_range=t_range,
        rate_limit_bytes=ratelimit,
        cookies_browser=cookies_browser,
        open_on_finish=open_on_finish,
        notify_on_finish=notify_on_finish,
        on_progress=_progreso_callback,
        on_complete=on_complete
    )

def accion_descargar_todo_cola():
    pendientes = Database.get_pending()
    if not pendientes:
        Alertas.alerta_ok(Variables.titulo, "Cola vacía", "No hay videos pendientes por descargar en la cola.")
        return

    res = Alertas.alerta_aceptar(
        Variables.titulo,
        "Descarga por Lotes",
        f"Se descargarán {len(pendientes)} videos pendientes en:\n{carpeta_salida_actual}\n\n¿Deseas iniciar ahora?"
    )
    if res != 1:
        return

    formato_raw = combo_formato.get().split()[0]
    calidad = combo_calidad.get()
    meta = chk_metadata_var.get()
    subs = chk_subtitles_var.get()
    t_range = parsear_recorte_tiempo()
    ratelimit = parsear_limite_velocidad()
    cookies_browser = combo_cookies.get()
    notify_on_finish = chk_notify_var.get()
    suspend_on_finish = chk_suspend_finish_var.get()
    concurrencia = int(combo_paralelo.get()) if combo_paralelo else 2

    def on_all_complete(completados: int, total: int):
        pbar['value'] = 100
        lbl_progreso_pct.config(text="100%")
        lbl_progreso_titulo.config(text=f"✅ Descarga masiva finalizada: {completados}/{total} videos completados")
        Alertas.alerta_ok(
            Variables.titulo,
            "Proceso Terminado",
            f"Se completaron {completados} de {total} descargas.\n\nCarpeta: {carpeta_salida_actual}"
        )

    Botones_Funciones.ejecutar_descarga_cola(
        output_dir=carpeta_salida_actual,
        format_type=formato_raw,
        quality=calidad,
        embed_metadata=meta,
        embed_thumbnail=meta,
        download_subtitles=subs,
        time_range=t_range,
        rate_limit_bytes=ratelimit,
        cookies_browser=cookies_browser,
        concurrency=concurrencia,
        notify_on_finish=notify_on_finish,
        suspend_on_finish=suspend_on_finish,
        on_progress=_progreso_callback,
        on_complete=on_all_complete
    )
