document.addEventListener('DOMContentLoaded', () => {
  const appContainer = document.getElementById('main-app');
  appContainer.innerHTML = document.getElementById('template-main-app').innerHTML;

  document.body.addEventListener('click', handleGlobalClick);
  document.body.addEventListener('change', handleGlobalChange);
  document.body.addEventListener('blur', handleGlobalBlur, true);
  document.body.addEventListener('input', handleGlobalInput);

  document.getElementById('view-evaluacion').style.display = 'block';
  const workflowContainer = document.getElementById('workflows-container');
  workflowContainer.innerHTML = document.getElementById('template-workflow-escaneado').innerHTML;
  const configContainer = document.getElementById('config-container-escaneado');
  configContainer.innerHTML = document.getElementById('template-configuracion-evaluacion').innerHTML;
  setupDragDrop('dropZoneEscaneado', 'archivosEscaneados', handleScannedFiles);

  appState.historial = JSON.parse(localStorage.getItem('historialEvaluaciones_v33')) || [];
  appState.nameCorrections = JSON.parse(localStorage.getItem('nameCorrections_v5')) || {};
});

function handleGlobalClick(e) {
  const target = e.target.closest('[data-action]');
  if (!target) return;
  const action = target.dataset.action;
  const params = target.dataset;
  const actions = {
    'switch-main-view': () => switchMainView(params.view),
    'show-workflow': () => mostrarWorkflow(params.workflow),
    'evaluate-scanned': iniciarEvaluacionEscaneada,
    'open-camera-modal': abrirModalCamara,
    'close-camera-modal': cerrarModalCamara,
    'capture-photo': capturarFoto,
    'confirmar-lote': confirmarLote,
    'ai-rubric-assistant': AIRubricAssistant,
    'copy-selection': () => mostrarDatosParaCopiar(true),
    'download-all-csv': exportarHistorialCSV,
    'copy-from-modal': copiarDatosDelModal,
    'select-all-history': () => selectAllHistory(target.checked),
    'clear-history': limpiarHistorial,
    'close-modal': () => document.getElementById(params.target).style.display = 'none',
    'ver-feedback': () => verFeedbackDetallado(params.id),
    'sort-history': () => sortHistory(params.sort),
    'switch-feedback-tab': switchFeedbackView,
    'add-decimas': () => abrirModalDecimas(params.id),
    'save-decimas': guardarDecimas
  };
  if (actions[action]) actions[action]();
}

function setupDragDrop(dropZoneId, fileInputId, handler) {
  const dropZone = document.getElementById(dropZoneId);
  const fileInput = document.getElementById(fileInputId);
  if (!dropZone || !fileInput) return;
  dropZone.onclick = () => fileInput.click();
  dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.style.borderColor = 'var(--primary)';
  });
  dropZone.addEventListener('dragleave', () => dropZone.style.borderColor = '#dee2e6');
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.style.borderColor = '#dee2e6';
    if (e.dataTransfer.files.length) {
      fileInput.files = e.dataTransfer.files;
      handler({ target: fileInput });
    }
  });
  fileInput.addEventListener('change', handler);
}

async function handleScannedFiles(event) {
  const newFiles = Array.from(event.target.files);
  appState.loteEscaneado.files.push(...newFiles);
  await renderizarPreviews();
  abrirModalConfirmacion(appState.loteEscaneado.files);
}

async function renderizarPreviews() {
  const previewContainer = document.getElementById('previewContainerEscaneado');
  previewContainer.innerHTML = 'Cargando vistas previas...';
  const previewPromises = appState.loteEscaneado.files.map(async file => {
    const item = document.createElement('div');
    item.className = 'preview-item';
    const icon = file.type.startsWith("image/") ? `<img src="${await readFileAsDataURL(file)}" alt="${file.name}">` : `<div>📄</div>`;
    item.innerHTML = `${icon}<div>${file.name}</div>`;
    return item;
  });
  const previewElements = await Promise.all(previewPromises);
  previewContainer.innerHTML = '';
  previewElements.forEach(el => previewContainer.appendChild(el));
}

function abrirModalConfirmacion(files) {
  const modal = document.getElementById('lote-confirm-modal');
  const totalFilesEl = document.getElementById('lote-total-files');
  const archivosPorEstudianteEl = document.getElementById('lote-archivos-por-estudiante');
  const totalEstudiantesEl = document.getElementById('lote-total-estudiantes');
  totalFilesEl.textContent = files.length;
  const updateTotalEstudiantes = () => {
    const archivosPor = parseInt(archivosPorEstudianteEl.value);
    if (archivosPor > 0 && files.length > 0) totalEstudiantesEl.value = Math.max(1, Math.round(files.length / archivosPor));
  };
  archivosPorEstudianteEl.oninput = updateTotalEstudiantes;
  updateTotalEstudiantes();
  modal.style.display = 'block';
}

function confirmarLote() {
  const archivosPorEstudiante = parseInt(document.getElementById('lote-archivos-por-estudiante').value);
  document.getElementById('lote-confirm-modal').style.display = 'none';
  procesarArchivosEscaneados(appState.loteEscaneado.files, archivosPorEstudiante);
}

async function procesarArchivosEscaneados(files, archivosPorEstudiante) {
  const revisionContainer = document.getElementById('revision-container');
  revisionContainer.innerHTML = `<h3>6. Revisión y Preparación</h3><p>Define el contexto para cada estudiante y corrige el material extraído antes de evaluar.</p>`;
  const grupos = [];
  for (let i = 0; i < files.length; i += archivosPorEstudiante) {
    grupos.push(files.slice(i, i + archivosPorEstudiante));
  }
  for (const [i, grupo] of grupos.entries()) {
    const studentId = `estudiante-lote-${Date.now() + i}`;
    const fileNames = grupo.map(f => f.name).join(', ');
    const placeholderDiv = document.createElement('div');
    placeholderDiv.className = 'section';
    placeholderDiv.innerHTML = `
      <h4>Estudiante ${i + 1} <small>(${fileNames})</small></h4>
      <div class="config-grid">
        <div>
          <label for="nombre-${studentId}"><strong>Nombre del Estudiante:</strong></label>
          <input type="text" id="nombre-${studentId}" placeholder="Extrayendo nombre...">
        </div>
        <div>
          <label for="contexto-${studentId}"><strong>Contexto de la Evaluación:</strong></label>
          <select id="contexto-${studentId}">
            <option value="Prueba / Trabajo Escrito">Prueba / Trabajo Escrito</option>
            <option value="Obra de Arte / Proyecto Visual">Obra de Arte / Proyecto Visual</option>
            <option value="Mapa Mental / Conceptual">Mapa Mental / Conceptual</option>
            <option value="Infografía / Diagrama">Infografía / Diagrama</option>
            <option value="Ejercicio Matemático / Científico">Ejercicio Matemático / Científico</option>
          </select>
        </div>
      </div>
      <label for="texto-${studentId}"><strong>Texto Extraído (Editable):</strong></label>
      <textarea id="texto-${studentId}" rows="6" disabled>⚙️ Procesando archivos, por favor espera...</textarea>
    `;
    revisionContainer.appendChild(placeholderDiv);
    let textoCompleto = '';
    for (const file of grupo) {
      try {
        const textoExtraido = await leerTextoDeArchivo(file);
        textoCompleto += `--- INICIO ${file.name} ---\n${textoExtraido}\n--- FIN ${file.name} ---\n`;
      } catch (e) {
        textoCompleto += `[ERROR LEYENDO ${file.name}: ${e.message}]\n`;
      }
    }
    const textoParaExtraerNombre = textoCompleto || ' ';
    const nombreExtraido = await extraerNombreConIA(textoParaExtraerNombre).catch(() => '');
    const nombreInput = document.getElementById(`nombre-${studentId}`);
    nombreInput.value = nombreExtraido;
    const textoTextarea = document.getElementById(`texto-${studentId}`);
    textoTextarea.value = textoCompleto.trim();
    textoTextarea.disabled = false;
    appState.loteEscaneado.studentData.push({
      id: studentId,
      nombreInputId: `nombre-${studentId}`,
      textoTextareaId: `texto-${studentId}`,
      contextoSelectId: `contexto-${studentId}`
    });
  }
}

async function iniciarEvaluacionEscaneada() {
  const btn = document.querySelector(`[data-action="evaluate-scanned"]`);
  btn.disabled = true;
  btn.textContent = '🧠 Evaluando...';
  const resultadosDiv = document.getElementById('resultados');
  resultadosDiv.style.display = 'block';
  resultadosDiv.innerHTML = `<h2>Resultados de Evaluación</h2>`;
  const statusContainer = document.createElement('div');
  statusContainer.style.cssText = 'font-family: monospace; white-space: pre-wrap; padding: 1rem; background: #f8f9fa; border-radius: var(--radius); margin-top: 1rem;';
  resultadosDiv.appendChild(statusContainer);
  const config = {
    sistema: document.getElementById('sistema-calificacion').value,
    nivelExigencia: parseInt(document.getElementById('nivel-exigencia').value) || 60,
    puntajeMaximo: parseInt(document.getElementById('puntaje-maximo').value) || 30,
    notaAprobacion: parseFloat(document.getElementById('nota-aprobacion').value) || 4.0,
    flexibility: parseInt(document.getElementById('ia-flexibility').value) || 5,
    fecha: document.getElementById('test-date-input').value || new Date().toISOString().split('T')[0]
  };
  for (const item of appState.loteEscaneado.studentData) {
    const nombreEstudiante = document.getElementById(item.nombreInputId).value.trim() || `Estudiante ${appState.loteEscaneado.studentData.indexOf(item) + 1}`;
    const textoRevisado = document.getElementById(item.textoTextareaId).value;
    const tipoDeTrabajo = document.getElementById(item.contextoSelectId).value;
    const log = msg => statusContainer.innerHTML += `[${nombreEstudiante}]: ${msg}\n`;
    try {
      log('Enviando a Evaluación con IA...');
      const payload = {
        alumno: nombreEstudiante,
        evaluacion: textoRevisado,
        rubrica: document.getElementById('instruccionesEscaneado').value,
        curso: document.getElementById('curso-escaneado').value || 'Sin Curso',
        nombrePrueba: document.getElementById('nombre-prueba-escaneada').value || 'Evaluación de Documento',
        flexibilidadIA: config.flexibility,
        notaMinima: config.notaAprobacion
      };
      const res = await fetch('/evaluar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const resultadoIA = await res.json();
      const evaluacionFinal = {
        ...resultadoIA,
        nombreEstudiante,
        id: item.id,
        nombrePrueba: payload.nombrePrueba,
        curso: payload.curso,
        configuracion: config,
        puntajeObtenido: resultadoIA.puntaje_calculado_ia,
        bonificacion: 0,
        justificacionDecimas: '',
        notaFinal: resultadoIA.nota_sugerida_ia
      };
      const divResultado = document.createElement('div');
      renderizarResultadoFinal(evaluacionFinal, divResultado, true);
      resultadosDiv.appendChild(divResultado);
      log(`✅ Evaluación completada. Nota: ${evaluacionFinal.notaFinal.toFixed(1)}`);
    } catch (error) {
      log(`❌ ERROR: ${error.message}`);
    }
  }
  btn.disabled = false;
  btn.textContent = '🚀 Iniciar Evaluación de Lote';
  renderizarHistorial();
}

function renderizarResultadoFinal(resultado, contenedor, guardarEnHistorial = true) {
  if (guardarEnHistorial) {
    appState.historial.push(resultado);
    localStorage.setItem('historialEvaluaciones_v33', JSON.stringify(appState.historial));
  }
  // Aquí va el resto de tu lógica de renderizado (igual que antes)
}

function mostrarDatosParaCopiar(selectionOnly = true) {
  let dataToExport = appState.historial;
  if (selectionOnly) {
    const selectedIds = [...document.querySelectorAll('.historial-checkbox:checked')].map(cb => cb.dataset.id);
    if (selectedIds.length === 0) {
      alert("Por favor, selecciona al menos una fila para copiar.");
      return;
    }
    dataToExport = appState.historial.filter(item => selectedIds.includes(item.id));
  }
  const headers = ["Estudiante", "Curso", "Evaluación", "Nota Final"];
  const rows = dataToExport.map(row => [row.nombreEstudiante, row.curso, row.nombrePrueba, row.notaFinal.toFixed(1)]);
  let tsvContent = headers.join('\t') + '\n';
  tsvContent += rows.map(row => row.join('\t')).join('\n');
  const modal = document.getElementById('copy-data-modal');
  const textarea = document.getElementById('copy-data-textarea');
  textarea.value = tsvContent;
  modal.style.display = 'block';
}

function exportarHistorialCSV() {
  const dataToExport = appState.historial;
  if (dataToExport.length === 0) {
    alert("No hay datos en el historial para exportar.");
    return;
  }
  const csvRows = [];
  const headers = ["ID", "Estudiante", "Curso", "Evaluación", "Fecha", "Puntaje Obtenido", "Puntaje Máximo", "Nota Final", "Bonificación"];
  csvRows.push(headers.join(','));
  for (const row of dataToExport) {
    const values = [
      row.id,
      `"${row.nombreEstudiante}"`,
      `"${row.curso}"`,
      `"${row.nombrePrueba}"`,
      row.configuracion.fecha || 'N/A',
      row.puntajeObtenido,
      row.configuracion.puntajeMaximo,
      row.notaFinal.toFixed(1),
      row.bonificacion || 0
    ];
    csvRows.push(values.join(','));
  }
  const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.setAttribute('hidden', '');
  a.setAttribute('href', url);
  a.setAttribute('download', `historial_evaluaciones_${new Date().toISOString().split('T')[0]}.csv`);
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

function renderizarHistorial() {
  const tbody = document.getElementById('historial-tbody');
  if (!tbody) return;
  const filtro = document.getElementById('search-historial').value.toLowerCase();
  let datosFiltrados = appState.historial.filter(e =>
    (e.nombreEstudiante || '').toLowerCase().includes(filtro) ||
    (e.curso || '').toLowerCase().includes(filtro) ||
    (e.nombrePrueba || '').toLowerCase().includes(filtro)
  );
  datosFiltrados.sort((a, b) => {
    if (appState.sortState.key) {
      let valA = a[appState.sortState.key] || '';
      let valB = b[appState.sortState.key] || '';
      if (typeof valA === 'string') {
        valA = valA.toLowerCase();
        valB = valB.toLowerCase();
      }
      if (valA < valB) return appState.sortState.asc ? -1 : 1;
      if (valA > valB) return appState.sortState.asc ? 1 : -1;
    }
    return 0;
  });
  tbody.innerHTML = datosFiltrados.map(e => `
    <tr data-student-row-id="${e.id}">
      <td><input type="checkbox" class="historial-checkbox" data-id="${e.id}"></td>
      <td>${e.curso}</td>
      <td contenteditable="true" data-blur-action="update-student-name" data-student-id="${e.id}" data-original-name="${e.nombreEstudiante}" data-student-name-sync-id="${e.id}">${e.nombreEstudiante}</td>
      <td>${e.nombrePrueba}</td>
      <td>${e.notaFinal.toFixed(1)}</td>
      <td>
        <button data-action="ver-feedback" data-id="${e.id}" class="action-btn">Ver</button>
        <button data-action="export-student-pdf" data-id="${e.id}" class="action-btn secondary">PDF Est.</button>
      </td>
    </tr>
  `).join('');
}

function verFeedbackDetallado(id) {
  const evaluacion = appState.historial.find(e => e.id === id);
  if (!evaluacion) return;
  const modalBody = document.getElementById('modal-body-feedback');
  const contenedor = document.createElement('div');
  renderizarResultadoFinal(evaluacion, contenedor, false);
  modalBody.innerHTML = '';
  modalBody.appendChild(contenedor);
  document.getElementById('feedback-modal').style.display = 'block';
}

function limpiarHistorial() {
  if (confirm('¿Borrar PERMANENTEMENTE todo el historial y la memoria de nombres?')) {
    appState.historial = [];
    appState.nameCorrections = {};
    localStorage.removeItem('historialEvaluaciones_v33');
    localStorage.removeItem('nameCorrections_v5');
    renderizarHistorial();
  }
}

function sortHistory(key) {
  appState.sortState.asc = appState.sortState.key === key ? !appState.sortState.asc : true;
  appState.sortState.key = key;
  renderizarHistorial();
}

function selectAllHistory(checked) {
  document.querySelectorAll('.historial-checkbox').forEach(cb => cb.checked = checked);
}

function switchMainView(viewName) {
  document.getElementById('view-evaluacion').style.display = viewName === 'evaluacion' ? 'block' : 'none';
  document.getElementById('view-historial').style.display = viewName === 'historial' ? 'block' : 'none';
  document.getElementById('view-analisis').style.display = viewName === 'analisis' ? 'block' : 'none';
  document.querySelectorAll('.main-tab').forEach(tab => tab.classList.remove('active'));
  document.querySelector(`[data-view="${viewName}"]`).classList.add('active');
}

function mostrarWorkflow(id) {
  const container = document.getElementById('workflows-container');
  const template = document.getElementById(`template-${id}`);
  if (!container || !template) return;
  container.innerHTML = template.innerHTML;
  const configContainerId = 'config-container-escaneado';
  const configContainer = document.getElementById(configContainerId);
  configContainer.innerHTML = document.getElementById('template-configuracion-evaluacion').innerHTML;
  setupDragDrop('dropZoneEscaneado', 'archivosEscaneados', handleScannedFiles);
  document.getElementById('archivoRubrica').addEventListener('change', handleRubricFile);
}

async function handleRubricFile(event) {
  const file = event.target.files[0];
  if (!file) return;
  try {
    const textoRubrica = await leerTextoDeArchivo(file);
    document.getElementById('instruccionesEscaneado').value = textoRubrica;
    document.querySelector('label[for="archivoRubrica"]').textContent = `✅ Rúbrica cargada: ${file.name}`;
  } catch (e) {
    alert(`Error al leer el archivo: ${e.message}`);
  }
}

async function leerTextoDeArchivo(file) {
  if (file.type.startsWith("image/")) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/ocr', { method: 'POST', body: formData });
    const data = await res.json();
    return data.readResults?.[0]?.content || '[Sin texto]';
  }
  if (file.name.endsWith('.docx')) {
    const arrayBuffer = await file.arrayBuffer();
    const result = await mammoth.extractRawText({ arrayBuffer });
    return result.value;
  }
  if (file.name.endsWith('.pdf')) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/ocr', { method: 'POST', body: formData });
    const data = await res.json();
    return data.readResults?.[0]?.content || '[Sin texto]';
  }
  return await file.text();
}

function abrirModalDecimas(id) {
  appState.currentEvaluationId = id;
  document.getElementById('decimas-modal').style.display = 'block';
}

function guardarDecimas() {
  const id = appState.currentEvaluationId;
  const index = appState.historial.findIndex(e => e.id === id);
  if (index === -1) return;
  const bonificacion = parseFloat(document.getElementById('decimas-input').value) || 0;
  const justificacion = document.getElementById('decimas-justificacion').value;
  const eval = appState.historial[index];
  eval.bonificacion = bonificacion;
  eval.justificacionDecimas = justificacion;
  eval.notaFinal = eval.nota_sugerida_ia + bonificacion;
  localStorage.setItem('historialEvaluaciones_v33', JSON.stringify(appState.historial));
  document.getElementById('decimas-modal').style.display = 'none';
  const feedbackWrapper = document.querySelector(`.tarjeta-feedback-wrapper[data-eval-wrapper-id="${id}"]`);
  if (feedbackWrapper) {
    const contenedor = document.createElement('div');
    renderizarResultadoFinal(eval, contenedor, false);
    feedbackWrapper.replaceWith(contenedor);
  }
  renderizarHistorial();
}

function renderizarAnalisis() {
  renderCourseComparisonChart();
  populateStudentProgressSelect();
  renderStudentProgressChart();
}

function renderCourseComparisonChart() {
  const courseData = appState.historial.reduce((acc, curr) => {
    const course = curr.curso || "Sin Curso";
    if (!acc[course]) acc[course] = { totalNota: 0, count: 0 };
    acc[course].totalNota += curr.notaFinal;
    acc[course].count++;
    return acc;
  }, {});
  const labels = Object.keys(courseData);
  const averages = labels.map(label => (courseData[label].totalNota / courseData[label].count).toFixed(1));
  const ctx = document.getElementById('course-comparison-chart')?.getContext('2d');
  if (!ctx) return;
  if (appState.charts.courseChart) appState.charts.courseChart.destroy();
  appState.charts.courseChart = new Chart(ctx, {
    type: 'bar',
     {
      labels: labels,
      datasets: [{
        label: 'Nota Promedio por Curso',
         averages,
        backgroundColor: 'rgba(94, 114, 228, 0.6)',
        borderColor: 'rgba(94, 114, 228, 1)',
        borderWidth: 1
      }]
    },
    options: { scales: { y: { beginAtZero: true, max: 7.0 } } }
  });
}

function populateStudentProgressSelect() {
  const select = document.getElementById('student-progress-select');
  if (!select) return;
  const studentNames = [...new Set(appState.historial.map(e => e.nombreEstudiante).sort())];
  select.innerHTML = `<option value="">-- Seleccione un estudiante --</option>` + studentNames.map(name => `<option value="${name}">${name}</option>`).join('');
}

function renderStudentProgressChart(studentName) {
  const select = document.getElementById('student-progress-select');
  if (!select) return;
  if (!studentName && select) studentName = select.value;
  const ctx = document.getElementById('student-progress-chart')?.getContext('2d');
  if (!ctx) return;
  if (appState.charts.studentChart) appState.charts.studentChart.destroy();
  if (!studentName) return;
  const studentEvals = appState.historial
    .filter(e => e.nombreEstudiante === studentName)
    .sort((a, b) => new Date(a.configuracion.fecha) - new Date(b.configuracion.fecha));
  const labels = studentEvals.map(e => `${e.nombrePrueba} (${e.configuracion.fecha})`);
  const data = studentEvals.map(e => e.notaFinal);
  appState.charts.studentChart = new Chart(ctx, {
    type: 'line',
     {
      labels,
      datasets: [{
        label: `Progreso de ${studentName}`,
        data,
        fill: false,
        borderColor: 'rgb(45, 206, 137)',
        tension: 0.1
      }]
    },
    options: { scales: { y: { beginAtZero: true, max: 7.0 } } }
  });
}

function switchFeedbackView(event) {
  const card = event.target.closest('.tarjeta-feedback');
  if (!card) return;
  const tabs = card.querySelectorAll('.tab');
  const contents = card.querySelectorAll('.feedback-content');
  const tabIndex = Array.from(tabs).indexOf(event.target);
  tabs.forEach(t => t.classList.remove('active'));
  contents.forEach(c => c.classList.remove('active'));
  event.target.classList.add('active');
  if (contents[tabIndex]) contents[tabIndex].classList.add('active');
}

function copiarDatosDelModal() {
  const textarea = document.getElementById('copy-data-textarea');
  textarea.select();
  document.execCommand('copy');
  const btn = document.querySelector('[data-action="copy-from-modal"]');
  btn.textContent = '✅ ¡Copiado!';
  setTimeout(() => btn.textContent = 'Copiar Todo al Portapapeles', 2000);
}

function handleGlobalInput(e) {
  if (e.target.id === 'search-historial') {
    renderizarHistorial();
  }
}

function handleGlobalChange(e) {
  if (e.target.id === 'student-progress-select') {
    renderStudentProgressChart(e.target.value);
  }
}

function handleGlobalBlur(e) {
  const target = e.target.closest('[data-blur-action]');
  if (!target) return;
  const action = target.dataset.blurAction;
  const params = target.dataset;
  if (action === 'update-student-name') {
    const studentId = params.studentId;
    const originalName = params.originalName;
    const correctedName = target.textContent.trim();
    if (originalName && correctedName.toLowerCase() !== originalName.toLowerCase()) {
      if (!appState.nameCorrections[correctedName]) appState.nameCorrections[correctedName] = [];
      if (!appState.nameCorrections[correctedName].includes(originalName.toLowerCase())) {
        appState.nameCorrections[correctedName].push(originalName.toLowerCase());
      }
      localStorage.setItem('nameCorrections_v5', JSON.stringify(appState.nameCorrections));
    }
    const index = appState.historial.findIndex(ev => ev.id === studentId);
    if (index > -1) {
      appState.historial[index].nombreEstudiante = correctedName;
      localStorage.setItem('historialEvaluaciones_v33', JSON.stringify(appState.historial));
    }
    document.querySelectorAll(`[data-student-name-sync-id="${studentId}"]`).forEach(el => {
      if (el.isContentEditable) {
        el.textContent = correctedName;
      } else {
        el.value = correctedName;
      }
    });
  }
}

async function extraerNombreConIA(texto) {
  const prompt = `Extrae el nombre del estudiante del siguiente texto: "${texto}"`;
  const res = await fetch('/evaluar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ alumno: '', evaluacion: texto, rubrica: '', curso: '', nombrePrueba: '', flexibilidadIA: 5, notaMinima: 4.0 })
  });
  const data = await res.json();
  return data.alumno || '';
}

function abrirModalCamara() {
  const modal = document.getElementById('camera-modal');
  navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }})
    .then(stream => {
      document.getElementById('video-feed').srcObject = stream;
      modal.style.display = 'block';
    })
    .catch(() => alert('No se pudo acceder a la cámara.'));
}

function cerrarModalCamara() {
  const stream = document.getElementById('video-feed').srcObject;
  if (stream) stream.getTracks().forEach(track => track.stop());
  document.getElementById('camera-modal').style.display = 'none';
}

function capturarFoto() {
  const video = document.getElementById('video-feed');
  const canvas = document.getElementById('photo-canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
  canvas.toBlob(blob => {
    const file = new File([blob], `captura-${Date.now()}.jpg`, { type: 'image/jpeg' });
    appState.loteEscaneado.files.push(file);
    renderizarPreviews();
    cerrarModalCamara();
  }, 'image/jpeg');
}

function renderizarPreviews() {
  const previewContainer = document.getElementById('previewContainerEscaneado');
  previewContainer.innerHTML = 'Cargando vistas previas...';
  const previewPromises = appState.loteEscaneado.files.map(async file => {
    const item = document.createElement('div');
    item.className = 'preview-item';
    const icon = file.type.startsWith("image/") ? `<img src="${await readFileAsDataURL(file)}" alt="${file.name}">` : `<div>📄</div>`;
    item.innerHTML = `${icon}<div>${file.name}</div>`;
    return item;
  });
  const previewElements = await Promise.all(previewPromises);
  previewContainer.innerHTML = '';
  previewElements.forEach(el => previewContainer.appendChild(el));
}

function readFileAsDataURL(file) {
  return new Promise(resolve => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.readAsDataURL(file);
  });
}
  </script>