from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    func,
    insert,
    inspect,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.shops import get_canonical_shop_code, get_shop_definition
from app.db.base import Base
from app.models.shop import Shop


ROLLBACK_INSTRUCTIONS = """
Rollback instructions:
1. Run this importer during a maintenance window after taking verified backups of every source shop DB and the target DB.
2. If validation fails before staff resume work, stop the app and restore the target single DB from the pre-import backup.
3. If you need to undo one imported shop without restoring the whole target DB, use shop_import_mappings for that shop_code and delete child tables first:
   chat_messages, audit_logs, whatsapp_logs, campaign_logs, payments, bill_items, bills, prescriptions, campaigns, vendors, customers, users, then shops if unused.
4. Do not delete source shop databases. Keep them read-only until production has passed the observation window.
"""


IMPORT_TABLES = (
    "users",
    "customers",
    "vendors",
    "prescriptions",
    "bills",
    "bill_items",
    "payments",
    "campaigns",
    "campaign_logs",
    "whatsapp_logs",
    "audit_logs",
    "chat_messages",
)

ENUM_NAME_COLUMNS = {
    ("users", "role"): {"admin": "admin", "staff": "staff"},
    ("customers", "gender"): {"male": "male", "female": "female", "other": "other"},
    ("bills", "payment_mode"): {
        "cash": "cash",
        "upi": "upi",
        "card": "card",
        "bank_transfer": "bank_transfer",
        "other": "other",
    },
    ("bills", "payment_status"): {"pending": "pending", "partial": "partial", "paid": "paid"},
    ("bill_items", "item_type"): {
        "frame": "frame",
        "lens": "lens",
        "coating": "coating",
        "contact_lens": "contact_lens",
        "eye_test": "eye_test",
        "repair": "repair",
        "accessory": "accessory",
        "other": "other",
    },
    ("payments", "mode"): {
        "cash": "cash",
        "upi": "upi",
        "card": "card",
        "bank_transfer": "bank_transfer",
        "other": "other",
    },
    ("campaigns", "status"): {
        "draft": "draft",
        "scheduled": "scheduled",
        "running": "running",
        "completed": "completed",
        "failed": "failed",
        "cancelled": "cancelled",
    },
    ("whatsapp_logs", "module_type"): {
        "customer": "customer",
        "prescription": "prescription",
        "bill": "bill",
        "campaign": "campaign",
    },
    ("whatsapp_logs", "message_type"): {"text": "text", "template": "template", "document": "document"},
    ("whatsapp_logs", "status"): {"pending": "pending", "sent": "sent", "failed": "failed"},
}

REFERENCE_TABLE_BY_MODULE = {
    "customer": "customers",
    "prescription": "prescriptions",
    "bill": "bills",
    "campaign": "campaigns",
}

ENTITY_TABLE_BY_TYPE = {
    "user": "users",
    "users": "users",
    "customer": "customers",
    "customers": "customers",
    "prescription": "prescriptions",
    "prescriptions": "prescriptions",
    "bill": "bills",
    "bills": "bills",
    "vendor": "vendors",
    "vendors": "vendors",
    "campaign": "campaigns",
    "campaigns": "campaigns",
    "campaign_log": "campaign_logs",
    "campaign_logs": "campaign_logs",
    "whatsapp_log": "whatsapp_logs",
    "whatsapp_logs": "whatsapp_logs",
    "chat_message": "chat_messages",
    "chat_messages": "chat_messages",
}


@dataclass
class TableImportCounts:
    source_count: int = 0
    would_insert: int = 0
    inserted: int = 0
    skipped_existing: int = 0


@dataclass
class ShopImportSummary:
    source_shop_code: str
    shop_code: str
    shop_id: int | None
    table_counts: dict[str, TableImportCounts] = field(default_factory=dict)
    validation_totals: dict[str, int] = field(default_factory=dict)


@dataclass
class ImportResult:
    dry_run: bool
    shops: list[ShopImportSummary]
    rollback_instructions: str = ROLLBACK_INSTRUCTIONS.strip()


class ShopDatabaseImporter:
    def __init__(self, *, source_map: Mapping[str, str], target_db_url: str, dry_run: bool = False):
        self.source_map = dict(source_map)
        self.target_db_url = target_db_url
        self.dry_run = dry_run
        self.target_engine = create_engine(target_db_url, future=True)
        self.target_sessionmaker = sessionmaker(bind=self.target_engine, autoflush=False, autocommit=False, future=True)
        self.mapping_table = _mapping_table()

    def run(self) -> ImportResult:
        if not self.dry_run:
            self.mapping_table.create(self.target_engine, checkfirst=True)

        summaries: list[ShopImportSummary] = []
        for source_shop_code, source_db_url in self.source_map.items():
            summaries.append(self._import_shop(source_shop_code=source_shop_code, source_db_url=source_db_url))

        return ImportResult(dry_run=self.dry_run, shops=summaries)

    def _import_shop(self, *, source_shop_code: str, source_db_url: str) -> ShopImportSummary:
        shop_code = _canonical_shop_code(source_shop_code)
        source_engine = create_engine(source_db_url, future=True)
        source_metadata = MetaData()
        source_metadata.reflect(bind=source_engine)

        with self.target_sessionmaker() as target_db:
            shop_id = self._ensure_shop(target_db=target_db, shop_code=shop_code)
            summary = ShopImportSummary(source_shop_code=source_shop_code, shop_code=shop_code, shop_id=shop_id)
            id_maps: dict[str, dict[int, int]] = {table_name: {} for table_name in IMPORT_TABLES}

            for table_name in IMPORT_TABLES:
                table_counts = self._import_table(
                    source_engine=source_engine,
                    source_metadata=source_metadata,
                    target_db=target_db,
                    shop_code=shop_code,
                    shop_id=shop_id,
                    table_name=table_name,
                    id_maps=id_maps,
                )
                summary.table_counts[table_name] = table_counts

            summary.validation_totals = self._validation_totals(target_db=target_db, shop_id=shop_id)

            if self.dry_run:
                target_db.rollback()
            else:
                target_db.commit()

        source_engine.dispose()
        return summary

    def _ensure_shop(self, *, target_db: Session, shop_code: str) -> int | None:
        existing_id = target_db.query(Shop.id).filter(Shop.code == shop_code).scalar()
        if existing_id is not None:
            return int(existing_id)

        definition = get_shop_definition(shop_code)
        if definition is None:
            raise ValueError(f"Unknown shop code {shop_code!r}. Add it to the shop registry before importing.")

        if self.dry_run:
            return None

        shop = Shop(
            code=definition.code,
            display_name=definition.display_name,
            location_label=definition.location_label,
            center_type=definition.center_type,
            is_active=definition.is_active,
        )
        target_db.add(shop)
        target_db.flush()
        return shop.id

    def _import_table(
        self,
        *,
        source_engine: Engine,
        source_metadata: MetaData,
        target_db: Session,
        shop_code: str,
        shop_id: int | None,
        table_name: str,
        id_maps: dict[str, dict[int, int]],
    ) -> TableImportCounts:
        counts = TableImportCounts()
        source_table = source_metadata.tables.get(table_name)
        target_table = Base.metadata.tables[table_name]

        if source_table is None:
            return counts

        source_rows = self._source_rows(source_engine, source_table)
        counts.source_count = len(source_rows)

        for row in source_rows:
            source_id = _int_or_none(row.get("id"))
            if source_id is None:
                continue

            existing_target_id = self._existing_mapping_id(target_db, shop_code, table_name, source_id)
            if existing_target_id is None:
                existing_target_id = self._find_natural_existing_id(target_db, target_table, table_name, shop_id, row)

            if existing_target_id is not None:
                id_maps[table_name][source_id] = existing_target_id
                counts.skipped_existing += 1
                if not self.dry_run:
                    self._record_mapping(target_db, shop_code, table_name, source_id, existing_target_id)
                    if table_name == "bills" and "bill_items" not in source_metadata.tables:
                        self._ensure_legacy_bill_children(
                            target_db=target_db,
                            shop_id=shop_id,
                            source_bill_row=row,
                            target_bill_id=existing_target_id,
                        )
                continue

            counts.would_insert += 1
            if self.dry_run:
                id_maps[table_name][source_id] = source_id
            payload = self._build_payload(
                target_table=target_table,
                table_name=table_name,
                row=row,
                shop_code=shop_code,
                shop_id=shop_id,
                id_maps=id_maps,
            )

            if self.dry_run:
                continue

            target_id = target_db.execute(insert(target_table).values(**payload)).inserted_primary_key[0]
            id_maps[table_name][source_id] = int(target_id)
            counts.inserted += 1
            self._record_mapping(target_db, shop_code, table_name, source_id, int(target_id))
            if table_name == "bills" and "bill_items" not in source_metadata.tables:
                self._ensure_legacy_bill_children(
                    target_db=target_db,
                    shop_id=shop_id,
                    source_bill_row=row,
                    target_bill_id=int(target_id),
                )

        return counts

    @staticmethod
    def _source_rows(source_engine: Engine, source_table: Table) -> list[dict[str, Any]]:
        with source_engine.connect() as source_conn:
            return [dict(row._mapping) for row in source_conn.execute(select(source_table).order_by(source_table.c.id))]

    def _build_payload(
        self,
        *,
        target_table: Table,
        table_name: str,
        row: dict[str, Any],
        shop_code: str,
        shop_id: int | None,
        id_maps: dict[str, dict[int, int]],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        target_columns = set(target_table.columns.keys())

        for column_name, value in row.items():
            if column_name == "id" or column_name not in target_columns:
                continue
            payload[column_name] = _normalize_value(table_name, column_name, value)

        if "shop_id" in target_columns:
            payload["shop_id"] = shop_id
        if "shop_key" in target_columns:
            payload["shop_key"] = shop_code
        if table_name == "chat_messages":
            payload["sender_shop_key"] = shop_code

        self._add_compatibility_defaults(table_name, payload, row)
        self._remap_foreign_keys(table_name, payload, row, id_maps)
        return payload

    @staticmethod
    def _add_compatibility_defaults(table_name: str, payload: dict[str, Any], row: dict[str, Any]) -> None:
        if table_name != "bills":
            return

        payload.setdefault("subtotal", row.get("whole_price") or 0)
        payload.setdefault("discount_total", row.get("discount") or 0)
        payload.setdefault("tax_total", row.get("tax_total") or 0)
        payload.setdefault("grand_total", row.get("final_price") or 0)
        payload.setdefault("paid_total", row.get("paid_amount") or 0)

    def _ensure_legacy_bill_children(
        self,
        *,
        target_db: Session,
        shop_id: int | None,
        source_bill_row: dict[str, Any],
        target_bill_id: int,
    ) -> None:
        bill_items_table = Base.metadata.tables["bill_items"]
        payments_table = Base.metadata.tables["payments"]

        existing_item_id = target_db.execute(
            select(bill_items_table.c.id).where(bill_items_table.c.bill_id == target_bill_id).limit(1)
        ).scalar_one_or_none()
        if existing_item_id is None:
            target_db.execute(
                insert(bill_items_table).values(
                    shop_id=shop_id,
                    bill_id=target_bill_id,
                    item_type="frame" if source_bill_row.get("frame_name") else "other",
                    item_name=source_bill_row.get("product_name") or "Legacy bill item",
                    quantity=1,
                    unit_price=source_bill_row.get("whole_price") or 0,
                    discount=source_bill_row.get("discount") or 0,
                    line_total=source_bill_row.get("final_price") or 0,
                    created_at=source_bill_row.get("created_at") or func.now(),
                    updated_at=source_bill_row.get("updated_at") or func.now(),
                )
            )

        paid_amount = source_bill_row.get("paid_amount") or 0
        existing_payment_id = target_db.execute(
            select(payments_table.c.id).where(payments_table.c.bill_id == target_bill_id).limit(1)
        ).scalar_one_or_none()
        if _is_positive_number(paid_amount) and existing_payment_id is None:
            target_db.execute(
                insert(payments_table).values(
                    shop_id=shop_id,
                    bill_id=target_bill_id,
                    mode=_normalize_value("bills", "payment_mode", source_bill_row.get("payment_mode") or "cash"),
                    amount=paid_amount,
                    paid_at=source_bill_row.get("created_at") or func.now(),
                    created_at=source_bill_row.get("created_at") or func.now(),
                    updated_at=source_bill_row.get("updated_at") or func.now(),
                )
            )

    def _remap_foreign_keys(self, table_name: str, payload: dict[str, Any], row: dict[str, Any], id_maps: dict[str, dict[int, int]]) -> None:
        if table_name in {"customers", "prescriptions", "bills", "campaigns"}:
            _remap_optional(payload, "created_by", row, id_maps, "users")
            _remap_optional(payload, "updated_by", row, id_maps, "users")

        if table_name == "prescriptions":
            payload["customer_id"] = _required_mapping(row, "customer_id", id_maps, "customers")

        if table_name == "bills":
            payload["customer_id"] = _required_mapping(row, "customer_id", id_maps, "customers")

        if table_name in {"bill_items", "payments"}:
            payload["bill_id"] = _required_mapping(row, "bill_id", id_maps, "bills")

        if table_name == "campaign_logs":
            payload["campaign_id"] = _required_mapping(row, "campaign_id", id_maps, "campaigns")
            _remap_optional(payload, "customer_id", row, id_maps, "customers")

        if table_name == "whatsapp_logs":
            _remap_optional(payload, "customer_id", row, id_maps, "customers")
            _remap_optional(payload, "vendor_id", row, id_maps, "vendors")
            module_type = _normalize_value(table_name, "module_type", row.get("module_type"))
            reference_table = REFERENCE_TABLE_BY_MODULE.get(str(module_type or ""))
            if reference_table is not None:
                payload["reference_id"] = _required_mapping(row, "reference_id", id_maps, reference_table)

        if table_name == "audit_logs":
            _remap_optional(payload, "actor_user_id", row, id_maps, "users")
            entity_table = ENTITY_TABLE_BY_TYPE.get(str(row.get("entity_type") or "").strip().lower())
            entity_id = _int_or_none(row.get("entity_id"))
            if entity_table is not None and entity_id is not None and entity_id in id_maps[entity_table]:
                payload["entity_id"] = str(id_maps[entity_table][entity_id])

        if table_name == "chat_messages":
            _remap_optional(payload, "sender_user_id", row, id_maps, "users")

    def _existing_mapping_id(self, target_db: Session, shop_code: str, table_name: str, source_id: int) -> int | None:
        if self.dry_run or not inspect(self.target_engine).has_table(self.mapping_table.name):
            return None

        result = target_db.execute(
            select(self.mapping_table.c.target_id).where(
                self.mapping_table.c.shop_code == shop_code,
                self.mapping_table.c.source_table == table_name,
                self.mapping_table.c.source_id == source_id,
            )
        ).scalar_one_or_none()
        return int(result) if result is not None else None

    def _find_natural_existing_id(
        self,
        target_db: Session,
        target_table: Table,
        table_name: str,
        shop_id: int | None,
        row: dict[str, Any],
    ) -> int | None:
        if table_name == "users":
            email = str(row.get("email") or "").strip().lower()
            if not email:
                return None
            existing = target_db.execute(select(target_table.c.id, target_table.c.shop_id).where(target_table.c.email == email)).first()
            if existing is None:
                return None
            if shop_id is not None and existing.shop_id not in (None, shop_id):
                raise ValueError(f"User email {email!r} already exists for a different shop_id; resolve before import.")
            return int(existing.id)

        if table_name == "customers":
            return _scalar_id(
                target_db,
                select(target_table.c.id).where(
                    target_table.c.shop_id == shop_id,
                    target_table.c.customer_id == row.get("customer_id"),
                ),
            )

        if table_name == "bills":
            return _scalar_id(
                target_db,
                select(target_table.c.id).where(
                    target_table.c.shop_id == shop_id,
                    target_table.c.bill_number == row.get("bill_number"),
                ),
            )

        if table_name == "vendors":
            return _scalar_id(
                target_db,
                select(target_table.c.id).where(
                    target_table.c.shop_id == shop_id,
                    target_table.c.vendor_name == row.get("vendor_name"),
                    target_table.c.whatsapp_no == row.get("whatsapp_no"),
                ),
            )

        return None

    def _record_mapping(self, target_db: Session, shop_code: str, table_name: str, source_id: int, target_id: int) -> None:
        existing = self._existing_mapping_id(target_db, shop_code, table_name, source_id)
        if existing is not None:
            return

        target_db.execute(
            insert(self.mapping_table).values(
                shop_code=shop_code,
                source_table=table_name,
                source_id=source_id,
                target_id=target_id,
            )
        )

    @staticmethod
    def _validation_totals(target_db: Session, shop_id: int | None) -> dict[str, int]:
        totals: dict[str, int] = {}
        for table_name in IMPORT_TABLES:
            target_table = Base.metadata.tables[table_name]
            if "shop_id" in target_table.c and shop_id is not None:
                query = select(func.count()).select_from(target_table).where(target_table.c.shop_id == shop_id)
            else:
                query = select(func.count()).select_from(target_table)
            totals[table_name] = int(target_db.execute(query).scalar_one())
        return totals


def import_shop_databases(*, source_map: Mapping[str, str], target_db_url: str, dry_run: bool = False) -> ImportResult:
    return ShopDatabaseImporter(source_map=source_map, target_db_url=target_db_url, dry_run=dry_run).run()


def _mapping_table() -> Table:
    metadata = MetaData()
    return Table(
        "shop_import_mappings",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("shop_code", String(64), nullable=False),
        Column("source_table", String(80), nullable=False),
        Column("source_id", Integer, nullable=False),
        Column("target_id", Integer, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
        UniqueConstraint("shop_code", "source_table", "source_id", name="uq_shop_import_mapping_source"),
    )


def _canonical_shop_code(raw_shop_code: str) -> str:
    canonical = get_canonical_shop_code(raw_shop_code)
    if canonical is None:
        raise ValueError(f"Unknown shop code {raw_shop_code!r}")
    return canonical


def _normalize_value(table_name: str, column_name: str, value: Any) -> Any:
    if value is None:
        return None

    enum_map = ENUM_NAME_COLUMNS.get((table_name, column_name))
    if enum_map is None:
        return value

    cleaned = str(value).strip()
    return enum_map.get(cleaned.lower(), cleaned.lower())


def _required_mapping(row: dict[str, Any], column_name: str, id_maps: dict[str, dict[int, int]], table_name: str) -> int:
    source_id = _int_or_none(row.get(column_name))
    if source_id is None or source_id not in id_maps[table_name]:
        raise ValueError(f"Missing imported {table_name} mapping for {column_name}={row.get(column_name)!r}")
    return id_maps[table_name][source_id]


def _remap_optional(payload: dict[str, Any], column_name: str, row: dict[str, Any], id_maps: dict[str, dict[int, int]], table_name: str) -> None:
    source_id = _int_or_none(row.get(column_name))
    payload[column_name] = id_maps[table_name].get(source_id) if source_id is not None else None


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_positive_number(value: Any) -> bool:
    try:
        return Decimal(str(value)) > Decimal("0")
    except (InvalidOperation, TypeError, ValueError):
        return False


def _scalar_id(target_db: Session, query) -> int | None:
    value = target_db.execute(query).scalar_one_or_none()
    return int(value) if value is not None else None


def _load_source_map(*, source_map_json: str | None, source_map_file: str | None, source_items: list[str] | None) -> dict[str, str]:
    loaded: dict[str, str] = {}

    if source_map_file:
        loaded.update(json.loads(Path(source_map_file).read_text()))

    if source_map_json:
        loaded.update(json.loads(source_map_json))

    for item in source_items or []:
        if "=" not in item:
            raise ValueError(f"Invalid --source value {item!r}; expected shop_code=db_url")
        shop_code, db_url = item.split("=", 1)
        loaded[shop_code.strip()] = db_url.strip()

    if not loaded:
        raise ValueError("At least one source DB mapping is required")

    return loaded


def _print_result(result: ImportResult) -> None:
    mode = "DRY RUN" if result.dry_run else "IMPORT"
    print(f"{mode} completed for {len(result.shops)} shop database(s).")
    for shop in result.shops:
        print(f"\nShop {shop.source_shop_code} -> {shop.shop_code} (shop_id={shop.shop_id})")
        for table_name, counts in shop.table_counts.items():
            print(
                f"  {table_name}: source={counts.source_count}, would_insert={counts.would_insert}, "
                f"inserted={counts.inserted}, skipped_existing={counts.skipped_existing}"
            )
        print("  validation totals:")
        for table_name, total in shop.validation_totals.items():
            print(f"    {table_name}: {total}")
    print("\n" + result.rollback_instructions)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import legacy per-shop databases into one single multi-shop database.")
    parser.add_argument("--target-db-url", required=True, help="Target single database URL")
    parser.add_argument("--source-map-json", help='JSON object mapping shop_code to source DB URL, e.g. {"shop":"sqlite:///..."}')
    parser.add_argument("--source-map-file", help="Path to JSON file mapping shop_code to source DB URL")
    parser.add_argument("--source", action="append", help="Repeatable shop_code=db_url mapping")
    parser.add_argument("--dry-run", action="store_true", help="Read and validate only; do not write target rows")
    args = parser.parse_args()

    source_map = _load_source_map(
        source_map_json=args.source_map_json,
        source_map_file=args.source_map_file,
        source_items=args.source,
    )
    result = import_shop_databases(source_map=source_map, target_db_url=args.target_db_url, dry_run=args.dry_run)
    _print_result(result)


if __name__ == "__main__":
    main()
