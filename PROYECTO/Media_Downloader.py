#!/usr/bin/env python3
"""
Media Downloader Pro V2.0
Descargador avanzado de videos y audio de YouTube, Playlists y +1000 plataformas.
Desarrollado con Python, yt-dlp, FFmpeg, SQLite y sv_ttk.
"""

import sys
import Home_Funciones
import Variables

def main():
    try:
        # Pantalla de carga inicial rápida y elegante
        Home_Funciones.screen_holding()
        # Inicialización y ejecución de la ventana principal
        Home_Funciones.crear_windows_principal()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Error inesperado al ejecutar la aplicación: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
