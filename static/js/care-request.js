/*
 * Solicitud de atención (CareRequest) — docs/design/care-request-ux.md,
 * care-request-screens.md: médico → fecha → slot → motivo/adjuntos →
 * confirmar → resultado. Una sola llamada atómica a
 * `POST /api/v1/care-requests/` (docs/design/care-request-service-contracts.md
 * §17) — a diferencia de la reserva directa de Agenda, no hay panel de
 * Hold/countdown: el servidor resuelve Hold→Appointment→ClinicalDocument→
 * CONVERTIDA en una sola operación.
 */
(function () {
  "use strict";

  function getCookie(name) {
    const match = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return match ? decodeURIComponent(match[2]) : null;
  }

  function apiFetchJson(url, options) {
    options = options || {};
    options.headers = Object.assign(
      { "Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken") },
      options.headers || {}
    );
    return fetch(url, options).then(parseJsonResponse, networkErrorResult);
  }

  function apiFetchForm(url, formData, extraHeaders) {
    // Sin "Content-Type": el navegador fija el boundary multipart correcto.
    return fetch(url, {
      method: "POST", body: formData,
      headers: Object.assign({ "X-CSRFToken": getCookie("csrftoken") }, extraHeaders || {}),
    }).then(parseJsonResponse, networkErrorResult);
  }

  function parseJsonResponse(response) {
    return response
      .json()
      .catch(function () {
        return {};
      })
      .then(function (body) {
        return { ok: response.ok, status: response.status, body: body };
      });
  }

  // `fetch()` RECHAZA su promesa (no la resuelve con un status HTTP) ante
  // un fallo de red real (sin conexión, DNS, CORS, servidor inalcanzable)
  // — a diferencia de un 4xx/5xx, que sí resuelve normalmente vía
  // `parseJsonResponse`. Sin este manejo, esa promesa rechazada se
  // propagaba sin capturar hasta cada caller (`searchSlots`/
  // `submitCareRequest`), que solo tienen `.then()`/`.finally()`: el
  // `.then()` de éxito nunca se ejecutaba (sin mensaje de error visible
  // para el usuario) y el rechazo quedaba como "unhandled promise
  // rejection" en consola. Convertir el rechazo en un resultado resuelto,
  // con la misma forma `{ok, status, body}` que ya usan ambos callers,
  // permite que `errorMessage()`/`showError()` funcionen sin cambios y
  // que `.finally()` siga restaurando el botón de forma predecible.
  function networkErrorResult() {
    return {
      ok: false,
      status: 0,
      body: { error: { code: "NETWORK_ERROR", message: "No se pudo conectar con el servidor. Verifica tu conexión e inténtalo de nuevo." } },
    };
  }

  function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function formatDate(isoDate) {
    // Se formatea a partir de las partes literales de "YYYY-MM-DD", nunca
    // vía `new Date(isoDate)` — eso interpreta la cadena como medianoche
    // UTC y, en un huso horario con offset negativo, puede mostrar el día
    // anterior al que el usuario realmente eligió.
    const parts = (isoDate || "").split("-");
    if (parts.length !== 3) return isoDate || "";
    return parts[2] + "/" + parts[1] + "/" + parts[0];
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  document.addEventListener("DOMContentLoaded", function () {
    const root = document.getElementById("care-request-app");
    if (!root) return;

    const config = JSON.parse(document.getElementById("care-request-config").textContent);
    const doctorClinicPairs = JSON.parse(document.getElementById("doctor-clinic-data").textContent);

    const doctorSelect = document.getElementById("doctor-select");
    const clinicSelect = document.getElementById("clinic-select");
    const dateInput = document.getElementById("date-input");
    const searchBtn = document.getElementById("search-slots-btn");
    const slotGrid = document.getElementById("slot-grid");
    const slotGridStatus = document.getElementById("slot-grid-status");
    const pickerPanel = document.getElementById("picker-panel");
    const detailsPanel = document.getElementById("details-panel");
    const successPanel = document.getElementById("success-panel");
    const summaryDoctor = document.getElementById("summary-doctor");
    const summaryClinic = document.getElementById("summary-clinic");
    const summaryDate = document.getElementById("summary-date");
    const summarySlot = document.getElementById("summary-slot");
    const motivoInput = document.getElementById("motivo-input");
    const padecimientoInput = document.getElementById("padecimiento-input");
    const descripcionInput = document.getElementById("descripcion-input");
    const attachmentsField = document.getElementById("attachments-field");
    const attachmentsInput = document.getElementById("attachments-input");
    const attachmentsError = document.getElementById("attachments-error");
    const attachmentsList = document.getElementById("attachments-list");
    const submittingStatus = document.getElementById("submitting-status");
    const confirmBtn = document.getElementById("confirm-btn");
    const cancelDetailsBtn = document.getElementById("cancel-details-btn");
    const patientSelect = document.getElementById("patient-select");
    const errorBox = document.getElementById("care-request-error");

    let selectedSlot = null;
    // Una clave por intento de solicitud (docs/design/care-request-ux.md
    // §5/§8: "Backend idempotency remains the authoritative protection"):
    // generada al seleccionar un horario, reutilizada mientras el usuario
    // siga en el mismo intento (incluido un reintento tras un error), y
    // renovada solo al seleccionar un horario distinto — nunca reenviada
    // como el mismo valor para una solicitud genuinamente diferente. Sin
    // esto, dos solicitudes HTTP reales (doble tap, dos pestañas) no
    // tenían ninguna relación entre sí para el servidor y podían crear
    // dos operaciones de negocio distintas — el botón deshabilitado solo
    // protege contra un doble clic dentro de la misma pestaña.
    let idempotencyKey = null;

    function showError(message) {
      errorBox.textContent = message;
      errorBox.hidden = false;
    }

    function clearError() {
      errorBox.hidden = true;
      errorBox.textContent = "";
    }

    function errorMessage(result, fallback) {
      return (result.body && result.body.error && result.body.error.message) || fallback;
    }

    function getPatientId() {
      if (config.fixedPatientId) return config.fixedPatientId;
      if (config.patientMode === "responsible") return patientSelect ? patientSelect.value : null;
      return null;
    }

    function populateDoctors() {
      const seen = {};
      doctorClinicPairs.forEach(function (pair) {
        if (seen[pair.doctor_id]) return;
        seen[pair.doctor_id] = true;
        const option = document.createElement("option");
        option.value = pair.doctor_id;
        option.textContent = pair.doctor_name;
        doctorSelect.appendChild(option);
      });
      populateClinics();
    }

    function populateClinics() {
      clinicSelect.innerHTML = "";
      const doctorId = doctorSelect.value;
      doctorClinicPairs
        .filter(function (pair) {
          return String(pair.doctor_id) === doctorId;
        })
        .forEach(function (pair) {
          const option = document.createElement("option");
          option.value = pair.clinic_id;
          option.textContent = pair.clinic_name;
          clinicSelect.appendChild(option);
        });
    }

    doctorSelect.addEventListener("change", populateClinics);
    populateDoctors();

    function renderSlots(slots) {
      slotGrid.innerHTML = "";
      if (!slots.length) {
        slotGridStatus.textContent = "No hay horarios disponibles para esta fecha.";
        slotGridStatus.hidden = false;
        return;
      }
      slotGridStatus.hidden = true;
      slots.forEach(function (slot) {
        const button = document.createElement("button");
        button.type = "button";
        button.className =
          "slot-grid__slot slot-grid__slot--button slot-grid__slot--" + slot.status.toLowerCase();
        const time = document.createElement("span");
        time.className = "slot-grid__time";
        time.textContent = formatTime(slot.start) + "–" + formatTime(slot.end);
        button.appendChild(time);
        if (slot.status !== "AVAILABLE") {
          button.disabled = true;
        } else {
          button.addEventListener("click", function () {
            selectSlot(slot);
          });
        }
        slotGrid.appendChild(button);
      });
    }

    function searchSlots() {
      clearError();
      const doctorId = doctorSelect.value;
      const clinicId = clinicSelect.value;
      const date = dateInput.value;
      if (!doctorId || !clinicId || !date) {
        showError("Selecciona médico, consultorio y fecha.");
        return;
      }
      slotGrid.innerHTML = "";
      slotGridStatus.textContent = "Cargando...";
      slotGridStatus.hidden = false;
      const url = config.slotsApiUrl + "?doctor_id=" + doctorId + "&clinic_id=" + clinicId + "&date=" + date;
      apiFetchJson(url).then(function (result) {
        if (!result.ok) {
          slotGridStatus.hidden = true;
          showError(errorMessage(result, "No se pudo cargar la disponibilidad."));
          return;
        }
        renderSlots(result.body.slots);
      });
    }

    searchBtn.addEventListener("click", searchSlots);

    function renderSummary(slot) {
      // docs/design/care-request-screens.md §3: médico/consultorio/fecha/
      // horario deben quedar visibles ANTES de confirmar, no solo en el
      // paso de selección (que ya queda oculto en este punto).
      summaryDoctor.textContent = doctorSelect.options[doctorSelect.selectedIndex]
        ? doctorSelect.options[doctorSelect.selectedIndex].text : "";
      summaryClinic.textContent = clinicSelect.options[clinicSelect.selectedIndex]
        ? clinicSelect.options[clinicSelect.selectedIndex].text : "";
      summaryDate.textContent = formatDate(dateInput.value);
      summarySlot.textContent = formatTime(slot.start) + "–" + formatTime(slot.end);
    }

    function selectSlot(slot) {
      clearError();
      selectedSlot = slot;
      idempotencyKey = crypto.randomUUID();
      renderSummary(slot);
      pickerPanel.hidden = true;
      detailsPanel.hidden = false;
    }

    cancelDetailsBtn.addEventListener("click", function () {
      selectedSlot = null;
      detailsPanel.hidden = true;
      pickerPanel.hidden = false;
    });

    // Validación de adjuntos en cliente (docs/design/care-request-ux.md
    // §10, care-request-screens.md §10) — mínima y coherente con las
    // reglas del servidor, reutilizadas tal cual desde `care_request_
    // config` (nunca hardcodeadas por separado aquí): cantidad máxima,
    // extensión permitida, tamaño máximo por archivo. El servidor sigue
    // siendo la única autoridad real (vuelve a validar tipo real por
    // contenido, MIME, etc. — esto es solo una ayuda de UX, nunca un
    // sustituto). No lee ni transforma el contenido del archivo — solo
    // `File.name`/`File.size`, ya disponibles sin I/O adicional.
    function fileExtension(filename) {
      const dot = filename.lastIndexOf(".");
      return dot === -1 ? "" : filename.slice(dot).toLowerCase();
    }

    function validateAttachments() {
      const files = Array.prototype.slice.call(attachmentsInput.files);
      const problems = [];
      if (files.length > config.maxAttachments) {
        problems.push("Máximo " + config.maxAttachments + " archivos por solicitud.");
      }
      files.forEach(function (file) {
        const ext = fileExtension(file.name);
        if (config.allowedAttachmentExtensions.indexOf(ext) === -1) {
          problems.push("'" + file.name + "': tipo no permitido (solo " + config.allowedAttachmentExtensions.join(", ") + ").");
        } else if (file.size > config.maxAttachmentSizeBytes) {
          problems.push("'" + file.name + "': excede el tamaño máximo (" + formatBytes(config.maxAttachmentSizeBytes) + ").");
        }
      });
      return { files: files, problems: problems };
    }

    function removeAttachmentAt(index) {
      const remaining = Array.prototype.slice.call(attachmentsInput.files);
      remaining.splice(index, 1);
      const transfer = new DataTransfer();
      remaining.forEach(function (file) {
        transfer.items.add(file);
      });
      attachmentsInput.files = transfer.files;
      refreshAttachmentsUi();
    }

    function refreshAttachmentsUi() {
      const validation = validateAttachments();

      attachmentsList.innerHTML = "";
      validation.files.forEach(function (file, index) {
        const item = document.createElement("li");
        const label = document.createElement("span");
        label.textContent = file.name + " (" + formatBytes(file.size) + ")";
        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "btn btn--secondary";
        removeBtn.textContent = "Quitar";
        removeBtn.addEventListener("click", function () {
          removeAttachmentAt(index);
        });
        item.appendChild(label);
        item.appendChild(document.createTextNode(" "));
        item.appendChild(removeBtn);
        attachmentsList.appendChild(item);
      });

      if (validation.problems.length) {
        attachmentsField.classList.add("field--error");
        attachmentsError.textContent = validation.problems.join(" ");
        attachmentsError.hidden = false;
      } else {
        attachmentsField.classList.remove("field--error");
        attachmentsError.hidden = true;
        attachmentsError.textContent = "";
      }

      // docs/design/care-request-screens.md §10: "prevent submission
      // while the invalid file remains selected" — el botón se
      // deshabilita mientras haya un problema, sin esperar al envío.
      confirmBtn.disabled = validation.problems.length > 0;
      return validation;
    }

    attachmentsInput.addEventListener("change", refreshAttachmentsUi);

    function submitCareRequest() {
      clearError();
      const patientId = getPatientId();
      if (config.patientMode === "responsible" && !patientId) {
        showError("Selecciona un paciente antes de continuar.");
        return;
      }
      const motivo = motivoInput.value.trim();
      if (!motivo) {
        showError("El motivo de la consulta es obligatorio.");
        return;
      }
      const validation = refreshAttachmentsUi();
      if (validation.problems.length) {
        showError("Corrige los archivos adjuntos antes de continuar.");
        return;
      }
      const formData = new FormData();
      formData.append("doctor_id", doctorSelect.value);
      formData.append("clinic_id", clinicSelect.value);
      formData.append("start", selectedSlot.start);
      formData.append("end", selectedSlot.end);
      formData.append("motivo", motivo);
      formData.append("padecimiento", padecimientoInput.value.trim());
      formData.append("descripcion", descripcionInput.value.trim());
      if (patientId) formData.append("patient_id", patientId);
      validation.files.forEach(function (file) {
        formData.append("attachments", file);
      });

      // docs/design/care-request-screens.md §4: impedir doble envío,
      // conservar el contexto del formulario, comunicar que se está
      // procesando — sin un segundo mecanismo de idempotencia en el
      // cliente; la protección real sigue siendo la del servidor
      // (docs/design/care-request-ux.md §5/§8).
      confirmBtn.disabled = true;
      cancelDetailsBtn.disabled = true;
      submittingStatus.hidden = false;
      apiFetchForm(config.createApiUrl, formData, { "Idempotency-Key": idempotencyKey })
        .then(function (result) {
          if (!result.ok) {
            showError(errorMessage(result, "No se pudo completar la solicitud."));
            return;
          }
          detailsPanel.hidden = true;
          successPanel.hidden = false;
          document.getElementById("success-detail").textContent =
            "Solicitud #" + result.body.care_request_id + " — cita #" + result.body.appointment_id + ".";
        })
        .finally(function () {
          submittingStatus.hidden = true;
          cancelDetailsBtn.disabled = false;
          confirmBtn.disabled = false;
        });
    }

    confirmBtn.addEventListener("click", submitCareRequest);
  });
})();
