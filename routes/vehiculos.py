"""
Rutas de Vehículos
==================
Gestión de entradas, salidas y cobros de vehículos.
"""
from flask import Blueprint, jsonify, request, session, render_template
from datetime import datetime

from models.database import get_db
from utils.helpers import login_required, calcular_penalidad, obtener_configuracion

# Crear el Blueprint
vehiculos_bp = Blueprint('vehiculos', __name__)


# ============================================
# CLIENTES
# ============================================

@vehiculos_bp.route("/buscar_cliente/<placa>")
@login_required
def buscar_cliente(placa):
    """Busca un cliente por placa"""
    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            SELECT nombre, celular, precio_dia
            FROM clientes
            WHERE placa = ?
        """, (placa.upper().strip(),))

        cliente = cursor.fetchone()

        if cliente:
            return jsonify({
                "existe": True,
                "nombre": cliente["nombre"],
                "celular": cliente["celular"],
                "precio_dia": cliente["precio_dia"]
            })
        else:
            return jsonify({"existe": False})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@vehiculos_bp.route("/historial_cliente/<placa>")
@login_required
def historial_cliente(placa):
    """Obtiene el historial de un cliente"""
    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM clientes WHERE placa = ?", (placa.upper(),))
        cliente = cursor.fetchone()

        if not cliente:
            return jsonify({"ok": False, "error": "Cliente no encontrado"})

        cursor.execute("""
            SELECT 
                e.*,
                t1.nombre as trabajador_entrada,
                t2.nombre as trabajador_salida
            FROM entradas e
            LEFT JOIN trabajadores t1 ON e.trabajador_id = t1.id
            LEFT JOIN trabajadores t2 ON e.trabajador_salida_id = t2.id
            WHERE e.cliente_id = ?
            ORDER BY e.fecha_registro DESC
        """, (cliente["id"],))

        visitas = cursor.fetchall()

        cursor.execute("""
            SELECT 
                COUNT(*) as total_visitas,
                SUM(monto) as total_gastado,
                SUM(CASE WHEN pagado = 0 THEN monto - IFNULL(adelanto, 0) ELSE 0 END) as deuda_actual,
                AVG(dias) as promedio_dias
            FROM entradas
            WHERE cliente_id = ?
        """, (cliente["id"],))

        estadisticas = cursor.fetchone()

        return jsonify({
            "ok": True,
            "cliente": dict(cliente),
            "estadisticas": dict(estadisticas),
            "visitas": [dict(v) for v in visitas]
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ============================================
# ENTRADAS
# ============================================

@vehiculos_bp.route("/guardar_entrada", methods=["POST"])
@login_required
def guardar_entrada():
    """Registra una nueva entrada de vehículo"""
    data = request.json

    # Validaciones
    if not data.get("placa"):
        return jsonify({"ok": False, "error": "Placa es requerida"})

    if not data.get("cliente"):
        return jsonify({"ok": False, "error": "Nombre del cliente es requerido"})

    try:
        precio = float(data.get("precio", 0))
        if precio <= 0:
            return jsonify({"ok": False, "error": "El precio por día es obligatorio y debe ser mayor a 0"})
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "Precio inválido"})

    try:
        dias = int(data.get("dias", 1))
        if dias < 1:
            return jsonify({"ok": False, "error": "Días debe ser al menos 1"})
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "Días inválido"})

    try:
        db = get_db()
        cursor = db.cursor()

        placa = data["placa"].upper().strip()

        # Verificar que no exista una entrada activa para esta placa
        cursor.execute("""
            SELECT e.id FROM entradas e
            JOIN clientes c ON e.cliente_id = c.id
            WHERE c.placa = ? AND e.salio = 0
        """, (placa,))
        if cursor.fetchone():
            return jsonify({"ok": False, "error": "Este vehiculo ya se encuentra en la cochera"})

        # Buscar o crear cliente
        cursor.execute("SELECT id FROM clientes WHERE placa = ?", (placa,))
        cliente_db = cursor.fetchone()

        if cliente_db:
            cliente_id = cliente_db["id"]
            cursor.execute("""
                UPDATE clientes
                SET nombre=?, celular=?, precio_dia=?, fecha_actualizacion=datetime('now', 'localtime')
                WHERE id=?
            """, (data["cliente"], data.get("celular", ""), precio, cliente_id))
        else:
            cursor.execute("""
                INSERT INTO clientes (placa, nombre, celular, precio_dia, fecha_actualizacion)
                VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
            """, (placa, data["cliente"], data.get("celular", ""), precio))
            cliente_id = cursor.lastrowid

        # Calcular montos
        monto = precio * dias
        adelanto = float(data.get("adelanto", 0))
        metodo_pago = data.get("metodo_pago", "efectivo")
        
        pago_completo = 1 if data.get("pagado") and adelanto >= monto else 0
        
        if data.get("pagado") and adelanto == 0:
            adelanto = monto
            pago_completo = 1

        # Insertar entrada
        cursor.execute("""
            INSERT INTO entradas (
                cliente_id, fecha_entrada, hora_entrada,
                fecha_hasta, hora_salida_esperada, dias, precio_dia, monto, 
                adelanto, metodo_pago, dejo_llave, pagado, pago_completo_adelantado,
                salio, observaciones, trabajador_id, fecha_registro
            )
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now', 'localtime'))
        """, (
            cliente_id,
            data.get("fecha_entrada"),
            data.get("hora_entrada"),
            data.get("fecha_hasta"),
            data.get("hora_salida"),
            dias,
            precio,
            monto,
            adelanto,
            metodo_pago,
            1 if data.get("dejo_llave") else 0,
            1 if pago_completo else 0,
            pago_completo,
            0,
            data.get("observaciones", ""),
            session["trabajador_id"]
        ))
        
        entrada_id = cursor.lastrowid

        # Registrar movimiento de caja si hay adelanto
        if adelanto > 0:
            tipo_mov = "PAGO_COMPLETO" if pago_completo else "ADELANTO"
            cursor.execute("""
                INSERT INTO movimientos_caja (
                    turno_id, entrada_id, trabajador_id, tipo, monto, metodo_pago, descripcion
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session["turno_id"],
                entrada_id,
                session["trabajador_id"],
                tipo_mov,
                adelanto,
                metodo_pago,
                f"{tipo_mov} - {placa} - {data['cliente']} - {dias} día(s)"
            ))

        db.commit()
        
        return jsonify({
            "ok": True, 
            "mensaje": "Entrada guardada exitosamente", 
            "id": entrada_id,
            "pago_completo": pago_completo == 1
        })

    except Exception as e:
        print(f"Error al guardar entrada: {e}")
        return jsonify({"ok": False, "error": str(e)})


@vehiculos_bp.route("/ingreso/<int:id>")
@login_required
def obtener_ingreso(id):
    """Obtiene los detalles de una entrada"""
    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            SELECT 
                e.*,
                c.placa,
                c.nombre as cliente,
                c.celular,
                t1.nombre as trabajador_entrada,
                t2.nombre as trabajador_salida
            FROM entradas e
            JOIN clientes c ON e.cliente_id = c.id
            LEFT JOIN trabajadores t1 ON e.trabajador_id = t1.id
            LEFT JOIN trabajadores t2 ON e.trabajador_salida_id = t2.id
            WHERE e.id = ?
        """, (id,))

        ingreso = cursor.fetchone()

        if ingreso:
            return jsonify(dict(ingreso))
        else:
            return jsonify({"error": "Ingreso no encontrado"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@vehiculos_bp.route("/actualizar_ingreso", methods=["POST"])
@login_required
def actualizar_ingreso():
    """Actualiza una entrada existente"""
    data = request.json

    if not data.get("id"):
        return jsonify({"ok": False, "error": "ID requerido"})

    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            UPDATE entradas
            SET fecha_entrada = ?, hora_entrada = ?, fecha_hasta = ?, 
                hora_salida_esperada = ?, precio_dia = ?, dias = ?, monto = ?,
                dejo_llave = ?, observaciones = ?
            WHERE id = ?
        """, (
            data.get("fecha_entrada"),
            data.get("hora_entrada"),
            data.get("fecha_hasta"),
            data.get("hora_salida"),
            float(data.get("precio", 0)),
            int(data.get("dias", 1)),
            float(data.get("monto", 0)),
            1 if data.get("dejo_llave") else 0,
            data.get("observaciones", ""),
            data["id"]
        ))

        if data.get("placa"):
            cursor.execute("""
                UPDATE clientes
                SET nombre = ?, celular = ?, precio_dia = ?
                WHERE placa = ?
            """, (
                data.get("cliente", ""),
                data.get("celular", ""),
                float(data.get("precio", 0)),
                data["placa"].upper().strip()
            ))

        db.commit()
        return jsonify({"ok": True, "mensaje": "Ingreso actualizado"})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ============================================
# AUTOS EN COCHERA
# ============================================

@vehiculos_bp.route("/autos_en_cochera")
@login_required
def autos_en_cochera():
    """Lista los autos actualmente en la cochera"""
    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            SELECT 
                e.id,
                c.placa,
                c.nombre as cliente,
                c.celular,
                e.fecha_entrada,
                e.hora_entrada,
                e.fecha_hasta,
                e.hora_salida_esperada,
                e.dias as dias_pactados,
                e.precio_dia,
                e.monto,
                e.adelanto,
                e.metodo_pago,
                e.dejo_llave,
                e.pagado,
                e.pago_completo_adelantado,
                e.observaciones,
                t.nombre as trabajador_entrada,
                CAST((julianday('now') - julianday(e.fecha_entrada)) AS INTEGER) + 1 as dias_reales
            FROM entradas e
            JOIN clientes c ON e.cliente_id = c.id
            LEFT JOIN trabajadores t ON e.trabajador_id = t.id
            WHERE e.salio = 0
            ORDER BY e.fecha_entrada DESC
        """)

        autos = cursor.fetchall()

        autos_list = []
        for auto in autos:
            dias_reales = auto["dias_reales"]
            dias_pactados = auto["dias_pactados"]
            excede_tiempo = dias_reales > dias_pactados
            
            penalidad = 0
            if auto["fecha_hasta"] and auto["hora_salida_esperada"]:
                penalidad = calcular_penalidad(
                    auto["fecha_entrada"],
                    auto["hora_entrada"],
                    auto["fecha_hasta"],
                    auto["hora_salida_esperada"],
                    auto["precio_dia"]
                )
            
            monto_total = dias_reales * float(auto["precio_dia"]) + penalidad
            adelanto = float(auto["adelanto"] or 0)
            pendiente = max(0, monto_total - adelanto)

            autos_list.append({
                "id": auto["id"],
                "placa": auto["placa"],
                "cliente": auto["cliente"],
                "celular": auto["celular"],
                "fecha_entrada": auto["fecha_entrada"],
                "hora_entrada": auto["hora_entrada"],
                "fecha_hasta": auto["fecha_hasta"],
                "hora_salida_esperada": auto["hora_salida_esperada"],
                "dias_pactados": dias_pactados,
                "dias_reales": dias_reales,
                "precio_dia": auto["precio_dia"],
                "monto": auto["monto"],
                "adelanto": adelanto,
                "penalidad": penalidad,
                "pendiente": pendiente,
                "metodo_pago": auto["metodo_pago"],
                "dejo_llave": auto["dejo_llave"],
                "pagado": auto["pagado"],
                "pago_completo_adelantado": auto["pago_completo_adelantado"],
                "observaciones": auto["observaciones"],
                "trabajador_entrada": auto["trabajador_entrada"],
                "excede_tiempo": excede_tiempo
            })

        return jsonify({
            "ok": True,
            "autos": autos_list,
            "total": len(autos_list)
        })

    except Exception as e:
        print(f"Error en autos_en_cochera: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================
# COBROS Y SALIDAS
# ============================================

@vehiculos_bp.route("/calcular_cobro/<int:id>")
@login_required
def calcular_cobro(id):
    """Calcula el cobro para un vehículo"""
    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            SELECT 
                e.*,
                c.placa,
                c.nombre as cliente,
                c.celular,
                t.nombre as trabajador_entrada,
                CAST((julianday('now') - julianday(e.fecha_entrada)) AS INTEGER) + 1 as dias_reales
            FROM entradas e
            JOIN clientes c ON e.cliente_id = c.id
            LEFT JOIN trabajadores t ON e.trabajador_id = t.id
            WHERE e.id = ?
        """, (id,))

        auto = cursor.fetchone()

        if not auto:
            return jsonify({"ok": False, "error": "Entrada no encontrada"})

        if auto["salio"]:
            return jsonify({"ok": False, "error": "Este auto ya salió"})

        dias_reales = auto["dias_reales"]
        precio_dia = float(auto["precio_dia"])
        adelanto = float(auto["adelanto"] or 0)
        
        penalidad = 0
        if auto["fecha_hasta"] and auto["hora_salida_esperada"]:
            penalidad = calcular_penalidad(
                auto["fecha_entrada"],
                auto["hora_entrada"],
                auto["fecha_hasta"],
                auto["hora_salida_esperada"],
                precio_dia
            )
        
        monto_dias = dias_reales * precio_dia
        monto_total = monto_dias + penalidad
        a_cobrar = max(0, monto_total - adelanto)
        
        ya_pago_completo = auto["pago_completo_adelantado"] == 1

        return jsonify({
            "ok": True,
            "id": auto["id"],
            "placa": auto["placa"],
            "cliente": auto["cliente"],
            "celular": auto["celular"],
            "trabajador_entrada": auto["trabajador_entrada"],
            "fecha_entrada": auto["fecha_entrada"],
            "hora_entrada": auto["hora_entrada"],
            "fecha_hasta": auto["fecha_hasta"],
            "hora_salida_esperada": auto["hora_salida_esperada"],
            "dias_pactados": auto["dias"],
            "dias_reales": dias_reales,
            "precio_dia": precio_dia,
            "monto_dias": monto_dias,
            "penalidad": penalidad,
            "monto_total": monto_total,
            "adelanto": adelanto,
            "a_cobrar": a_cobrar,
            "dejo_llave": auto["dejo_llave"],
            "ya_pago_completo": ya_pago_completo,
            "observaciones": auto["observaciones"]
        })

    except Exception as e:
        print(f"Error al calcular cobro: {e}")
        return jsonify({"ok": False, "error": str(e)})


@vehiculos_bp.route("/registrar_salida", methods=["POST"])
@login_required
def registrar_salida():
    """Registra la salida de un vehículo"""
    data = request.json

    if not data.get("id"):
        return jsonify({"ok": False, "error": "ID de entrada requerido"})

    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            SELECT 
                e.*,
                c.placa,
                c.nombre as cliente_nombre,
                CAST((julianday('now') - julianday(e.fecha_entrada)) AS INTEGER) + 1 as dias_reales
            FROM entradas e
            JOIN clientes c ON e.cliente_id = c.id
            WHERE e.id = ?
        """, (data["id"],))

        entrada = cursor.fetchone()

        if not entrada:
            return jsonify({"ok": False, "error": "Entrada no encontrada"})

        if entrada["salio"] == 1:
            return jsonify({"ok": False, "error": "Este auto ya salió"})

        dias_reales = data.get("dias_reales", entrada["dias_reales"])
        precio_dia = float(entrada["precio_dia"])
        adelanto = float(entrada["adelanto"] or 0)
        penalidad = float(data.get("penalidad", 0))
        descuento = float(data.get("descuento", 0))
        metodo_pago = data.get("metodo_pago", "efectivo")
        
        monto_dias = dias_reales * precio_dia
        monto_total = monto_dias + penalidad - descuento
        monto_a_cobrar = max(0, monto_total - adelanto)

        if entrada["pago_completo_adelantado"] == 1:
            monto_a_cobrar = max(0, penalidad - descuento)

        cursor.execute("""
            UPDATE entradas
            SET salio = 1,
                fecha_salida = date('now'),
                hora_salida_real = time('now'),
                dias = ?,
                monto = ?,
                penalidad = ?,
                descuento = ?,
                pagado = 1,
                observaciones = ?,
                trabajador_salida_id = ?
            WHERE id = ?
        """, (
            dias_reales,
            monto_total,
            penalidad,
            descuento,
            data.get("observaciones", entrada["observaciones"]),
            session["trabajador_id"],
            data["id"]
        ))

        if monto_a_cobrar > 0:
            descripcion = f"Cobro salida - {entrada['placa']} - {entrada['cliente_nombre']} - {dias_reales} día(s)"
            if penalidad > 0:
                descripcion += f" (+ penalidad S/ {penalidad:.2f})"
            if descuento > 0:
                descripcion += f" (- descuento S/ {descuento:.2f})"
                
            cursor.execute("""
                INSERT INTO movimientos_caja (
                    turno_id, entrada_id, trabajador_id, tipo, monto, metodo_pago, descripcion
                )
                VALUES (?, ?, ?, 'COBRO_SALIDA', ?, ?, ?)
            """, (
                session["turno_id"],
                data["id"],
                session["trabajador_id"],
                monto_a_cobrar,
                metodo_pago,
                descripcion
            ))

        db.commit()

        return jsonify({
            "ok": True,
            "mensaje": "Salida registrada exitosamente",
            "monto_total": monto_total,
            "adelanto": adelanto,
            "penalidad": penalidad,
            "descuento": descuento,
            "monto_cobrado": monto_a_cobrar,
            "dias_reales": dias_reales,
            "ya_pago_completo": entrada["pago_completo_adelantado"] == 1
        })

    except Exception as e:
        print(f"Error al registrar salida: {e}")
        return jsonify({"ok": False, "error": str(e)})


@vehiculos_bp.route("/autorizar_salida", methods=["POST"])
@login_required
def autorizar_salida():
    """Autoriza la salida de un vehículo con pago completo adelantado"""
    data = request.json

    if not data.get("id"):
        return jsonify({"ok": False, "error": "ID de entrada requerido"})

    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            SELECT e.*, c.placa, c.nombre as cliente_nombre
            FROM entradas e
            JOIN clientes c ON e.cliente_id = c.id
            WHERE e.id = ? AND e.pago_completo_adelantado = 1 AND e.salio = 0
        """, (data["id"],))

        entrada = cursor.fetchone()

        if not entrada:
            return jsonify({"ok": False, "error": "Entrada no encontrada o no válida para autorización"})

        penalidad = float(data.get("penalidad", 0))
        descuento = float(data.get("descuento", 0))
        monto_extra = max(0, penalidad - descuento)
        metodo_pago = data.get("metodo_pago", "efectivo")

        cursor.execute("""
            UPDATE entradas
            SET salio = 1,
                fecha_salida = date('now'),
                hora_salida_real = time('now'),
                penalidad = ?,
                descuento = ?,
                observaciones = ?,
                trabajador_salida_id = ?
            WHERE id = ?
        """, (
            penalidad,
            descuento,
            data.get("observaciones", entrada["observaciones"]),
            session["trabajador_id"],
            data["id"]
        ))

        if monto_extra > 0:
            cursor.execute("""
                INSERT INTO movimientos_caja (
                    turno_id, entrada_id, trabajador_id, tipo, monto, metodo_pago, descripcion
                )
                VALUES (?, ?, ?, 'PENALIDAD', ?, ?, ?)
            """, (
                session["turno_id"],
                data["id"],
                session["trabajador_id"],
                monto_extra,
                metodo_pago,
                f"Penalidad - {entrada['placa']} - {entrada['cliente_nombre']}"
            ))

        db.commit()

        return jsonify({
            "ok": True,
            "mensaje": "Salida autorizada exitosamente",
            "penalidad_cobrada": monto_extra
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ============================================
# CAPACIDAD Y ALERTAS
# ============================================

@vehiculos_bp.route("/verificar_capacidad")
@login_required
def verificar_capacidad():
    """Verifica la capacidad de la cochera"""
    capacidad = int(obtener_configuracion('capacidad_maxima', 50))

    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute("SELECT COUNT(*) FROM entradas WHERE salio = 0")
        ocupados = cursor.fetchone()[0]

        disponibles = capacidad - ocupados
        porcentaje = (ocupados / capacidad) * 100 if capacidad > 0 else 0

        return jsonify({
            "ok": True,
            "ocupados": ocupados,
            "disponibles": disponibles,
            "capacidad": capacidad,
            "porcentaje": round(porcentaje, 1)
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@vehiculos_bp.route("/obtener_alertas")
@login_required
def obtener_alertas():
    """Obtiene las alertas del sistema"""
    try:
        db = get_db()
        cursor = db.cursor()

        alertas = []

        # Alertas de vehículos que exceden tiempo
        cursor.execute("""
            SELECT 
                c.placa,
                c.nombre as cliente,
                e.dias as dias_pactados,
                CAST((julianday('now') - julianday(e.fecha_entrada)) AS INTEGER) + 1 as dias_reales
            FROM entradas e
            JOIN clientes c ON e.cliente_id = c.id
            WHERE e.salio = 0
            AND CAST((julianday('now') - julianday(e.fecha_entrada)) AS INTEGER) + 1 > e.dias
        """)

        for auto in cursor.fetchall():
            exceso = auto["dias_reales"] - auto["dias_pactados"]
            alertas.append({
                "tipo": "exceso_tiempo",
                "nivel": "warning",
                "titulo": f"⚠️ {auto['placa']} excede tiempo",
                "mensaje": f"{auto['cliente']} - Exceso: {exceso} día(s)",
                "placa": auto["placa"]
            })

        # Alertas de capacidad
        capacidad = int(obtener_configuracion('capacidad_maxima', 50))
        cursor.execute("SELECT COUNT(*) FROM entradas WHERE salio = 0")
        ocupados = cursor.fetchone()[0]
        porcentaje = (ocupados / capacidad) * 100 if capacidad > 0 else 0

        if porcentaje >= 90:
            alertas.append({
                "tipo": "capacidad",
                "nivel": "danger",
                "titulo": "🚨 Cochera casi llena",
                "mensaje": f"Ocupación: {porcentaje:.0f}% ({ocupados}/{capacidad})",
                "placa": None
            })
        elif porcentaje >= 75:
            alertas.append({
                "tipo": "capacidad",
                "nivel": "warning",
                "titulo": "⚠️ Cochera llegando al límite",
                "mensaje": f"Ocupación: {porcentaje:.0f}% ({ocupados}/{capacidad})",
                "placa": None
            })

        return jsonify({
            "ok": True,
            "alertas": alertas,
            "total": len(alertas)
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@vehiculos_bp.route("/generar_ticket/<int:id>")
@login_required
def generar_ticket(id):
    """Genera el ticket de una entrada"""
    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            SELECT 
                e.*,
                c.placa,
                c.nombre as cliente,
                c.celular,
                t.nombre as trabajador
            FROM entradas e
            JOIN clientes c ON e.cliente_id = c.id
            LEFT JOIN trabajadores t ON e.trabajador_id = t.id
            WHERE e.id = ?
        """, (id,))

        entrada = cursor.fetchone()

        if not entrada:
            return jsonify({"ok": False, "error": "Entrada no encontrada"})

        return jsonify({
            "ok": True,
            "ticket": {
                "id": entrada["id"],
                "placa": entrada["placa"],
                "cliente": entrada["cliente"],
                "fecha_entrada": entrada["fecha_entrada"],
                "hora_entrada": entrada["hora_entrada"],
                "fecha_hasta": entrada["fecha_hasta"],
                "hora_salida_esperada": entrada["hora_salida_esperada"],
                "dias": entrada["dias"],
                "precio_dia": entrada["precio_dia"],
                "monto": entrada["monto"],
                "adelanto": entrada["adelanto"],
                "trabajador": entrada["trabajador"],
                "fecha_emision": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@vehiculos_bp.route("/ticket_entrada/<int:id>")
@login_required
def ticket_entrada(id):
    """Muestra ticket de entrada para imprimir"""
    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            SELECT
                e.*,
                c.placa,
                c.nombre as cliente,
                t.nombre as trabajador
            FROM entradas e
            JOIN clientes c ON e.cliente_id = c.id
            LEFT JOIN trabajadores t ON e.trabajador_id = t.id
            WHERE e.id = ?
        """, (id,))

        entrada = cursor.fetchone()
        if not entrada:
            return "Entrada no encontrada", 404

        ticket = {
            "id": entrada["id"],
            "placa": entrada["placa"],
            "cliente": entrada["cliente"],
            "fecha_entrada": entrada["fecha_entrada"],
            "hora_entrada": entrada["hora_entrada"],
            "dias": entrada["dias"],
            "precio_dia": entrada["precio_dia"],
            "monto": entrada["monto"],
            "adelanto": entrada["adelanto"] or 0,
            "trabajador": entrada["trabajador"] or "",
            "fecha_emision": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return render_template("ticket_entrada.html", ticket=ticket)

    except Exception as e:
        return f"Error: {e}", 500
