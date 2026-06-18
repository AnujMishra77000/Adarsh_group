from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.shops import get_shop_definition
from app.models.visit_prescription import VisitPrescription


@dataclass
class GeneratedVisitPrescriptionPdf:
    file_path: Path


class VisitPrescriptionPdfService:
    @staticmethod
    def _text(value: object) -> str:
        normalized = str(value).strip() if value is not None else ""
        return escape(normalized or "-")

    @staticmethod
    def _eye(data: dict, section: str, eye: str) -> dict:
        section_data = data.get(section)
        if not isinstance(section_data, dict):
            return {}
        eye_data = section_data.get(eye)
        return eye_data if isinstance(eye_data, dict) else {}

    @classmethod
    def _eye_row(cls, data: dict, section: str, eye: str, include_add: bool) -> str:
        values = cls._eye(data, section, eye)
        add_cell = f"<td>{cls._text(values.get('add'))}</td>" if include_add else ""
        return (
            f"<tr><td><strong>{escape(eye.title())}</strong></td>"
            f"<td>{cls._text(values.get('sph'))}</td>"
            f"<td>{cls._text(values.get('cyl'))}</td>"
            f"<td>{cls._text(values.get('axis'))}</td>"
            f"{add_cell}<td>{cls._text(values.get('va'))}</td></tr>"
        )

    def _build_html(self, prescription: VisitPrescription, examiner_name: str) -> str:
        visit = prescription.visit
        customer = prescription.customer
        shop = get_shop_definition(visit.shop_key)
        branch_name = shop.display_name if shop else visit.shop_key
        branch_location = shop.location_label if shop else ""
        finalized_at = prescription.finalized_at or datetime.now(UTC)
        data = prescription.data or {}
        version_identifier = f"VISIT-{visit.id}-RX-V{prescription.version_number}"

        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8" />
          <style>
            @page {{ size: A4; margin: 24px; }}
            body {{ font-family: DejaVu Sans, Arial, sans-serif; color: #172033; font-size: 12px; margin: 0; }}
            .header {{ border-bottom: 3px solid #be185d; padding-bottom: 12px; }}
            h1 {{ font-size: 20px; margin: 0; }}
            .branch {{ color: #475569; margin-top: 4px; }}
            .meta {{ display: table; width: 100%; margin: 16px 0; }}
            .meta-row {{ display: table-row; }}
            .meta-label, .meta-value {{ display: table-cell; padding: 3px 8px 3px 0; }}
            .meta-label {{ color: #64748b; width: 18%; }}
            .meta-value {{ font-weight: 600; width: 32%; }}
            h2 {{ font-size: 14px; margin: 18px 0 7px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #cbd5e1; padding: 8px; text-align: left; }}
            th {{ background: #f8fafc; color: #475569; font-size: 11px; }}
            .measurements, .instructions {{ margin-top: 14px; padding: 10px; background: #f8fafc; border: 1px solid #e2e8f0; }}
            .footer {{ margin-top: 20px; padding-top: 10px; border-top: 1px solid #cbd5e1; color: #64748b; }}
          </style>
        </head>
        <body>
          <div class="header">
            <h1>Adarsh Optical Group</h1>
            <div class="branch">{escape(branch_name)}{f' · {escape(branch_location)}' if branch_location else ''}</div>
          </div>
          <div class="meta">
            <div class="meta-row"><div class="meta-label">Patient</div><div class="meta-value">{escape(customer.name)} ({escape(customer.customer_id)})</div><div class="meta-label">Prescription ID</div><div class="meta-value">{escape(version_identifier)}</div></div>
            <div class="meta-row"><div class="meta-label">Prescription Date</div><div class="meta-value">{finalized_at.strftime('%d %b %Y')}</div><div class="meta-label">Examiner</div><div class="meta-value">{escape(examiner_name)}</div></div>
          </div>
          <h2>Distance Prescription</h2>
          <table><thead><tr><th>Eye</th><th>Sphere</th><th>Cylinder</th><th>Axis</th><th>Visual Acuity</th></tr></thead><tbody>
            {self._eye_row(data, 'distance', 'right', False)}
            {self._eye_row(data, 'distance', 'left', False)}
          </tbody></table>
          <h2>Near Prescription</h2>
          <table><thead><tr><th>Eye</th><th>Sphere</th><th>Cylinder</th><th>Axis</th><th>Add</th><th>Visual Acuity</th></tr></thead><tbody>
            {self._eye_row(data, 'near', 'right', True)}
            {self._eye_row(data, 'near', 'left', True)}
          </tbody></table>
          <div class="measurements"><strong>PD:</strong> {self._text(data.get('pd'))} &nbsp;&nbsp; <strong>Fitting Height:</strong> {self._text(data.get('fitting_height'))}</div>
          <div class="instructions"><strong>Patient Instructions:</strong><br />{self._text(prescription.patient_instructions)}</div>
          <div class="footer">Finalized prescription · Version {prescription.version_number}</div>
        </body>
        </html>
        """

    def generate_visit_prescription_pdf(
        self,
        prescription: VisitPrescription,
        examiner_name: str,
    ) -> GeneratedVisitPrescriptionPdf:
        try:
            from weasyprint import HTML
        except Exception as exc:  # pragma: no cover - environment dependent
            raise AppException(
                status_code=500,
                code="pdf_generation_dependency_missing",
                message="PDF generation dependencies are not available. Install WeasyPrint requirements.",
            ) from exc

        output_dir = settings.prescription_media_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        customer = prescription.customer
        file_path = output_dir / (
            f"VISIT-PRESC-{customer.customer_id}-{prescription.visit_id}-V{prescription.version_number}.pdf"
        )

        try:
            HTML(string=self._build_html(prescription, examiner_name)).write_pdf(str(file_path))
        except Exception as exc:  # pragma: no cover - environment dependent
            raise AppException(
                status_code=500,
                code="prescription_pdf_generation_failed",
                message="Prescription PDF generation failed",
            ) from exc

        return GeneratedVisitPrescriptionPdf(file_path=file_path)
