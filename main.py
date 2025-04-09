from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.lang import Builder
from kivy.properties import ListProperty
import sqlite3
from datetime import datetime

# ---------- CONFIG ----------
CONTRASENA_ADMIN = "rosse1290"

# ---------- DB ----------
def setup_db():
    conn = sqlite3.connect('restaurante.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, precio REAL NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY, producto_id INTEGER, cantidad INTEGER, estado TEXT, fecha TEXT,
        FOREIGN KEY (producto_id) REFERENCES productos (id))''')
    cursor.execute("SELECT COUNT(*) FROM productos")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO productos (nombre, precio) VALUES (?, ?)", [
            ("Hamburguesa", 50),
            ("Papas Fritas", 20),
            ("Refresco", 15)
        ])
    conn.commit()
    conn.close()

setup_db()

# ---------- PANTALLAS ----------
class CajeroScreen(Screen):
    productos = ListProperty([])

    def on_enter(self):
        conn = sqlite3.connect('restaurante.db')
        cursor = conn.cursor()
        cursor.execute("SELECT nombre FROM productos")
        self.productos = [row[0] for row in cursor.fetchall()]
        conn.close()
        self.ids.productos_spinner.values = self.productos

    def enviar_pedido(self):
        producto = self.ids.productos_spinner.text
        cantidad = int(self.ids.cantidad_spinner.text)
        if producto not in self.productos:
            self.popup("Error", "Selecciona un producto válido.")
            return
        conn = sqlite3.connect('restaurante.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM productos WHERE nombre = ?", (producto,))
        producto_id = cursor.fetchone()[0]
        cursor.execute("INSERT INTO pedidos (producto_id, cantidad, estado, fecha) VALUES (?, ?, 'Pendiente', ?)",
                       (producto_id, cantidad, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        self.popup("Éxito", "Pedido enviado a cocina.")

    def popup(self, title, msg):
        Popup(title=title, content=Label(text=msg), size_hint=(None, None), size=(300, 200)).open()


class CocinaScreen(Screen):
    def on_enter(self):
        self.actualizar()

    def actualizar(self):
        self.ids.pedidos_grid.clear_widgets()
        conn = sqlite3.connect('restaurante.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT p.id, pr.nombre, p.cantidad FROM pedidos p
                          JOIN productos pr ON p.producto_id = pr.id
                          WHERE p.estado = 'Pendiente' ''')
        for pedido_id, nombre, cantidad in cursor.fetchall():
            fila = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
            fila.add_widget(Label(text=f"{nombre} x{cantidad}", size_hint_x=0.7))
            btn = Button(text="Listo", size_hint_x=0.3)
            btn.bind(on_release=lambda _, pid=pedido_id: self.marcar_listo(pid))
            fila.add_widget(btn)
            self.ids.pedidos_grid.add_widget(fila)
        conn.close()

    def marcar_listo(self, pedido_id):
        conn = sqlite3.connect('restaurante.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE pedidos SET estado = 'Listo' WHERE id = ?", (pedido_id,))
        conn.commit()
        conn.close()
        self.actualizar()


class VentasScreen(Screen):
    def on_enter(self):
        self.ids.info_layout.clear_widgets()
        self.ids.lista_ventas.clear_widgets()
        self.ids.label_total.text = ""
        self.ids.input_contrasena.text = ""

    def verificar_contrasena(self):
        if self.ids.input_contrasena.text == CONTRASENA_ADMIN:
            self.ids.input_contrasena.disabled = True
            self.ids.btn_acceso.disabled = True
            self.ids.info_layout.add_widget(self.ids.btn_actualizar)
            self.ids.info_layout.add_widget(self.ids.btn_reiniciar)
            self.actualizar_ventas()
        else:
            self.popup("Error", "Contraseña incorrecta")

    def actualizar_ventas(self):
        self.ids.lista_ventas.clear_widgets()
        total = 0
        hoy = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect('restaurante.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT pr.nombre, p.cantidad, pr.precio * p.cantidad, p.fecha
                          FROM pedidos p JOIN productos pr ON p.producto_id = pr.id
                          WHERE p.estado = 'Listo' AND date(p.fecha) = ?
                          ORDER BY p.fecha DESC''', (hoy,))
        for nombre, cantidad, total_linea, fecha in cursor.fetchall():
            hora = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S").strftime("%H:%M")
            self.ids.lista_ventas.add_widget(Label(
                text=f"{nombre} x{cantidad} - ${total_linea:.2f} a las {hora}", size_hint_y=None, height=30))
            total += total_linea
        self.ids.label_total.text = f"Total vendido hoy: ${total:.2f}"
        conn.close()

    def reiniciar_ventas(self):
        hoy = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect('restaurante.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pedidos WHERE estado = 'Listo' AND date(fecha) = ?", (hoy,))
        conn.commit()
        conn.close()
        self.actualizar_ventas()
        self.popup("Listo", "Ventas reiniciadas")

    def popup(self, title, msg):
        Popup(title=title, content=Label(text=msg), size_hint=(None, None), size=(300, 200)).open()


class AdminScreen(Screen):
    def on_enter(self):
        self.actualizar()

    def actualizar(self):
        self.ids.lista_admin.clear_widgets()
        conn = sqlite3.connect('restaurante.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, precio FROM productos")
        for pid, nombre, precio in cursor.fetchall():
            fila = BoxLayout(size_hint_y=None, height=40)
            fila.add_widget(Label(text=f"{pid} - {nombre} - ${precio:.2f}"))
            btn_edit = Button(text="Editar", size_hint_x=0.2)
            btn_edit.bind(on_release=lambda _, id=pid: self.editar(id))
            btn_del = Button(text="Eliminar", size_hint_x=0.2)
            btn_del.bind(on_release=lambda _, id=pid: self.eliminar(id))
            fila.add_widget(btn_edit)
            fila.add_widget(btn_del)
            self.ids.lista_admin.add_widget(fila)
        conn.close()

    def agregar(self):
        self.popup_agregar()

    def editar(self, producto_id):
        self.popup_editar(producto_id)

    def eliminar(self, producto_id):
        conn = sqlite3.connect('restaurante.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE producto_id = ? AND estado = 'Pendiente'", (producto_id,))
        if cursor.fetchone()[0] > 0:
            self.popup("Error", "No se puede eliminar, hay pedidos pendientes")
        else:
            cursor.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
            conn.commit()
            self.popup("Éxito", "Producto eliminado")
        conn.close()
        self.actualizar()

    def popup(self, titulo, mensaje):
        Popup(title=titulo, content=Label(text=mensaje), size_hint=(None, None), size=(300, 200)).open()

    def popup_agregar(self):
        box = BoxLayout(orientation='vertical')
        nombre = TextInput(hint_text="Nombre")
        precio = TextInput(hint_text="Precio")
        box.add_widget(nombre)
        box.add_widget(precio)
        btn = Button(text="Guardar")
        box.add_widget(btn)

        def guardar(_):
            conn = sqlite3.connect('restaurante.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO productos (nombre, precio) VALUES (?, ?)",
                           (nombre.text, float(precio.text)))
            conn.commit()
            conn.close()
            popup.dismiss()
            self.actualizar()

        btn.bind(on_release=guardar)
        popup = Popup(title="Agregar producto", content=box, size_hint=(None, None), size=(300, 300))
        popup.open()

    def popup_editar(self, pid):
        conn = sqlite3.connect('restaurante.db')
        cursor = conn.cursor()
        cursor.execute("SELECT nombre, precio FROM productos WHERE id = ?", (pid,))
        nombre_actual, precio_actual = cursor.fetchone()
        conn.close()

        box = BoxLayout(orientation='vertical')
        nombre = TextInput(text=nombre_actual)
        precio = TextInput(text=str(precio_actual))
        box.add_widget(nombre)
        box.add_widget(precio)
        btn = Button(text="Actualizar")
        box.add_widget(btn)

        def actualizar(_):
            conn = sqlite3.connect('restaurante.db')
            cursor = conn.cursor()
            cursor.execute("UPDATE productos SET nombre = ?, precio = ? WHERE id = ?",
                           (nombre.text, float(precio.text), pid))
            conn.commit()
            conn.close()
            popup.dismiss()
            self.actualizar()

        btn.bind(on_release=actualizar)
        popup = Popup(title="Editar producto", content=box, size_hint=(None, None), size=(300, 300))
        popup.open()

# ---------- UI ----------
Builder.load_string("""
<CajeroScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 10
        spacing: 10

        Spinner:
            id: productos_spinner
            text: "Seleccionar producto"
            size_hint_y: None
            height: 44

        Spinner:
            id: cantidad_spinner
            text: "1"
            values: [str(i) for i in range(1, 11)]
            size_hint_y: None
            height: 44

        Button:
            text: "Enviar a cocina"
            on_release: root.enviar_pedido()

        Button:
            text: "Ir a Cocina"
            on_release: app.root.current = 'cocina'

        Button:
            text: "Ir a Ventas"
            on_release: app.root.current = 'ventas'

        Button:
            text: "Ir a Administración"
            on_release: app.root.current = 'admin'

<CocinaScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 10
        spacing: 10

        ScrollView:
            GridLayout:
                id: pedidos_grid
                cols: 1
                size_hint_y: None
                height: self.minimum_height

        Button:
            text: "Actualizar"
            on_release: root.actualizar()

        Button:
            text: "Ir a Cajero"
            on_release: app.root.current = 'cajero'

<VentasScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 10
        spacing: 10

        TextInput:
            id: input_contrasena
            hint_text: "Contraseña"
            password: True
            multiline: False
            size_hint_y: None
            height: 40

        Button:
            id: btn_acceso
            text: "Ingresar"
            on_release: root.verificar_contrasena()

        BoxLayout:
            id: info_layout
            orientation: 'horizontal'
            size_hint_y: None
            height: 40
            spacing: 5

            Button:
                id: btn_actualizar
                text: "Actualizar"
                on_release: root.actualizar_ventas()

            Button:
                id: btn_reiniciar
                text: "Reiniciar"
                on_release: root.reiniciar_ventas()

        Label:
            id: label_total
            text: ""

        ScrollView:
            GridLayout:
                id: lista_ventas
                cols: 1
                size_hint_y: None
                height: self.minimum_height

        Button:
            text: "Ir a Cajero"
            on_release: app.root.current = 'cajero'

<AdminScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 10
        spacing: 10

        ScrollView:
            GridLayout:
                id: lista_admin
                cols: 1
                size_hint_y: None
                height: self.minimum_height

        Button:
            text: "Agregar producto"
            on_release: root.agregar()

        Button:
            text: "Ir a Cajero"
            on_release: app.root.current = 'cajero'
""")

# ---------- APP ----------
class RestauranteApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(CajeroScreen(name='cajero'))
        sm.add_widget(CocinaScreen(name='cocina'))
        sm.add_widget(VentasScreen(name='ventas'))
        sm.add_widget(AdminScreen(name='admin'))
        return sm

if __name__ == "__main__":
    RestauranteApp().run()

print('Hola desde Kivy')