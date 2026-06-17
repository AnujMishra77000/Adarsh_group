from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    STAFF = "staff"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class PaymentMode(str, Enum):
    CASH = "cash"
    UPI = "upi"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    OTHER = "other"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"


class BillItemType(str, Enum):
    FRAME = "frame"
    LENS = "lens"
    COATING = "coating"
    CONTACT_LENS = "contact_lens"
    EYE_TEST = "eye_test"
    REPAIR = "repair"
    ACCESSORY = "accessory"
    OTHER = "other"


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WhatsAppMessageType(str, Enum):
    TEXT = "text"
    TEMPLATE = "template"
    DOCUMENT = "document"


class WhatsAppStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class WhatsAppModuleType(str, Enum):
    CUSTOMER = "customer"
    PRESCRIPTION = "prescription"
    BILL = "bill"
    CAMPAIGN = "campaign"


def enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]
