import os
import sys
import threading
import time
from typing import Optional, Callable, Dict, Any, List

# Ensure lib/yt_dlp_bin is on sys.path
lib_bin_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "lib", "yt_dlp_bin"))
if os.path.exists(lib_bin_path) and lib_bin_path not in sys.path:
    sys.path.insert(0, lib_bin_path)

try:
    import yt_dlp
except ImportError:
    # Fallback to local import
    import importlib.util
    spec = importlib.util.spec_from_file_location("yt_dlp", lib_bin_path)
    if spec and spec.loader:
        yt_dlp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(yt_dlp)
    else:
        raise RuntimeError("No se pudo cargar la librería yt_dlp.")


def format_seconds(seconds: Optional[int]) -> str:
    """Convierte segundos a formato MM:SS o HH:MM:SS"""
    if not seconds or seconds < 0:
        return "--:--"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_bytes(bytes_val: Optional[float]) -> str:
    """Convierte bytes a formato legible (KB, MB, GB)"""
    if not bytes_val or bytes_val <= 0:
        return "0 MB"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"


class DownloaderEngine:
    """Motor moderno de descarga y análisis de medios con yt-dlp y FFmpeg."""

    @staticmethod
    def is_playlist(url: str) -> bool:
        url_lower = url.lower()
        return "playlist?list=" in url_lower or "&list=" in url_lower or "/sets/" in url_lower

    @staticmethod
    def extract_info(url: str, is_playlist_hint: Optional[bool] = None) -> Dict[str, Any]:
        """
        Extrae información y metadatos de un enlace sin descargarlo.
        Soporta videos únicos, listas de reproducción y más de 1000 plataformas.
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': 'in_playlist',
            'ignoreerrors': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise ValueError("No se pudo obtener información del enlace proporcionado.")

            # Comprobar si es lista de reproducción
            if 'entries' in info:
                entries = []
                for idx, entry in enumerate(info.get('entries', []), start=1):
                    if not entry:
                        continue
                    v_url = entry.get('url') or entry.get('webpage_url')
                    if not v_url and entry.get('id'):
                        v_url = f"https://www.youtube.com/watch?v={entry.get('id')}"

                    entries.append({
                        'index': idx,
                        'title': entry.get('title', f"Video {idx}"),
                        'duration': entry.get('duration', 0),
                        'duration_str': format_seconds(entry.get('duration')),
                        'url': v_url or url,
                        'uploader': entry.get('uploader') or entry.get('channel') or 'Desconocido',
                        'thumbnail': entry.get('thumbnail') or ''
                    })

                return {
                    'is_playlist': True,
                    'title': info.get('title', 'Lista de reproducción'),
                    'uploader': info.get('uploader') or info.get('channel') or '',
                    'count': len(entries),
                    'entries': entries,
                    'url': url
                }
            else:
                # Video único
                duration = info.get('duration', 0)
                # Formatos de resolución disponibles
                available_resolutions = set()
                formats = info.get('formats', [])
                for f in formats:
                    height = f.get('height')
                    if height:
                        available_resolutions.add(f"{height}p")

                # Ordenar resoluciones comunes
                order_priority = ["2160p (4K)", "1440p (2K)", "1080p", "720p", "480p", "360p", "240p"]
                sorted_resolutions = []
                # Map standard heights
                standard_map = {
                    "2160p": "2160p (4K)",
                    "1440p": "1440p (2K)",
                    "1080p": "1080p",
                    "720p": "720p",
                    "480p": "480p",
                    "360p": "360p",
                    "240p": "240p"
                }
                for std, label in standard_map.items():
                    if std in available_resolutions:
                        sorted_resolutions.append(label)

                if not sorted_resolutions:
                    sorted_resolutions = ["1080p", "720p", "480p", "360p"]

                return {
                    'is_playlist': False,
                    'title': info.get('title', 'Sin título'),
                    'duration': duration,
                    'duration_str': format_seconds(duration),
                    'uploader': info.get('uploader') or info.get('channel') or 'Desconocido',
                    'thumbnail': info.get('thumbnail', ''),
                    'views': info.get('view_count', 0),
                    'resolutions': sorted_resolutions,
                    'url': info.get('webpage_url') or url
                }

    @staticmethod
    def download(
        url: str,
        output_dir: str,
        format_type: str = "MP4",
        quality: str = "1080p",
        embed_metadata: bool = True,
        embed_thumbnail: bool = True,
        download_subtitles: bool = False,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> str:
        """
        Descarga el medio con las opciones especificadas.
        format_type: MP4, MP3, M4A, WAV, FLAC
        quality: "Mejor", "2160p (4K)", "1440p (2K)", "1080p", "720p", "480p", "360p"
                 o para audio "320 kbps", "256 kbps", "192 kbps", "128 kbps"
        """
        os.makedirs(output_dir, exist_ok=True)
        final_filename = ""

        def progress_hook(d):
            if cancel_event and cancel_event.is_set():
                raise Exception("DESCARGA_CANCELADA_POR_USUARIO")

            if not progress_callback:
                return

            status = d.get('status')
            if status == 'downloading':
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded_bytes = d.get('downloaded_bytes') or 0
                speed = d.get('speed') or 0
                eta = d.get('eta') or 0

                percent = 0.0
                if total_bytes > 0:
                    percent = (downloaded_bytes / total_bytes) * 100.0

                progress_data = {
                    'status': 'downloading',
                    'percent': percent,
                    'percent_str': f"{percent:.1f}%",
                    'downloaded_str': format_bytes(downloaded_bytes),
                    'total_str': format_bytes(total_bytes) if total_bytes > 0 else "...",
                    'speed_str': f"{format_bytes(speed)}/s" if speed else "Calculando...",
                    'eta_str': format_seconds(eta) if eta else "--:--",
                    'filename': os.path.basename(d.get('filename', ''))
                }
                progress_callback(progress_data)

            elif status == 'finished':
                progress_callback({
                    'status': 'processing',
                    'percent': 100.0,
                    'percent_str': "100%",
                    'speed_str': "Completado",
                    'eta_str': "Procesando audio/video con FFmpeg...",
                    'filename': os.path.basename(d.get('filename', ''))
                })

        # Template de archivo de salida
        outtmpl = os.path.join(output_dir, '%(title)s [%(id)s].%(ext)s')

        # Configurar ydl_opts
        ydl_opts: Dict[str, Any] = {
            'outtmpl': outtmpl,
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [progress_hook],
            'ignoreerrors': False,
            'nocheckcertificate': True,
        }

        # Configuración según Formato
        format_clean = format_type.upper().strip()

        if format_clean in ["MP3", "M4A", "WAV", "FLAC"]:
            # Extracción de Audio
            ydl_opts['format'] = 'bestaudio/best'
            postprocessors = []

            # Calidad de audio
            audio_quality = "192"
            if "320" in quality:
                audio_quality = "320"
            elif "256" in quality:
                audio_quality = "256"
            elif "128" in quality:
                audio_quality = "128"

            postprocessors.append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': format_clean.lower(),
                'preferredquality': audio_quality,
            })

            if embed_metadata:
                postprocessors.append({'key': 'FFmpegMetadata'})

            if embed_thumbnail and format_clean in ["MP3", "M4A"]:
                ydl_opts['writethumbnail'] = True
                postprocessors.append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})

            ydl_opts['postprocessors'] = postprocessors

        else:
            # Descarga de Video (MP4 por defecto)
            # Parsear resolución objetivo
            height = None
            if "2160" in quality or "4K" in quality:
                height = 2160
            elif "1440" in quality or "2K" in quality:
                height = 1440
            elif "1080" in quality:
                height = 1080
            elif "720" in quality:
                height = 720
            elif "480" in quality:
                height = 480
            elif "360" in quality:
                height = 360

            if height:
                ydl_opts['format'] = (
                    f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/'
                    f'bestvideo[height<={height}]+bestaudio/'
                    f'best[height<={height}]/best'
                )
            else:
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'

            ydl_opts['merge_output_format'] = 'mp4'

            postprocessors = []
            if embed_metadata:
                postprocessors.append({'key': 'FFmpegMetadata'})

            if embed_thumbnail:
                ydl_opts['writethumbnail'] = True
                postprocessors.append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})

            if postprocessors:
                ydl_opts['postprocessors'] = postprocessors

        # Subtítulos
        if download_subtitles:
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitleslangs'] = ['es', 'en']
            ydl_opts['subtitlesformat'] = 'srt'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                title = info.get('title', 'Video')
                if progress_callback:
                    progress_callback({
                        'status': 'finished',
                        'percent': 100.0,
                        'percent_str': "100%",
                        'speed_str': "Finalizado",
                        'eta_str': "¡Listo!",
                        'title': title
                    })
                return title

        return "Descarga completa"
