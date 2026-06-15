from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

import structlog

from app.core.config import settings
from app.models.bill import Bill
from app.models.customer import Customer

logger = structlog.get_logger(__name__)


class EmailService:
    def __init__(self) -> None:
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.smtp_from_email = settings.smtp_from_email or settings.smtp_username
        self.smtp_from_name = settings.smtp_from_name
        self.smtp_use_tls = settings.smtp_use_tls
        self.smtp_use_ssl = settings.smtp_use_ssl
        self.smtp_timeout_seconds = settings.smtp_timeout_seconds

    def is_configured(self) -> bool:
        return bool(
            settings.customer_welcome_email_enabled
            and self.smtp_host
            and self.smtp_port
            and self.smtp_username
            and self.smtp_password
            and self.smtp_from_email
        )

    def _send_message(self, message: EmailMessage) -> None:
        if self.smtp_use_ssl:
            with smtplib.SMTP_SSL(
                self.smtp_host,
                self.smtp_port,
                timeout=self.smtp_timeout_seconds,
            ) as smtp:
                smtp.login(self.smtp_username or "", self.smtp_password or "")
                smtp.send_message(message)
            return

        with smtplib.SMTP(
            self.smtp_host,
            self.smtp_port,
            timeout=self.smtp_timeout_seconds,
        ) as smtp:
            if self.smtp_use_tls:
                smtp.starttls(context=ssl.create_default_context())
            smtp.login(self.smtp_username or "", self.smtp_password or "")
            smtp.send_message(message)

    @staticmethod
    def _build_welcome_email(customer: Customer) -> tuple[str, str, str]:
        subject = f"Welcome to {settings.project_name}"

        plain_text = (
            f"Hello {customer.name},\n\n"
            f"Welcome to {settings.project_name}.\n"
            f"Your customer ID is: {customer.customer_id}\n\n"
            "Thank you for choosing us.\n"
            "If you have any queries, please contact our staff.\n\n"
            "Regards,\n"
            "Aadarsh Eye Boutique Care Centre"
        )

        html_text = f"""
        <html>
          <body style=\"font-family: Arial, sans-serif; line-height: 1.6; color: #111827;\">
            <p>Hello <strong>{customer.name}</strong>,</p>
            <p>Welcome to <strong>{settings.project_name}</strong>.</p>
            <p>Your customer ID is: <strong>{customer.customer_id}</strong></p>
            <p>Thank you for choosing us.</p>
            <p>If you have any queries, please contact our staff.</p>
            <p>Regards,<br />Aadarsh Eye Boutique Care Centre</p>
          </body>
        </html>
        """.strip()

        return subject, plain_text, html_text

    @staticmethod
    def _build_bill_email(customer: Customer, bill: Bill) -> tuple[str, str, str]:
        subject = f"Invoice {bill.bill_number} - {settings.project_name}"

        plain_text = (
            f"Hello {customer.name},\n\n"
            f"Please find attached your invoice {bill.bill_number}.\n"
            f"Product: {bill.product_name}\n"
            f"Final amount: INR {bill.final_price}\n"
            f"Balance amount: INR {bill.balance_amount}\n\n"
            "Thank you for visiting Aadarsh Eye Boutique Care Centre.\n\n"
            "Regards,\n"
            "Aadarsh Eye Boutique Care Centre"
        )

        html_text = f"""
        <html>
          <body style=\"font-family: Arial, sans-serif; line-height: 1.6; color: #111827;\">
            <p>Hello <strong>{customer.name}</strong>,</p>
            <p>Please find attached your invoice <strong>{bill.bill_number}</strong>.</p>
            <p>
              Product: <strong>{bill.product_name}</strong><br />
              Final amount: <strong>INR {bill.final_price}</strong><br />
              Balance amount: <strong>INR {bill.balance_amount}</strong>
            </p>
            <p>Thank you for visiting Aadarsh Eye Boutique Care Centre.</p>
            <p>Regards,<br />Aadarsh Eye Boutique Care Centre</p>
          </body>
        </html>
        """.strip()

        return subject, plain_text, html_text

    def send_customer_welcome_email(self, customer: Customer) -> bool:
        recipient = (customer.email or "").strip()
        if not recipient:
            return False

        if not self.is_configured():
            logger.warning(
                "email.welcome.skipped_missing_configuration",
                customer_id=customer.id,
                recipient=recipient,
            )
            return False

        subject, plain_text, html_text = self._build_welcome_email(customer)

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = formataddr((self.smtp_from_name, self.smtp_from_email or ""))
        message["To"] = recipient
        message.set_content(plain_text)
        message.add_alternative(html_text, subtype="html")

        try:
            self._send_message(message)

            logger.info(
                "email.welcome.sent",
                customer_id=customer.id,
                customer_business_id=customer.customer_id,
                recipient=recipient,
            )
            return True
        except Exception as exc:  # pragma: no cover - defensive email transport guard
            logger.error(
                "email.welcome.failed",
                customer_id=customer.id,
                recipient=recipient,
                error=str(exc),
            )
            return False

    def send_bill_invoice_email(self, customer: Customer, bill: Bill, invoice_pdf_path: Path) -> bool:
        recipient = (customer.email or "").strip()
        if not recipient:
            return False

        if not self.is_configured():
            logger.warning(
                "email.bill.skipped_missing_configuration",
                bill_id=bill.id,
                customer_id=customer.id,
                recipient=recipient,
            )
            return False

        if not invoice_pdf_path.exists() or not invoice_pdf_path.is_file():
            logger.warning(
                "email.bill.skipped_missing_pdf_file",
                bill_id=bill.id,
                customer_id=customer.id,
                recipient=recipient,
                invoice_path=str(invoice_pdf_path),
            )
            return False

        subject, plain_text, html_text = self._build_bill_email(customer=customer, bill=bill)

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = formataddr((self.smtp_from_name, self.smtp_from_email or ""))
        message["To"] = recipient
        message.set_content(plain_text)
        message.add_alternative(html_text, subtype="html")

        try:
            with invoice_pdf_path.open("rb") as pdf_file:
                pdf_bytes = pdf_file.read()
            message.add_attachment(
                pdf_bytes,
                maintype="application",
                subtype="pdf",
                filename=invoice_pdf_path.name,
            )

            self._send_message(message)
            logger.info(
                "email.bill.sent",
                bill_id=bill.id,
                bill_number=bill.bill_number,
                customer_id=customer.id,
                recipient=recipient,
            )
            return True
        except Exception as exc:  # pragma: no cover - defensive email transport guard
            logger.error(
                "email.bill.failed",
                bill_id=bill.id,
                bill_number=bill.bill_number,
                customer_id=customer.id,
                recipient=recipient,
                error=str(exc),
            )
            return False
