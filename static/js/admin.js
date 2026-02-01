// ========================================
// ADMIN PANEL - JavaScript
// ========================================

// --- TABS ---
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.admin-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.admin-tab-content').forEach(c => c.classList.remove('active'));
            this.classList.add('active');
            document.getElementById('tab-' + this.dataset.tab).classList.add('active');

            if (this.dataset.tab === 'usuarios') cargarUsuarios();
            if (this.dataset.tab === 'configuracion') cargarConfiguracion();
            if (this.dataset.tab === 'reportes') cargarFiltrosTrabajadores();
        });
    });
});

// --- USUARIOS ---
function cargarUsuarios() {
    fetch('/admin/usuarios')
        .then(r => r.json())
        .then(data => {
            if (!data.ok) return;
            const tbody = document.getElementById('tbody-usuarios');
            if (!data.usuarios.length) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No hay usuarios</td></tr>';
                return;
            }
            tbody.innerHTML = data.usuarios.map(u => `
                <tr>
                    <td>${u.id}</td>
                    <td>${u.nombre}</td>
                    <td>${u.usuario}</td>
                    <td><span class="badge badge-${u.rol === 'admin' ? 'admin' : 'worker'}">${u.rol}</span></td>
                    <td><span class="badge badge-${u.activo ? 'active' : 'inactive'}">${u.activo ? 'Activo' : 'Inactivo'}</span></td>
                    <td>${u.fecha_creacion || '-'}</td>
                    <td>
                        <button class="btn-sm btn-edit" onclick='editarUsuario(${JSON.stringify(u)})'>Editar</button>
                        ${u.activo ? `<button class="btn-sm btn-danger" onclick="desactivarUsuario(${u.id})">Desactivar</button>` : ''}
                    </td>
                </tr>
            `).join('');
        });
}

function abrirModalUsuario() {
    document.getElementById('modal-usuario-titulo').textContent = 'Nuevo Usuario';
    document.getElementById('form-usuario').reset();
    document.getElementById('usuario-id').value = '';
    document.getElementById('pass-hint').style.display = 'none';
    document.getElementById('usuario-pass').required = true;
    document.getElementById('grupo-activo').style.display = 'none';
    document.getElementById('modal-usuario').style.display = 'flex';
}

function editarUsuario(u) {
    document.getElementById('modal-usuario-titulo').textContent = 'Editar Usuario';
    document.getElementById('usuario-id').value = u.id;
    document.getElementById('usuario-nombre').value = u.nombre;
    document.getElementById('usuario-user').value = u.usuario;
    document.getElementById('usuario-pass').value = '';
    document.getElementById('usuario-pass').required = false;
    document.getElementById('pass-hint').style.display = 'inline';
    document.getElementById('usuario-rol').value = u.rol;
    document.getElementById('usuario-activo').checked = !!u.activo;
    document.getElementById('grupo-activo').style.display = 'block';
    document.getElementById('modal-usuario').style.display = 'flex';
}

function cerrarModalUsuario() {
    document.getElementById('modal-usuario').style.display = 'none';
}

function guardarUsuario(e) {
    e.preventDefault();
    const id = document.getElementById('usuario-id').value;
    const payload = {
        nombre: document.getElementById('usuario-nombre').value,
        usuario: document.getElementById('usuario-user').value,
        rol: document.getElementById('usuario-rol').value
    };
    const pass = document.getElementById('usuario-pass').value;
    if (pass) payload.password = pass;

    let url;
    if (id) {
        url = '/admin/usuarios/editar';
        payload.id = parseInt(id);
        payload.activo = document.getElementById('usuario-activo').checked;
    } else {
        url = '/admin/usuarios/crear';
        if (!pass) { mostrarToast('La contrasena es requerida', 'error'); return; }
        payload.password = pass;
    }

    fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(data => {
        if (data.ok) {
            mostrarToast(data.mensaje);
            cerrarModalUsuario();
            cargarUsuarios();
        } else {
            mostrarToast(data.error, 'error');
        }
    });
}

function desactivarUsuario(id) {
    if (!confirm('Desactivar este usuario?')) return;
    fetch('/admin/usuarios/eliminar/' + id, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                mostrarToast(data.mensaje);
                cargarUsuarios();
            } else {
                mostrarToast(data.error, 'error');
            }
        });
}

// --- CONFIGURACION ---
function cargarConfiguracion() {
    fetch('/admin/configuracion')
        .then(r => r.json())
        .then(data => {
            if (!data.ok) return;
            data.configuracion.forEach(c => {
                const input = document.querySelector(`[name="${c.clave}"]`);
                if (input) input.value = c.valor;
            });
        });
}

function guardarConfiguracion(e) {
    e.preventDefault();
    const form = document.getElementById('form-config');
    const payload = {};
    form.querySelectorAll('input[name]').forEach(input => {
        payload[input.name] = input.value;
    });

    fetch('/admin/configuracion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(data => {
        mostrarToast(data.ok ? data.mensaje : data.error, data.ok ? 'exito' : 'error');
    });
}

// --- REPORTES DE TURNOS ---
let reportesPagina = 1;

function cargarFiltrosTrabajadores() {
    fetch('/admin/reportes_turnos?pagina=1&por_pagina=1')
        .then(r => r.json())
        .then(data => {
            if (!data.ok) return;
            const select = document.getElementById('filtro-trabajador');
            const currentVal = select.value;
            select.innerHTML = '<option value="">Todos</option>';
            data.trabajadores.forEach(t => {
                select.innerHTML += `<option value="${t.id}">${t.nombre}</option>`;
            });
            select.value = currentVal;
        });
}

function buscarReportes(pagina) {
    reportesPagina = pagina || 1;
    const params = new URLSearchParams({
        trabajador_id: document.getElementById('filtro-trabajador').value,
        fecha_desde: document.getElementById('filtro-reporte-desde').value,
        fecha_hasta: document.getElementById('filtro-reporte-hasta').value,
        pagina: reportesPagina,
        por_pagina: 20
    });

    fetch('/admin/reportes_turnos?' + params)
        .then(r => r.json())
        .then(data => {
            if (!data.ok) return;
            const tbody = document.getElementById('tbody-reportes');

            if (!data.turnos.length) {
                tbody.innerHTML = '<tr><td colspan="10" class="tabla-vacia"><div class="empty-state"><span class="empty-icon">📋</span><p>No se encontraron turnos</p></div></td></tr>';
                document.getElementById('paginacion-reportes').innerHTML = '';
                return;
            }

            tbody.innerHTML = data.turnos.map(t => {
                const dif = parseFloat(t.diferencia || 0);
                const difClass = dif < 0 ? 'texto-danger' : dif > 0 ? 'texto-warning' : 'texto-exito';
                const estadoBadge = t.estado === 'cerrado'
                    ? '<span class="badge badge-inactive">Cerrado</span>'
                    : '<span class="badge badge-active">Abierto</span>';

                return `
                <tr>
                    <td><strong>${t.trabajador}</strong></td>
                    <td class="fecha-col">${formatearFecha(t.fecha_inicio)}</td>
                    <td class="fecha-col">${t.fecha_fin ? formatearFecha(t.fecha_fin) : '-'}</td>
                    <td>S/ ${parseFloat(t.total_efectivo).toFixed(2)}</td>
                    <td>S/ ${parseFloat(t.total_yape).toFixed(2)}</td>
                    <td><strong>S/ ${parseFloat(t.total).toFixed(2)}</strong></td>
                    <td>${t.efectivo_declarado != null ? 'S/ ' + parseFloat(t.efectivo_declarado).toFixed(2) : '-'}</td>
                    <td class="${difClass}">${t.efectivo_declarado != null ? 'S/ ' + dif.toFixed(2) : '-'}</td>
                    <td>${estadoBadge}</td>
                    <td>
                        <button class="btn-sm btn-edit" onclick="verDetalleTurno(${t.id})">Ver</button>
                        <a href="/reporte_turno/${t.id}" target="_blank" class="btn-sm btn-primary" style="margin-left:4px;text-decoration:none;">Reporte</a>
                    </td>
                </tr>`;
            }).join('');

            // Paginacion
            let pagHtml = '';
            if (data.total_paginas > 1) {
                for (let i = 1; i <= data.total_paginas; i++) {
                    pagHtml += `<button class="btn-sm ${i === data.pagina ? 'btn-primary' : 'btn-secondary'}" onclick="buscarReportes(${i})">${i}</button> `;
                }
            }
            pagHtml += `<span class="pag-total">Total: ${data.total} turnos</span>`;
            document.getElementById('paginacion-reportes').innerHTML = pagHtml;
        });
}

function limpiarFiltrosReportes() {
    document.getElementById('filtro-trabajador').value = '';
    document.getElementById('filtro-reporte-desde').value = '';
    document.getElementById('filtro-reporte-hasta').value = '';
    document.getElementById('tbody-reportes').innerHTML = '<tr><td colspan="10" class="tabla-vacia"><div class="empty-state"><span class="empty-icon">📋</span><p>Seleccione filtros y presione Buscar</p></div></td></tr>';
    document.getElementById('paginacion-reportes').innerHTML = '';
}

function verDetalleTurno(turnoId) {
    document.getElementById('modal-detalle-turno').style.display = 'flex';
    document.getElementById('detalle-turno-body').innerHTML = '<p style="text-align:center;padding:2rem;">Cargando...</p>';

    fetch('/admin/detalle_turno/' + turnoId)
        .then(r => r.json())
        .then(data => {
            if (!data.ok) {
                document.getElementById('detalle-turno-body').innerHTML = '<p>Error al cargar detalle</p>';
                return;
            }

            const t = data.turno;
            const totalTurno = parseFloat(t.total_efectivo || 0) + parseFloat(t.total_yape || 0);
            const dif = parseFloat(t.efectivo_declarado || 0) - parseFloat(t.total_efectivo || 0);
            const difClass = dif < 0 ? 'texto-danger' : dif > 0 ? 'texto-warning' : 'texto-exito';

            let html = `
            <div class="detalle-turno-info">
                <div class="detalle-turno-cards">
                    <div class="dt-card">
                        <span class="dt-label">Trabajador</span>
                        <span class="dt-value">${t.trabajador}</span>
                    </div>
                    <div class="dt-card">
                        <span class="dt-label">Inicio</span>
                        <span class="dt-value">${formatearFecha(t.fecha_inicio)}</span>
                    </div>
                    <div class="dt-card">
                        <span class="dt-label">Fin</span>
                        <span class="dt-value">${t.fecha_fin ? formatearFecha(t.fecha_fin) : 'Abierto'}</span>
                    </div>
                    <div class="dt-card">
                        <span class="dt-label">Estado</span>
                        <span class="dt-value">${t.estado === 'cerrado' ? 'Cerrado' : 'Abierto'}</span>
                    </div>
                </div>
                <div class="detalle-turno-resumen">
                    <div class="dt-stat">
                        <span class="dt-stat-label">Efectivo</span>
                        <span class="dt-stat-value">S/ ${parseFloat(t.total_efectivo || 0).toFixed(2)}</span>
                    </div>
                    <div class="dt-stat">
                        <span class="dt-stat-label">Yape</span>
                        <span class="dt-stat-value">S/ ${parseFloat(t.total_yape || 0).toFixed(2)}</span>
                    </div>
                    <div class="dt-stat dt-stat-total">
                        <span class="dt-stat-label">Total</span>
                        <span class="dt-stat-value">S/ ${totalTurno.toFixed(2)}</span>
                    </div>
                    ${t.efectivo_declarado != null ? `
                    <div class="dt-stat">
                        <span class="dt-stat-label">Declarado</span>
                        <span class="dt-stat-value">S/ ${parseFloat(t.efectivo_declarado).toFixed(2)}</span>
                    </div>
                    <div class="dt-stat">
                        <span class="dt-stat-label">Diferencia</span>
                        <span class="dt-stat-value ${difClass}">S/ ${dif.toFixed(2)}</span>
                    </div>` : ''}
                </div>
                ${data.desglose ? `
                <div class="detalle-turno-desglose">
                    <span>Adelantos: <strong>S/ ${parseFloat(data.desglose.total_adelantos).toFixed(2)}</strong></span>
                    <span>Cobros salida: <strong>S/ ${parseFloat(data.desglose.total_cobros).toFixed(2)}</strong></span>
                    <span>Penalidades: <strong>S/ ${parseFloat(data.desglose.total_penalidades).toFixed(2)}</strong></span>
                </div>` : ''}
                ${t.observaciones ? `<div class="detalle-turno-obs"><strong>Observaciones:</strong> ${t.observaciones}</div>` : ''}
            </div>

            <h4 style="margin: 1.5rem 0 0.75rem;">Movimientos (${data.movimientos.length})</h4>
            <div class="table-responsive">
                <table class="admin-table">
                    <thead>
                        <tr>
                            <th>Hora</th>
                            <th>Tipo</th>
                            <th>Placa</th>
                            <th>Cliente</th>
                            <th>Monto</th>
                            <th>Metodo</th>
                        </tr>
                    </thead>
                    <tbody>`;

            if (data.movimientos.length === 0) {
                html += '<tr><td colspan="6" style="text-align:center;">Sin movimientos</td></tr>';
            } else {
                data.movimientos.forEach(m => {
                    html += `
                    <tr>
                        <td class="fecha-col">${m.fecha_movimiento || '-'}</td>
                        <td><span class="badge badge-info">${m.tipo}</span></td>
                        <td><strong>${m.placa || '-'}</strong></td>
                        <td>${m.cliente || '-'}</td>
                        <td>S/ ${parseFloat(m.monto).toFixed(2)}</td>
                        <td><span class="badge badge-${m.metodo_pago === 'yape' ? 'yape' : 'efectivo'}">${m.metodo_pago}</span></td>
                    </tr>`;
                });
            }

            html += '</tbody></table></div>';
            document.getElementById('detalle-turno-body').innerHTML = html;
        });
}

function cerrarModalDetalleTurno() {
    document.getElementById('modal-detalle-turno').style.display = 'none';
}

function formatearFecha(str) {
    if (!str) return '-';
    return str.replace('T', ' ').substring(0, 16);
}

