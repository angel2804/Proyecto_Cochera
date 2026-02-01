"""
Script de Migración - Sistema de Cochera v2.0
=============================================
Ejecuta este script UNA SOLA VEZ si ya tienes una base de datos existente.
Este script agregará las nuevas tablas y columnas necesarias.

Uso: python migrar_db.py
"""

import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

def migrar_base_datos():
    print("=" * 60)
    print("🔄 MIGRACIÓN DE BASE DE DATOS - Sistema Cochera v2.0")
    print("=" * 60)
    print()
    
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    errores = []
    exitos = []
    
    try:
        # =============================================
        # 1. AGREGAR COLUMNAS NUEVAS A 'entradas'
        # =============================================
        print("📋 Verificando tabla 'entradas'...")
        
        cursor.execute("PRAGMA table_info(entradas)")
        columnas_existentes = [col[1] for col in cursor.fetchall()]
        
        columnas_nuevas = {
            'fecha_salida': 'TEXT',
            'trabajador_salida_id': 'INTEGER'
        }
        
        for columna, tipo in columnas_nuevas.items():
            if columna not in columnas_existentes:
                try:
                    cursor.execute(f"ALTER TABLE entradas ADD COLUMN {columna} {tipo}")
                    exitos.append(f"✅ Columna '{columna}' agregada a 'entradas'")
                except Exception as e:
                    errores.append(f"❌ Error agregando '{columna}': {e}")
            else:
                print(f"   ℹ️  Columna '{columna}' ya existe")
        
        # =============================================
        # 2. CREAR TABLA 'movimientos_caja'
        # =============================================
        print("\n📋 Verificando tabla 'movimientos_caja'...")
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='movimientos_caja'
        """)
        
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE movimientos_caja (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entrada_id INTEGER,
                    trabajador_id INTEGER,
                    tipo TEXT NOT NULL,
                    monto REAL NOT NULL,
                    descripcion TEXT,
                    fecha_movimiento TEXT DEFAULT (datetime('now')),
                    turno_inicio TEXT,
                    FOREIGN KEY (entrada_id) REFERENCES entradas(id),
                    FOREIGN KEY (trabajador_id) REFERENCES trabajadores(id)
                )
            """)
            exitos.append("✅ Tabla 'movimientos_caja' creada")
        else:
            print("   ℹ️  Tabla 'movimientos_caja' ya existe")
        
        # =============================================
        # 3. CREAR TABLA 'cierres_turno'
        # =============================================
        print("\n📋 Verificando tabla 'cierres_turno'...")
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='cierres_turno'
        """)
        
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE cierres_turno (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trabajador_id INTEGER,
                    inicio_turno TEXT,
                    fin_turno TEXT,
                    total_sistema REAL,
                    efectivo_declarado REAL,
                    diferencia REAL,
                    autos_atendidos INTEGER,
                    autos_salieron INTEGER,
                    observaciones TEXT,
                    FOREIGN KEY (trabajador_id) REFERENCES trabajadores(id)
                )
            """)
            exitos.append("✅ Tabla 'cierres_turno' creada")
        else:
            print("   ℹ️  Tabla 'cierres_turno' ya existe")
        
        # =============================================
        # 4. ACTUALIZAR TABLA 'trabajadores'
        # =============================================
        print("\n📋 Verificando tabla 'trabajadores'...")
        
        cursor.execute("PRAGMA table_info(trabajadores)")
        columnas_trabajadores = [col[1] for col in cursor.fetchall()]
        
        if 'activo' not in columnas_trabajadores:
            try:
                cursor.execute("ALTER TABLE trabajadores ADD COLUMN activo INTEGER DEFAULT 1")
                exitos.append("✅ Columna 'activo' agregada a 'trabajadores'")
            except Exception as e:
                errores.append(f"❌ Error agregando 'activo': {e}")
        
        if 'fecha_creacion' not in columnas_trabajadores:
            try:
                cursor.execute("ALTER TABLE trabajadores ADD COLUMN fecha_creacion TEXT")
                exitos.append("✅ Columna 'fecha_creacion' agregada a 'trabajadores'")
            except Exception as e:
                errores.append(f"❌ Error agregando 'fecha_creacion': {e}")
        
        # =============================================
        # 5. CREAR TRABAJADORES ADICIONALES
        # =============================================
        print("\n👥 Verificando trabajadores...")
        
        trabajadores_demo = [
            ('María García', 'maria', '1234'),
            ('Carlos López', 'carlos', '1234')
        ]
        
        for nombre, usuario, password in trabajadores_demo:
            cursor.execute("SELECT id FROM trabajadores WHERE usuario = ?", (usuario,))
            if not cursor.fetchone():
                try:
                    password_hash = generate_password_hash(password)
                    cursor.execute("""
                        INSERT INTO trabajadores (nombre, usuario, password, activo, fecha_creacion)
                        VALUES (?, ?, ?, 1, datetime('now'))
                    """, (nombre, usuario, password_hash))
                    exitos.append(f"✅ Trabajador '{usuario}' creado")
                except Exception as e:
                    errores.append(f"❌ Error creando trabajador '{usuario}': {e}")
            else:
                print(f"   ℹ️  Trabajador '{usuario}' ya existe")
        
        # =============================================
        # 6. MIGRAR ADELANTOS EXISTENTES A MOVIMIENTOS_CAJA
        # =============================================
        print("\n💰 Migrando adelantos existentes...")
        
        # Verificar si hay adelantos sin migrar
        cursor.execute("""
            SELECT e.id, e.adelanto, e.trabajador_id, e.fecha_registro, 
                   c.placa, c.nombre as cliente
            FROM entradas e
            JOIN clientes c ON e.cliente_id = c.id
            WHERE e.adelanto > 0
            AND e.id NOT IN (SELECT entrada_id FROM movimientos_caja WHERE entrada_id IS NOT NULL)
        """)
        
        adelantos_pendientes = cursor.fetchall()
        
        if adelantos_pendientes:
            for adelanto in adelantos_pendientes:
                try:
                    cursor.execute("""
                        INSERT INTO movimientos_caja (
                            entrada_id, trabajador_id, tipo, monto, descripcion, 
                            fecha_movimiento, turno_inicio
                        )
                        VALUES (?, ?, 'ADELANTO', ?, ?, ?, ?)
                    """, (
                        adelanto['id'],
                        adelanto['trabajador_id'],
                        adelanto['adelanto'],
                        f"Adelanto migrado - {adelanto['placa']} - {adelanto['cliente']}",
                        adelanto['fecha_registro'],
                        adelanto['fecha_registro']
                    ))
                except Exception as e:
                    errores.append(f"❌ Error migrando adelanto ID {adelanto['id']}: {e}")
            
            exitos.append(f"✅ {len(adelantos_pendientes)} adelantos migrados a movimientos_caja")
        else:
            print("   ℹ️  No hay adelantos pendientes de migrar")
        
        # =============================================
        # 7. MIGRAR COBROS DE SALIDAS EXISTENTES
        # =============================================
        print("\n💵 Migrando cobros de salidas existentes...")
        
        cursor.execute("""
            SELECT e.id, e.monto, e.adelanto, e.trabajador_id, e.fecha_salida,
                   e.fecha_registro, c.placa, c.nombre as cliente, e.dias
            FROM entradas e
            JOIN clientes c ON e.cliente_id = c.id
            WHERE e.salio = 1 AND e.pagado = 1
            AND e.id NOT IN (
                SELECT entrada_id FROM movimientos_caja 
                WHERE tipo = 'COBRO_SALIDA' AND entrada_id IS NOT NULL
            )
        """)
        
        cobros_pendientes = cursor.fetchall()
        
        if cobros_pendientes:
            for cobro in cobros_pendientes:
                monto_cobrado = float(cobro['monto'] or 0) - float(cobro['adelanto'] or 0)
                if monto_cobrado > 0:
                    try:
                        fecha_mov = cobro['fecha_salida'] or cobro['fecha_registro']
                        cursor.execute("""
                            INSERT INTO movimientos_caja (
                                entrada_id, trabajador_id, tipo, monto, descripcion,
                                fecha_movimiento, turno_inicio
                            )
                            VALUES (?, ?, 'COBRO_SALIDA', ?, ?, ?, ?)
                        """, (
                            cobro['id'],
                            cobro['trabajador_id'],
                            monto_cobrado,
                            f"Cobro migrado - {cobro['placa']} - {cobro['cliente']} - {cobro['dias']} días",
                            fecha_mov,
                            fecha_mov
                        ))
                    except Exception as e:
                        errores.append(f"❌ Error migrando cobro ID {cobro['id']}: {e}")
            
            exitos.append(f"✅ {len(cobros_pendientes)} cobros migrados a movimientos_caja")
        else:
            print("   ℹ️  No hay cobros pendientes de migrar")
        
        # =============================================
        # CONFIRMAR CAMBIOS
        # =============================================
        conn.commit()
        
        # =============================================
        # RESUMEN FINAL
        # =============================================
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE LA MIGRACIÓN")
        print("=" * 60)
        
        if exitos:
            print("\n✅ OPERACIONES EXITOSAS:")
            for exito in exitos:
                print(f"   {exito}")
        
        if errores:
            print("\n❌ ERRORES ENCONTRADOS:")
            for error in errores:
                print(f"   {error}")
        
        # Mostrar estadísticas finales
        print("\n📈 ESTADÍSTICAS DE LA BASE DE DATOS:")
        
        cursor.execute("SELECT COUNT(*) FROM trabajadores")
        print(f"   👥 Trabajadores: {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM clientes")
        print(f"   🚗 Clientes: {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM entradas")
        print(f"   📋 Entradas: {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM entradas WHERE salio = 0")
        print(f"   🅿️  Autos en cochera: {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM movimientos_caja")
        print(f"   💰 Movimientos de caja: {cursor.fetchone()[0]}")
        
        print("\n" + "=" * 60)
        print("✅ MIGRACIÓN COMPLETADA")
        print("=" * 60)
        print("\n🚀 Ahora puedes ejecutar: python app.py")
        print()
        
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def verificar_integridad():
    """Verifica la integridad de la base de datos después de la migración"""
    print("\n🔍 Verificando integridad de la base de datos...")
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    try:
        # Verificar tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas = [t[0] for t in cursor.fetchall()]
        
        tablas_requeridas = ['trabajadores', 'clientes', 'entradas', 'movimientos_caja', 'cierres_turno']
        
        for tabla in tablas_requeridas:
            if tabla in tablas:
                print(f"   ✅ Tabla '{tabla}' existe")
            else:
                print(f"   ❌ Tabla '{tabla}' NO existe")
        
        print("\n✅ Verificación completada")
        
    finally:
        conn.close()


if __name__ == "__main__":
    migrar_base_datos()
    verificar_integridad()
