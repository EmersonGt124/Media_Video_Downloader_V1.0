import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
from typing import Optional, Dict, Any

import Variables
import Alertas
import Botones_Funciones
from Database import Database
from Downloader_Engine import DownloaderEngine, format_seconds, format_bytes

# Variables de la vista
current_analyzed_info: Optional[Dict[str, Any]] = None
thumb_label_ref: Optional[ttk.Label] = None
default_no_thumb_img: Optional[ImageTk.PhotoImage] = None

# Controles de interfaz
entry_url = None
lbl_preview_title = None
lbl_preview_meta = None
lbl_preview_thumb = None
combo_formato = None
combo_calidad = None
chk_metadata_var = None
chk_subtitles_var = None
btn_descargar_ahora = None
btn_agregar_cola = None

# Progreso
frame_progreso = None
pbar = None
lbl_progreso_pct = None
lbl_progreso_detalles = None
lbl_progreso_titulo = None
btn_cancelar = None

# Carpeta de salida elegida por el usuario
carpeta_salida_actual = Variables.carpeta_descargas_default

def Centro_youtube(parent_frame):
    """Construye la vista principal moderna del descargador multimedia."""
    global entry_url, lbl_preview_title, lbl_preview_meta, lbl_preview_thumb
    global combo_formato, combo_calidad, chk_metadata_var, chk_subtitles_var
    global btn_descargar_ahora, btn_agregar_cola
    global frame_progreso, pbar, lbl_progreso_pct, lbl_progreso_detalles, lbl_progreso_titulo, btn_cancelar

    container = ttk.Frame(parent_frame, padding=12)
    container.pack(fill="both", expand=True)

    # ==========================================
    # 1. TARJETA DE BÚSQUEDA Y URL
    # ==========================================
    card_busqueda = ttk.LabelFrame(container, text="  Enlace de Video o Lista de Reproducción  ", padding=10)
    card_busqueda.pack(fill="x", pady=(0, 8))

    frame_input = ttk.Frame(card_busqueda)
    frame_input.pack(fill="x")

    placeholder = "Pega una URL (YouTube, Playlist, Shorts, TikTok, Instagram, Twitter/X...)"
    url_var = tk.StringVar(value="")

    entry_url = ttk.Entry(frame_input, textvariable=url_var, font=("Helvetica", 11))
    entry_url.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=4)
    entry_url.insert(0, placeholder)

    def on_entry_focus_in(event):
        if entry_url.get() == placeholder:
            entry_url.delete(0, tk.END)

    def on_entry_focus_out(event):
        if not entry_url.get().strip():
            entry_url.insert(0, placeholder)

    entry_url.bind("<FocusIn>", on_entry_focus_in)
    entry_url.bind("<FocusOut>", on_entry_focus_out)
    entry_url.bind("<Return>", lambda event: iniciar_analisis())

    # Botones de acción del input
    btn_pegar = ttk.Button(frame_input, text="📋 Pegar", command=lambda: accion_pegar_portapapeles())
    btn_pegar.pack(side="left", padx=(0, 6))

    btn_analizar = ttk.Button(frame_input, text="🔍 Analizar", style="Accent.TButton", command=lambda: iniciar_analisis())
    btn_analizar.pack(side="left", padx=(0, 6))

    btn_web = ttk.Button(frame_input, text="🌐 Abrir YouTube", command=lambda: accion_abrir_youtube())
    btn_web.pack(side="left")

    # ==========================================
    # 2. TARJETA DE VISTA PREVIA Y OPCIONES
    # ==========================================
    card_preview = ttk.LabelFrame(container, text="  Opciones y Previsualización  ", padding=10)
    card_preview.pack(fill="x", pady=(0, 8))

    frame_prev_inner = ttk.Frame(card_preview)
    frame_prev_inner.pack(fill="x")

    # Columna Izquierda: Miniatura
    frame_thumb = ttk.Frame(frame_prev_inner, width=170, height=95)
    frame_thumb.pack(side="left", padx=(0, 14))
    frame_thumb.pack_propagate(False)

    lbl_preview_thumb = ttk.Label(frame_thumb, text="Sin vista previa", anchor="center")
    lbl_preview_thumb.pack(fill="both", expand=True)

    # Columna Derecha: Información y Opciones
    frame_detalles = ttk.Frame(frame_prev_inner)
    frame_detalles.pack(side="left", fill="both", expand=True)

    lbl_preview_title = ttk.Label(
        frame_detalles,
        text="Introduce un enlace y pulsa 'Analizar' para ver detalles",
        font=("Helvetica", 11, "bold"),
        wraplength=550
    )
    lbl_preview_title.pack(anchor="w", pady=(0, 4))

    lbl_preview_meta = ttk.Label(
        frame_detalles,
        text="Canal: -- | Duración: --:-- | Calidad recomendada: 1080p",
        font=("Helvetica", 9),
        foreground="#94a3b8"
    )
    lbl_preview_meta.pack(anchor="w", pady=(0, 8))

    # Fila de configuración de formato y calidad
    frame_opciones = ttk.Frame(frame_detalles)
    frame_opciones.pack(fill="x", pady=(0, 6))

    ttk.Label(frame_opciones, text="Formato:").pack(side="left", padx=(0, 4))
    formatos = ["MP4 (Video)", "MP3 (Audio)", "M4A (Audio)", "WAV", "FLAC"]
    formato_var = tk.StringVar(value="MP4 (Video)")
    combo_formato = ttk.Combobox(frame_opciones, textvariable=formato_var, values=formatos, state="readonly", width=14)
    combo_formato.pack(side="left", padx=(0, 14))

    ttk.Label(frame_opciones, text="Calidad:").pack(side="left", padx=(0, 4))
    calidades_video = ["Mejor", "2160p (4K)", "1440p (2K)", "1080p", "720p", "480p", "360p"]
    calidades_audio = ["320 kbps (Máx)", "256 kbps (Alta)", "192 kbps (Estándar)", "128 kbps (Básica)"]
    calidad_var = tk.StringVar(value="1080p")
    combo_calidad = ttk.Combobox(frame_opciones, textvariable=calidad_var, values=calidades_video, state="readonly", width=16)
    combo_calidad.pack(side="left", padx=(0, 14))

    def on_formato_changed(event):
        fmt = formato_var.get()
        if "MP4" in fmt:
            combo_calidad.config(values=calidades_video)
            combo_calidad.set("1080p")
        else:
            combo_calidad.config(values=calidades_audio)
            combo_calidad.set("320 kbps (Máx)")

    combo_formato.bind("<<ComboboxSelected>>", on_formato_changed)

    # Checkboxes de metadatos y subtítulos
    chk_metadata_var = tk.BooleanVar(value=True)
    chk_subtitles_var = tk.BooleanVar(value=False)

    chk_meta = ttk.Checkbutton(frame_opciones, text="Incrustar Carátula / ID3", variable=chk_metadata_var)
    chk_meta.pack(side="left", padx=(0, 10))

    chk_subs = ttk.Checkbutton(frame_opciones, text="Subtítulos (.srt)", variable=chk_subtitles_var)
    chk_subs.pack(side="left")

    # Botones de Acción Rápida de la tarjeta
    frame_action_btns = ttk.Frame(frame_detalles)
    frame_action_btns.pack(fill="x", pady=(4, 0))

    btn_descargar_ahora = ttk.Button(
        frame_action_btns,
        text="⬇️ Descargar Ahora",
        style="Accent.TButton",
        command=lambda: accion_descargar_inmediato()
    )
    btn_descargar_ahora.pack(side="left", padx=(0, 8))

    btn_agregar_cola = ttk.Button(
        frame_action_btns,
        text="➕ Agregar a la Cola",
        command=lambda: accion_agregar_a_cola()
    )
    btn_agregar_cola.pack(side="left", padx=(0, 8))

    btn_carpeta = ttk.Button(
        frame_action_btns,
        text="📁 Carpeta de Descargas",
        command=lambda: accion_cambiar_carpeta()
    )
    btn_carpeta.pack(side="left")

    # ==========================================
    # 3. TARJETA DE PROGRESO DE DESCARGA
    # ==========================================
    frame_progreso = ttk.LabelFrame(container, text="  Progreso de Descarga en Vivo  ", padding=8)
    frame_progreso.pack(fill="x", pady=(0, 8))

    frame_pbar_row = ttk.Frame(frame_progreso)
    frame_pbar_row.pack(fill="x", pady=(2, 4))

    pbar = ttk.Progressbar(frame_pbar_row, mode="determinate", maximum=100)
    pbar.pack(side="left", fill="x", expand=True, padx=(0, 8))

    lbl_progreso_pct = ttk.Label(frame_pbar_row, text="0%", font=("Helvetica", 10, "bold"), width=7, anchor="center")
    lbl_progreso_pct.pack(side="left", padx=(0, 8))

    btn_cancelar = ttk.Button(frame_pbar_row, text="⏹️ Cancelar", command=lambda: Botones_Funciones.cancelar_descarga())
    btn_cancelar.pack(side="left")

    frame_pbar_meta = ttk.Frame(frame_progreso)
    frame_pbar_meta.pack(fill="x")

    lbl_progreso_titulo = ttk.Label(frame_pbar_meta, text="En espera de descarga...", font=("Helvetica", 9))
    lbl_progreso_titulo.pack(side="left", fill="x", expand=True)

    lbl_progreso_detalles = ttk.Label(frame_pbar_meta, text="Velocidad: -- | Restante: --:-- | 0 MB / 0 MB", font=("Helvetica", 9), foreground="#94a3b8")
    lbl_progreso_detalles.pack(side="right")

    # ==========================================
    # 4. COLA DE DESCARGAS Y PLAYLISTS
    # ==========================================
    card_cola = ttk.LabelFrame(container, text="  Cola de Descargas / Historial  ", padding=8)
    card_cola.pack(fill="both", expand=True)

    # Treeview
    Botones_Funciones.crear_treeview(card_cola)

    # Botones inferiores de la cola
    frame_cola_btns = ttk.Frame(card_cola)
    frame_cola_btns.pack(fill="x", pady=(8, 0))

    btn_descargar_sel = ttk.Button(
        frame_cola_btns,
        text="⬇️ Descargar Seleccionado",
        style="Accent.TButton",
        command=lambda: accion_descargar_seleccionado_cola()
    )
    btn_descargar_sel.pack(side="left", padx=(0, 6))

    btn_descargar_todo = ttk.Button(
        frame_cola_btns,
        text="⚡ Descargar Todo Pendiente",
        command=lambda: accion_descargar_todo_cola()
    )
    btn_descargar_todo.pack(side="left", padx=(0, 6))

    btn_abrir_destino = ttk.Button(
        frame_cola_btns,
        text="📂 Abrir Carpeta",
        command=lambda: Botones_Funciones.abrir_carpeta(carpeta_salida_actual)
    )
    btn_abrir_destino.pack(side="left", padx=(0, 6))

    btn_eliminar = ttk.Button(
        frame_cola_btns,
        text="🗑️ Eliminar de la Cola",
        command=lambda: Botones_Funciones.eliminar_seleccionado()
    )
    btn_eliminar.pack(side="right", padx=(6, 0))

    btn_limpiar = ttk.Button(
        frame_cola_btns,
        text="🧹 Limpiar Cola",
        command=lambda: Botones_Funciones.clear()
    )
    btn_limpiar.pack(side="right")

    return container

# ==========================================
# ACCIONES Y CONTROLADORES
# ==========================================

def accion_pegar_portapapeles():
    """Pega el contenido del portapapeles y analiza si es un enlace."""
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

def accion_cambiar_carpeta():
    global carpeta_salida_actual
    nueva = filedialog.askdirectory(initialdir=carpeta_salida_actual, title="Seleccionar Carpeta de Descargas")
    if nueva:
        carpeta_salida_actual = nueva
        Alertas.alerta_ok(Variables.titulo, "Carpeta Actualizada", f"Las descargas se guardarán en:\n{carpeta_salida_actual}")

def iniciar_analisis():
    """Analiza la URL en un hilo en segundo plano para no congelar la GUI."""
    url = entry_url.get().strip()
    if not url or "Pega una URL" in url:
        Alertas.alerta_Amarilla(Variables.titulo, "Campo vacío", "Introduce una URL válida para analizar.")
        return

    lbl_preview_title.config(text="🔍 Analizando enlace con yt-dlp... Por favor espera.")
    lbl_preview_meta.config(text="Obteniendo metadatos, calidades y miniaturas...")

    def _worker():
        try:
            info = DownloaderEngine.extract_info(url)
            Variables.root.after(0, lambda: _mostrar_resultado_analisis(info))
        except Exception as e:
            err = str(e)
            Variables.root.after(0, lambda: _mostrar_error_analisis(err))

    threading.Thread(target=_worker, daemon=True).start()

def _mostrar_resultado_analisis(info: Dict[str, Any]):
    global current_analyzed_info
    current_analyzed_info = info

    if info.get('is_playlist'):
        # Lista de reproducción
        titulo = info.get('title', 'Lista de reproducción')
        conteo = info.get('count', 0)
        lbl_preview_title.config(text=f"📋 Playlist: {titulo} ({conteo} videos)")
        lbl_preview_meta.config(text=f"Canal/Creador: {info.get('uploader')} | Total videos: {conteo}")
        lbl_preview_thumb.config(text="📋 Playlist", image="")

        # Preguntar si desea agregar automáticamente a la cola
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
        # Video individual
        titulo = info.get('title', 'Sin título')
        duracion = info.get('duration_str', '--:--')
        uploader = info.get('uploader', 'Desconocido')
        vistas = info.get('views', 0)
        vistas_str = f"{vistas:,}" if vistas else "N/A"

        lbl_preview_title.config(text=titulo)
        lbl_preview_meta.config(text=f"Canal: {uploader} | Duración: {duracion} | Vistas: {vistas_str}")

        # Cargar miniatura
        thumb_url = info.get('thumbnail')
        if thumb_url:
            Botones_Funciones.descargar_miniatura_async(thumb_url, _actualizar_miniatura_ui)

        # Actualizar resoluciones disponibles en el combobox
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
    """Agrega el video analizado actual a la cola de SQLite."""
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
    """Actualiza la barra de progreso y etiquetas en tiempo real."""
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
    """Descarga el video analizado inmediatamente."""
    global current_analyzed_info, carpeta_salida_actual
    if not current_analyzed_info:
        url = entry_url.get().strip()
        if url and "http" in url:
            iniciar_analisis()
            return
        Alertas.alerta_Amarilla(Variables.titulo, "Aviso", "Introduce y analiza un video antes de descargar.")
        return

    url = current_analyzed_info.get('url')
    formato_raw = combo_formato.get().split()[0]  # MP4, MP3, etc.
    calidad = combo_calidad.get()
    meta = chk_metadata_var.get()
    subs = chk_subtitles_var.get()

    # Guardar en base de datos como pendiente
    Database.add_video(
        title=current_analyzed_info.get('title', 'Video'),
        duration=current_analyzed_info.get('duration_str', '00:00'),
        status=Variables.Descargando,
        link=url,
        thumbnail=current_analyzed_info.get('thumbnail', ''),
        uploader=current_analyzed_info.get('uploader', '')
    )
    Botones_Funciones.actualizar_treeview()

    # Iniciar descarga
    pbar['value'] = 0
    lbl_progreso_pct.config(text="0%")
    lbl_progreso_titulo.config(text=f"Iniciando descarga de: {current_analyzed_info.get('title')}")

    def on_complete(success: bool, msg: str):
        if success:
            pbar['value'] = 100
            lbl_progreso_pct.config(text="100%")
            lbl_progreso_titulo.config(text="✅ Descarga completada")
            lbl_progreso_detalles.config(text="Archivo procesado correctamente con FFmpeg.")
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
        on_progress=_progreso_callback,
        on_complete=on_complete
    )

def accion_descargar_seleccionado_cola():
    """Descarga el elemento seleccionado en la cola."""
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

    pbar['value'] = 0
    lbl_progreso_pct.config(text="0%")
    lbl_progreso_titulo.config(text=f"Descargando de cola: {title}")

    def on_complete(success: bool, msg: str):
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
        on_progress=_progreso_callback,
        on_complete=on_complete
    )

def accion_descargar_todo_cola():
    """Descarga por lotes todos los videos pendientes de la cola."""
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
        on_progress=_progreso_callback,
        on_complete=on_all_complete
    )
