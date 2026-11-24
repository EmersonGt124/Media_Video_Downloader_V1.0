#!/usr/bin/env python3
"""
Media Downloader Pro - Universal Build Script
Empaqueta la aplicación para Windows, Linux y macOS usando PyInstaller.
"""
import os
import sys
import shutil
import zipfile
import tarfile
import platform
import subprocess

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROYECTO_DIR = os.path.join(ROOT_DIR, "PROYECTO")
ENTRY_POINT = os.path.join(PROYECTO_DIR, "Media_Downloader.py")
DATA_DIR = os.path.join(PROYECTO_DIR, "lib", "data")
DIST_DIR = os.path.join(ROOT_DIR, "dist")
BUILD_DIR = os.path.join(ROOT_DIR, "build")
OUTPUT_NAME = "MediaDownloaderPro"

def clean():
    """Limpia directorios de compilación anteriores."""
    for d in [DIST_DIR, BUILD_DIR]:
        if os.path.exists(d):
            print(f"Limpiando {d}...")
            shutil.rmtree(d, ignore_errors=True)

def run_pyinstaller():
    """Ejecuta PyInstaller con todos los argumentos requeridos."""
    system = platform.system().lower()
    sep = ";" if system == "windows" else ":"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--name", OUTPUT_NAME,
        "--onedir",
        "--clean",
        # Incluir temas de Sun Valley, yt-dlp y Pillow completos
        "--collect-all", "sv_ttk",
        "--collect-all", "yt_dlp",
        "--collect-all", "PIL",
        # Incluir recursos y assets de la app
        f"--add-data={DATA_DIR}{sep}lib/data",
    ]

    # Incluir FFmpeg si está en lib/ffmpeg
    ffmpeg_dir = os.path.join(PROYECTO_DIR, "lib", "ffmpeg")
    if os.path.isdir(ffmpeg_dir):
        print(f"Incluyendo binarios de FFmpeg desde {ffmpeg_dir}...")
        cmd.append(f"--add-data={ffmpeg_dir}{sep}lib/ffmpeg")

    # Icono según sistema operativo
    if system == "windows":
        ico = os.path.join(DATA_DIR, "icon.ico")
        if os.path.exists(ico):
            cmd.extend(["--icon", ico])
    else:
        png = os.path.join(DATA_DIR, "icon.png")
        if os.path.exists(png):
            cmd.extend(["--icon", png])

    # Entry point
    cmd.append(ENTRY_POINT)

    print("Ejecutando comando PyInstaller:")
    print(" ".join(cmd))
    res = subprocess.run(cmd, cwd=ROOT_DIR)
    if res.returncode != 0:
        print("Error: PyInstaller falló con código de salida:", res.returncode)
        sys.exit(res.returncode)

def package_artifacts():
    """Comprime la carpeta generada en dist/ a un archivo portable listo para descargar."""
    system = platform.system().lower()
    target_folder = os.path.join(DIST_DIR, OUTPUT_NAME)

    if not os.path.exists(target_folder):
        print(f"Error: No se encontró la carpeta compilada en {target_folder}")
        sys.exit(1)

    if system == "windows":
        archive_name = os.path.join(DIST_DIR, f"{OUTPUT_NAME}-Windows-x64.zip")
        print(f"Comprimiendo a {archive_name}...")
        with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(target_folder):
                for f in files:
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, DIST_DIR)
                    zipf.write(full_p, rel_p)
        print(f"✓ Archivo generado exitosamente: {archive_name}")

    elif system == "darwin":
        archive_name = os.path.join(DIST_DIR, f"{OUTPUT_NAME}-macOS-x64.zip")
        print(f"Comprimiendo a {archive_name}...")
        with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(target_folder):
                for f in files:
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, DIST_DIR)
                    zipf.write(full_p, rel_p)
        print(f"✓ Archivo generado exitosamente: {archive_name}")

    else:
        archive_name = os.path.join(DIST_DIR, f"{OUTPUT_NAME}-Linux-x64.tar.gz")
        print(f"Comprimiendo a {archive_name}...")
        with tarfile.open(archive_name, "w:gz") as tar:
            tar.add(target_folder, arcname=OUTPUT_NAME)
        print(f"✓ Archivo generado exitosamente: {archive_name}")

if __name__ == "__main__":
    clean()
    run_pyinstaller()
    package_artifacts()
