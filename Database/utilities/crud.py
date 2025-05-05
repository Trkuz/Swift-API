from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, update, and_
from collections.abc import Sequence

from Database.db_models import SwiftData
from Database.utilities.swift_utils import process_dataframe_row, is_headquarter, extract_bank_identifier

#UPDATE
def create_swift(db: Session, row: dict) -> SwiftData | None:

    processed = process_dataframe_row(db, row)
    new_entry = SwiftData(**processed)

    try:
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
    except IntegrityError:
        db.rollback()
        return None


    if new_entry.is_headquarter:
        db.execute(
            update(SwiftData)
            .where(
                and_(
                    SwiftData.headquarter_id.is_(None),
                    SwiftData.swift_code.like(f"{extract_bank_identifier(new_entry.swift_code)}%"),
                    SwiftData.id != new_entry.id
                )
            )
            .values(headquarter_id = new_entry.id)
        )
        db.commit()
    return new_entry

#READ
def get_swift_by_country(db: Session, country_iso2: str ) -> Sequence[SwiftData]:

    country_iso2 = country_iso2.upper()
    stmt = (
    select(SwiftData)
    .where(SwiftData.country_iso2 ==country_iso2)
    .order_by(SwiftData.swift_code)
    )
    return db.execute(stmt).scalars().all()

#DELETE
def delete_swift(db: Session, swift_code: str) -> bool:
    is_hq =  is_headquarter(swift_code)

    #update the branches code
    if is_hq:
        #get headquarter id
        hq_id = db.execute(
            select(SwiftData.id)
            .where(SwiftData.swift_code == swift_code)
        ).scalar_one_or_none()

        #Set branches headquarter_id  to None
        db.execute(
            update(SwiftData)
            .where(SwiftData.headquarter_id == hq_id)
            .values(headquarter_id=None)
        )

    #delete entry
    result = db.execute(
        delete(SwiftData)
        .where(SwiftData.swift_code == swift_code)
    )

    db.commit()
    return result.rowcount > 0
