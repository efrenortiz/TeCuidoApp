/*
 * Reprogramación de cita (docs/design/phase-2-agenda-ux.md §19-20): sin
 * hold — el médico está fijo, se elige nuevo consultorio/fecha/horario y
 * se confirma directamente contra el endpoint de reprogramación.
 */
(function () {
  "use strict";

  function getCookie(name) {
    const match = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return match ? decodeURIComponent(match[2]) : null;
  }

  function apiFetch(url, options) {
    options = options || {};
    options.headers = Object.assign(
      { "Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken") },
      options.headers || {}
    );
    return fetch(url, options).then(function (response) {
      return response.json().catch(function () {
        return {};
      }).then(function (body) {
        return { ok: response.ok, status: response.status, body: body };
      });
    });
  }

  function formatTime(isoString) {
    return new Date(isoString).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  document.addEventListener("DOMContentLoaded", function () {
    const root = document.getElementById("reschedule-app");
    if (!root) return;

    const config = JSON.parse(document.getElementById("reschedule-config").textContent);
    const clinics = JSON.parse(document.getElementById("reschedule-clinics-data").textContent);

    const clinicSelect = document.getElementById("clinic-select");
    const dateInput = document.getElementById("date-input");
    const reasonSelect = document.getElementById("reason-select");
    const searchBtn = document.getElementById("search-slots-btn");
    const slotGrid = document.getElementById("slot-grid");
    const slotGridStatus = document.getElementById("slot-grid-status");
    const pickerPanel = document.getElementById("picker-panel");
    const confirmPanel = document.getElementById("confirm-panel");
    const confirmSummary = document.getElementById("confirm-summary");
    const successPanel = document.getElementById("success-panel");
    const backBtn = document.getElementById("back-btn");
    const confirmBtn = document.getElementById("confirm-btn");
    const errorBox = document.getElementById("reschedule-error");

    let selectedSlot = null;

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

    clinics.forEach(function (clinic) {
      const option = document.createElement("option");
      option.value = clinic.clinic_id;
      option.textContent = clinic.clinic_name;
      if (clinic.clinic_id === config.currentClinicId) option.selected = true;
      clinicSelect.appendChild(option);
    });

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
      const clinicId = clinicSelect.value;
      const date = dateInput.value;
      if (!clinicId || !date) {
        showError("Selecciona consultorio y fecha.");
        return;
      }
      slotGrid.innerHTML = "";
      slotGridStatus.textContent = "Cargando...";
      slotGridStatus.hidden = false;
      const url =
        config.slotsApiUrl + "?doctor_id=" + config.doctorId + "&clinic_id=" + clinicId + "&date=" + date;
      apiFetch(url).then(function (result) {
        if (!result.ok) {
          slotGridStatus.hidden = true;
          showError(errorMessage(result, "No se pudo cargar la disponibilidad."));
          return;
        }
        renderSlots(result.body.slots);
      });
    }

    searchBtn.addEventListener("click", searchSlots);

    function selectSlot(slot) {
      selectedSlot = slot;
      pickerPanel.hidden = true;
      confirmPanel.hidden = false;
      confirmSummary.textContent =
        dateInput.value + " · " + formatTime(slot.start) + "–" + formatTime(slot.end) + " · " +
        clinicSelect.options[clinicSelect.selectedIndex].textContent;
    }

    backBtn.addEventListener("click", function () {
      selectedSlot = null;
      confirmPanel.hidden = true;
      pickerPanel.hidden = false;
    });

    confirmBtn.addEventListener("click", function () {
      if (!selectedSlot) return;
      clearError();
      confirmBtn.disabled = true;
      confirmBtn.textContent = "Guardando...";
      const idempotencyKey =
        window.crypto && window.crypto.randomUUID ? window.crypto.randomUUID() : String(Date.now() + Math.random());

      apiFetch(config.rescheduleApiUrl, {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
        body: JSON.stringify({
          clinic_id: clinicSelect.value,
          start: selectedSlot.start,
          end: selectedSlot.end,
          reason: reasonSelect.value,
        }),
      }).then(function (result) {
        confirmBtn.disabled = false;
        confirmBtn.textContent = "Confirmar reprogramación";
        if (!result.ok) {
          showError(errorMessage(result, "No se pudo reprogramar la cita."));
          if (result.status === 409) {
            // phase-2-agenda-ux.md §20 — la cita original queda intacta;
            // se vuelve al selector para elegir otro horario.
            selectedSlot = null;
            confirmPanel.hidden = true;
            pickerPanel.hidden = false;
            searchSlots();
          }
          return;
        }
        confirmPanel.hidden = true;
        successPanel.hidden = false;
      });
    });

    const today = new Date().toISOString().slice(0, 10);
    dateInput.min = today;
    dateInput.value = today;
  });
})();
