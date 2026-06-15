from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol

import httpx


class SupportsRequest(Protocol):
    def request(self, method: str, url: str, **kwargs: Any) -> Any: ...

    def close(self) -> None: ...


@dataclass
class QaResult:
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def mark_pass(self, message: str) -> None:
        self.passed.append(message)
        print(f"[PASS] {message}")

    def mark_fail(self, message: str) -> None:
        self.failed.append(message)
        print(f"[FAIL] {message}")

    def mark_warn(self, message: str) -> None:
        self.warnings.append(message)
        print(f"[WARN] {message}")


def _extract_error_message(payload: Any) -> str:
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict):
            code = err.get("code")
            message = err.get("message")
            if code and message:
                return f"{code}: {message}"
            if message:
                return str(message)
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
        if isinstance(detail, dict):
            err = detail.get("error")
            if isinstance(err, dict):
                code = err.get("code")
                message = err.get("message")
                if code and message:
                    return f"{code}: {message}"
                if message:
                    return str(message)
    return str(payload)


def _assert_status(
    *,
    result: QaResult,
    step: str,
    response: Any,
    allowed: set[int],
    warn_only: bool = False,
) -> bool:
    if response.status_code in allowed:
        result.mark_pass(f"{step} (HTTP {response.status_code})")
        return True

    message = f"{step} failed: HTTP {response.status_code} - {_extract_error_message(response.json())}"
    if warn_only:
        result.mark_warn(message)
    else:
        result.mark_fail(message)
    return False


def run_qa(
    client: SupportsRequest,
    *,
    result: QaResult,
    admin_email: str,
    admin_password: str,
    strict_external: bool,
) -> int:
    unique = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    contact_no = f"9{unique[-9:]}"
    vendor_no = f"8{unique[-9:]}"

    access_token: str | None = None
    refresh_token: str | None = None

    # 1) Login
    login_resp = client.request(
        "POST",
        "/auth/login",
        json={"email": admin_email, "password": admin_password},
    )
    if not _assert_status(result=result, step="Admin login", response=login_resp, allowed={200}):
        return 1

    login_payload = login_resp.json()
    access_token = login_payload["access_token"]
    refresh_token = login_payload["refresh_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # 2) Auth me
    me_resp = client.request("GET", "/auth/me", headers=auth_headers)
    if not _assert_status(result=result, step="Fetch /auth/me", response=me_resp, allowed={200}):
        return 1

    # 3) Create customer
    customer_payload = {
        "name": f"QA Customer {unique}",
        "age": 31,
        "contact_no": contact_no,
        "whatsapp_no": contact_no,
        "gender": "male",
        "address": "QA Street, Bengaluru",
        "purpose_of_visit": "QA validation",
        "whatsapp_opt_in": True,
    }
    customer_resp = client.request("POST", "/customers", json=customer_payload, headers=auth_headers)
    if not _assert_status(result=result, step="Create customer", response=customer_resp, allowed={201}):
        return 1
    customer = customer_resp.json()
    customer_id = int(customer["id"])

    # 4) Customer detail
    customer_detail_resp = client.request("GET", f"/customers/{customer_id}", headers=auth_headers)
    if not _assert_status(result=result, step="Fetch customer detail", response=customer_detail_resp, allowed={200}):
        return 1

    # 5) Create vendor
    vendor_payload = {
        "vendor_name": f"QA Vendor {unique}",
        "contact_person": "QA Ops",
        "whatsapp_no": vendor_no,
        "address": "Vendor QA Zone",
        "is_active": True,
    }
    vendor_resp = client.request("POST", "/vendors", json=vendor_payload, headers=auth_headers)
    if not _assert_status(result=result, step="Create vendor", response=vendor_resp, allowed={201}):
        return 1
    vendor_id = int(vendor_resp.json()["id"])

    # 6) Create prescription
    prescription_payload = {
        "customer_id": customer_id,
        "prescription_date": date.today().isoformat(),
        "right_sph": -1.25,
        "right_cyl": -0.5,
        "right_axis": 90,
        "right_vn": "6/6",
        "left_sph": -1.0,
        "left_cyl": -0.25,
        "left_axis": 95,
        "left_vn": "6/6",
        "fh": "18",
        "add_power": 1.0,
        "pd": 62.0,
        "notes": "QA prescription",
    }
    prescription_resp = client.request("POST", "/prescriptions", json=prescription_payload, headers=auth_headers)
    if not _assert_status(result=result, step="Create prescription", response=prescription_resp, allowed={201}):
        return 1
    prescription_id = int(prescription_resp.json()["id"])

    # 7) Validate latest prescription first for customer
    list_pres_resp = client.request("GET", f"/prescriptions/customer/{customer_id}", headers=auth_headers)
    if not _assert_status(result=result, step="List customer prescriptions", response=list_pres_resp, allowed={200}):
        return 1
    list_pres_payload = list_pres_resp.json()
    if not list_pres_payload or int(list_pres_payload[0]["id"]) != prescription_id:
        result.mark_fail("Latest prescription is not first in customer prescription list")
        return 1
    result.mark_pass("Latest prescription appears first")

    # 8) Generate prescription PDF
    prescription_pdf_resp = client.request("POST", f"/prescriptions/{prescription_id}/pdf", headers=auth_headers)
    if not _assert_status(result=result, step="Generate prescription PDF", response=prescription_pdf_resp, allowed={200}):
        return 1
    prescription_pdf_url = prescription_pdf_resp.json().get("pdf_url")
    if not isinstance(prescription_pdf_url, str) or not prescription_pdf_url:
        result.mark_fail("Prescription PDF URL is missing")
        return 1
    result.mark_pass("Prescription PDF URL generated")

    # 9) Send prescription to vendor (external dependency)
    send_prescription_resp = client.request(
        "POST",
        f"/prescriptions/{prescription_id}/send-vendor",
        json={"vendor_id": vendor_id, "caption": "QA send to vendor"},
        headers=auth_headers,
    )
    if send_prescription_resp.status_code == 200:
        result.mark_pass("Send prescription to vendor on WhatsApp")
    else:
        message = _extract_error_message(send_prescription_resp.json())
        target = "Send prescription to vendor on WhatsApp"
        if strict_external:
            result.mark_fail(f"{target} failed: HTTP {send_prescription_resp.status_code} - {message}")
        else:
            result.mark_warn(
                f"{target} not fully validated (expected without WhatsApp creds): HTTP {send_prescription_resp.status_code} - {message}"
            )

    # 10) Create bill
    bill_payload = {
        "customer_id": customer_id,
        "product_name": "Blue Block Lens",
        "frame_name": "QA Frame",
        "whole_price": 2500,
        "discount": 200,
        "paid_amount": 1000,
        "payment_mode": "upi",
        "delivery_date": (date.today() + timedelta(days=3)).isoformat(),
        "notes": "QA billing check",
    }
    bill_resp = client.request("POST", "/bills", json=bill_payload, headers=auth_headers)
    if not _assert_status(result=result, step="Create bill", response=bill_resp, allowed={201}):
        return 1
    bill = bill_resp.json()
    bill_id = int(bill["id"])

    expected_final = Decimal("2300.00")
    expected_balance = Decimal("1300.00")
    actual_final = Decimal(str(bill["final_price"]))
    actual_balance = Decimal(str(bill["balance_amount"]))
    if actual_final != expected_final or actual_balance != expected_balance:
        result.mark_fail(
            f"Bill calculation mismatch. expected final={expected_final} balance={expected_balance}, "
            f"got final={actual_final} balance={actual_balance}"
        )
        return 1
    result.mark_pass("Bill discount/final/balance calculations are correct")

    # 11) Generate bill PDF
    bill_pdf_resp = client.request("POST", f"/bills/{bill_id}/generate-pdf", headers=auth_headers)
    if not _assert_status(result=result, step="Generate bill PDF", response=bill_pdf_resp, allowed={200}):
        return 1

    # 12) Send bill via WhatsApp (external dependency)
    send_bill_resp = client.request("POST", f"/bills/{bill_id}/send-whatsapp", headers=auth_headers)
    if send_bill_resp.status_code == 200:
        result.mark_pass("Send bill to customer on WhatsApp")
    else:
        message = _extract_error_message(send_bill_resp.json())
        target = "Send bill to customer on WhatsApp"
        if strict_external:
            result.mark_fail(f"{target} failed: HTTP {send_bill_resp.status_code} - {message}")
        else:
            result.mark_warn(
                f"{target} not fully validated (expected without WhatsApp creds): HTTP {send_bill_resp.status_code} - {message}"
            )

    # 13) Create campaign
    campaign_payload = {
        "title": f"QA Campaign {unique}",
        "message_body": "QA campaign send test",
        "scheduled_at": (datetime.now(UTC) + timedelta(minutes=2)).isoformat(),
    }
    campaign_resp = client.request("POST", "/campaigns", json=campaign_payload, headers=auth_headers)
    if not _assert_status(result=result, step="Create campaign", response=campaign_resp, allowed={201}):
        return 1
    campaign_id = int(campaign_resp.json()["id"])

    # 14) Schedule campaign (requires broker/worker for full verification)
    schedule_resp = client.request("POST", f"/campaigns/{campaign_id}/schedule", headers=auth_headers)
    if schedule_resp.status_code == 200:
        result.mark_pass("Schedule campaign")
    else:
        message = _extract_error_message(schedule_resp.json())
        target = "Schedule campaign"
        if strict_external:
            result.mark_fail(f"{target} failed: HTTP {schedule_resp.status_code} - {message}")
        else:
            result.mark_warn(
                f"{target} not fully validated (likely Redis/Celery not running): "
                f"HTTP {schedule_resp.status_code} - {message}"
            )

    # 15) Campaign logs endpoint
    logs_resp = client.request("GET", f"/campaigns/{campaign_id}/logs", headers=auth_headers)
    if not _assert_status(result=result, step="Fetch campaign logs", response=logs_resp, allowed={200}):
        return 1

    # 16) Dashboard analytics
    dash_resp = client.request("GET", "/analytics/dashboard", headers=auth_headers)
    if not _assert_status(result=result, step="Fetch dashboard analytics", response=dash_resp, allowed={200}):
        return 1

    # 17) Revenue summary + timeseries
    rev_summary_resp = client.request("GET", "/analytics/revenue", params={"range": "last_7_days"}, headers=auth_headers)
    if not _assert_status(result=result, step="Fetch revenue summary", response=rev_summary_resp, allowed={200}):
        return 1

    rev_ts_resp = client.request("GET", "/analytics/revenue/timeseries", params={"range": "last_30_days"}, headers=auth_headers)
    if not _assert_status(result=result, step="Fetch revenue timeseries", response=rev_ts_resp, allowed={200}):
        return 1

    # 18) Logout
    if refresh_token:
        logout_resp = client.request("POST", "/auth/logout", json={"refresh_token": refresh_token})
        _assert_status(result=result, step="Logout", response=logout_resp, allowed={200})

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual QA smoke flow for Eye Boutique CRM")
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1", help="API base URL for live HTTP mode")
    parser.add_argument("--admin-email", default="admin@aadarsh-eye.com")
    parser.add_argument("--admin-password", default="Admin@12345")
    parser.add_argument(
        "--strict-external",
        action="store_true",
        help="Fail when WhatsApp/Redis/Celery dependent checks fail",
    )
    parser.add_argument(
        "--in-process",
        action="store_true",
        help="Run in-process using FastAPI TestClient (no running server required)",
    )
    args = parser.parse_args()

    result = QaResult()

    if args.in_process:
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app, base_url="http://testserver/api/v1") as client:
            run_qa(
                client,
                result=result,
                admin_email=args.admin_email,
                admin_password=args.admin_password,
                strict_external=args.strict_external,
            )
    else:
        with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
            run_qa(
                client,
                result=result,
                admin_email=args.admin_email,
                admin_password=args.admin_password,
                strict_external=args.strict_external,
            )

    print("\n=== QA Summary ===")
    print(f"Passed: {len(result.passed)}")
    print(f"Warnings: {len(result.warnings)}")
    print(f"Failed: {len(result.failed)}")

    if result.warnings:
        print("\nWarnings:")
        for item in result.warnings:
            print(f"- {item}")

    if result.failed:
        print("\nFailures:")
        for item in result.failed:
            print(f"- {item}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
