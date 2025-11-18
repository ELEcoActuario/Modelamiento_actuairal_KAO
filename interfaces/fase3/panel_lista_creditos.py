import tkinter as tk
from tkinter import ttk

class PanelListaCreditos(ttk.Frame):
    """
    Panel para mostrar la lista de créditos filtrados y permitir su selección.
    """
    def __init__(self, master, select_command):
        super().__init__(master, padding=10)
        self.select_command = select_command
        self._crear_widgets()

    def _crear_widgets(self):
        ttk.Label(self, text="Créditos Disponibles:", font=("Arial", 12, "bold")).pack(anchor="w")

        frame_lista = ttk.Frame(self)
        frame_lista.pack(fill="both", expand=True)

        # Listbox con scrollbar
        self.scrollbar = ttk.Scrollbar(frame_lista, orient="vertical")
        self.lista_creditos = tk.Listbox(frame_lista, height=20, yscrollcommand=self.scrollbar.set, exportselection=False)
        self.scrollbar.config(command=self.lista_creditos.yview)

        self.lista_creditos.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.lista_creditos.bind("<<ListboxSelect>>", self.select_command)

    def actualizar_lista(self, lista_ids):
        """
        Reemplaza el contenido de la lista con los ID de créditos proporcionados.
        """
        self.lista_creditos.delete(0, tk.END)
        for id_credito in lista_ids:
            self.lista_creditos.insert(tk.END, str(id_credito))

    def get_seleccion_actual(self):
        """
        Devuelve el ID de crédito actualmente seleccionado.
        """
        sel = self.lista_creditos.curselection()
        if not sel:
            return None
        return self.lista_creditos.get(sel[0])

    def limpiar_lista(self):
        """Elimina todos los créditos mostrados en la lista."""
        self.lista_creditos.delete(0, tk.END)

    def deshabilitar_lista(self):
        """Desactiva la lista temporalmente."""
        self.lista_creditos.config(state="disabled")

    def habilitar_lista(self):
        """Activa nuevamente la lista."""
        self.lista_creditos.config(state="normal")
