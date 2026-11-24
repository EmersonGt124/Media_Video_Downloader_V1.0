import os
import getpass
import sys
from pathlib import Path

# INFORMACIÓN DE LA APLICACIÓN
titulo = "Media Downloader Pro V2.0"
version = "2.0.0"
Usuario = getpass.getuser()

# RUTAS BASE (Compatibilidad completa con PyInstaller frozen y modo desarrollo)
if getattr(sys, 'frozen', False):
    BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "lib", "data")
FONT_DIR = os.path.join(DATA_DIR, "fuente")

# RECURSOS GRÁFICOS
icono_v = os.path.join(DATA_DIR, "icon.png") if os.path.exists(os.path.join(DATA_DIR, "icon.png")) else os.path.join(DATA_DIR, "icon.ico")
Youtube_logo = os.path.join(DATA_DIR, "Youtube_logo.png")
Youtube_logo1 = os.path.join(DATA_DIR, "Youtube_logo1.png")
Campo_busqueda = os.path.join(DATA_DIR, "bar_search.png")
lupa = os.path.join(DATA_DIR, "search.png")
lupa1 = os.path.join(DATA_DIR, "search1.png")
D_seleccion = os.path.join(DATA_DIR, "D_selecion.png")
D_seleccion1 = os.path.join(DATA_DIR, "D_selecion1.png")
D_todo = os.path.join(DATA_DIR, "D_Todo.png")
D_todo1 = os.path.join(DATA_DIR, "D_Todo1.png")
recicle = os.path.join(DATA_DIR, "recile.png")
recicle1 = os.path.join(DATA_DIR, "recile1.png")

# RUTA POR DEFECTO PARA DESCARGAS
user_home = str(Path.home())
descargas_posibles = [
    os.path.join(user_home, "Descargas"),
    os.path.join(user_home, "Downloads"),
    user_home
]
carpeta_descargas_default = next((p for p in descargas_posibles if os.path.exists(p)), user_home)

# BASE DE DATOS Y COMPATIBILIDAD
data_db = os.path.join(DATA_DIR, "downloads.db")
data_excel = os.path.join(DATA_DIR, "y_data.xlsx")
yotube_link = "https://www.youtube.com"

# ESTADOS
Pendiente = "Pendiente"
Descargando = "Descargando"
Terminado = "Terminado"
Error = "Error"
Cancelado = "Cancelado"

# PALETA DE COLORES MODERNA (Dark & Accent)
BG_DARK = "#0f172a"        # Slate 900
BG_CARD = "#1e293b"        # Slate 800
BG_HOVER = "#334155"       # Slate 700
ACCENT_COLOR = "#0ea5e9"   # Sky 500
ACCENT_HOVER = "#0284c7"   # Sky 600
RED_ACCENT = "#ef4444"     # Red 500
GREEN_ACCENT = "#10b981"   # Emerald 500
TEXT_PRIMARY = "#f8fafc"   # Slate 50
TEXT_SECONDARY = "#94a3b8" # Slate 400

# Colores legacy para retrocompatibilidad
Y_boton = '#F53939'
Y_backgroun = '#0f172a'
c_barras = '#1e293b'
c_selecion = '#334155'
poppins = "Helvetica"
poppins_negrita = "Helvetica"

# Variables globales de ejecución (se asignan al arrancar)
root = None
entry_lik = ""
enlace = ""
fila = 0
cantidad = 0
