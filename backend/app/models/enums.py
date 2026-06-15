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


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"


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
