"""
Módulo de rutas (Blueprints)
"""
from .auth import auth_bp
from .dashboard import dashboard_bp
from .vehiculos import vehiculos_bp
from .admin import admin_bp

__all__ = ['auth_bp', 'dashboard_bp', 'vehiculos_bp', 'admin_bp']
