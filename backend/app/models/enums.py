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


class VisitStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ExamSectionState(str, Enum):
    INCOMPLETE = "incomplete"
    COMPLETE = "complete"
    OPTIONAL = "optional"
    NOT_APPLICABLE = "not_applicable"
    FUTURE = "future"


class PrescriptionVersionStatus(str, Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"
    SUPERSEDED = "superseded"
    CANCELLED = "cancelled"


class DispensingOrderStatus(str, Enum):
    DRAFT = "draft"
    READY_FOR_VENDOR = "ready_for_vendor"
    SENT_TO_VENDOR = "sent_to_vendor"
    IN_PRODUCTION = "in_production"
    READY_FOR_DELIVERY = "ready_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class LensType(str, Enum):
    SINGLE_VISION = "single_vision"
    BIFOCAL = "bifocal"
    PROGRESSIVE = "progressive"
    OFFICE_LENS = "office_lens"
    OCCUPATIONAL_LENS = "occupational_lens"
    SUNGLASS_LENS = "sunglass_lens"


class FollowUpStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class FollowUpInterval(str, Enum):
    ONE_WEEK = "one_week"
    FIFTEEN_DAYS = "fifteen_days"
    ONE_MONTH = "one_month"
    CUSTOM = "custom"


class FollowUpType(str, Enum):
    CONTACT_LENS = "contact_lens"
    PROGRESSIVE_ADAPTATION = "progressive_adaptation"
    PEDIATRIC_REVIEW = "pediatric_review"
    REFERRAL_FOLLOW_UP = "referral_follow_up"
    DRY_EYE_REVIEW = "dry_eye_review"
    CUSTOM = "custom"


class FollowUpReminderState(str, Enum):
    NOT_SCHEDULED = "not_scheduled"
    SCHEDULED = "scheduled"
    SENT = "sent"
    FAILED = "failed"


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
    DISPENSING_ORDER = "dispensing_order"


def enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]
