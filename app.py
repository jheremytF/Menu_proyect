"""Inventario web local con Flask y SQLite.

Ejecutar: pip install -r requirements.txt && python app.py
Abrir: http://127.0.0.1:5000
"""

from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path
import sqlite3

from flask import Flask, abort, redirect, render_template_string, request, url_for

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "inventario.db"


@contextmanager
def conectar():
    """Abre la BD, confirma cambios y cierra la conexión."""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def crear_base_datos():
    with conectar() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                precio_centimos INTEGER NOT NULL CHECK (precio_centimos >= 0),
                cantidad INTEGER NOT NULL CHECK (cantidad >= 0)
            )
        """)


@app.template_filter("moneda")
def moneda(centimos):
    return f"S/ {centimos // 100:,}.{centimos % 100:02d}"


HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Gestión de inventario</title>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; background: #f4f7fb; color: #243247;
           font-family: system-ui, -apple-system, Segoe UI, sans-serif; }
    header { background: #183153; color: white; padding: 18px 24px; }
    nav { max-width: 1000px; margin: auto; display: flex; gap: 22px;
          justify-content: space-between; align-items: center; flex-wrap: wrap; }
    nav a { color: white; text-decoration: none; font-weight: 600; margin-right: 15px; }
    main { max-width: 1000px; margin: 36px auto; padding: 0 20px; }
    h1 { font-size: 1.8rem; margin: 0 0 10px; }
    p { line-height: 1.6; }
    .card { background: white; border: 1px solid #e1e7f0; border-radius: 12px;
            padding: 24px; box-shadow: 0 3px 15px #1c305212; margin-bottom: 18px; }
    .acciones { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 20px; }
    .btn { display: inline-block; color: white; background: #2563eb; border: 0;
           border-radius: 7px; padding: 11px 17px; font: inherit; cursor: pointer;
           text-decoration: none; font-weight: 600; }
    .btn.secundario { background: #35506f; }
    .btn.eliminar { background: #b42318; padding: 8px 12px; }
    label { display: block; margin: 15px 0 6px; font-weight: 600; }
    input { width: 100%; border: 1px solid #bfcbda; padding: 11px;
            border-radius: 7px; font: inherit; }
    .formulario { max-width: 540px; }
    .alerta { padding: 12px 16px; border-radius: 7px; margin-bottom: 20px; }
    .error { background: #fef1f1; color: #912018; }
    .exito { background: #edf9ef; color: #176334; }
    .resumen { display: flex; flex-wrap: wrap; gap: 12px; margin: 18px 0; }
    .indicador { background: #edf3fc; border-radius: 9px; padding: 14px 18px; }
    .indicador strong { display: block; font-size: 1.3rem; }
    .tabla { overflow-x: auto; }
    table { border-collapse: collapse; width: 100%; text-align: left; }
    th, td { padding: 13px; border-bottom: 1px solid #e2e7ee; }
    th { background: #f1f5fb; }
    .pie { color: #5a697b; font-size: .9rem; margin-top: 20px; }
  </style>
</head>
<body>
  <header>
    <nav>
      <strong>Inventario de productos</strong>
      <div>
        <a href="{{ url_for('inicio') }}">Menú</a>
        <a href="{{ url_for('agregar') }}">Agregar producto</a>
        <a href="{{ url_for('inventario') }}">Consultar inventario</a>
      </div>
    </nav>
  </header>
  <main>
  {% if vista == 'inicio' %}
    <div class="card">
      <h1>Sistema de gestión de inventario</h1>
      <p>Registra productos, consulta sus existencias y elimina registros desde tu navegador.</p>
      <div class="acciones">
        <a class="btn" href="{{ url_for('agregar') }}">Registrar producto</a>
        <a class="btn secundario" href="{{ url_for('inventario') }}">Ver inventario</a>
      </div>
    </div>
  {% elif vista == 'agregar' %}
    <div class="card formulario">
      <h1>Registrar producto</h1>
      {% if error %}<div class="alerta error">{{ error }}</div>{% endif %}
      <form action="{{ url_for('agregar') }}" method="post">
        <label for="nombre">Nombre del producto</label>
        <input id="nombre" name="nombre" maxlength="120" required
               placeholder="Ej.: Guantes de nitrilo" value="{{ formulario.get('nombre', '') }}">
        <label for="precio">Precio unitario (soles)</label>
        <input id="precio" name="precio" type="number" min="0" step="0.01"
               required placeholder="Ej.: 12.50" value="{{ formulario.get('precio', '') }}">
        <label for="cantidad">Cantidad disponible</label>
        <input id="cantidad" name="cantidad" type="number" min="0" step="1"
               required placeholder="Ej.: 15" value="{{ formulario.get('cantidad', '') }}">
        <div class="acciones">
          <button class="btn" type="submit">Guardar producto</button>
          <a class="btn secundario" href="{{ url_for('inventario') }}">Ver inventario</a>
        </div>
      </form>
    </div>
  {% elif vista == 'inventario' %}
    <div class="card">
      <h1>Inventario</h1>
      {% if creado %}<div class="alerta exito">El producto se registró correctamente.</div>{% endif %}
      {% if eliminado %}<div class="alerta exito">El producto se eliminó correctamente.</div>{% endif %}
      <div class="resumen">
        <div class="indicador">Productos registrados<strong>{{ productos|length }}</strong></div>
        <div class="indicador">Unidades totales<strong>{{ unidades }}</strong></div>
        <div class="indicador">Valor del inventario<strong>{{ valor|moneda }}</strong></div>
      </div>
      <div class="acciones"><a class="btn" href="{{ url_for('agregar') }}">+ Agregar producto</a></div>
      <div class="tabla">
        <table>
          <thead><tr><th>ID</th><th>Producto</th><th>Precio unitario</th>
                     <th>Cantidad</th><th>Valor total</th><th>Acciones</th></tr></thead>
          <tbody>
          {% for producto in productos %}
            <tr>
              <td>{{ producto['id'] }}</td>
              <td>{{ producto['nombre'] }}</td>
              <td>{{ producto['precio_centimos']|moneda }}</td>
              <td>{{ producto['cantidad'] }}</td>
              <td>{{ (producto['precio_centimos'] * producto['cantidad'])|moneda }}</td>
              <td>
                <form action="{{ url_for('eliminar', producto_id=producto['id']) }}"
                      method="post" onsubmit="return confirm('¿Eliminar este producto?');">
                  <button class="btn eliminar" type="submit">Eliminar</button>
                </form>
              </td>
            </tr>
          {% else %}
            <tr><td colspan="6">Todavía no hay productos registrados.</td></tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      <p class="pie">El valor del inventario es precio unitario × cantidad para cada producto.</p>
    </div>
  {% endif %}
  </main>
</body>
</html>
"""


@app.get("/")
def inicio():
    return render_template_string(HTML, vista="inicio")


@app.route("/agregar", methods=["GET", "POST"])
def agregar():
    if request.method == "GET":
        return render_template_string(HTML, vista="agregar", error=None, formulario={})

    nombre = request.form.get("nombre", "").strip()
    precio_texto = request.form.get("precio", "").strip().replace(",", ".")
    cantidad_texto = request.form.get("cantidad", "").strip()
    error = None

    if not nombre or len(nombre) > 120:
        error = "El nombre debe contener entre 1 y 120 caracteres."
    else:
        try:
            precio = Decimal(precio_texto)
            if (not precio.is_finite() or precio < 0 or precio > 100000000
                    or precio * 100 != (precio * 100).to_integral_value()):
                raise ValueError("Precio fuera de rango o con más de dos decimales")
            if not cantidad_texto.isascii() or not cantidad_texto.isdecimal():
                raise ValueError("Cantidad no entera")
            cantidad = int(cantidad_texto)
            if cantidad > 1000000000:
                raise ValueError("Cantidad fuera de rango")
            precio_centimos = int(precio * 100)
        except (InvalidOperation, ValueError):
            error = "Introduce un precio válido (máximo 2 decimales) y una cantidad entera no negativa."

    if error:
        return render_template_string(HTML, vista="agregar", error=error,
                                      formulario=request.form), 400

    with conectar() as db:
        db.execute(
            "INSERT INTO productos (nombre, precio_centimos, cantidad) VALUES (?, ?, ?)",
            (nombre, precio_centimos, cantidad),
        )
    return redirect(url_for("inventario", creado=1))


@app.get("/inventario")
def inventario():
    with conectar() as db:
        productos = db.execute("SELECT * FROM productos ORDER BY id DESC").fetchall()
    unidades = sum(p["cantidad"] for p in productos)
    valor = sum(p["precio_centimos"] * p["cantidad"] for p in productos)
    return render_template_string(HTML, vista="inventario", productos=productos,
                                  unidades=unidades, valor=valor,
                                  creado=request.args.get("creado") == "1",
                                  eliminado=request.args.get("eliminado") == "1")


@app.post("/eliminar/<int:producto_id>")
def eliminar(producto_id):
    with conectar() as db:
        resultado = db.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
        if resultado.rowcount == 0:
            abort(404, description="No existe ese producto")
    return redirect(url_for("inventario", eliminado=1))


crear_base_datos()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
