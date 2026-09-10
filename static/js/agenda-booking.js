/*
 * Reserva de cita (docs/design/phase-2-agenda-ux.md §10-15, §30-31):
 * médico → consultorio → fecha → slot → hold (15 min, con cuenta
 * regresiva) → confirmar. Habla exclusivamente con el API JSON de
 * Agenda (appointments/api.py) vía fetch() — nunca decide reglas de
 * negocio aquí, solo refleja lo que el backend responde.
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
    const date = new Date(isoString);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  document.addEventListener("DOMContentLoaded", function () {
    const root = document.getElementById("booking-app");
    if (!root) return;

    const config = JSON.parse(document.getElementById("booking-config").textContent);
    const doctorClinicPairs = JSON.parse(document.getElementById("doctor-clinic-data").textContent);

    const doctorSelect = document.getElementById("doctor-select");
    const clinicSelect = document.getElementById("clinic-select");
    const dateInput = document.getElementById("date-input");
    const searchBtn = document.getElementById("search-slots-btn");
    const slotGrid = document.getElementById("slot-grid");
    const slotGridStatus = document.getElementById("slot-grid-status");
    const pickerPanel = document.getElementById("picker-panel");
    const holdPanel = document.getElementById("hold-panel");
    const successPanel = document.getElementById("success-panel");
    const countdownEl = document.getElementById("countdown");
    const holdSummaryEl = document.getElementById("hold-summary");
    const continueBtn = document.getElementById("continue-btn");
    const releaseBtn = document.getElementById("release-btn");
    const patientIdInput = document.getElementById("patient-id-input");
    const patientSelect = document.getElementById("patient-select");
    const errorBox = document.getElementById("booking-error");

    let currentHold = null;
    let countdownTimer = null;

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
      if (config.patientMode === "manual") return patientIdInput ? patientIdInput.value : null;
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
            createHold(slot);
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

    function createHold(slot) {
      clearError();
      const patientId = getPatientId();
      if (!patientId) {
        showError("Selecciona un paciente antes de continuar.");
        return;
      }
      apiFetch(config.holdsApiUrl, {
        method: "POST",
        body: JSON.stringify({
          doctor_id: doctorSelect.value,
          clinic_id: clinicSelect.value,
          start: slot.start,
          end: slot.end,
        }),
      }).then(function (result) {
        if (!result.ok) {
          showError(errorMessage(result, "No se pudo reservar el horario temporalmente."));
          if (result.status === 409) searchSlots();
          return;
        }
        currentHold = result.body;
        showHoldPanel();
      });
    }

    function showHoldPanel() {
      pickerPanel.hidden = true;
      holdPanel.hidden = false;
      holdSummaryEl.textContent =
        "Horario reservado temporalmente: " + formatTime(currentHold.start) + "–" + formatTime(currentHold.end);
      startCountdown();
    }

    function startCountdown() {
      clearInterval(countdownTimer);
      countdownTimer = setInterval(function () {
        const remainingMs = new Date(currentHold.expires_at).getTime() - Date.now();
        if (remainingMs <= 0) {
          clearInterval(countdownTimer);
          onHoldExpired();
          return;
        }
        const totalSeconds = Math.floor(remainingMs / 1000);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        countdownEl.textContent =
          String(minutes).padStart(2, "0") + ":" + String(seconds).padStart(2, "0");
      }, 1000);
    }

    function backToPicker() {
      clearInterval(countdownTimer);
      currentHold = null;
      holdPanel.hidden = true;
      pickerPanel.hidden = false;
    }

    function onHoldExpired() {
      backToPicker();
      showError("El tiempo de reserva terminó. Selecciona nuevamente un horario disponible.");
      searchSlots();
    }

    releaseBtn.addEventListener("click", function () {
      if (!currentHold || !window.confirm("¿Liberar este horario?")) return;
      apiFetch(config.holdsApiUrl + currentHold.id + "/release/", { method: "POST" }).then(function () {
        backToPicker();
        searchSlots();
      });
    });

    continueBtn.addEventListener("click", function () {
      if (!currentHold) return;
      clearError();
      continueBtn.disabled = true;
      continueBtn.textContent = "Guardando...";
      const idempotencyKey =
        window.crypto && window.crypto.randomUUID ? window.crypto.randomUUID() : String(Date.now() + Math.random());

      apiFetch(config.appointmentsApiUrl, {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
        body: JSON.stringify({ hold_id: currentHold.id, patient_id: getPatientId() }),
      }).then(function (result) {
        continueBtn.disabled = false;
        continueBtn.textContent = "Continuar";
        if (!result.ok) {
          showError(errorMessage(result, "No se pudo crear la cita."));
          if (result.status === 409) {
            backToPicker();
            searchSlots();
          }
          return;
        }
        clearInterval(countdownTimer);
        holdPanel.hidden = true;
        showSuccess(result.body);
      });
    });

    function showSuccess(appointment) {
      successPanel.hidden = false;
      document.getElementById("success-detail").textContent =
        formatTime(appointment.start) + "–" + formatTime(appointment.end) + " · " +
        appointment.duration_minutes + " min";
    }

    populateDoctors();
    if (doctorSelect.options.length) {
      populateClinics();
    }
    const today = new Date().toISOString().slice(0, 10);
    dateInput.min = today;
    dateInput.value = today;
  });
})();
