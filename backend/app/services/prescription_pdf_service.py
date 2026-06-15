from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from html import escape
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import AppException
from app.models.customer import Customer
from app.models.prescription import Prescription


@dataclass
class GeneratedPdf:
    file_path: Path
    public_url: str


class PrescriptionPdfService:
    def __init__(self) -> None:
        self.company_name = "Aadarsh Eye Boutique Care Centre"

    @staticmethod
    def _format_datetime(value: datetime | None) -> str:
        if value is None:
            return "-"
        return value.astimezone(UTC).strftime("%d %b %Y, %I:%M %p UTC")

    @staticmethod
    def _format_date(value) -> str:
        if value is None:
            return "-"
        return value.strftime("%d %b %Y")

    @staticmethod
    def _format_decimal(value: Decimal | None) -> str:
        if value is None:
            return "-"
        return f"{Decimal(value):.2f}"

    def _build_html(self, prescription: Prescription, customer: Customer, staff_name: str) -> str:
        generated_at = self._format_datetime(datetime.now(UTC))

        return f"""
        <!DOCTYPE html>
        <html lang=\"en\">
        <head>
          <meta charset=\"utf-8\" />
          <style>
            @page {{ size: A4; margin: 24px; }}
            body {{
              font-family: DejaVu Sans, Arial, sans-serif;
              font-size: 12px;
              color: #111827;
              margin: 0;
            }}
            .wrapper {{ border: 1px solid #d1d5db; border-radius: 12px; overflow: hidden; }}
            .header {{
              background: #0f172a;
              color: #e2e8f0;
              padding: 16px 18px;
            }}
            .title {{ margin: 0; font-size: 18px; font-weight: 700; }}
            .subtitle {{ margin-top: 4px; font-size: 11px; color: #93c5fd; }}
            .meta {{ margin-top: 10px; font-size: 11px; color: #cbd5e1; }}
            .content {{ padding: 16px 18px 20px 18px; }}
            .grid {{ display: table; width: 100%; border-collapse: collapse; margin-top: 12px; }}
            .row {{ display: table-row; }}
            .head .cell {{
              font-size: 11px;
              text-transform: uppercase;
              color: #374151;
              border-bottom: 1px solid #d1d5db;
              font-weight: 700;
            }}
            .cell {{ display: table-cell; padding: 8px 6px; border-bottom: 1px solid #e5e7eb; }}
            .section-title {{ margin-top: 14px; font-size: 13px; font-weight: 700; color: #0f172a; }}
            .notes {{ margin-top: 12px; border-radius: 8px; background: #f8fafc; padding: 10px; }}
            .footer {{ margin-top: 14px; border-top: 1px dashed #d1d5db; padding-top: 10px; font-size: 11px; color: #4b5563; }}
            .label {{ color: #6b7280; }}
            .value {{ color: #111827; font-weight: 600; }}
          </style>
        </head>
        <body>
          <div class=\"wrapper\">
            <div class=\"header\">
              <p class=\"title\">{escape(self.company_name)}</p>
              <p class=\"subtitle\">Optical Prescription</p>
              <div class=\"meta\">Generated: {escape(generated_at)}</div>
            </div>

            <div class=\"content\">
              <div>
                <span class=\"label\">Customer:</span>
                <span class=\"value\"> {escape(customer.name)} ({escape(customer.customer_id)})</span>
              </div>
              <div style=\"margin-top:4px;\">
                <span class=\"label\">Contact:</span>
                <span class=\"value\"> {escape(customer.contact_no)}</span>
              </div>
              <div style=\"margin-top:4px;\">
                <span class=\"label\">Prescription Date:</span>
                <span class=\"value\"> {escape(self._format_date(prescription.prescription_date))}</span>
              </div>

              <p class=\"section-title\">Lens Parameters</p>
              <div class=\"grid\">
                <div class=\"row head\">
                  <div class=\"cell\">Eye</div>
                  <div class=\"cell\">SPH</div>
                  <div class=\"cell\">CYL</div>
                  <div class=\"cell\">Axis</div>
                  <div class=\"cell\">VN</div>
                </div>
                <div class=\"row\">
                  <div class=\"cell\"><strong>Right</strong></div>
                  <div class=\"cell\">{escape(self._format_decimal(prescription.right_sph))}</div>
                  <div class=\"cell\">{escape(self._format_decimal(prescription.right_cyl))}</div>
                  <div class=\"cell\">{escape(str(prescription.right_axis) if prescription.right_axis is not None else '-')}</div>
                  <div class=\"cell\">{escape(prescription.right_vn or '-')}</div>
                </div>
                <div class=\"row\">
                  <div class=\"cell\"><strong>Left</strong></div>
                  <div class=\"cell\">{escape(self._format_decimal(prescription.left_sph))}</div>
                  <div class=\"cell\">{escape(self._format_decimal(prescription.left_cyl))}</div>
                  <div class=\"cell\">{escape(str(prescription.left_axis) if prescription.left_axis is not None else '-')}</div>
                  <div class=\"cell\">{escape(prescription.left_vn or '-')}</div>
                </div>
              </div>

              <p class=\"section-title\">Additional Measurements</p>
              <div class=\"grid\">
                <div class=\"row\">
                  <div class=\"cell\"><strong>FH</strong></div>
                  <div class=\"cell\">{escape(prescription.fh or '-')}</div>
                  <div class=\"cell\"><strong>ADD Power</strong></div>
                  <div class=\"cell\">{escape(self._format_decimal(prescription.add_power))}</div>
                  <div class=\"cell\"><strong>PD:</strong> {escape(self._format_decimal(prescription.pd))}</div>
                </div>
              </div>

              <div class=\"notes\"><strong>Notes:</strong> {escape(prescription.notes or '-')}</div>

              <div class=\"footer\">
                <div><strong>Prepared By:</strong> {escape(staff_name)}</div>
                <div><strong>Record Updated:</strong> {escape(self._format_datetime(prescription.updated_at))}</div>
              </div>
            </div>
          </div>
        </body>
        </html>
        """

    def _build_public_url(self, absolute_path: Path) -> str:
        media_root = settings.media_root_path.resolve()
        try:
            relative = absolute_path.resolve().relative_to(media_root)
        except ValueError:
            return str(absolute_path)

        return f"{settings.backend_public_url}{settings.media_url_prefix}/{relative.as_posix()}"

    def generate_prescription_pdf(self, prescription: Prescription, customer: Customer, staff_name: str) -> GeneratedPdf:
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

        file_path = output_dir / f"PRESC-{customer.customer_id}-{prescription.id}.pdf"
        html_content = self._build_html(prescription=prescription, customer=customer, staff_name=staff_name)

        try:
            HTML(string=html_content).write_pdf(str(file_path))
        except Exception as exc:  # pragma: no cover - environment dependent
            raise AppException(
                status_code=500,
                code="prescription_pdf_generation_failed",
                message="Prescription PDF generation failed",
            ) from exc

        return GeneratedPdf(file_path=file_path, public_url=self._build_public_url(file_path))
