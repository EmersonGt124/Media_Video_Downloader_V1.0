import sys
from tkinter import messagebox
import tkinter as tk

def _ensure_tk_root():
    """Asegura que haya una instancia de Tk si aún no se ha creado."""
    try:
        if tk._default_root is None:
            temp_root = tk.Tk()
            temp_root.withdraw()
    except Exception:
        pass

def alerta_ok(titulo_ventana, titulo, texto):
    """Muestra alerta informativa con botón Aceptar."""
    _ensure_tk_root()
    messagebox.showinfo(title=titulo or titulo_ventana, message=texto)
    return 1

def alerta_error(titulo_ventana, titulo, texto):
    """Muestra alerta de error con botón Aceptar."""
    _ensure_tk_root()
    messagebox.showerror(title=titulo or titulo_ventana, message=texto)
    return 1

def alerta_aceptar(titulo_ventana, titulo, texto):
    """Muestra diálogo de confirmación (Sí/No). Retorna 1 si confirma, 2 si cancela."""
    _ensure_tk_root()
    resp = messagebox.askyesno(title=titulo or titulo_ventana, message=texto)
    return 1 if resp else 2

def alerta_aceptar_sin(titulo, texto):
    """Muestra diálogo de confirmación independiente."""
    _ensure_tk_root()
    resp = messagebox.askyesno(title=titulo, message=texto)
    return 1 if resp else 2

def alerta_cerrar(titulo_ventana, titulo, texto):
    """Muestra alerta de confirmación para cerrar."""
    _ensure_tk_root()
    resp = messagebox.askokcancel(title=titulo or titulo_ventana, message=texto)
    return 1 if resp else 2

def alerta_Amarilla(titulo_ventana, titulo, texto):
    """Muestra alerta de advertencia con botón Aceptar."""
    _ensure_tk_root()
    messagebox.showwarning(title=titulo or titulo_ventana, message=texto)
    return 1
