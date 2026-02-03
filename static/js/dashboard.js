/**
 * Dashboard - JavaScript
 * ======================
 * Funciones del dashboard del trabajador
 */

// ========================================
// VARIABLES GLOBALES
// ========================================
let autosEnCocheraData = [];
let historialPaginaActual = 1;

// ========================================
// INICIALIZACION
// ========================================
document.addEventListener('DOMContentLoaded', function() {
    cargarIngresos();
    cargarAlertas();

    setInterval(cargarIngresos, 30000);
    setInterval(cargarAlertas, 30000);

    inicializarFechas();
    inicializarEventosEntrada();
    inicializarEventosSalida();
});

function inicializarFechas() {
    const now = new Date();
    const hoy = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0');
    const ahora = new Date().toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit', hour12: false });

    const fechaEntrada = document.getElementById('fechaEntrada');
    const horaEntrada = document.getElementById('horaEntrada');
    const fechaHasta = document.getElementById('fechaHasta');

    if (fechaEntrada) fechaEntrada.value = hoy;
    if (horaEntrada) horaEntrada.value = ahora;
    if (fechaHasta) {
        const manana = new Date();
        manana.setDate(manana.getDate() + 1);
        fechaHasta.value = manana.getFullYear() + '-' + String(manana.getMonth() + 1).padStart(2, '0') + '-' + String(manana.getDate()).padStart(2, '0');
    }
}

// ========================================
// EVENTOS INTERACTIVOS - ENTRADA
// ========================================
function inicializarEventosEntrada() {
    const fechaEntrada = document.getElementById('fechaEntrada');
    const fechaHasta = document.getElementById('fechaHasta');
    const dias = document.getElementById('dias');
    const precio = document.getElementById('precio');
    const placa = document.getElementById('placa');

    // Auto-calcular dias al cambiar fechas
    if (fechaEntrada && fechaHasta) {
        fechaEntrada.addEventListener('change', calcularDiasAutomatico);
        fechaHasta.addEventListener('change', calcularDiasAutomatico);
    }

    // Recalcular monto en tiempo real
    if (dias) dias.addEventListener('input', calcularMonto);
    if (precio) precio.addEventListener('input', calcularMonto);

    // Buscar cliente al escribir placa (con debounce)
    if (placa) {
        let placaTimeout;
        placa.addEventListener('input', function() {
            clearTimeout(placaTimeout);
            const val = this.value.trim().toUpperCase();
            if (val.length >= 3) {
                placaTimeout = setTimeout(() => buscarClientePorPlaca(val), 400);
            }
        });
    }
}

function calcularDiasAutomatico() {
    const fechaEntrada = document.getElementById('fechaEntrada').value;
    const fechaHasta = document.getElementById('fechaHasta').value;

    if (fechaEntrada && fechaHasta) {
        const entrada = new Date(fechaEntrada);
        const hasta = new Date(fechaHasta);
        let diff = Math.ceil((hasta - entrada) / (1000 * 60 * 60 * 24));
        if (diff < 1) diff = 1;
        document.getElementById('dias').value = diff;
        calcularMonto();
    }
}

async function buscarClientePorPlaca(placa) {
    try {
        const response = await fetch(`/buscar_cliente/${placa}`);
        const data = await response.json();

        if (data.existe) {
            document.getElementById('cliente').value = data.nombre || '';
            document.getElementById('celular').value = data.celular || '';
            document.getElementById('precio').value = data.precio_dia || 10;
            calcularMonto();
            mostrarToast('Cliente encontrado: ' + data.nombre, 'exito');
        }
    } catch (error) {
        console.error('Error buscando cliente:', error);
    }
}

// ========================================
// EVENTOS INTERACTIVOS - SALIDA
// ========================================
function inicializarEventosSalida() {
    const placaSalida = document.getElementById('placaSalida');
    if (placaSalida) {
        // Buscar al escribir (con debounce) - busqueda predictiva
        let salidaTimeout;
        placaSalida.addEventListener('input', function() {
            clearTimeout(salidaTimeout);
            const val = this.value.trim().toUpperCase();
            if (val.length >= 2) {
                salidaTimeout = setTimeout(() => buscarSugerenciasSalida(val), 300);
            } else {
                ocultarSugerencias();
            }
        });

        // Buscar con Enter
        placaSalida.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                buscarParaSalida();
            }
        });
    }

    // Recalcular cobro en tiempo real
    const penalidad = document.getElementById('salidaPenalidad');
    const descuento = document.getElementById('salidaDescuento');
    if (penalidad) penalidad.addEventListener('input', recalcularCobro);
    if (descuento) descuento.addEventListener('input', recalcularCobro);
}

async function buscarSugerenciasSalida(texto) {
    try {
        const response = await fetch('/autos_en_cochera');
        const data = await response.json();
        if (!data.ok) return;

        const coincidencias = data.autos.filter(a =>
            a.placa.includes(texto) || a.cliente.toUpperCase().includes(texto)
        );

        const container = document.getElementById('sugerenciasSalida');
        if (!container) return;

        if (coincidencias.length === 0) {
            container.innerHTML = '<div class="sugerencia-item sugerencia-vacia">No se encontraron resultados</div>';
            container.style.display = 'block';
            return;
        }

        container.innerHTML = coincidencias.slice(0, 5).map(a => `
            <div class="sugerencia-item" onclick="seleccionarSugerencia(${a.id}, '${a.placa}')">
                <strong>${a.placa}</strong>
                <span>${a.cliente}</span>
                <small>${a.dias_reales}d - S/ ${a.pendiente.toFixed(2)} pend.</small>
            </div>
        `).join('');
        container.style.display = 'block';
    } catch (e) {
        console.error(e);
    }
}

function seleccionarSugerencia(id, placa) {
    document.getElementById('placaSalida').value = placa;
    ocultarSugerencias();
    prepararSalida(id);
}

function ocultarSugerencias() {
    const container = document.getElementById('sugerenciasSalida');
    if (container) container.style.display = 'none';
}

// ========================================
// MODAL ENTRADA
// ========================================
function abrirModal() {
    document.getElementById('modalEntrada').style.display = 'flex';
    inicializarFechas();
    limpiarFormularioEntrada();
    // Focus en placa
    setTimeout(() => document.getElementById('placa')?.focus(), 200);
}

function cerrarModal() {
    document.getElementById('modalEntrada').style.display = 'none';
}

function limpiarFormularioEntrada() {
    document.getElementById('placa').value = '';
    document.getElementById('cliente').value = '';
    document.getElementById('celular').value = '';
    document.getElementById('dias').value = '1';
    document.getElementById('precio').value = '10';
    document.getElementById('adelanto').value = '0';
    document.getElementById('observaciones').value = '';
    document.getElementById('dejoLlave').checked = false;
    document.getElementById('pagadoCompleto').checked = false;
    calcularMonto();
}

function calcularMonto() {
    const dias = parseInt(document.getElementById('dias').value) || 1;
    const precio = parseFloat(document.getElementById('precio').value) || 0;
    const monto = dias * precio;
    document.getElementById('montoTotal').value = 'S/ ' + monto.toFixed(2);
}

function togglePagoCompleto() {
    const pagado = document.getElementById('pagadoCompleto').checked;
    if (pagado) {
        const monto = parseFloat(document.getElementById('dias').value) * parseFloat(document.getElementById('precio').value);
        document.getElementById('adelanto').value = monto;
    } else {
        document.getElementById('adelanto').value = '0';
    }
}

function verHistorialPlaca() {
    const placa = document.getElementById('placa').value.trim().toUpperCase();
    if (placa) verHistorialCliente(placa);
}

async function guardarEntrada() {
    const placa = document.getElementById('placa').value.trim();
    const cliente = document.getElementById('cliente').value.trim();
    const precio = parseFloat(document.getElementById('precio').value);

    if (!placa) { mostrarToast('La placa es requerida', 'error'); return; }
    if (!cliente) { mostrarToast('El nombre del cliente es requerido', 'error'); return; }
    if (!precio || precio <= 0) { mostrarToast('El precio debe ser mayor a 0', 'error'); return; }

    const datos = {
        placa: placa,
        cliente: cliente,
        celular: document.getElementById('celular').value,
        fecha_entrada: document.getElementById('fechaEntrada').value,
        hora_entrada: document.getElementById('horaEntrada').value,
        fecha_hasta: document.getElementById('fechaHasta').value,
        hora_salida: document.getElementById('horaSalida').value,
        dias: parseInt(document.getElementById('dias').value) || 1,
        precio: precio,
        adelanto: parseFloat(document.getElementById('adelanto').value) || 0,
        metodo_pago: document.getElementById('metodoPago').value,
        dejo_llave: document.getElementById('dejoLlave').checked,
        pagado: document.getElementById('pagadoCompleto').checked,
        observaciones: document.getElementById('observaciones').value
    };

    try {
        const response = await fetch('/guardar_entrada', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datos)
        });
        const data = await response.json();

        if (data.ok) {
            mostrarToast('Entrada registrada exitosamente', 'exito');
            cerrarModal();
            cargarIngresos();
            window.open('/ticket_entrada/' + data.id, '_blank');
        } else {
            mostrarToast(data.error, 'error');
        }
    } catch (error) {
        mostrarToast('Error al guardar', 'error');
    }
}

// ========================================
// CARGAR INGRESOS DEL TURNO
// ========================================
async function cargarIngresos() {
    try {
        const response = await fetch('/ingresos_turno');
        const data = await response.json();

        const tbody = document.getElementById('tablaIngresos');

        if (!data.ingresos || data.ingresos.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="tabla-vacia">
                        <div class="empty-state">
                            <span class="empty-icon">📭</span>
                            <p>Sin movimientos en este turno</p>
                        </div>
                    </td>
                </tr>
            `;
        } else {
            tbody.innerHTML = '';
            data.ingresos.forEach(ing => {
                const tipoBadge = getTipoBadge(ing.tipo);
                const metodoBadge = ing.metodo_pago === 'yape'
                    ? '<span class="badge badge-yape"><img src="/static/img/yape.png" alt="Yape" class="yape-icon"></span>'
                    : '<span class="badge badge-efectivo">💵</span>';

                tbody.innerHTML += `
                    <tr>
                        <td>${ing.hora}</td>
                        <td>${tipoBadge}</td>
                        <td><strong>${ing.placa}</strong></td>
                        <td>${ing.cliente}</td>
                        <td class="monto">S/ ${ing.monto.toFixed(2)}</td>
                        <td>${metodoBadge}</td>
                        <td>
                            <button class="btn-icono" onclick="verDetalle(${ing.id})" title="Ver detalle">👁️</button>
                        </td>
                    </tr>
                `;
            });
        }

        document.getElementById('totalEfectivo').textContent = data.total_efectivo.toFixed(2);
        document.getElementById('totalYape').textContent = data.total_yape.toFixed(2);
        document.getElementById('totalTurno').textContent = data.total.toFixed(2);

        // Actualizar KPI cards en tiempo real
        const kpiTotal = document.getElementById('kpiTotalCaja');
        const kpiEfectivo = document.getElementById('kpiEfectivo');
        const kpiYape = document.getElementById('kpiYape');
        const kpiIngresados = document.getElementById('kpiIngresados');
        const kpiSalieron = document.getElementById('kpiSalieron');
        const kpiEnCochera = document.getElementById('kpiEnCochera');

        if (kpiTotal) kpiTotal.textContent = `S/ ${data.total.toFixed(2)}`;
        if (kpiEfectivo) kpiEfectivo.textContent = data.total_efectivo.toFixed(2);
        if (kpiYape) kpiYape.textContent = data.total_yape.toFixed(2);
        if (kpiIngresados) kpiIngresados.textContent = data.autos_ingresados;
        if (kpiSalieron) kpiSalieron.textContent = data.autos_salieron;
        if (kpiEnCochera) kpiEnCochera.textContent = data.autos_en_cochera;

    } catch (error) {
        console.error('Error cargando ingresos:', error);
    }
}

function getTipoBadge(tipo) {
    if (tipo.includes('ADELANTO')) return '<span class="badge badge-info">Adelanto</span>';
    if (tipo === 'PAGO_COMPLETO') return '<span class="badge badge-success">Pago Total</span>';
    if (tipo === 'COBRO_SALIDA') return '<span class="badge badge-success">Cobro</span>';
    if (tipo === 'PENALIDAD') return '<span class="badge badge-danger">Penalidad</span>';
    return `<span class="badge">${tipo}</span>`;
}

// ========================================
// AUTOS EN COCHERA
// ========================================
function abrirModalAutosEnCochera() {
    document.getElementById('modalAutosEnCochera').style.display = 'flex';
    cargarAutosEnCochera();
}

function cerrarModalAutosEnCochera() {
    document.getElementById('modalAutosEnCochera').style.display = 'none';
}

async function cargarAutosEnCochera() {
    try {
        const response = await fetch('/autos_en_cochera');
        const data = await response.json();
        if (!data.ok) throw new Error(data.error);

        autosEnCocheraData = data.autos;
        renderizarAutosEnCochera(data.autos);
        document.getElementById('contadorAutos').textContent = data.total + ' autos';
    } catch (error) {
        mostrarToast('Error cargando autos', 'error');
    }
}

function renderizarAutosEnCochera(autos) {
    const tbody = document.getElementById('tablaAutosEnCochera');

    if (!autos || autos.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="7" class="tabla-vacia">
                <div class="empty-state">
                    <span class="empty-icon">🅿️</span>
                    <p>No hay autos en la cochera</p>
                </div>
            </td></tr>
        `;
        return;
    }

    tbody.innerHTML = autos.map(auto => {
        const estadoBadge = auto.excede_tiempo
            ? '<span class="badge badge-danger">Excede</span>'
            : (auto.pago_completo_adelantado
                ? '<span class="badge badge-success">Pagado</span>'
                : '<span class="badge badge-info">Normal</span>');

        return `
            <tr class="${auto.excede_tiempo ? 'fila-excedida' : ''}">
                <td><strong>${auto.placa}</strong></td>
                <td>${auto.cliente}</td>
                <td class="fecha-col">${auto.fecha_entrada} ${auto.hora_entrada || ''}</td>
                <td><span class="badge ${auto.dias_reales > auto.dias_pactados ? 'badge-danger' : 'badge-info'}">${auto.dias_reales} / ${auto.dias_pactados}</span></td>
                <td class="monto">S/ ${auto.pendiente.toFixed(2)}</td>
                <td>${estadoBadge}</td>
                <td class="acciones-col">
                    <button class="btn-icono btn-cobrar" onclick="prepararSalida(${auto.id})" title="Cobrar salida">💰</button>
                    <button class="btn-icono" onclick="verHistorialCliente('${auto.placa}')" title="Ver historial">📋</button>
                </td>
            </tr>
        `;
    }).join('');
}

function filtrarAutosEnCochera() {
    const filtro = document.getElementById('buscarAutoEnCochera').value.toLowerCase();
    const filtrados = autosEnCocheraData.filter(auto =>
        auto.placa.toLowerCase().includes(filtro) ||
        auto.cliente.toLowerCase().includes(filtro)
    );
    renderizarAutosEnCochera(filtrados);
}

// ========================================
// SALIDA Y COBRO
// ========================================
function abrirModalSalidaCobro() {
    document.getElementById('modalSalidaCobro').style.display = 'flex';
    document.getElementById('placaSalida').value = '';
    document.getElementById('infoSalida').style.display = 'none';
    document.getElementById('btnRegistrarSalida').style.display = 'none';
    ocultarSugerencias();
    setTimeout(() => document.getElementById('placaSalida')?.focus(), 200);
}

function cerrarModalSalidaCobro() {
    document.getElementById('modalSalidaCobro').style.display = 'none';
    ocultarSugerencias();
}

async function buscarParaSalida() {
    const placa = document.getElementById('placaSalida').value.trim().toUpperCase();
    if (!placa) { mostrarToast('Ingrese una placa', 'error'); return; }

    ocultarSugerencias();

    try {
        const response = await fetch('/autos_en_cochera');
        const data = await response.json();
        const auto = data.autos.find(a => a.placa === placa);

        if (!auto) {
            mostrarToast('Vehiculo no encontrado en cochera', 'error');
            return;
        }
        prepararSalida(auto.id);
    } catch (error) {
        mostrarToast('Error buscando vehiculo', 'error');
    }
}

async function prepararSalida(id) {
    try {
        const response = await fetch(`/calcular_cobro/${id}`);
        const data = await response.json();
        if (!data.ok) throw new Error(data.error);

        document.getElementById('modalSalidaCobro').style.display = 'flex';

        document.getElementById('salidaEntradaId').value = data.id;
        document.getElementById('placaSalida').value = data.placa;
        document.getElementById('salidaPlaca').textContent = data.placa;
        document.getElementById('salidaCliente').textContent = data.cliente;
        document.getElementById('salidaCelular').textContent = data.celular || '-';
        document.getElementById('salidaFechaEntrada').textContent = data.fecha_entrada + ' ' + (data.hora_entrada || '');
        document.getElementById('salidaFechaHasta').textContent = data.fecha_hasta || '-';
        document.getElementById('salidaDiasPactados').textContent = data.dias_pactados;
        document.getElementById('salidaDiasReales').textContent = data.dias_reales;
        document.getElementById('salidaPrecioDia').textContent = 'S/ ' + data.precio_dia.toFixed(2);
        document.getElementById('salidaMontoDias').textContent = 'S/ ' + data.monto_dias.toFixed(2);

        // Highlight si excede dias
        const diasRealesEl = document.getElementById('salidaDiasReales');
        if (data.dias_reales > data.dias_pactados) {
            diasRealesEl.classList.add('texto-danger');
            diasRealesEl.classList.remove('texto-exito');
        } else {
            diasRealesEl.classList.add('texto-exito');
            diasRealesEl.classList.remove('texto-danger');
        }

        // Calculos
        document.getElementById('calcMontoDias').textContent = 'S/ ' + data.monto_dias.toFixed(2);
        document.getElementById('calcAdelanto').textContent = '- S/ ' + data.adelanto.toFixed(2);
        document.getElementById('salidaPenalidad').value = data.penalidad.toFixed(2);
        document.getElementById('salidaDescuento').value = '0';
        document.getElementById('calcTotalCobrar').textContent = 'S/ ' + data.a_cobrar.toFixed(2);

        // Ya pago completo
        const pagoBadge = document.getElementById('salidaPagoBadge');
        if (pagoBadge) {
            if (data.ya_pago_completo) {
                pagoBadge.innerHTML = '<span class="badge badge-success">Pago completo adelantado</span>';
            } else if (data.adelanto > 0) {
                pagoBadge.innerHTML = '<span class="badge badge-info">Adelanto: S/ ' + data.adelanto.toFixed(2) + '</span>';
            } else {
                pagoBadge.innerHTML = '<span class="badge badge-warning">Sin adelanto</span>';
            }
        }

        // Guardar datos para recalcular
        const info = document.getElementById('infoSalida');
        info.dataset.montoDias = data.monto_dias;
        info.dataset.adelanto = data.adelanto;
        info.dataset.diasReales = data.dias_reales;
        info.dataset.yaPagoCompleto = data.ya_pago_completo;

        info.style.display = 'block';
        document.getElementById('btnRegistrarSalida').style.display = 'inline-flex';

        ocultarSugerencias();

    } catch (error) {
        mostrarToast(error.message, 'error');
    }
}

function recalcularCobro() {
    const info = document.getElementById('infoSalida');
    const montoDias = parseFloat(info.dataset.montoDias) || 0;
    const adelanto = parseFloat(info.dataset.adelanto) || 0;
    const penalidad = parseFloat(document.getElementById('salidaPenalidad').value) || 0;
    const descuento = parseFloat(document.getElementById('salidaDescuento').value) || 0;
    const yaPagoCompleto = info.dataset.yaPagoCompleto === 'true';

    let total;
    if (yaPagoCompleto) {
        total = Math.max(0, penalidad - descuento);
    } else {
        total = Math.max(0, montoDias + penalidad - descuento - adelanto);
    }

    const elem = document.getElementById('calcTotalCobrar');
    elem.textContent = 'S/ ' + total.toFixed(2);

    // Animar el cambio
    elem.classList.add('animate-pulse-once');
    setTimeout(() => elem.classList.remove('animate-pulse-once'), 300);
}

async function registrarSalida() {
    const id = document.getElementById('salidaEntradaId').value;
    const info = document.getElementById('infoSalida');

    const datos = {
        id: parseInt(id),
        dias_reales: parseInt(info.dataset.diasReales),
        penalidad: parseFloat(document.getElementById('salidaPenalidad').value) || 0,
        descuento: parseFloat(document.getElementById('salidaDescuento').value) || 0,
        metodo_pago: document.getElementById('salidaMetodoPago').value,
        observaciones: document.getElementById('salidaObservaciones').value
    };

    try {
        const response = await fetch('/registrar_salida', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datos)
        });
        const data = await response.json();

        if (data.ok) {
            mostrarToast('Salida registrada exitosamente', 'exito');
            cerrarModalSalidaCobro();
            cerrarModalAutosEnCochera();
            cargarIngresos();
        } else {
            mostrarToast(data.error, 'error');
        }
    } catch (error) {
        mostrarToast('Error al registrar salida', 'error');
    }
}

// ========================================
// HISTORIAL
// ========================================
function abrirModalHistorialGeneral() {
    document.getElementById('modalHistorialGeneral').style.display = 'flex';
    // Auto-buscar al abrir
    buscarHistorialPaginado(1);
}

function cerrarModalHistorialGeneral() {
    document.getElementById('modalHistorialGeneral').style.display = 'none';
}

async function buscarHistorial() {
    buscarHistorialPaginado(1);
}

async function buscarHistorialPaginado(pagina) {
    historialPaginaActual = pagina || 1;

    const placa = document.getElementById('filtroPlaca').value;
    const fechaDesde = document.getElementById('filtroFechaDesde').value;
    const fechaHasta = document.getElementById('filtroFechaHasta').value;
    const estado = document.getElementById('filtroEstado').value;

    const params = new URLSearchParams();
    if (placa) params.append('placa', placa);
    if (fechaDesde) params.append('fecha_desde', fechaDesde);
    if (fechaHasta) params.append('fecha_hasta', fechaHasta);
    if (estado) params.append('estado', estado);
    params.append('pagina', historialPaginaActual);
    params.append('por_pagina', 30);

    try {
        const response = await fetch('/admin/historial_vehiculos?' + params.toString());
        const data = await response.json();
        if (!data.ok) throw new Error(data.error);

        renderizarHistorial(data.historial);
        renderizarPaginacion(data);
    } catch (error) {
        mostrarToast('Error cargando historial', 'error');
    }
}

function renderizarHistorial(historial) {
    const tbody = document.getElementById('tablaHistorial');

    if (!historial || historial.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="tabla-vacia">
            <div class="empty-state"><span class="empty-icon">📋</span><p>Sin resultados</p></div>
        </td></tr>`;
        return;
    }

    tbody.innerHTML = historial.map(h => {
        const estadoBadge = h.salio
            ? '<span class="badge badge-success">Salio</span>'
            : '<span class="badge badge-warning">En cochera</span>';
        const pagoBadge = h.pago_completo
            ? '<span class="badge badge-success">Pagado</span>'
            : (h.adelanto > 0 ? '<span class="badge badge-info">Adelanto</span>' : '');

        return `
            <tr>
                <td><strong>${h.placa}</strong></td>
                <td>${h.cliente}</td>
                <td class="fecha-col">${h.fecha_entrada}</td>
                <td class="fecha-col">${h.fecha_salida || '-'}</td>
                <td>${h.dias_reales || h.dias}</td>
                <td class="monto">S/ ${(h.monto || 0).toFixed(2)}</td>
                <td>${estadoBadge} ${pagoBadge}</td>
                <td><button class="btn-icono" onclick="verHistorialCliente('${h.placa}')" title="Ver historial cliente">📋</button></td>
            </tr>
        `;
    }).join('');
}

function renderizarPaginacion(data) {
    const container = document.getElementById('paginacionHistorial');
    if (!container || data.total_paginas <= 1) {
        if (container) container.innerHTML = `<small class="texto-muted">${data.total} registros</small>`;
        return;
    }

    let html = '';
    if (data.pagina > 1) {
        html += `<button class="btn-mini" onclick="buscarHistorialPaginado(${data.pagina - 1})">◀</button>`;
    }

    const start = Math.max(1, data.pagina - 2);
    const end = Math.min(data.total_paginas, data.pagina + 2);

    for (let i = start; i <= end; i++) {
        const active = i === data.pagina ? 'btn-primario' : '';
        html += `<button class="btn-mini ${active}" onclick="buscarHistorialPaginado(${i})">${i}</button>`;
    }

    if (data.pagina < data.total_paginas) {
        html += `<button class="btn-mini" onclick="buscarHistorialPaginado(${data.pagina + 1})">▶</button>`;
    }
    html += `<small class="texto-muted" style="margin-left:12px;">${data.total} registros</small>`;
    container.innerHTML = html;
}

function exportarHistorial() {
    const placa = document.getElementById('filtroPlaca').value;
    const fechaDesde = document.getElementById('filtroFechaDesde').value;
    const fechaHasta = document.getElementById('filtroFechaHasta').value;
    const estado = document.getElementById('filtroEstado').value;

    const params = new URLSearchParams();
    if (placa) params.append('placa', placa);
    if (fechaDesde) params.append('fecha_desde', fechaDesde);
    if (fechaHasta) params.append('fecha_hasta', fechaHasta);
    if (estado) params.append('estado', estado);

    window.open('/admin/exportar_historial?' + params.toString(), '_blank');
}

// ========================================
// HISTORIAL CLIENTE
// ========================================
async function verHistorialCliente(placa) {
    try {
        const response = await fetch(`/historial_cliente/${placa}`);
        const data = await response.json();

        if (!data.ok) { mostrarToast(data.error, 'error'); return; }

        document.getElementById('modalHistorialCliente').style.display = 'flex';

        document.getElementById('histClienteNombre').textContent = data.cliente.nombre;
        document.getElementById('histClientePlaca').textContent = data.cliente.placa;
        document.getElementById('histClienteCelular').textContent = data.cliente.celular || '-';

        document.getElementById('histClienteVisitas').textContent = data.estadisticas.total_visitas;
        document.getElementById('histClienteGastado').textContent = 'S/ ' + (data.estadisticas.total_gastado || 0).toFixed(2);
        document.getElementById('histClientePromedio').textContent = Math.round(data.estadisticas.promedio_dias || 0);
        document.getElementById('histClienteDeuda').textContent = 'S/ ' + (data.estadisticas.deuda_actual || 0).toFixed(2);

        const tbody = document.getElementById('tablaHistorialCliente');

        if (data.visitas.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="tabla-vacia">Sin historial</td></tr>';
            return;
        }

        tbody.innerHTML = data.visitas.map(v => {
            let estado;
            if (v.salio && v.pagado) estado = '<span class="badge badge-success">Pagado</span>';
            else if (v.pago_completo_adelantado) estado = '<span class="badge badge-info">Pagado adel.</span>';
            else if (!v.salio) estado = '<span class="badge badge-warning">En cochera</span>';
            else estado = '<span class="badge badge-danger">Pendiente</span>';

            return `
                <tr>
                    <td class="fecha-col">${v.fecha_entrada}</td>
                    <td>${v.dias}</td>
                    <td class="monto">S/ ${(v.monto || 0).toFixed(2)}</td>
                    <td>S/ ${(v.adelanto || 0).toFixed(2)}</td>
                    <td>${estado}</td>
                    <td><small>${v.trabajador_entrada || '-'}</small></td>
                </tr>
            `;
        }).join('');

    } catch (error) {
        mostrarToast('Error al cargar historial', 'error');
    }
}

function cerrarModalHistorialCliente() {
    document.getElementById('modalHistorialCliente').style.display = 'none';
}

// ========================================
// ALERTAS
// ========================================
async function cargarAlertas() {
    try {
        const response = await fetch('/obtener_alertas');
        const data = await response.json();
        if (!data.ok) return;

        const seccion = document.getElementById('seccionAlertas');
        const contador = document.getElementById('contadorAlertas');
        const lista = document.getElementById('listaAlertas');

        if (data.alertas.length === 0) { seccion.style.display = 'none'; return; }

        seccion.style.display = 'block';
        contador.textContent = data.alertas.length;

        lista.innerHTML = data.alertas.map(a => `
            <div class="alerta-item alerta-${a.nivel}">
                <div class="alerta-contenido">
                    <strong>${a.titulo}</strong>
                    <small>${a.mensaje}</small>
                </div>
                ${a.placa ? `<button class="btn btn-mini" onclick="verHistorialCliente('${a.placa}')">Ver</button>` : ''}
            </div>
        `).join('');
    } catch (error) {
        console.error('Error alertas:', error);
    }
}

function toggleAlertas() {
    const lista = document.getElementById('listaAlertas');
    const icono = document.getElementById('iconoAlertas');
    if (lista.style.display === 'none') {
        lista.style.display = 'block';
        icono.textContent = '▲';
    } else {
        lista.style.display = 'none';
        icono.textContent = '▼';
    }
}

// ========================================
// CERRAR TURNO
// ========================================
function abrirModalCerrarTurno() {
    document.getElementById('modalCerrarTurno').style.display = 'flex';
    document.getElementById('resumenCierre').style.display = 'none';
    document.getElementById('btnConfirmarCierre').style.display = 'none';
    document.getElementById('btnCalcularCierre').style.display = 'inline-flex';
    document.getElementById('efectivoDeclarado').value = '';
    document.getElementById('yapeDeclarado').value = '';
}

function cerrarModalCerrarTurno() {
    document.getElementById('modalCerrarTurno').style.display = 'none';
}

function formatearDif(elem, dif) {
    if (dif > 0) {
        elem.className = 'texto-exito';
        elem.textContent = `+ S/ ${dif.toFixed(2)} (Sobrante)`;
    } else if (dif < 0) {
        elem.className = 'texto-danger';
        elem.textContent = `- S/ ${Math.abs(dif).toFixed(2)} (Faltante)`;
    } else {
        elem.className = 'texto-exito';
        elem.textContent = 'S/ 0.00 (Cuadrado)';
    }
}

async function calcularCierre() {
    const efectivo = parseFloat(document.getElementById('efectivoDeclarado').value);
    const yape = parseFloat(document.getElementById('yapeDeclarado').value);
    if (isNaN(efectivo) || efectivo < 0) { mostrarToast('Ingresa un monto de efectivo válido', 'error'); return; }
    if (isNaN(yape) || yape < 0) { mostrarToast('Ingresa un monto de Yape válido', 'error'); return; }

    try {
        const response = await fetch('/cerrar_turno', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ efectivo_declarado: efectivo, yape_declarado: yape, solo_calcular: true })
        });
        const data = await response.json();
        if (!data.ok) throw new Error(data.error);

        document.getElementById('cierreAutosIngresados').textContent = data.autos_ingresados;
        document.getElementById('cierreAutosSalieron').textContent = data.autos_salieron;
        document.getElementById('cierreTotalEfectivo').textContent = data.total_efectivo.toFixed(2);
        document.getElementById('cierreEfectivoDeclarado').textContent = efectivo.toFixed(2);
        document.getElementById('cierreTotalYape').textContent = data.total_yape.toFixed(2);
        document.getElementById('cierreYapeDeclarado').textContent = yape.toFixed(2);

        formatearDif(document.getElementById('cierreDifEfectivo'), data.dif_efectivo);
        formatearDif(document.getElementById('cierreDifYape'), data.dif_yape);
        formatearDif(document.getElementById('cierreDiferencia'), data.diferencia);

        document.getElementById('resumenCierre').style.display = 'block';
        document.getElementById('btnCalcularCierre').style.display = 'none';
        document.getElementById('btnConfirmarCierre').style.display = 'inline-flex';
    } catch (error) {
        mostrarToast(error.message, 'error');
    }
}

async function confirmarCierreTurno() {
    if (!confirm('Cerrar turno? Esta accion cerrara tu sesion.')) return;
    const efectivo = parseFloat(document.getElementById('efectivoDeclarado').value);
    const yape = parseFloat(document.getElementById('yapeDeclarado').value);

    try {
        const response = await fetch('/cerrar_turno', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                efectivo_declarado: efectivo,
                yape_declarado: yape,
                observaciones: document.getElementById('observacionesCierre').value
            })
        });
        const data = await response.json();
        if (!data.ok) throw new Error(data.error);

        // Abrir reporte con turno_id (funciona aunque la sesión se cierre)
        window.open(`/reporte_turno/${data.turno_id}`, '_blank');
        mostrarToast('Turno cerrado. Imprime tu reporte antes de salir.', 'exito');
        setTimeout(() => { window.location.href = '/logout'; }, 5000);
    } catch (error) {
        mostrarToast(error.message, 'error');
    }
}

// ========================================
// VER DETALLE MOVIMIENTO
// ========================================
async function verDetalle(id) {
    try {
        const response = await fetch(`/admin/detalle_movimiento/${id}`);
        const data = await response.json();
        if (!data.ok) throw new Error(data.error);

        const m = data.movimiento;

        // Construir el contenido del modal dinamicamente
        const body = document.getElementById('detalleMovBody');

        const val = (v, prefix) => {
            if (v === null || v === undefined || v === '') return '-';
            if (prefix) return prefix + ' ' + parseFloat(v).toFixed(2);
            return v;
        };

        body.innerHTML = `
            <div class="detalle-card-grid">
                <div class="detalle-card">
                    <div class="detalle-card-header">
                        <span class="detalle-card-icon">🚗</span>
                        <h4>Vehiculo</h4>
                    </div>
                    <div class="detalle-card-body">
                        <div class="detalle-row">
                            <span class="detalle-label">Placa</span>
                            <span class="detalle-valor destacado">${val(m.placa)}</span>
                        </div>
                        <div class="detalle-row">
                            <span class="detalle-label">Cliente</span>
                            <span class="detalle-valor">${val(m.cliente)}</span>
                        </div>
                        <div class="detalle-row">
                            <span class="detalle-label">Celular</span>
                            <span class="detalle-valor">${val(m.celular)}</span>
                        </div>
                    </div>
                </div>
                <div class="detalle-card">
                    <div class="detalle-card-header">
                        <span class="detalle-card-icon">📅</span>
                        <h4>Fechas</h4>
                    </div>
                    <div class="detalle-card-body">
                        <div class="detalle-row">
                            <span class="detalle-label">Entrada</span>
                            <span class="detalle-valor">${val(m.fecha_entrada)} ${val(m.hora_entrada)}</span>
                        </div>
                        <div class="detalle-row">
                            <span class="detalle-label">Salida</span>
                            <span class="detalle-valor">${val(m.fecha_salida)} ${val(m.hora_salida_real)}</span>
                        </div>
                        <div class="detalle-row">
                            <span class="detalle-label">Dias</span>
                            <span class="detalle-valor">${val(m.dias)}</span>
                        </div>
                    </div>
                </div>
                <div class="detalle-card">
                    <div class="detalle-card-header">
                        <span class="detalle-card-icon">💰</span>
                        <h4>Montos</h4>
                    </div>
                    <div class="detalle-card-body">
                        <div class="detalle-row">
                            <span class="detalle-label">Precio/dia</span>
                            <span class="detalle-valor">${val(m.precio_dia, 'S/')}</span>
                        </div>
                        <div class="detalle-row">
                            <span class="detalle-label">Monto total</span>
                            <span class="detalle-valor destacado">${val(m.monto_total, 'S/')}</span>
                        </div>
                        <div class="detalle-row">
                            <span class="detalle-label">Adelanto</span>
                            <span class="detalle-valor texto-info">${val(m.adelanto, 'S/')}</span>
                        </div>
                        <div class="detalle-row">
                            <span class="detalle-label">Penalidad</span>
                            <span class="detalle-valor ${m.penalidad > 0 ? 'texto-danger' : ''}">${val(m.penalidad, 'S/')}</span>
                        </div>
                        <div class="detalle-row">
                            <span class="detalle-label">Descuento</span>
                            <span class="detalle-valor ${m.descuento > 0 ? 'texto-exito' : ''}">${val(m.descuento, 'S/')}</span>
                        </div>
                    </div>
                </div>
                <div class="detalle-card">
                    <div class="detalle-card-header">
                        <span class="detalle-card-icon">👤</span>
                        <h4>Trabajadores</h4>
                    </div>
                    <div class="detalle-card-body">
                        <div class="detalle-row">
                            <span class="detalle-label">Entrada</span>
                            <span class="detalle-valor">${val(m.trabajador_entrada)}</span>
                        </div>
                        <div class="detalle-row">
                            <span class="detalle-label">Salida</span>
                            <span class="detalle-valor">${val(m.trabajador_salida)}</span>
                        </div>
                        <div class="detalle-row">
                            <span class="detalle-label">Movimiento</span>
                            <span class="detalle-valor">${val(m.trabajador_movimiento)}</span>
                        </div>
                    </div>
                </div>
            </div>
            ${m.observaciones ? `
            <div class="detalle-obs">
                <strong>Observaciones:</strong> ${m.observaciones}
            </div>` : ''}
            ${m.pago_completo_adelantado ? '<div class="detalle-badge-full"><span class="badge badge-success">Pago completo adelantado</span></div>' : ''}
        `;

        document.getElementById('modalDetalleMovimiento').style.display = 'flex';

    } catch (error) {
        mostrarToast('Error cargando detalle', 'error');
    }
}

function cerrarModalDetalle() {
    document.getElementById('modalDetalleMovimiento').style.display = 'none';
}

// ========================================
// MIS REPORTES
// ========================================
let misReportesPagina = 1;

function abrirModalMisReportes() {
    document.getElementById('modal-mis-reportes').style.display = 'flex';
    document.getElementById('mis-reportes-detalle').style.display = 'none';
}

function cerrarModalMisReportes() {
    document.getElementById('modal-mis-reportes').style.display = 'none';
}

function buscarMisReportes(pagina) {
    misReportesPagina = pagina || 1;
    const params = new URLSearchParams({
        fecha_desde: document.getElementById('mis-reportes-desde').value,
        fecha_hasta: document.getElementById('mis-reportes-hasta').value,
        pagina: misReportesPagina,
        por_pagina: 15
    });

    fetch('/mis_reportes?' + params)
        .then(r => r.json())
        .then(data => {
            if (!data.ok) return;
            const tbody = document.getElementById('tbody-mis-reportes');
            document.getElementById('mis-reportes-detalle').style.display = 'none';

            if (!data.turnos.length) {
                tbody.innerHTML = '<tr><td colspan="8" class="tabla-vacia"><div class="empty-state"><span class="empty-icon">📋</span><p>No se encontraron turnos</p></div></td></tr>';
                document.getElementById('paginacion-mis-reportes').innerHTML = '';
                return;
            }

            tbody.innerHTML = data.turnos.map(t => {
                const dif = parseFloat(t.diferencia || 0);
                const difClass = dif < 0 ? 'texto-danger' : dif > 0 ? 'texto-warning' : 'texto-exito';
                const estado = t.estado === 'cerrado'
                    ? '<span class="badge badge-success">Cerrado</span>'
                    : '<span class="badge badge-warning">Abierto</span>';
                const inicio = t.fecha_inicio ? t.fecha_inicio.replace('T',' ').substring(0,16) : '-';
                const fin = t.fecha_fin ? t.fecha_fin.replace('T',' ').substring(0,16) : '-';

                return `
                <tr>
                    <td class="fecha-col">${inicio}</td>
                    <td class="fecha-col">${fin}</td>
                    <td>S/ ${parseFloat(t.total_efectivo).toFixed(2)}</td>
                    <td>S/ ${parseFloat(t.total_yape).toFixed(2)}</td>
                    <td><strong>S/ ${parseFloat(t.total).toFixed(2)}</strong></td>
                    <td class="${difClass}">${t.efectivo_declarado != null ? 'S/ ' + dif.toFixed(2) : '-'}</td>
                    <td>${estado}</td>
                    <td><button class="btn-icon btn-sm" onclick="verMiTurnoDetalle(${t.id})" title="Ver detalle">🔍</button></td>
                </tr>`;
            }).join('');

            let pagHtml = '';
            if (data.total_paginas > 1) {
                for (let i = 1; i <= data.total_paginas; i++) {
                    pagHtml += `<button class="btn-sm ${i === data.pagina ? 'btn-primary' : 'btn-secondary'}" onclick="buscarMisReportes(${i})">${i}</button> `;
                }
            }
            pagHtml += `<span style="margin-left:0.5rem;opacity:0.7;">Total: ${data.total}</span>`;
            document.getElementById('paginacion-mis-reportes').innerHTML = pagHtml;
        });
}

function verMiTurnoDetalle(turnoId) {
    const container = document.getElementById('mis-reportes-detalle');
    const body = document.getElementById('mis-reportes-detalle-body');
    container.style.display = 'block';
    body.innerHTML = '<p>Cargando...</p>';

    fetch('/detalle_mi_turno/' + turnoId)
        .then(r => r.json())
        .then(data => {
            if (!data.ok) {
                body.innerHTML = '<p>Error al cargar</p>';
                return;
            }

            const t = data.turno;
            const total = parseFloat(t.total_efectivo || 0) + parseFloat(t.total_yape || 0);

            let html = `
            <div class="mini-stats-row">
                <div class="mini-stat"><span class="mini-stat-label">Efectivo</span><span>S/ ${parseFloat(t.total_efectivo||0).toFixed(2)}</span></div>
                <div class="mini-stat"><span class="mini-stat-label">Yape</span><span>S/ ${parseFloat(t.total_yape||0).toFixed(2)}</span></div>
                <div class="mini-stat total"><span class="mini-stat-label">Total</span><span>S/ ${total.toFixed(2)}</span></div>
            </div>`;

            if (data.movimientos.length) {
                html += `<table class="tabla-moderna" style="margin-top:0.75rem;">
                    <thead><tr><th>Hora</th><th>Tipo</th><th>Placa</th><th>Monto</th><th>Pago</th></tr></thead><tbody>`;
                data.movimientos.forEach(m => {
                    html += `<tr>
                        <td class="fecha-col">${m.fecha_movimiento || '-'}</td>
                        <td><span class="badge badge-info">${m.tipo}</span></td>
                        <td><strong>${m.placa || '-'}</strong></td>
                        <td>S/ ${parseFloat(m.monto).toFixed(2)}</td>
                        <td><span class="badge badge-${m.metodo_pago === 'yape' ? 'yape' : 'efectivo'}">${m.metodo_pago}</span></td>
                    </tr>`;
                });
                html += '</tbody></table>';
            } else {
                html += '<p style="opacity:0.6;margin-top:0.5rem;">Sin movimientos en este turno</p>';
            }

            body.innerHTML = html;
        });
}
