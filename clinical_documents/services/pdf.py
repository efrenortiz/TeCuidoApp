"""Generación server-side y síncrona de PDF (ADR-027).

Determinista: a partir únicamente de los datos ya persistidos de la
versión concreta que se está emitiendo — nunca vuelve a leer datos que
puedan cambiar después. `fpdf2` (puro Python, sin dependencias de sistema)
— ver justificación en `docs/phases/phase-4-implementation/stage-03-files-pdf.md`.
"""

from fpdf import FPDF

_MARGIN = 15


def _base_pdf(*, title, clinic, patient, doctor, issued_at, version_number):
    pdf = FPDF(format="Letter")
    pdf.set_margin(_MARGIN)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 11)
    local_issued_at = issued_at.astimezone(clinic.zoneinfo) if clinic is not None else issued_at
    pdf.cell(0, 7, f"Consultorio: {clinic.name if clinic else '-'}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Paciente: {patient.person}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Médico: {doctor.person}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Fecha de emisión: {local_issued_at:%Y-%m-%d %H:%M}", new_x="LMARGIN", new_y="NEXT")
    if version_number and version_number > 1:
        pdf.cell(0, 7, f"Versión: {version_number}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    return pdf


def render_prescription_pdf(prescription) -> bytes:
    clinic = prescription.clinical_encounter.appointment.clinic
    pdf = _base_pdf(
        title="Receta médica", clinic=clinic, patient=prescription.patient, doctor=prescription.doctor,
        issued_at=prescription.issued_at, version_number=prescription.version_number,
    )
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Medicamentos", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for item in prescription.items.order_by("position"):
        line = f"{item.position}. {item.medication_name}"
        if item.presentation:
            line += f" ({item.presentation})"
        line += f" - {item.dose}"
        if item.dose_unit:
            line += f" {item.dose_unit}"
        line += f", {item.route}, {item.frequency}"
        if item.duration:
            line += f", {item.duration}"
        pdf.multi_cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
        if item.instructions:
            pdf.set_font("Helvetica", "I", 10)
            pdf.multi_cell(0, 6, f"   Indicaciones: {item.instructions}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 11)
        pdf.ln(1)
    return bytes(pdf.output())


def render_study_order_pdf(study_order) -> bytes:
    clinic = study_order.clinical_encounter.appointment.clinic
    pdf = _base_pdf(
        title="Solicitud de estudio", clinic=clinic, patient=study_order.patient, doctor=study_order.doctor,
        issued_at=study_order.issued_at, version_number=study_order.version_number,
    )
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Tipo de estudio: {study_order.get_study_type_display()}", new_x="LMARGIN", new_y="NEXT")
    if study_order.indications:
        pdf.multi_cell(0, 6, f"Indicaciones: {study_order.indications}", new_x="LMARGIN", new_y="NEXT")
    if study_order.observations:
        pdf.multi_cell(0, 6, f"Observaciones: {study_order.observations}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Estudios solicitados", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for item in study_order.items.order_by("position"):
        line = f"{item.position}. {item.study_name}"
        pdf.multi_cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
        if item.specific_instructions:
            pdf.set_font("Helvetica", "I", 10)
            pdf.multi_cell(0, 6, f"   Indicaciones: {item.specific_instructions}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 11)
        pdf.ln(1)
    return bytes(pdf.output())
