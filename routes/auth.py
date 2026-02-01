"""
Rutas de Autenticación
======================
Login, logout y manejo de sesiones.
"""
from flask import Blueprint, render_template, request, redirect, session
from werkzeug.security import check_password_hash
from datetime import datetime

from models.database import get_db
from utils.helpers import obtener_turno_activo, crear_turno

# Crear el Blueprint
auth_bp = Blueprint('auth', __name__)


@auth_bp.route("/", methods=["GET", "POST"])
def login():
    """Página de login"""
    error = None

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")

        if not usuario or not password:
            error = "Usuario y contraseña son requeridos"
            return render_template("login.html", error=error)

        try:
            db = get_db()
            cursor = db.cursor()
            cursor.execute(
                "SELECT id, nombre, password, rol FROM trabajadores WHERE usuario=? AND activo=1",
                (usuario,)
            )
            trabajador = cursor.fetchone()

            if trabajador and check_password_hash(trabajador["password"], password):
                # Login exitoso
                session.permanent = True
                session["trabajador_id"] = trabajador["id"]
                session["nombre"] = trabajador["nombre"]
                session["es_admin"] = trabajador["rol"] == "admin"
                session["rol"] = trabajador["rol"]
                
                # Obtener o crear turno
                turno = obtener_turno_activo(trabajador["id"])
                
                if turno:
                    session["turno_id"] = turno["id"]
                    session["inicio_turno"] = turno["fecha_inicio"]
                else:
                    turno_id = crear_turno(trabajador["id"])
                    session["turno_id"] = turno_id
                    session["inicio_turno"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Redirigir según rol
                if trabajador["rol"] == "admin":
                    return redirect("/admin")
                else:
                    return redirect("/dashboard")
            else:
                error = "Usuario o contraseña incorrectos"

        except Exception as e:
            print(f"Error en login: {e}")
            error = "Error en el servidor"

    return render_template("login.html", error=error)


@auth_bp.route("/logout")
def logout():
    """Cerrar sesión"""
    session.clear()
    return redirect("/")
