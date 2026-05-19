#!/usr/bin/env python3
"""
room_editor.py — Editor grafico per definire le stanze sulla mappa ROS2.

Uso:
    python3 room_editor.py --map /path/to/home_map.yaml

Dipendenze:
    pip install pillow pyyaml
"""

import argparse
import json
import math
import os
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
from PIL import Image, ImageTk, ImageDraw
import yaml


# ─────────────────────────────────────────────────────────────────────────────
# Conversione pixel ↔ coordinate mondo ROS
# ─────────────────────────────────────────────────────────────────────────────

class MapInfo:
    def __init__(self, yaml_path: str):
        with open(yaml_path, 'r') as f:
            meta = yaml.safe_load(f)

        self.resolution = meta['resolution']          # metri/pixel
        self.origin     = meta['origin']              # [x, y, yaw] angolo in basso a sinistra
        self.image_path = os.path.join(os.path.dirname(yaml_path), meta['image'])

    def pixel_to_world(self, px: int, py: int, img_height: int):
        """Converte coordinate pixel (origine in alto a sinistra) in coordinate mondo ROS (metri)."""
        wx = self.origin[0] + px * self.resolution
        wy = self.origin[1] + (img_height - py) * self.resolution
        return round(wx, 3), round(wy, 3)

    def world_to_pixel(self, wx: float, wy: float, img_height: int):
        px = int((wx - self.origin[0]) / self.resolution)
        py = int(img_height - (wy - self.origin[1]) / self.resolution)
        return px, py


# ─────────────────────────────────────────────────────────────────────────────
# Applicazione principale
# ─────────────────────────────────────────────────────────────────────────────

COLORS = ['#e74c3c','#3498db','#2ecc71','#f39c12','#9b59b6',
          '#1abc9c','#e67e22','#34495e','#e91e63','#00bcd4']

class RoomEditor:
    def __init__(self, root: tk.Tk, map_info: MapInfo | None = None):
        self.root      = root
        self.map_info  = map_info
        self.rooms     = []          # lista di dict con nome e coordinate
        self.color_idx = 0

        # Stato disegno
        self.drawing    = False
        self.start_x    = 0
        self.start_y    = 0
        self.current_rect = None

        # Zoom e pan
        self.scale      = 1.0
        self.offset_x   = 0
        self.offset_y   = 0
        self._pan_start = None

        self._build_ui()

        if map_info:
            self._load_map_image(map_info.image_path)
        else:
            self._blank_canvas()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.root.title('Room Editor')
        self.root.configure(bg='#1e1e2e')

        # Toolbar
        toolbar = tk.Frame(self.root, bg='#2a2a3e', pady=6)
        toolbar.pack(fill=tk.X)

        btn_style = dict(bg='#3a3a5e', fg='white', relief=tk.FLAT,
                         padx=10, pady=4, cursor='hand2', font=('Courier', 10))

        tk.Button(toolbar, text='📂  Apri mappa', command=self._open_map,   **btn_style).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text='💾  Salva stanze', command=self._save_rooms, **btn_style).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text='📥  Carica stanze', command=self._load_rooms,**btn_style).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text='🗑  Cancella ultima', command=self._delete_last, **btn_style).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text='🔄  Reset zoom',    command=self._reset_zoom,    **btn_style).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text='⛶  Adatta schermo', command=self._fit_to_window, **btn_style).pack(side=tk.LEFT, padx=4)

        self.mode_label = tk.Label(toolbar, text='MODALITÀ: DISEGNA', bg='#2a2a3e',
                                   fg='#2ecc71', font=('Courier', 10, 'bold'))
        self.mode_label.pack(side=tk.RIGHT, padx=10)

        # Layout principale
        main = tk.Frame(self.root, bg='#1e1e2e')
        main.pack(fill=tk.BOTH, expand=True)

        # Canvas mappa
        self.canvas = tk.Canvas(main, bg='#111122', cursor='crosshair',
                                 highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Sidebar stanze
        sidebar = tk.Frame(main, bg='#2a2a3e', width=240)
        sidebar.pack(side=tk.RIGHT, fill=tk.Y)
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text='STANZE', bg='#2a2a3e', fg='#aaaacc',
                 font=('Courier', 11, 'bold')).pack(pady=(12, 4))

        self.room_listbox = tk.Listbox(sidebar, bg='#1e1e2e', fg='white',
                                        font=('Courier', 10), selectbackground='#3a3a6e',
                                        relief=tk.FLAT, borderwidth=0)
        self.room_listbox.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.room_listbox.bind('<<ListboxSelect>>', self._on_room_select)

        tk.Button(sidebar, text='✏️  Rinomina', command=self._rename_room,
                  bg='#3a3a5e', fg='white', relief=tk.FLAT, pady=4,
                  font=('Courier', 10)).pack(fill=tk.X, padx=8, pady=2)
        tk.Button(sidebar, text='🗑  Elimina', command=self._delete_selected,
                  bg='#5e3a3a', fg='white', relief=tk.FLAT, pady=4,
                  font=('Courier', 10)).pack(fill=tk.X, padx=8, pady=2)

        # Status bar
        self.status = tk.Label(self.root, text='Apri una mappa .yaml o disegna su tela vuota',
                               bg='#12121e', fg='#666688', anchor='w',
                               font=('Courier', 9), padx=8)
        self.status.pack(fill=tk.X)

        # Binding mouse
        self.canvas.bind('<ButtonPress-1>',   self._on_press)
        self.canvas.bind('<B1-Motion>',       self._on_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_release)
        self.canvas.bind('<ButtonPress-2>',   self._pan_start_cb)
        self.canvas.bind('<B2-Motion>',       self._pan_move_cb)
        self.canvas.bind('<ButtonPress-3>',   self._pan_start_cb)
        self.canvas.bind('<B3-Motion>',       self._pan_move_cb)
        self.canvas.bind('<MouseWheel>',      self._on_zoom)
        self.canvas.bind('<Button-4>',        self._on_zoom)
        self.canvas.bind('<Button-5>',        self._on_zoom)
        self.canvas.bind('<Motion>',          self._on_motion)

    # ── Mappa ────────────────────────────────────────────────────────────────

    def _open_map(self):
        path = filedialog.askopenfilename(
            title='Apri mappa ROS2',
            filetypes=[('YAML map', '*.yaml'), ('Tutti i file', '*.*')]
        )
        if not path:
            return
        try:
            self.map_info = MapInfo(path)
            self._load_map_image(self.map_info.image_path)
            self.status.config(text=f'Mappa caricata: {path}')
        except Exception as e:
            messagebox.showerror('Errore', f'Impossibile caricare la mappa:\n{e}')

    def _load_map_image(self, image_path: str):
        img = Image.open(image_path).convert('RGB')
        self.orig_image  = img
        self.img_width   = img.width
        self.img_height  = img.height
        self._fit_to_window()

    def _blank_canvas(self):
        self.orig_image  = Image.new('RGB', (800, 600), color=(30, 30, 50))
        self.img_width   = 800
        self.img_height  = 600
        self.map_info    = None
        self._fit_to_window()

    def _fit_to_window(self):
        """Scala la mappa per riempire il canvas mantenendo l'aspect ratio."""
        self.root.update_idletasks()
        cw = self.canvas.winfo_width()  or 900
        ch = self.canvas.winfo_height() or 700
        scale_x = cw / self.img_width
        scale_y = ch / self.img_height
        self.scale    = min(scale_x, scale_y) * 0.95   # 5% margine
        self.offset_x = (cw - self.img_width  * self.scale) / 2
        self.offset_y = (ch - self.img_height * self.scale) / 2
        self._render()

    def _reset_zoom(self):
        self.scale    = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self._render()

    def _render(self):
        """Ridisegna canvas con zoom/pan e tutti i rettangoli."""
        w = int(self.img_width  * self.scale)
        h = int(self.img_height * self.scale)

        resized = self.orig_image.resize((w, h), Image.NEAREST)

        # Disegna rettangoli sulla copia
        draw = ImageDraw.Draw(resized)
        for i, room in enumerate(self.rooms):
            color = room['color']
            x1, y1, x2, y2 = [int(c * self.scale) for c in room['pixels']]
            draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
            draw.rectangle([x1, y1, x1 + len(room['name'])*7 + 6, y1 + 16],
                           fill=color)
            draw.text((x1 + 3, y1 + 1), room['name'], fill='white')

        self.tk_image = ImageTk.PhotoImage(resized)
        self.canvas.delete('all')
        self.canvas.create_image(self.offset_x, self.offset_y,
                                  anchor=tk.NW, image=self.tk_image)

    # ── Disegno rettangoli ────────────────────────────────────────────────────

    def _canvas_to_img(self, cx, cy):
        """Converte coordinate canvas in coordinate immagine originale."""
        ix = (cx - self.offset_x) / self.scale
        iy = (cy - self.offset_y) / self.scale
        return ix, iy

    def _on_press(self, event):
        self.drawing  = True
        self.start_x  = event.x
        self.start_y  = event.y
        self.current_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline=COLORS[self.color_idx % len(COLORS)], width=2, dash=(4, 2)
        )

    def _on_drag(self, event):
        if self.drawing and self.current_rect:
            self.canvas.coords(self.current_rect,
                                self.start_x, self.start_y, event.x, event.y)

    def _on_release(self, event):
        if not self.drawing:
            return
        self.drawing = False

        x1c, y1c = min(self.start_x, event.x), min(self.start_y, event.y)
        x2c, y2c = max(self.start_x, event.x), max(self.start_y, event.y)

        if abs(x2c - x1c) < 10 or abs(y2c - y1c) < 10:
            if self.current_rect:
                self.canvas.delete(self.current_rect)
            return

        # Coordinate immagine originale
        x1i, y1i = self._canvas_to_img(x1c, y1c)
        x2i, y2i = self._canvas_to_img(x2c, y2c)

        name = simpledialog.askstring('Nome stanza', 'Inserisci il nome della stanza:',
                                       parent=self.root)
        if not name:
            self.canvas.delete(self.current_rect)
            return

        color = COLORS[self.color_idx % len(COLORS)]
        self.color_idx += 1

        room = {
            'name':   name,
            'color':  color,
            'pixels': [int(x1i), int(y1i), int(x2i), int(y2i)],
        }

        # Coordinate mondo se disponibile la mappa
        if self.map_info:
            wx1, wy1 = self.map_info.pixel_to_world(int(x1i), int(y1i), self.img_height)
            wx2, wy2 = self.map_info.pixel_to_world(int(x2i), int(y2i), self.img_height)
            room['world'] = {
                'x_min': min(wx1, wx2), 'y_min': min(wy1, wy2),
                'x_max': max(wx1, wx2), 'y_max': max(wy1, wy2),
                'center_x': round((wx1 + wx2) / 2, 3),
                'center_y': round((wy1 + wy2) / 2, 3),
            }

        self.rooms.append(room)
        self._update_listbox()
        self._render()
        self.status.config(text=f'Stanza "{name}" aggiunta.')

    # ── Pan e zoom ───────────────────────────────────────────────────────────

    def _pan_start_cb(self, event):
        self._pan_start = (event.x, event.y, self.offset_x, self.offset_y)

    def _pan_move_cb(self, event):
        if not self._pan_start:
            return
        dx = event.x - self._pan_start[0]
        dy = event.y - self._pan_start[1]
        self.offset_x = self._pan_start[2] + dx
        self.offset_y = self._pan_start[3] + dy
        self._render()

    def _on_zoom(self, event):
        factor = 1.1 if (event.delta > 0 or event.num == 4) else 0.9
        # Zoom centrato sul cursore
        cx = (event.x - self.offset_x) / self.scale
        cy = (event.y - self.offset_y) / self.scale
        self.scale    *= factor
        self.scale     = max(0.1, min(self.scale, 10.0))
        self.offset_x  = event.x - cx * self.scale
        self.offset_y  = event.y - cy * self.scale
        self._render()

    def _on_motion(self, event):
        ix, iy = self._canvas_to_img(event.x, event.y)
        if self.map_info:
            wx, wy = self.map_info.pixel_to_world(int(ix), int(iy), self.img_height)
            self.status.config(text=f'Pixel: ({int(ix)}, {int(iy)})  |  Mondo: ({wx}, {wy}) m')
        else:
            self.status.config(text=f'Pixel: ({int(ix)}, {int(iy)})')

    # ── Gestione stanze ───────────────────────────────────────────────────────

    def _update_listbox(self):
        self.room_listbox.delete(0, tk.END)
        for i, room in enumerate(self.rooms):
            label = f'{i+1}. {room["name"]}'
            if 'world' in room:
                c = room['world']
                label += f'  ({c["center_x"]}, {c["center_y"]})'
            self.room_listbox.insert(tk.END, label)

    def _on_room_select(self, event):
        pass

    def _delete_last(self):
        if self.rooms:
            removed = self.rooms.pop()
            self._update_listbox()
            self._render()
            self.status.config(text=f'Stanza "{removed["name"]}" rimossa.')

    def _delete_selected(self):
        sel = self.room_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        name = self.rooms[idx]['name']
        self.rooms.pop(idx)
        self._update_listbox()
        self._render()
        self.status.config(text=f'Stanza "{name}" eliminata.')

    def _rename_room(self):
        sel = self.room_listbox.curselection()
        if not sel:
            messagebox.showinfo('Info', 'Seleziona prima una stanza dalla lista.')
            return
        idx = sel[0]
        new_name = simpledialog.askstring('Rinomina',
                                           f'Nuovo nome per "{self.rooms[idx]["name"]}":',
                                           parent=self.root)
        if new_name:
            self.rooms[idx]['name'] = new_name
            self._update_listbox()
            self._render()

    # ── Salva / carica ────────────────────────────────────────────────────────

    def _save_rooms(self):
        if not self.rooms:
            messagebox.showinfo('Info', 'Nessuna stanza da salvare.')
            return

        path = filedialog.asksaveasfilename(
            title='Salva stanze',
            defaultextension='.json',
            filetypes=[('JSON', '*.json')]
        )
        if not path:
            return

        # Output pulito senza colore e pixel interni
        output = []
        for room in self.rooms:
            entry = {'name': room['name']}
            if 'world' in room:
                entry['world'] = room['world']
            else:
                entry['pixels'] = room['pixels']
            output.append(entry)

        with open(path, 'w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        self.status.config(text=f'Stanze salvate in: {path}')
        messagebox.showinfo('Salvato', f'{len(output)} stanze salvate in:\n{path}')

    def _load_rooms(self):
        path = filedialog.askopenfilename(
            title='Carica stanze',
            filetypes=[('JSON', '*.json')]
        )
        if not path:
            return
        with open(path, 'r') as f:
            data = json.load(f)

        self.rooms = []
        for i, entry in enumerate(data):
            room = {
                'name':  entry['name'],
                'color': COLORS[i % len(COLORS)],
            }
            if 'world' in entry and self.map_info:
                room['world']  = entry['world']
                # Riconverti in pixel per il disegno
                px1, py1 = self.map_info.world_to_pixel(
                    entry['world']['x_min'], entry['world']['y_max'], self.img_height)
                px2, py2 = self.map_info.world_to_pixel(
                    entry['world']['x_max'], entry['world']['y_min'], self.img_height)
                room['pixels'] = [px1, py1, px2, py2]
            elif 'pixels' in entry:
                room['pixels'] = entry['pixels']
            self.rooms.append(room)

        self._update_listbox()
        self._render()
        self.status.config(text=f'{len(self.rooms)} stanze caricate da {path}')


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Room Editor per mappe ROS2')
    parser.add_argument('--map', type=str, default=None,
                        help='Path al file .yaml della mappa (es. ~/map/home_map.yaml)')
    args = parser.parse_args()

    map_info = None
    if args.map:
        try:
            map_info = MapInfo(args.map)
        except Exception as e:
            print(f'[WARN] Impossibile caricare la mappa: {e}')

    root = tk.Tk()
    root.geometry('1200x800')
    app  = RoomEditor(root, map_info)
    root.mainloop()


if __name__ == '__main__':
    main()