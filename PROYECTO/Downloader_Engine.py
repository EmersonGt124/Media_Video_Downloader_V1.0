import os
import sys
import re
import threading
import time
from typing import Optional, Callable, Dict, Any, List, Tuple

# Ensure lib/yt_dlp_bin is on sys.path
lib_bin_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "lib", "yt_dlp_bin"))
if os.path.exists(lib_bin_path) and lib_bin_path not in sys.path:
    sys.path.insert(0, lib_bin_path)

try:
    import yt_dlp
    from yt_dlp.utils import download_range_func
except ImportError:
    import importlib.util
    spec = importlib.util.spec_from_file_location("yt_dlp", lib_bin_path)
    if spec and spec.loader:
        yt_dlp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(yt_dlp)
        from yt_dlp.utils import download_range_func
    else:
        raise RuntimeError("No se pudo cargar la librería yt_dlp.")


def clean_ansi(text: str) -> str:
    """Elimina secuencias de escape ANSI de mensajes de error de yt-dlp."""
    if not text:
        return ""
    cleaned = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
    cleaned = cleaned.replace('\x1b', '').strip()
    return cleaned


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


def parse_time_str(time_str: str) -> Optional[int]:
    """Convierte cadenas 'MM:SS', 'HH:MM:SS' o segundos directos a un entero."""
    if not time_str or not str(time_str).strip():
        return None
    parts = str(time_str).strip().split(":")
    try:
        if len(parts) == 1:
            return int(float(parts[0]))
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except Exception:
        return None
    return None


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
    def get_ffmpeg_location() -> Optional[str]:
        """Detecta la ubicación de FFmpeg si está empaquetado con la app o en lib/ffmpeg."""
        if getattr(sys, 'frozen', False):
            base_candidates = [
                getattr(sys, '_MEIPASS', ''),
                os.path.dirname(sys.executable),
                os.path.join(os.path.dirname(sys.executable), 'ffmpeg'),
            ]
            for base in base_candidates:
                if not base:
                    continue
                for fname in ['ffmpeg.exe', 'ffmpeg']:
                    if os.path.isfile(os.path.join(base, fname)):
                        return base

        local_ffmpeg = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib', 'ffmpeg')
        if os.path.isdir(local_ffmpeg):
            for fname in ['ffmpeg.exe', 'ffmpeg']:
                if os.path.isfile(os.path.join(local_ffmpeg, fname)):
                    return local_ffmpeg

        return None

    @staticmethod
    def is_playlist(url: str) -> bool:
        url_lower = url.lower()
        return "playlist?list=" in url_lower or "&list=" in url_lower or "/sets/" in url_lower

    @staticmethod
    def search_youtube(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Busca videos en YouTube directamente por palabras clave y devuelve resultados."""
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'extract_flat': True,
            'ignoreerrors': True,
        }
        search_query = f"ytsearch{max_results}:{query}"
        results = []
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(search_query, download=False)
            if res and 'entries' in res:
                for idx, entry in enumerate(res['entries'], start=1):
                    if not entry:
                        continue
                    v_url = entry.get('url') or entry.get('webpage_url')
                    if not v_url and entry.get('id'):
                        v_url = f"https://www.youtube.com/watch?v={entry.get('id')}"

                    dur = entry.get('duration', 0)
                    results.append({
                        'index': idx,
                        'title': entry.get('title', f"Resultado {idx}"),
                        'duration': dur,
                        'duration_str': format_seconds(dur),
                        'url': v_url,
                        'uploader': entry.get('uploader') or entry.get('channel') or 'Desconocido',
                        'thumbnail': entry.get('thumbnail') or f"https://i.ytimg.com/vi/{entry.get('id')}/mqdefault.jpg" if entry.get('id') else '',
                        'views': entry.get('view_count', 0)
                    })
        return results

    @staticmethod
    def extract_info(url: str, cookies_browser: Optional[str] = None) -> Dict[str, Any]:
        """Extrae información y metadatos de un enlace sin descargarlo."""
        ydl_opts: Dict[str, Any] = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': 'in_playlist',
            'ignoreerrors': True,
        }
        if cookies_browser and cookies_browser.lower() != "ninguno":
            ydl_opts['cookiesfrombrowser'] = (cookies_browser.lower(),)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise ValueError("No se pudo obtener información del enlace proporcionado.")

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
                duration = info.get('duration', 0)
                available_resolutions = set()
                formats = info.get('formats', [])
                for f in formats:
                    height = f.get('height')
                    if height:
                        available_resolutions.add(f"{height}p")

                standard_map = {
                    "2160p": "2160p (4K)",
                    "1440p": "1440p (2K)",
                    "1080p": "1080p",
                    "720p": "720p",
                    "480p": "480p",
                    "360p": "360p",
                    "240p": "240p"
                }
                sorted_resolutions = []
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
    def _execute_ydl(
        url: str,
        output_dir: str,
        format_type: str,
        quality: str,
        embed_metadata: bool,
        embed_thumbnail: bool,
        download_subtitles: bool,
        time_range: Optional[Tuple[int, int]],
        rate_limit_bytes: Optional[int],
        cookies_browser: Optional[str],
        progress_callback: Optional[Callable[[Dict[str, Any]], None]],
        cancel_event: Optional[threading.Event]
    ) -> Tuple[str, Optional[str], str]:
        """Función interna que configura y ejecuta yt-dlp."""
        os.makedirs(output_dir, exist_ok=True)
        final_downloaded_file = ""

        def progress_hook(d):
            nonlocal final_downloaded_file
            if cancel_event and cancel_event.is_set():
                raise Exception("DESCARGA_CANCELADA_POR_USUARIO")

            fname = d.get('filename')
            if fname:
                final_downloaded_file = fname

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
                    'filename': os.path.basename(fname or '')
                }
                progress_callback(progress_data)

            elif status == 'finished':
                progress_callback({
                    'status': 'processing',
                    'percent': 100.0,
                    'percent_str': "100%",
                    'speed_str': "Completado",
                    'eta_str': "Procesando audio/video con FFmpeg...",
                    'filename': os.path.basename(fname or '')
                })

        outtmpl = os.path.join(output_dir, '%(title)s [%(id)s].%(ext)s')

        ydl_opts: Dict[str, Any] = {
            'outtmpl': outtmpl,
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [progress_hook],
            'ignoreerrors': False,
            'nocheckcertificate': True,
        }

        # Ubicación personalizada o empaquetada de FFmpeg
        ffmpeg_loc = DownloaderEngine.get_ffmpeg_location()
        if ffmpeg_loc:
            ydl_opts['ffmpeg_location'] = ffmpeg_loc

        # Límite de velocidad
        if rate_limit_bytes and rate_limit_bytes > 0:
            ydl_opts['ratelimit'] = rate_limit_bytes

        # Cookies del navegador
        if cookies_browser and cookies_browser.lower() != "ninguno":
            ydl_opts['cookiesfrombrowser'] = (cookies_browser.lower(),)

        # Recorte por tiempo (Trim / Download Sections)
        if time_range:
            start_s, end_s = time_range
            if start_s is not None and end_s is not None and end_s > start_s:
                ydl_opts['download_ranges'] = download_range_func(None, [(start_s, end_s)])
                ydl_opts['force_keyframes_at_cuts'] = True

        format_clean = format_type.upper().strip()

        if format_clean in ["MP3", "M4A", "WAV", "FLAC"]:
            ydl_opts['format'] = 'bestaudio/best'
            postprocessors = []

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
            title = info.get('title', 'Video') if info else 'Descarga completa'

            # Determinar ruta final del archivo
            target_ext = format_clean.lower()
            if not final_downloaded_file and info:
                final_downloaded_file = ydl.prepare_filename(info)
            if final_downloaded_file:
                base_f = os.path.splitext(final_downloaded_file)[0]
                possible_path = f"{base_f}.{target_ext}"
                if os.path.exists(possible_path):
                    final_downloaded_file = possible_path

            if progress_callback:
                progress_callback({
                    'status': 'finished',
                    'percent': 100.0,
                    'percent_str': "100%",
                    'speed_str': "Finalizado",
                    'eta_str': "¡Listo!",
                    'title': title
                })
            return title, None, final_downloaded_file

    @classmethod
    def download(
        cls,
        url: str,
        output_dir: str,
        format_type: str = "MP4",
        quality: str = "1080p",
        embed_metadata: bool = True,
        embed_thumbnail: bool = True,
        download_subtitles: bool = False,
        time_range: Optional[Tuple[int, int]] = None,
        rate_limit_bytes: Optional[int] = None,
        cookies_browser: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> Tuple[str, Optional[str], str]:
        """
        Descarga el medio con tolerancia a fallos, soporte de recorte, límites de velocidad y cookies.
        """
        try:
            return cls._execute_ydl(
                url=url,
                output_dir=output_dir,
                format_type=format_type,
                quality=quality,
                embed_metadata=embed_metadata,
                embed_thumbnail=embed_thumbnail,
                download_subtitles=download_subtitles,
                time_range=time_range,
                rate_limit_bytes=rate_limit_bytes,
                cookies_browser=cookies_browser,
                progress_callback=progress_callback,
                cancel_event=cancel_event
            )
        except Exception as e:
            err_msg = clean_ansi(str(e))
            if "DESCARGA_CANCELADA_POR_USUARIO" in err_msg:
                raise e

            if download_subtitles and any(k in err_msg.lower() for k in ["subtitle", "subtítulo", "429"]):
                try:
                    title, _, final_path = cls._execute_ydl(
                        url=url,
                        output_dir=output_dir,
                        format_type=format_type,
                        quality=quality,
                        embed_metadata=embed_metadata,
                        embed_thumbnail=embed_thumbnail,
                        download_subtitles=False,
                        time_range=time_range,
                        rate_limit_bytes=rate_limit_bytes,
                        cookies_browser=cookies_browser,
                        progress_callback=progress_callback,
                        cancel_event=cancel_event
                    )
                    warning = (
                        "⚠️ Nota de Subtítulos:\n"
                        "YouTube no permitió la descarga de subtítulos para este video "
                        "(Error 429: Too Many Requests o no disponibles).\n\n"
                        "El video/audio se descargó y procesó con éxito sin subtítulos.\n"
                        "Puedes desmarcar la casilla 'Subtítulos (.srt)' para evitar esta comprobación."
                    )
                    return title, warning, final_path
                except Exception as e2:
                    err_msg = clean_ansi(str(e2))

            if embed_thumbnail and any(k in err_msg.lower() for k in ["thumbnail", "carátula", "mutagen", "atomicparsley"]):
                try:
                    title, _, final_path = cls._execute_ydl(
                        url=url,
                        output_dir=output_dir,
                        format_type=format_type,
                        quality=quality,
                        embed_metadata=embed_metadata,
                        embed_thumbnail=False,
                        download_subtitles=False,
                        time_range=time_range,
                        rate_limit_bytes=rate_limit_bytes,
                        cookies_browser=cookies_browser,
                        progress_callback=progress_callback,
                        cancel_event=cancel_event
                    )
                    warning = (
                        "⚠️ Nota de Carátula:\n"
                        "No fue posible incrustar la carátula en este archivo específico.\n\n"
                        "El video/audio se descargó correctamente sin carátula embebida.\n"
                        "Puedes desactivar la opción 'Carátula / ID3'."
                    )
                    return title, warning, final_path
                except Exception as e3:
                    err_msg = clean_ansi(str(e3))

            raise Exception(err_msg)
