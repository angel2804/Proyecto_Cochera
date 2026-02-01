# 🎨 CSS Organizado - Sistema de Cochera

## Estructura

```
css/
├── estilos.css          ← Archivo principal (solo imports)
├── _variables.css       ← Variables y temas (claro/oscuro)
├── _base.css            ← Reset y estilos base
├── _login.css           ← Página de login
├── _layout.css          ← Header, main, acciones
├── _kpis.css            ← Tarjetas de KPIs
├── _tables.css          ← Tablas y badges
├── _forms.css           ← Formularios e inputs
├── _buttons.css         ← Botones
├── _modals.css          ← Ventanas modales
├── _components.css      ← Alertas, tickets, toasts
├── _admin.css           ← Panel de administración
├── _utilities.css       ← Clases helper
├── _animations.css      ← Keyframes
└── _responsive.css      ← Media queries
```

## 🆚 Comparación

| Antes | Después |
|-------|---------|
| 1 archivo de 2,008 líneas | 14 archivos (~100-200 líneas c/u) |
| Difícil de encontrar estilos | Organizado por componente |
| Difícil de mantener | Fácil de editar |

## 📝 Cómo usar

El archivo `estilos.css` importa todos los demás:

```css
@import '_variables.css';
@import '_base.css';
@import '_login.css';
/* ... etc */
```

**Solo necesitas incluir `estilos.css` en tu HTML:**

```html
<link rel="stylesheet" href="css/estilos.css">
```

## 🎯 Guía rápida

| ¿Qué quieres modificar? | Archivo |
|-------------------------|---------|
| Colores, tema oscuro | `_variables.css` |
| Página de login | `_login.css` |
| Header, navegación | `_layout.css` |
| Tarjetas de estadísticas | `_kpis.css` |
| Tablas, badges | `_tables.css` |
| Inputs, selects, forms | `_forms.css` |
| Botones | `_buttons.css` |
| Ventanas modales | `_modals.css` |
| Alertas, toasts, tickets | `_components.css` |
| Panel de admin | `_admin.css` |
| Clases de utilidad | `_utilities.css` |
| Animaciones | `_animations.css` |
| Responsive/móvil | `_responsive.css` |

## ⚠️ Nota sobre @import

Los `@import` de CSS funcionan bien para desarrollo, pero en producción es mejor:

1. **Concatenar** todos los archivos en uno solo, o
2. **Usar un preprocesador** como Sass/SCSS

Para concatenar manualmente:
```bash
cat _variables.css _base.css _login.css ... > estilos.min.css
```

## 🌙 Modo Oscuro

Para activar el modo oscuro, agrega la clase `dark-theme` o `tema-oscuro` al body:

```javascript
document.body.classList.toggle('dark-theme');
```

Las variables CSS cambiarán automáticamente.
