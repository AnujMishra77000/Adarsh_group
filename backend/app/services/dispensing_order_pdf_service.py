from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import AppException
from app.models.dispensing_order import DispensingOrder


@dataclass
class GeneratedVendorOrderPdf:
    file_path: Path


class DispensingOrderPdfService:
    @staticmethod
    def _text(value: object) -> str:
        normalized = str(value).strip() if value is not None else ""
        return escape(normalized or "-")

    @classmethod
    def _rows(cls, items: tuple[tuple[str, object], ...]) -> str:
        return "".join(
            f"<tr><th>{escape(label)}</th><td>{cls._text(value)}</td></tr>"
            for label, value in items
        )

    @classmethod
    def _eye_row(cls, order: DispensingOrder, section: str, eye: str) -> str:
        prescription_data = order.prescription.data or {}
        section_data = prescription_data.get(section)
        eye_data = section_data.get(eye) if isinstance(section_data, dict) else {}
        eye_data = eye_data if isinstance(eye_data, dict) else {}
        return (
            f"<tr><td><strong>{escape(eye.title())}</strong></td>"
            f"<td>{cls._text(eye_data.get('sph'))}</td>"
            f"<td>{cls._text(eye_data.get('cyl'))}</td>"
            f"<td>{cls._text(eye_data.get('axis'))}</td>"
            f"<td>{cls._text(eye_data.get('add'))}</td>"
            f"<td>{cls._text(eye_data.get('va'))}</td></tr>"
        )

    def _build_html(self, order: DispensingOrder, branch_name: str) -> str:
        frame = order.frame_data or {}
        measurements = order.measurement_data or {}
        lens = order.lens_data or {}
        prescription_identifier = f"VISIT-{order.visit_id}-RX-V{order.prescription.version_number}"
        frame_rows = self._rows(
            (
                ("Brand", frame.get("brand")),
                ("Model number", frame.get("model_number")),
                ("Colour code", frame.get("colour_code")),
                ("Frame type", frame.get("frame_type")),
                ("Barcode", frame.get("barcode")),
                ("A size (mm)", frame.get("a_size_mm")),
                ("B size (mm)", frame.get("b_size_mm")),
                ("DBL (mm)", frame.get("dbl_mm")),
                ("Temple length (mm)", frame.get("temple_length_mm")),
                ("Effective diameter (mm)", frame.get("effective_diameter_mm")),
            )
        )
        measurement_rows = self._rows(
            (
                ("Right monocular PD (mm)", measurements.get("right_monocular_pd_mm")),
                ("Left monocular PD (mm)", measurements.get("left_monocular_pd_mm")),
                ("Total PD (mm)", measurements.get("total_pd_mm")),
                ("Right fitting height (mm)", measurements.get("right_fitting_height_mm")),
                ("Left fitting height (mm)", measurements.get("left_fitting_height_mm")),
                ("Right segment height (mm)", measurements.get("right_segment_height_mm")),
                ("Left segment height (mm)", measurements.get("left_segment_height_mm")),
                ("Pantoscopic tilt (degrees)", measurements.get("pantoscopic_tilt_degrees")),
                ("Vertex distance (mm)", measurements.get("vertex_distance_mm")),
                ("Measured by", measurements.get("measured_by")),
                ("Measurement notes", measurements.get("measurement_notes")),
            )
        )
        lens_rows = self._rows(
            (
                ("Lens type", str(lens.get("lens_type", "")).replace("_", " ").title()),
                ("Brand", lens.get("brand")),
                ("Material", lens.get("material")),
                ("Index", lens.get("index")),
                ("Design", lens.get("design")),
                ("Coating", lens.get("coating")),
                ("Tint / photochromic", lens.get("tint_or_photochromic")),
            )
        )

        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8" />
          <style>
            @page {{ size: A4; margin: 22px; }}
            body {{ font-family: DejaVu Sans, Arial, sans-serif; color: #172033; font-size: 11px; margin: 0; }}
            .header {{ border-bottom: 3px solid #be185d; padding-bottom: 10px; }}
            h1 {{ font-size: 19px; margin: 0; }}
            .branch {{ color: #475569; margin-top: 4px; }}
            .meta {{ margin: 13px 0; padding: 9px; background: #f8fafc; border: 1px solid #e2e8f0; }}
            h2 {{ font-size: 13px; margin: 14px 0 6px; }}
            table {{ border-collapse: collapse; width: 100%; page-break-inside: avoid; }}
            th, td {{ border: 1px solid #cbd5e1; padding: 6px; text-align: left; }}
            th {{ background: #f8fafc; color: #475569; width: 38%; }}
            .power th {{ width: auto; }}
            .instructions {{ margin-top: 14px; padding: 9px; border: 1px solid #cbd5e1; }}
            .footer {{ margin-top: 15px; padding-top: 8px; border-top: 1px solid #cbd5e1; color: #64748b; }}
          </style>
        </head>
        <body>
          <div class="header"><h1>Adarsh Optical Group</h1><div class="branch">Vendor Spectacle Order · {escape(branch_name)}</div></div>
          <div class="meta"><strong>Order reference:</strong> {escape(order.order_reference)} &nbsp; · &nbsp; <strong>Prescription:</strong> {escape(prescription_identifier)}</div>
          <h2>Prescription Lens Powers</h2>
          <table class="power"><thead><tr><th>Eye</th><th>Sphere</th><th>Cylinder</th><th>Axis</th><th>Add</th><th>VA</th></tr></thead><tbody>
            {self._eye_row(order, 'distance', 'right')}
            {self._eye_row(order, 'distance', 'left')}
            {self._eye_row(order, 'near', 'right')}
            {self._eye_row(order, 'near', 'left')}
          </tbody></table>
          <h2>Frame</h2><table>{frame_rows}</table>
          <h2>Dispensing Measurements</h2><table>{measurement_rows}</table>
          <h2>Lens Specification</h2><table>{lens_rows}</table>
          <div class="instructions"><strong>Manufacturing instructions</strong><br />{self._text(order.manufacturing_instructions)}</div>
          <div class="footer">Vendor fulfilment document · Prescription version {order.prescription.version_number}</div>
        </body>
        </html>
        """

    def generate_vendor_order_pdf(self, order: DispensingOrder, branch_name: str) -> GeneratedVendorOrderPdf:
        try:
            from weasyprint import HTML
        except Exception as exc:  # pragma: no cover - environment dependent
            raise AppException(
                status_code=500,
                code="pdf_generation_dependency_missing",
                message="PDF generation dependencies are not available. Install WeasyPrint requirements.",
            ) from exc

        output_dir = settings.vendor_order_media_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / f"{order.order_reference}.pdf"
        try:
            HTML(string=self._build_html(order, branch_name)).write_pdf(str(file_path))
        except Exception as exc:  # pragma: no cover - environment dependent
            raise AppException(
                status_code=500,
                code="dispensing_order_pdf_generation_failed",
                message="Vendor order PDF generation failed",
            ) from exc
        return GeneratedVendorOrderPdf(file_path=file_path)

