import tkinter as tk
from PIL import Image, ImageDraw, ImageFont, ImageTk
import getpass
import socket
import os

Host_nombre = socket.gethostname()
nombre_usuario = getpass.getuser()
host_y_usuario = f"{Host_nombre} / {nombre_usuario}"

def mostrar_imagen_con_texto(duration_ms=1200):
    """Muestra una pantalla de carga elegante y se cierra automáticamente."""
    try:
        root = tk.Tk()
        root.overrideredirect(True)

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        width = 320
        height = 320
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        root.geometry(f"{width}x{height}+{x}+{y}")
        root.configure(bg="#0f172a")

        # Cargar y procesar imagen si existe
        img_path = os.path.join(os.path.dirname(__file__), 'lib', 'data', 'loading.png')
        if os.path.exists(img_path):
            img = Image.open(img_path).convert("RGBA")
            img = img.resize((width, height), Image.Resampling.LANCZOS)
            draw = ImageDraw.Draw(img)

            # Texto estilizado
            font_path = os.path.join(os.path.dirname(__file__), 'lib', 'data', 'fuente', 'poppins.ttf')
            font_title = None
            font_sub = None
            if os.path.exists(font_path):
                try:
                    font_title = ImageFont.truetype(font_path, 18)
                    font_sub = ImageFont.truetype(font_path, 11)
                except Exception:
                    pass

            draw.text((35, 180), "Media Downloader Pro", fill="#ffffff", font=font_title)
            draw.text((105, 215), "Iniciando...", fill="#38bdf8", font=font_sub)
            draw.text((70, 275), host_y_usuario, fill="#94a3b8", font=font_sub)

            tk_img = ImageTk.PhotoImage(img)
            label = tk.Label(root, image=tk_img, bg="#0f172a", bd=0)
            label.image = tk_img
            label.pack(expand=True, fill="both")
        else:
            # Fallback simple sin imagen
            lbl_title = tk.Label(root, text="Media Downloader Pro", font=("Helvetica", 16, "bold"), fg="#ffffff", bg="#0f172a")
            lbl_title.pack(pady=(100, 10))
            lbl_sub = tk.Label(root, text="Iniciando...", font=("Helvetica", 11), fg="#38bdf8", bg="#0f172a")
            lbl_sub.pack()

        # Cerrar automáticamente tras duration_ms
        root.after(duration_ms, root.destroy)
        root.mainloop()
    except Exception as e:
        print(f"Nota en splash screen: {e}")

if __name__ == "__main__":
    mostrar_imagen_con_texto()
