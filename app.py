"""
Aplicación Principal - Sistema de Cochera
==========================================
"""
import os
from flask import Flask, render_template, session

from models.database import init_app
from routes import auth_bp, dashboard_bp, vehiculos_bp, admin_bp


def create_app():
    app = Flask(__name__)

    app.secret_key = os.environ.get('SECRET_KEY', 'cochera-secret-key-2024')
    app.config['DATABASE_PATH'] = os.environ.get('DATABASE_PATH', 'database.db')
    app.config['PERMANENT_SESSION_LIFETIME'] = 28800  # 8 horas

    # Inicializar base de datos
    init_app(app)

    # Registrar blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(vehiculos_bp)
    app.register_blueprint(admin_bp)

    # Manejadores de error
    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html'), 500

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
