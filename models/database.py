"""
Módulo de Base de Datos
=======================
Maneja la conexión y operaciones con SQLite.
"""
import sqlite3
import shutil
import os
import glob
from datetime import datetime, timedelta
from flask import g, current_app
from werkzeug.security import generate_password_hash


def get_db():
    """
    Obtiene la conexión a la base de datos.
    Usa el contexto de Flask para reutilizar conexiones.
    """
    if 'db' not in g:
        db_path = current_app.config.get('DATABASE_PATH', 'database.db')
        g.db = sqlite3.connect(db_path, timeout=10)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    """Cierra la conexión al finalizar la petición"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Inicializa la base de datos con las tablas necesarias"""
    db = get_db()
    cursor = db.cursor()
    
    # Tabla de trabajadores
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trabajadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        usuario TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        rol TEXT DEFAULT 'trabajador',
        activo INTEGER DEFAULT 1,
        fecha_creacion TEXT DEFAULT (datetime('now', 'localtime'))
    )
    """)
    
    # Tabla de clientes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        placa TEXT UNIQUE NOT NULL,
        nombre TEXT,
        celular TEXT,
        precio_dia REAL,
        fecha_actualizacion TEXT
    )
    """)
    
    # Tabla de entradas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS entradas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        fecha_entrada TEXT,
        hora_entrada TEXT,
        fecha_hasta TEXT,
        hora_salida_esperada TEXT,
        hora_salida_real TEXT,
        dias INTEGER,
        precio_dia REAL,
        monto REAL,
        adelanto REAL DEFAULT 0,
        penalidad REAL DEFAULT 0,
        descuento REAL DEFAULT 0,
        metodo_pago TEXT DEFAULT 'efectivo',
        dejo_llave INTEGER DEFAULT 0,
        pagado INTEGER DEFAULT 0,
        pago_completo_adelantado INTEGER DEFAULT 0,
        salio INTEGER DEFAULT 0,
        observaciones TEXT,
        trabajador_id INTEGER,
        trabajador_salida_id INTEGER,
        fecha_registro TEXT,
        fecha_salida TEXT,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id),
        FOREIGN KEY (trabajador_id) REFERENCES trabajadores(id),
        FOREIGN KEY (trabajador_salida_id) REFERENCES trabajadores(id)
    )
    """)
    
    # Tabla de turnos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS turnos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trabajador_id INTEGER,
        fecha_inicio TEXT,
        fecha_fin TEXT,
        estado TEXT DEFAULT 'abierto',
        tipo_turno TEXT DEFAULT '',
        total_efectivo REAL DEFAULT 0,
        total_yape REAL DEFAULT 0,
        efectivo_declarado REAL,
        observaciones TEXT,
        FOREIGN KEY (trabajador_id) REFERENCES trabajadores(id)
    )
    """)
    
    # Migración: agregar tipo_turno si no existe
    try:
        cursor.execute("ALTER TABLE turnos ADD COLUMN tipo_turno TEXT DEFAULT ''")
    except Exception:
        pass  # Ya existe la columna

    # Migración: agregar yape_declarado si no existe
    try:
        cursor.execute("ALTER TABLE turnos ADD COLUMN yape_declarado REAL")
    except Exception:
        pass  # Ya existe la columna

    # Tabla de movimientos de caja
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS movimientos_caja (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        turno_id INTEGER,
        entrada_id INTEGER,
        trabajador_id INTEGER,
        tipo TEXT NOT NULL,
        monto REAL NOT NULL,
        metodo_pago TEXT DEFAULT 'efectivo',
        descripcion TEXT,
        fecha_movimiento TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (turno_id) REFERENCES turnos(id),
        FOREIGN KEY (entrada_id) REFERENCES entradas(id),
        FOREIGN KEY (trabajador_id) REFERENCES trabajadores(id)
    )
    """)
    
    # Tabla de configuración
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configuracion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        clave TEXT UNIQUE NOT NULL,
        valor TEXT,
        descripcion TEXT
    )
    """)
    
    # Insertar configuraciones por defecto
    configuraciones_default = [
        ('tolerancia_minutos', '60', 'Minutos de tolerancia antes de cobrar penalidad'),
        ('capacidad_maxima', '50', 'Capacidad máxima de la cochera'),
        ('precio_default', '10', 'Precio por día por defecto')
    ]
    
    for clave, valor, desc in configuraciones_default:
        cursor.execute("""
            INSERT OR IGNORE INTO configuracion (clave, valor, descripcion)
            VALUES (?, ?, ?)
        """, (clave, valor, desc))
    
    db.commit()


def crear_usuarios_default():
    """Crea el usuario administrador por defecto si no existe"""
    db = get_db()
    cursor = db.cursor()

    # Solo crear el admin si no existe ningún usuario admin
    cursor.execute("SELECT id FROM trabajadores WHERE rol = 'admin' LIMIT 1")
    if not cursor.fetchone():
        password_hash = generate_password_hash("angelccasa284")
        cursor.execute("""
            INSERT INTO trabajadores (nombre, usuario, password, rol)
            VALUES (?, ?, ?, ?)
        """, ("Administrador", "angel", password_hash, "admin"))
        db.commit()


def recuperar_db(db_path):
    """Si la DB no existe o está corrupta, recupera del último backup."""
    necesita_recuperar = False

    if not os.path.exists(db_path):
        necesita_recuperar = True
    else:
        try:
            conn = sqlite3.connect(db_path)
            result = conn.execute("PRAGMA integrity_check").fetchone()
            conn.close()
            if result[0] != 'ok':
                necesita_recuperar = True
        except Exception:
            necesita_recuperar = True

    if not necesita_recuperar:
        return False

    backups_dir = os.path.join(os.path.dirname(db_path) or '.', 'backups')
    if not os.path.isdir(backups_dir):
        return False

    archivos = sorted(glob.glob(os.path.join(backups_dir, 'cochera_backup_*.db')), reverse=True)
    if not archivos:
        return False

    shutil.copy2(archivos[0], db_path)
    print(f"[BACKUP] Base de datos recuperada desde {os.path.basename(archivos[0])}")
    return True


def backup_db(db_path):
    """Crea backup si el último tiene más de 2 días. Mantiene máximo 5."""
    if not os.path.exists(db_path):
        return

    backups_dir = os.path.join(os.path.dirname(db_path) or '.', 'backups')
    os.makedirs(backups_dir, exist_ok=True)

    archivos = sorted(glob.glob(os.path.join(backups_dir, 'cochera_backup_*.db')), reverse=True)

    if archivos:
        nombre = os.path.basename(archivos[0])
        try:
            fecha_str = nombre.replace('cochera_backup_', '').replace('.db', '')
            fecha_ultimo = datetime.strptime(fecha_str, '%Y%m%d')
            if datetime.now() - fecha_ultimo < timedelta(days=2):
                return
        except ValueError:
            pass

    hoy = datetime.now().strftime('%Y%m%d')
    destino = os.path.join(backups_dir, f'cochera_backup_{hoy}.db')
    shutil.copy2(db_path, destino)
    print(f"[BACKUP] Backup creado: cochera_backup_{hoy}.db")

    # Mantener máximo 5 backups
    archivos = sorted(glob.glob(os.path.join(backups_dir, 'cochera_backup_*.db')), reverse=True)
    for antiguo in archivos[5:]:
        os.remove(antiguo)


def init_app(app):
    """Registra las funciones de base de datos con la aplicación Flask"""
    app.teardown_appcontext(close_db)

    db_path = app.config.get('DATABASE_PATH', 'database.db')
    recuperar_db(db_path)

    with app.app_context():
        init_db()
        crear_usuarios_default()

    backup_db(db_path)
