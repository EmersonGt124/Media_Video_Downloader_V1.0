import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

try:
    import sv_ttk
    HAS_SV_TTK = True
except ImportError:
    HAS_SV_TTK = False

import Variables
import Screen_Holding
import Botones_Funciones
import Youtube_Funciones

Centro_p = None
clipboard_monitor_active = False
last_clipboard_content = ""

def al_cerrar_ventana():
    """Manejo limpio de salida: detiene descargas activas y cierra."""
    if Botones_Funciones.is_downloading:
        resp = messagebox.askyesno(
            "Descarga en curso",
            "Hay una descarga activa en segundo plano.\n¿Estás seguro de que deseas salir y cancelarla?"
        )
        if not resp:
            return
        Botones_Funciones.cancelar_descarga()

    if Variables.root:
        Variables.root.destroy()
    sys.exit(0)

def screen_holding():
    """Muestra pantalla de carga inicial sin dependencias de .exe."""
    try:
        Screen_Holding.mostrar_imagen_con_texto(duration_ms=800)
    except Exception as e:
        print(f"Aviso splash: {e}")

def toggle_theme():
    """Alterna entre tema oscuro y claro."""
    if HAS_SV_TTK:
        sv_ttk.toggle_theme()

def check_clipboard_loop():
    """Monitorea el portapapeles para autodetectar URLs de video copiadas."""
    global last_clipboard_content, clipboard_monitor_active
    if not clipboard_monitor_active or not Variables.root:
        return

    try:
        clip = Variables.root.clipboard_get().strip()
        if clip != last_clipboard_content and (clip.startswith("http://") or clip.startswith("https://")):
            last_clipboard_content = clip
            if any(domain in clip.lower() for domain in ["youtube.com", "youtu.be", "tiktok.com", "instagram.com", "twitter.com", "x.com", "facebook.com", "soundcloud.com"]):
                if Youtube_Funciones.entry_url:
                    Youtube_Funciones.entry_url.delete(0, tk.END)
                    Youtube_Funciones.entry_url.insert(0, clip)
                    Youtube_Funciones.iniciar_analisis()
    except Exception:
        pass

    if clipboard_monitor_active and Variables.root:
        Variables.root.after(1500, check_clipboard_loop)

def toggle_clipboard_monitor(var):
    global clipboard_monitor_active
    clipboard_monitor_active = var.get()
    if clipboard_monitor_active:
        check_clipboard_loop()

def mostrar_dialogo_acerca_de():
    info_text = (
        f"{Variables.titulo}\n"
        f"Versión: {Variables.version}\n\n"
        "Novedades y Características:\n"
        "• Descarga en 1080p, 2K, 4K y 60 FPS con FFmpeg.\n"
        "• Extracción de Audio a MP3 real (320kbps), M4A, WAV y FLAC.\n"
        "• Tolerancia a fallos: Subtítulos y carátulas con auto-recuperación si YouTube limita peticiones (429).\n"
        "• Diseño 100% responsivo adaptable a cualquier resolución.\n"
        "• Base de datos local SQLite ultrarrápida.\n"
        "• Soporte para YouTube, Playlists, TikTok, Instagram, Twitter y +1000 sitios.\n\n"
        f"Usuario: {Variables.Usuario}\n"
        f"Destino actual: {Youtube_Funciones.carpeta_salida_actual}"
    )
    messagebox.showinfo("Acerca de Media Downloader Pro", info_text)

def Barra_superior():
    """Barra superior estilizada y compacta."""
    barra_opcion = ttk.Frame(Variables.root, padding=(10, 6))
    barra_opcion.pack(side='top', fill='x')

    # Izquierda: Título y versión
    lbl_app_name = ttk.Label(
        barra_opcion,
        text="⚡ Media Downloader Pro",
        font=("Helvetica", 12, "bold")
    )
    lbl_app_name.pack(side='left', padx=(0, 4))

    lbl_version = ttk.Label(
        barra_opcion,
        text="v2.0",
        font=("Helvetica", 8),
        foreground="#94a3b8"
    )
    lbl_version.pack(side='left', padx=(0, 10))

    # Derecha: Controles
    lbl_user = ttk.Label(
        barra_opcion,
        text=f"👤 {Variables.Usuario}",
        font=("Helvetica", 9),
        foreground="#94a3b8"
    )
    lbl_user.pack(side='right', padx=(8, 0))

    btn_info = ttk.Button(
        barra_opcion,
        text="ℹ️ Info",
        width=7,
        command=mostrar_dialogo_acerca_de
    )
    btn_info.pack(side='right', padx=(4, 0))

    if HAS_SV_TTK:
        btn_tema = ttk.Button(
            barra_opcion,
            text="🌓 Tema",
            width=8,
            command=toggle_theme
        )
        btn_tema.pack(side='right', padx=(4, 0))

    clip_var = tk.BooleanVar(value=False)
    chk_clip = ttk.Checkbutton(
        barra_opcion,
        text="📋 Auto-URLs",
        variable=clip_var,
        command=lambda: toggle_clipboard_monitor(clip_var)
    )
    chk_clip.pack(side='right', padx=(4, 8))

    sep = ttk.Separator(Variables.root, orient="horizontal")
    sep.pack(side="top", fill="x")

def crear_windows_principal():
    """Inicializa la ventana principal con tamaño responsivo y límites adaptables."""
    root = tk.Tk()
    Variables.root = root

    root.title(Variables.titulo)
    root.geometry("860x660")
    root.minsize(680, 520)

    if os.path.exists(Variables.icono_v):
        try:
            if sys.platform == "win32" and Variables.icono_v.endswith(".ico"):
                root.iconbitmap(Variables.icono_v)
            else:
                img_ico = ImageTk.PhotoImage(file=Variables.icono_v)
                root.iconphoto(True, img_ico)
        except Exception:
            pass

    if HAS_SV_TTK:
        sv_ttk.set_theme("dark")

    Barra_superior()

    global Centro_p
    Centro_p = ttk.Frame(root)
    Centro_p.pack(side="top", fill="both", expand=True)

    Youtube_Funciones.Centro_youtube(Centro_p)

    root.protocol("WM_DELETE_WINDOW", al_cerrar_ventana)
    root.mainloop()
