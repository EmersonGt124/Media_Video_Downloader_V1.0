import os
import sys
import webbrowser
import threading
import subprocess
import urllib.request
import io
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
from typing import Optional, Callable, Dict, Any, List

import Variables
import Alertas
from Database import Database
from Downloader_Engine import DownloaderEngine, format_seconds, format_bytes, clean_ansi

cancel_event = threading.Event()
is_downloading = False
current_download_thread = None

thumbnail_cache = {}

def abrir_carpeta(ruta: str):
    """Abre la carpeta en el explorador de archivos del sistema."""
    if not os.path.exists(ruta):
        try:
            os.makedirs(ruta, exist_ok=True)
        except Exception:
            pass

    try:
        if sys.platform == "win32":
            os.startfile(ruta)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", ruta])
        else:
            subprocess.Popen(["xdg-open", ruta])
    except Exception as e:
        Alertas.alerta_Amarilla(Variables.titulo, "Abrir carpeta", f"No se pudo abrir la carpeta automáticamente:\n{ruta}\n{e}")

def abrir_link(consulta: str):
    """Abre la búsqueda o enlace en el navegador."""
    try:
        if consulta.startswith("http://") or consulta.startswith("https://"):
            webbrowser.open(consulta)
        else:
            consulta = consulta.replace(" ", "+")
            url = f"https://www.youtube.com/results?search_query={consulta}"
            webbrowser.open(url)
    except Exception as e:
        print("Error al abrir navegador:", e)

def descargar_miniatura_async(url: str, callback: Callable[[Optional[ImageTk.PhotoImage]], None], size=(160, 90)):
    """Descarga una miniatura en segundo plano sin congelar la interfaz."""
    if not url:
        callback(None)
        return

    if url in thumbnail_cache:
        callback(thumbnail_cache[url])
        return

    def _fetch():
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                img_data = response.read()
                pil_img = Image.open(io.BytesIO(img_data)).convert("RGBA")
                pil_img = pil_img.resize(size, Image.Resampling.LANCZOS)
                Variables.root.after(0, lambda: _create_photo(pil_img, url, callback))
        except Exception:
            Variables.root.after(0, lambda: callback(None))

    def _create_photo(pil_img, url, callback):
        try:
            photo = ImageTk.PhotoImage(pil_img)
            thumbnail_cache[url] = photo
            callback(photo)
        except Exception:
            callback(None)

    threading.Thread(target=_fetch, daemon=True).start()

# ==========================================
# GESTIÓN DEL TREEVIEW Y BASE DE DATOS
# ==========================================

treeview_ref = None

def crear_treeview(parent):
    """Crea y estiliza el Treeview de la cola de descargas con scrollbars responsivas."""
    global treeview_ref

    frame_tv = ttk.Frame(parent)
    frame_tv.pack(fill="both", expand=True)

    scroll_y = ttk.Scrollbar(frame_tv, orient="vertical")
    scroll_x = ttk.Scrollbar(frame_tv, orient="horizontal")

    columns = ("id", "title", "duration", "uploader", "status")
    tree = ttk.Treeview(
        frame_tv,
        columns=columns,
        show="headings",
        selectmode="browse",
        yscrollcommand=scroll_y.set,
        xscrollcommand=scroll_x.set
    )

    scroll_y.config(command=tree.yview)
    scroll_x.config(command=tree.xview)

    scroll_y.pack(side="right", fill="y")
    scroll_x.pack(side="bottom", fill="x")
    tree.pack(side="left", fill="both", expand=True)

    tree.heading("id", text="#")
    tree.heading("title", text="Título del Video / Pista")
    tree.heading("duration", text="Duración")
    tree.heading("uploader", text="Canal / Artista")
    tree.heading("status", text="Estado")

    tree.column("id", width=40, minwidth=35, anchor="center")
    tree.column("title", width=360, minwidth=180, anchor="w")
    tree.column("duration", width=80, minwidth=60, anchor="center")
    tree.column("uploader", width=140, minwidth=100, anchor="w")
    tree.column("status", width=110, minwidth=80, anchor="center")

    tree.tag_configure("Terminado", foreground="#10b981")
    tree.tag_configure("Descargando", foreground="#38bdf8")
    tree.tag_configure("Pendiente", foreground="#f59e0b")
    tree.tag_configure("Error", foreground="#ef4444")
    tree.tag_configure("Cancelado", foreground="#94a3b8")

    treeview_ref = tree
    actualizar_treeview(tree)
    return tree

def actualizar_treeview(tree=None):
    """Actualiza la vista del Treeview leyendo desde SQLite."""
    global treeview_ref
    tv = tree or treeview_ref
    if not tv:
        return

    for row in tv.get_children():
        tv.delete(row)

    registros = Database.get_all()
    for item in registros:
        item_id = item[0]
        title = item[1]
        duration = item[2]
        status = item[3]
        uploader = item[6] if len(item) > 6 and item[6] else "Desconocido"

        tv.insert(
            "",
            "end",
            iid=str(item_id),
            values=(item_id, title, duration, uploader, status),
            tags=(status,)
        )

def clear(archivo_dummy=None):
    """Limpia la base de datos y la vista."""
    res = Alertas.alerta_aceptar(Variables.titulo, "Limpiar cola", "¿Estás seguro de que deseas vaciar toda la cola de descargas?")
    if res == 1:
        Database.clear_all()
        actualizar_treeview()

def eliminar_seleccionado():
    """Elimina el elemento seleccionado de la cola."""
    if not treeview_ref:
        return
    seleccion = treeview_ref.selection()
    if not seleccion:
        Alertas.alerta_Amarilla(Variables.titulo, "Eliminar", "Selecciona un elemento de la lista para eliminar.")
        return
    item_id = int(seleccion[0])
    Database.delete_by_id(item_id)
    actualizar_treeview()

# ==========================================
# PROCESO DE DESCARGA EN SEGUNDO PLANO
# ==========================================

def cancelar_descarga():
    """Cancela la descarga que está activa actualmente."""
    global cancel_event, is_downloading
    if is_downloading:
        cancel_event.set()

def ejecutar_descarga(
    url: str,
    output_dir: str,
    format_type: str,
    quality: str,
    embed_metadata: bool,
    embed_thumbnail: bool,
    download_subtitles: bool,
    on_progress: Callable[[Dict[str, Any]], None],
    on_complete: Callable[[bool, str], None]
):
    """Ejecuta una descarga individual en un hilo dedicado con yt-dlp y FFmpeg."""
    global is_downloading, cancel_event
    cancel_event.clear()
    is_downloading = True

    def _worker():
        global is_downloading
        success = False
        message = ""
        try:
            Database.update_status(url, Variables.Descargando)
            Variables.root.after(0, actualizar_treeview)

            title, warning = DownloaderEngine.download(
                url=url,
                output_dir=output_dir,
                format_type=format_type,
                quality=quality,
                embed_metadata=embed_metadata,
                embed_thumbnail=embed_thumbnail,
                download_subtitles=download_subtitles,
                progress_callback=lambda d: Variables.root.after(0, lambda: on_progress(d)),
                cancel_event=cancel_event
            )
            Database.update_status(url, Variables.Terminado)
            success = True
            if warning:
                message = f"Descarga finalizada:\n{title}\n\nGuardado en:\n{output_dir}\n\n{warning}"
            else:
                message = f"Descarga finalizada con éxito:\n{title}\n\nGuardado en:\n{output_dir}"

        except Exception as e:
            err_str = clean_ansi(str(e))
            if "DESCARGA_CANCELADA_POR_USUARIO" in err_str:
                Database.update_status(url, Variables.Cancelado)
                message = "La descarga fue cancelada por el usuario."
            else:
                Database.update_status(url, Variables.Error)
                message = f"Error en la descarga:\n{err_str}"
        finally:
            is_downloading = False
            Variables.root.after(0, actualizar_treeview)
            Variables.root.after(0, lambda: on_complete(success, message))

    threading.Thread(target=_worker, daemon=True).start()

def ejecutar_descarga_cola(
    output_dir: str,
    format_type: str,
    quality: str,
    embed_metadata: bool,
    embed_thumbnail: bool,
    download_subtitles: bool,
    on_progress: Callable[[Dict[str, Any]], None],
    on_complete: Callable[[int, int], None]
):
    """Descarga secuencialmente todos los videos pendientes en la cola."""
    global is_downloading, cancel_event
    cancel_event.clear()
    is_downloading = True

    def _worker():
        global is_downloading
        pendientes = Database.get_pending()
        total = len(pendientes)
        completados = 0

        for idx, item in enumerate(pendientes, start=1):
            if cancel_event.is_set():
                break

            url = item['link']
            title = item['title']
            try:
                Database.update_status(url, Variables.Descargando)
                Variables.root.after(0, actualizar_treeview)

                title_dl, warning = DownloaderEngine.download(
                    url=url,
                    output_dir=output_dir,
                    format_type=format_type,
                    quality=quality,
                    embed_metadata=embed_metadata,
                    embed_thumbnail=embed_thumbnail,
                    download_subtitles=download_subtitles,
                    progress_callback=lambda d: Variables.root.after(0, lambda: on_progress(d)),
                    cancel_event=cancel_event
                )
                Database.update_status(url, Variables.Terminado)
                completados += 1
            except Exception as e:
                err_str = clean_ansi(str(e))
                if "DESCARGA_CANCELADA_POR_USUARIO" in err_str:
                    Database.update_status(url, Variables.Cancelado)
                    break
                else:
                    Database.update_status(url, Variables.Error)

            Variables.root.after(0, actualizar_treeview)

        is_downloading = False
        Variables.root.after(0, actualizar_treeview)
        Variables.root.after(0, lambda: on_complete(completados, total))

    threading.Thread(target=_worker, daemon=True).start()

# Compatibilidad con código previo
def crear_excel_lista(datos, dummy=None):
    pass
def crear_excel_video(datos, dummy=None):
    pass
def leer_datos_excel(dummy=None):
    return Database.get_all()
def actualizar_estado(val):
    pass
def actualizar_estado_lista(val, enlace):
    pass
def selecionar_boton(btn):
    pass
def seleccionar_label(l, o, h):
    pass
def cambio_ventana(f, frame):
    return lambda event=None: None
