"""
Rutas del Dashboard (Trabajador)
================================
Dashboard principal y funciones del trabajador.
"""
from flask import Blueprint, render_template, session, jsonify, request
from datetime import datetime

from models.database import get_db
from utils.helpers import login_required

# Crear el Blueprint
dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    """Dashboard principal del trabajador"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        turno_id = session.get("turno_id")

        # Total efectivo del turno
        cursor.execute("""
            SELECT IFNULL(SUM(monto), 0)
            FROM movimientos_caja
            WHERE turno_id = ? AND metodo_pago = 'efectivo'
        """, (turno_id,))
        total_efectivo = cursor.fetchone()[0]
        
        # Total yape del turno
        cursor.execute("""
            SELECT IFNULL(SUM(monto), 0)
            FROM movimientos_caja
            WHERE turno_id = ? AND metodo_pago = 'yape'
        """, (turno_id,))
        total_yape = cursor.fetchone()[0]
        
        total_turno = total_efectivo + total_yape

        # Autos ingresados en el turno
        cursor.execute("""
            SELECT COUNT(*)
            FROM entradas
            WHERE trabajador_id = ?
            AND fecha_registro >= ?
        """, (session["trabajador_id"], session["inicio_turno"]))
        autos_ingresados = cursor.fetchone()[0]
        
        # Autos que salieron en el turno
        cursor.execute("""
            SELECT COUNT(*)
            FROM movimientos_caja
            WHERE turno_id = ? AND tipo = 'COBRO_SALIDA'
        """, (turno_id,))
        autos_salieron = cursor.fetchone()[0]

        # Total de autos en cochera
        cursor.execute("SELECT COUNT(*) FROM entradas WHERE salio = 0")
        autos_en_cochera = cursor.fetchone()[0]

        return render_template(
            "dashboard.html",
            nombre=session["nombre"],
            total_turno=total_turno,
            total_efectivo=total_efectivo,
            total_yape=total_yape,
            autos_ingresados=autos_ingresados,
            autos_salieron=autos_salieron,
            autos_en_cochera=autos_en_cochera,
            inicio_turno=session["inicio_turno"],
            tipo_turno=session.get("tipo_turno", ""),
            es_admin=session.get("es_admin", False)
        )

    except Exception as e:
        print(f"Error en dashboard: {e}")
        return "Error al cargar dashboard", 500


@dashboard_bp.route("/ingresos_turno")
@login_required
def ingresos_turno():
    """Obtiene los ingresos del turno actual"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        turno_id = session.get("turno_id")

        cursor.execute("""
            SELECT 
                m.id,
                m.tipo,
                m.monto,
                m.metodo_pago,
                m.descripcion,
                m.fecha_movimiento,
                m.entrada_id,
                c.placa,
                c.nombre AS cliente
            FROM movimientos_caja m
            LEFT JOIN entradas e ON m.entrada_id = e.id
            LEFT JOIN clientes c ON e.cliente_id = c.id
            WHERE m.turno_id = ?
            ORDER BY m.fecha_movimiento DESC
        """, (turno_id,))

        rows = cursor.fetchall()

        ingresos = []
        total_efectivo = 0
        total_yape = 0

        for r in rows:
            monto = float(r["monto"] or 0)
            
            if r["metodo_pago"] == "efectivo":
                total_efectivo += monto
            else:
                total_yape += monto

            ingresos.append({
                "id": r["id"],
                "entrada_id": r["entrada_id"],
                "tipo": r["tipo"],
                "hora": r["fecha_movimiento"].split(" ")[1][:5] if r["fecha_movimiento"] else "",
                "fecha": r["fecha_movimiento"].split(" ")[0] if r["fecha_movimiento"] else "",
                "placa": r["placa"] or "-",
                "cliente": r["cliente"] or "-",
                "monto": monto,
                "metodo_pago": r["metodo_pago"],
                "descripcion": r["descripcion"]
            })

        # KPIs: autos ingresados y salidos en este turno
        cursor.execute("""
            SELECT COUNT(*) FROM entradas
            WHERE trabajador_id = ? AND fecha_registro >= ?
        """, (session["trabajador_id"], session["inicio_turno"]))
        autos_ingresados = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM movimientos_caja
            WHERE turno_id = ? AND tipo = 'COBRO_SALIDA'
        """, (turno_id,))
        autos_salieron = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM entradas WHERE salio = 0")
        autos_en_cochera = cursor.fetchone()[0]

        return jsonify({
            "ingresos": ingresos,
            "total_efectivo": total_efectivo,
            "total_yape": total_yape,
            "total": total_efectivo + total_yape,
            "autos_ingresados": autos_ingresados,
            "autos_salieron": autos_salieron,
            "autos_en_cochera": autos_en_cochera
        })

    except Exception as e:
        print(f"Error en ingresos_turno: {e}")
        return jsonify({"ingresos": [], "total": 0, "error": str(e)})


@dashboard_bp.route("/reporte_turno")
@login_required
def reporte_turno():
    """Genera el reporte del turno actual"""
    if session.get("es_admin"):
        return "El administrador no tiene turno propio", 400

    try:
        db = get_db()
        cursor = db.cursor()
        
        turno_id = session.get("turno_id")

        cursor.execute("""
            SELECT 
                IFNULL(SUM(monto), 0) as total_cobrado,
                IFNULL(SUM(CASE WHEN metodo_pago = 'efectivo' THEN monto ELSE 0 END), 0) as total_efectivo,
                IFNULL(SUM(CASE WHEN metodo_pago = 'yape' THEN monto ELSE 0 END), 0) as total_yape,
                IFNULL(SUM(CASE WHEN tipo LIKE '%ADELANTO%' OR tipo = 'PAGO_COMPLETO' THEN monto ELSE 0 END), 0) as total_adelantos,
                IFNULL(SUM(CASE WHEN tipo = 'COBRO_SALIDA' THEN monto ELSE 0 END), 0) as total_cobros,
                IFNULL(SUM(CASE WHEN tipo = 'PENALIDAD' THEN monto ELSE 0 END), 0) as total_penalidades
            FROM movimientos_caja
            WHERE turno_id = ?
        """, (turno_id,))
        
        stats_mov = cursor.fetchone()

        cursor.execute("""
            SELECT COUNT(*) FROM entradas
            WHERE trabajador_id = ? AND fecha_registro >= ?
        """, (session["trabajador_id"], session["inicio_turno"]))
        autos_ingresados = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM movimientos_caja
            WHERE turno_id = ? AND tipo = 'COBRO_SALIDA'
        """, (turno_id,))
        autos_salieron = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM entradas WHERE salio = 0")
        autos_en_cochera = cursor.fetchone()[0]

        stats = {
            "total_cobrado": stats_mov["total_cobrado"],
            "total_efectivo": stats_mov["total_efectivo"],
            "total_yape": stats_mov["total_yape"],
            "total_adelantos": stats_mov["total_adelantos"],
            "total_cobros": stats_mov["total_cobros"],
            "total_penalidades": stats_mov["total_penalidades"],
            "autos_ingresados": autos_ingresados,
            "autos_salieron": autos_salieron,
            "autos_en_cochera": autos_en_cochera
        }

        cursor.execute("""
            SELECT 
                m.*,
                c.placa,
                c.nombre as cliente
            FROM movimientos_caja m
            LEFT JOIN entradas e ON m.entrada_id = e.id
            LEFT JOIN clientes c ON e.cliente_id = c.id
            WHERE m.turno_id = ?
            ORDER BY m.fecha_movimiento DESC
        """, (turno_id,))

        detalles = [dict(d) for d in cursor.fetchall()]

        return render_template(
            "reporte_turno.html",
            trabajador=session["nombre"],
            nombre=session["nombre"],
            es_admin=session.get("es_admin", False),
            inicio_turno=session["inicio_turno"],
            fin_turno=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            stats=stats,
            detalles=detalles
        )

    except Exception as e:
        print(f"Error en reporte: {e}")
        return "Error al generar reporte", 500


@dashboard_bp.route("/mis_reportes")
@login_required
def mis_reportes():
    """Historial de turnos del trabajador logueado"""
    try:
        db = get_db()
        cursor = db.cursor()

        trabajador_id = session["trabajador_id"]
        filtro_fecha_desde = request.args.get('fecha_desde', '')
        filtro_fecha_hasta = request.args.get('fecha_hasta', '')
        pagina = int(request.args.get('pagina', 1))
        por_pagina = int(request.args.get('por_pagina', 15))

        query = """
            SELECT
                t.id,
                t.fecha_inicio,
                t.fecha_fin,
                t.estado,
                IFNULL(t.total_efectivo, 0) as total_efectivo,
                IFNULL(t.total_yape, 0) as total_yape,
                IFNULL(t.total_efectivo, 0) + IFNULL(t.total_yape, 0) as total,
                t.efectivo_declarado,
                IFNULL(t.efectivo_declarado, 0) - IFNULL(t.total_efectivo, 0) as diferencia,
                t.observaciones,
                (SELECT COUNT(*) FROM movimientos_caja m WHERE m.turno_id = t.id) as num_movimientos
            FROM turnos t
            WHERE t.trabajador_id = ?
        """
        params = [trabajador_id]

        if filtro_fecha_desde:
            query += " AND date(t.fecha_inicio) >= ?"
            params.append(filtro_fecha_desde)
        if filtro_fecha_hasta:
            query += " AND date(t.fecha_inicio) <= ?"
            params.append(filtro_fecha_hasta)

        count_query = f"SELECT COUNT(*) FROM ({query})"
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]

        query += " ORDER BY t.fecha_inicio DESC"
        query += f" LIMIT {por_pagina} OFFSET {(pagina - 1) * por_pagina}"

        cursor.execute(query, params)
        turnos = [dict(r) for r in cursor.fetchall()]

        return jsonify({
            "ok": True,
            "turnos": turnos,
            "total": total,
            "pagina": pagina,
            "total_paginas": (total + por_pagina - 1) // por_pagina
        })

    except Exception as e:
        print(f"Error en mis_reportes: {e}")
        return jsonify({"ok": False, "error": str(e)})


@dashboard_bp.route("/detalle_mi_turno/<int:turno_id>")
@login_required
def detalle_mi_turno(turno_id):
    """Detalle de un turno del trabajador logueado"""
    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            SELECT * FROM turnos WHERE id = ? AND trabajador_id = ?
        """, (turno_id, session["trabajador_id"]))
        turno = cursor.fetchone()
        if not turno:
            return jsonify({"ok": False, "error": "Turno no encontrado"})

        cursor.execute("""
            SELECT m.*, c.placa, c.nombre as cliente
            FROM movimientos_caja m
            LEFT JOIN entradas e ON m.entrada_id = e.id
            LEFT JOIN clientes c ON e.cliente_id = c.id
            WHERE m.turno_id = ?
            ORDER BY m.fecha_movimiento DESC
        """, (turno_id,))
        movimientos = [dict(m) for m in cursor.fetchall()]

        return jsonify({
            "ok": True,
            "turno": dict(turno),
            "movimientos": movimientos
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@dashboard_bp.route("/cerrar_turno", methods=["POST"])
@login_required
def cerrar_turno():
    """Cierra el turno actual"""
    if session.get("es_admin"):
        return jsonify({"ok": False, "error": "El administrador no tiene turno propio para cerrar"})

    data = request.json

    try:
        db = get_db()
        cursor = db.cursor()
        
        turno_id = session.get("turno_id")

        cursor.execute("""
            SELECT 
                IFNULL(SUM(CASE WHEN metodo_pago = 'efectivo' THEN monto ELSE 0 END), 0) as total_efectivo,
                IFNULL(SUM(CASE WHEN metodo_pago = 'yape' THEN monto ELSE 0 END), 0) as total_yape,
                IFNULL(SUM(monto), 0) as total
            FROM movimientos_caja
            WHERE turno_id = ?
        """, (turno_id,))

        totales = cursor.fetchone()
        
        cursor.execute("""
            SELECT COUNT(*) FROM entradas
            WHERE trabajador_id = ? AND fecha_registro >= ?
        """, (session["trabajador_id"], session["inicio_turno"]))
        autos_ingresados = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM movimientos_caja
            WHERE turno_id = ? AND tipo = 'COBRO_SALIDA'
        """, (turno_id,))
        autos_salieron = cursor.fetchone()[0]

        efectivo_declarado = float(data.get("efectivo_declarado", 0))
        yape_declarado = float(data.get("yape_declarado", 0))
        total_efectivo = float(totales["total_efectivo"] or 0)
        total_yape = float(totales["total_yape"] or 0)
        dif_efectivo = efectivo_declarado - total_efectivo
        dif_yape = yape_declarado - total_yape
        diferencia = dif_efectivo + dif_yape

        if data.get("solo_calcular"):
            return jsonify({
                "ok": True,
                "autos_ingresados": autos_ingresados,
                "autos_salieron": autos_salieron,
                "total_efectivo": total_efectivo,
                "total_yape": total_yape,
                "total_cobrado": float(totales["total"] or 0),
                "efectivo_declarado": efectivo_declarado,
                "yape_declarado": yape_declarado,
                "dif_efectivo": dif_efectivo,
                "dif_yape": dif_yape,
                "diferencia": diferencia
            })

        cursor.execute("""
            UPDATE turnos
            SET estado = 'cerrado',
                fecha_fin = datetime('now', 'localtime'),
                total_efectivo = ?,
                total_yape = ?,
                efectivo_declarado = ?,
                yape_declarado = ?,
                observaciones = ?
            WHERE id = ?
        """, (
            total_efectivo,
            total_yape,
            efectivo_declarado,
            yape_declarado,
            data.get("observaciones", ""),
            turno_id
        ))

        db.commit()

        return jsonify({
            "ok": True,
            "mensaje": "Turno cerrado exitosamente",
            "cerrado": True,
            "autos_ingresados": autos_ingresados,
            "autos_salieron": autos_salieron,
            "total_efectivo": total_efectivo,
            "total_yape": total_yape,
            "efectivo_declarado": efectivo_declarado,
            "yape_declarado": yape_declarado,
            "dif_efectivo": dif_efectivo,
            "dif_yape": dif_yape,
            "diferencia": diferencia
        })

    except Exception as e:
        print(f"Error al cerrar turno: {e}")
        return jsonify({"ok": False, "error": str(e)})
