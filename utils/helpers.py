"""
Utilidades y Funciones Auxiliares
=================================
Funciones comunes usadas en toda la aplicación.
"""
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, jsonify
from models.database import get_db


# ============================================
# DECORADORES DE AUTENTICACIÓN
# ============================================

def login_required(f):
    """Requiere que el usuario esté autenticado.
    Si el turno fue cerrado (desde otro dispositivo), fuerza logout."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "trabajador_id" not in session:
            return redirect("/")

        # Para trabajadores (no admin), verificar que su turno siga abierto
        turno_id = session.get("turno_id")
        if turno_id and not session.get("es_admin"):
            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT estado FROM turnos WHERE id = ?", (turno_id,))
            turno = cursor.fetchone()
            if not turno or turno["estado"] != "abierto":
                session.clear()
                return redirect("/")

        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Requiere que el usuario sea administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "trabajador_id" not in session:
            return redirect("/")
        if not session.get("es_admin"):
            return jsonify({
                "ok": False, 
                "error": "Acceso denegado. Se requiere rol de administrador."
            }), 403
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# FUNCIONES DE TURNO
# ============================================

def obtener_turno_activo(trabajador_id):
    """Obtiene el turno activo de un trabajador"""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        SELECT * FROM turnos 
        WHERE trabajador_id = ? AND estado = 'abierto'
        ORDER BY fecha_inicio DESC LIMIT 1
    """, (trabajador_id,))
    
    turno = cursor.fetchone()
    return dict(turno) if turno else None


def crear_turno(trabajador_id, tipo_turno=""):
    """Crea un nuevo turno para un trabajador"""
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO turnos (trabajador_id, fecha_inicio, estado, tipo_turno)
        VALUES (?, datetime('now', 'localtime'), 'abierto', ?)
    """, (trabajador_id, tipo_turno))

    turno_id = cursor.lastrowid
    db.commit()

    return turno_id


def obtener_turno_trabajador_activo():
    """Busca el turno abierto del trabajador (no admin) activo.
    Retorna dict con turno_id y trabajador_id, o None si no hay."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT t.id as turno_id, t.trabajador_id
        FROM turnos t
        JOIN trabajadores tr ON t.trabajador_id = tr.id
        WHERE t.estado = 'abierto' AND tr.rol != 'admin'
        ORDER BY t.fecha_inicio DESC LIMIT 1
    """)
    row = cursor.fetchone()
    return dict(row) if row else None


# ============================================
# FUNCIONES DE CONFIGURACIÓN
# ============================================

def obtener_configuracion(clave, default=None):
    """Obtiene un valor de configuración de la base de datos"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave,))
    result = cursor.fetchone()
    return result['valor'] if result else default


# ============================================
# FUNCIONES DE CÁLCULO
# ============================================

def calcular_penalidad(fecha_entrada, hora_entrada, fecha_salida_esperada, 
                       hora_salida_esperada, precio_dia):
    """
    Calcula la penalidad por exceso de tiempo.
    
    Args:
        fecha_entrada: Fecha de entrada del vehículo
        hora_entrada: Hora de entrada
        fecha_salida_esperada: Fecha esperada de salida
        hora_salida_esperada: Hora esperada de salida
        precio_dia: Precio por día
    
    Returns:
        float: Monto de penalidad (0 si está dentro del tiempo)
    """
    try:
        tolerancia = int(obtener_configuracion('tolerancia_minutos', 60))
        
        salida_esperada = datetime.strptime(
            f"{fecha_salida_esperada} {hora_salida_esperada}", 
            "%Y-%m-%d %H:%M"
        )
        ahora = datetime.now()
        salida_con_tolerancia = salida_esperada + timedelta(minutes=tolerancia)
        
        if ahora <= salida_con_tolerancia:
            return 0
        
        diferencia = ahora - salida_con_tolerancia
        horas_exceso = diferencia.total_seconds() / 3600
        precio_hora = float(precio_dia) / 24
        penalidad = round(horas_exceso * precio_hora, 2)
        
        return penalidad
        
    except Exception as e:
        print(f"Error calculando penalidad: {e}")
        return 0


# ============================================
# FUNCIONES DE FORMATO
# ============================================

def formato_moneda(valor):
    """Formatea un valor como moneda"""
    return f"S/ {valor:.2f}"


def formato_fecha(fecha_str):
    """Formatea una fecha para mostrar"""
    if not fecha_str:
        return ""
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
        return fecha.strftime("%d/%m/%Y")
    except:
        return fecha_str


def formato_hora(hora_str):
    """Formatea una hora para mostrar"""
    if not hora_str:
        return ""
    return hora_str[:5] if len(hora_str) >= 5 else hora_str
