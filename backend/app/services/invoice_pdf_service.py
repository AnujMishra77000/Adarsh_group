from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from html import escape
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import AppException
from app.models.bill import Bill


@dataclass(frozen=True)
class GeneratedInvoicePdf:
    file_path: Path


class InvoicePdfService:
    def __init__(self) -> None:
        self.company_name = "Adarsh Optical Group"

    @staticmethod
    def _format_money(value: Decimal) -> str:
        return f"{Decimal(value):,.2f}"

    @staticmethod
    def _format_date(value: datetime | None) -> str:
        if value is None:
            return "-"
        return value.astimezone(UTC).strftime("%d %b %Y, %I:%M %p UTC")

    @staticmethod
    def _format_simple_date(value) -> str:
        if value is None:
            return "-"
        return value.strftime("%d %b %Y")

    def _build_html(self, bill: Bill, staff_name: str) -> str:
        generated_at = self._format_date(datetime.now(UTC))
        customer_business_id = bill.customer.customer_id if bill.customer else "-"
        customer_contact_no = bill.customer.contact_no if bill.customer else "-"
        items = list(bill.items) or [
            {
                "item_type": "other",
                "item_name": bill.product_name,
                "quantity": Decimal("1.00"),
                "unit_price": bill.whole_price,
                "discount": bill.discount,
                "line_total": bill.final_price,
            }
        ]
        payments = list(bill.payments)

        item_rows = ""
        for item in items:
            item_type = item.item_type.value if hasattr(item, "item_type") else str(item["item_type"])
            item_name = item.item_name if hasattr(item, "item_name") else str(item["item_name"])
            quantity = item.quantity if hasattr(item, "quantity") else Decimal(item["quantity"])
            unit_price = item.unit_price if hasattr(item, "unit_price") else Decimal(item["unit_price"])
            discount = item.discount if hasattr(item, "discount") else Decimal(item["discount"])
            line_total = item.line_total if hasattr(item, "line_total") else Decimal(item["line_total"])
            item_rows += f"""
              <tr>
                <td>{escape(item_type.replace("_", " ").title())}</td>
                <td>{escape(item_name)}</td>
                <td class="num">{self._format_money(quantity)}</td>
                <td class="num">INR {self._format_money(unit_price)}</td>
                <td class="num">INR {self._format_money(discount)}</td>
                <td class="num">INR {self._format_money(line_total)}</td>
              </tr>
            """

        if payments:
            payment_rows = ""
            for payment in payments:
                payment_rows += f"""
                  <tr>
                    <td>{escape(payment.mode.value.replace("_", " ").title())}</td>
                    <td>INR {self._format_money(payment.amount)}</td>
                    <td>{escape(self._format_date(payment.paid_at))}</td>
                    <td>{escape(payment.reference_no or "-")}</td>
                  </tr>
                """
        else:
            payment_rows = """
              <tr>
                <td colspan="4">No payments recorded yet.</td>
              </tr>
            """

        logo_svg = """
        <svg width="56" height="56" viewBox="0 0 56 56" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect x="1" y="1" width="54" height="54" rx="12" fill="#0f172a" stroke="#1ea9ff" stroke-width="2"/>
          <path d="M17 38L25 17H31L39 38H34L32.5 33.5H23.5L22 38H17ZM24.8 30H31.2L28 20.6L24.8 30Z" fill="#93d9ff"/>
        </svg>
        """.strip()

        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8" />
          <style>
            @page {{ size: A4; margin: 24px; }}
            body {{
              font-family: DejaVu Sans, Arial, sans-serif;
              font-size: 12px;
              color: #111827;
              margin: 0;
            }}
            .container {{ border: 1px solid #d1d5db; border-radius: 12px; overflow: hidden; }}
            .header {{
              background: #0f172a;
              color: #e2e8f0;
              padding: 16px 18px;
              display: flex;
              align-items: center;
              justify-content: space-between;
            }}
            .header-left {{ display: flex; align-items: center; gap: 12px; }}
            .header-title {{ font-size: 18px; font-weight: 700; margin: 0; }}
            .header-subtitle {{ font-size: 11px; color: #93c5fd; margin-top: 4px; }}
            .meta {{ text-align: right; font-size: 11px; color: #cbd5e1; }}
            .content {{ padding: 16px 18px 20px 18px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 14px; }}
            th {{
              text-align: left;
              font-size: 11px;
              letter-spacing: .03em;
              text-transform: uppercase;
              color: #374151;
              border-bottom: 1px solid #d1d5db;
              padding: 8px 6px;
            }}
            td {{ border-bottom: 1px solid #e5e7eb; padding: 9px 6px; }}
            .num {{ text-align: right; white-space: nowrap; }}
            .label {{ color: #6b7280; width: 35%; }}
            .value {{ color: #111827; font-weight: 600; }}
            .totals {{ margin-top: 14px; width: 100%; }}
            .totals td {{ border: none; padding: 3px 0; }}
            .totals .name {{ color: #4b5563; }}
            .totals .amount {{ text-align: right; font-weight: 700; }}
            .totals .final {{ font-size: 14px; color: #0f172a; }}
            .footer {{
              border-top: 1px dashed #d1d5db;
              margin-top: 16px;
              padding-top: 10px;
              color: #4b5563;
              font-size: 11px;
            }}
            .notes {{ margin-top: 12px; background: #f8fafc; border-radius: 8px; padding: 10px; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <div class="header-left">
                {logo_svg}
                <div>
                  <p class="header-title">{escape(self.company_name)}</p>
                  <p class="header-subtitle">Invoice / Bill</p>
                </div>
              </div>
              <div class="meta">
                <div><strong>Bill:</strong> {escape(bill.bill_number)}</div>
                <div><strong>Generated:</strong> {escape(generated_at)}</div>
              </div>
            </div>

            <div class="content">
              <table>
                <tbody>
                  <tr>
                    <td class="label">Customer Name</td>
                    <td class="value">{escape(bill.customer_name_snapshot)}</td>
                  </tr>
                  <tr>
                    <td class="label">Customer ID</td>
                    <td class="value">{escape(customer_business_id)}</td>
                  </tr>
                  <tr>
                    <td class="label">Mobile Number</td>
                    <td class="value">{escape(customer_contact_no)}</td>
                  </tr>
                  <tr>
                    <td class="label">Payment Status</td>
                    <td class="value">{escape(bill.payment_status.value.upper())}</td>
                  </tr>
                </tbody>
              </table>

              <table>
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Item</th>
                    <th class="num">Qty</th>
                    <th class="num">Unit</th>
                    <th class="num">Discount</th>
                    <th class="num">Line Total</th>
                  </tr>
                </thead>
                <tbody>
                  {item_rows}
                </tbody>
              </table>

              <table>
                <thead>
                  <tr>
                    <th>Payment Mode</th>
                    <th>Amount</th>
                    <th>Paid At</th>
                    <th>Reference</th>
                  </tr>
                </thead>
                <tbody>
                  {payment_rows}
                </tbody>
              </table>

              <table class="totals">
                <tbody>
                  <tr>
                    <td class="name">Subtotal</td>
                    <td class="amount">INR {self._format_money(bill.subtotal)}</td>
                  </tr>
                  <tr>
                    <td class="name">Discount Total</td>
                    <td class="amount">INR {self._format_money(bill.discount_total)}</td>
                  </tr>
                  <tr>
                    <td class="name">Tax Total</td>
                    <td class="amount">INR {self._format_money(bill.tax_total)}</td>
                  </tr>
                  <tr>
                    <td class="name">Grand Total</td>
                    <td class="amount">INR {self._format_money(bill.grand_total)}</td>
                  </tr>
                  <tr>
                    <td class="name">Paid Total</td>
                    <td class="amount">INR {self._format_money(bill.paid_total)}</td>
                  </tr>
                  <tr>
                    <td class="name final">Balance Amount</td>
                    <td class="amount final">INR {self._format_money(bill.balance_amount)}</td>
                  </tr>
                </tbody>
              </table>

              <div class="notes">
                <strong>Notes:</strong> {escape(bill.notes or "-")}
              </div>

              <div class="footer">
                <div><strong>Delivery Date:</strong> {escape(self._format_simple_date(bill.delivery_date))}</div>
                <div><strong>Handled By:</strong> {escape(staff_name)}</div>
              </div>
            </div>
          </div>
        </body>
        </html>
        """

    def generate_invoice_pdf(self, bill: Bill, staff_name: str) -> GeneratedInvoicePdf:
        try:
            from weasyprint import HTML
        except Exception as exc:  # pragma: no cover - environment dependent
            raise AppException(
                status_code=500,
                code="pdf_generation_dependency_missing",
                message="PDF generation dependencies are not available. Install WeasyPrint requirements.",
            ) from exc

        output_dir = settings.invoice_media_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        file_path = output_dir / f"{bill.bill_number}.pdf"
        html_content = self._build_html(bill=bill, staff_name=staff_name)

        try:
            HTML(string=html_content).write_pdf(str(file_path))
        except Exception as exc:  # pragma: no cover - environment dependent
            raise AppException(
                status_code=500,
                code="pdf_generation_failed",
                message="Invoice PDF generation failed",
            ) from exc

        return GeneratedInvoicePdf(file_path=file_path)
