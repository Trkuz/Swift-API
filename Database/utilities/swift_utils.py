from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select

from Database.db_models import SwiftData


def is_headquarter(swift_code: str) -> bool:
    code = swift_code.upper()
    return (len(code) == 8) or (len(code) == 11 and code.endswith("XXX"))

def extract_bank_identifier(swift_code: str) -> str:
    return swift_code.upper()[:8]


def get_headquarter_id(db: Session, swift_code: str) -> Optional[UUID]:
    if is_headquarter(swift_code):
        return None

    bank_id = extract_bank_identifier(swift_code)

    stmt = (
        select(SwiftData.id)
        .where(
            SwiftData.swift_code.ilike(f"{bank_id}%"),
            SwiftData.is_headquarter == True

        )
    )

    result = db.execute(stmt).scalar_one_or_none()
    return result


def process_dataframe_row(db: Session, row: dict) -> dict:
    code = row.get('swift_code') or row.get('swiftCode')
    if not code:
        raise ValueError("Row missing (swift_code or swiftCode)")

    is_hq = is_headquarter(code)

    return {
        **row,
        "is_headquarter": is_hq,
        "headquarter_id": None if is_hq else get_headquarter_id(db, code),
    }

