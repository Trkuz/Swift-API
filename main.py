from fastapi import APIRouter, HTTPException, Depends, FastAPI
from Database.db_models import SessionLocal, SwiftData
from sqlalchemy.orm import Session
from Models.models import( SwiftEntryHeadquarter, MessageResponse, SwiftEntry,
                     SwiftCodesByCountry, SwiftCodeCreateRequest, SwiftEntryBranch)
from Database.utilities.crud import create_swift, delete_swift
from logging import getLogger

logger = getLogger(__name__)

app = FastAPI()

router = APIRouter(prefix='/v1/swift-codes')

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/{swift_code}", response_model=SwiftEntryHeadquarter | SwiftEntryBranch)
async def get_swift_code_details(swift_code: str, db: Session = Depends(get_db)):

    entry = db.query(SwiftData).filter(SwiftData.swift_code == swift_code).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"SWIFT code {swift_code} not found!")

    if entry.is_headquarter:
        branches = db.query(SwiftData).filter(SwiftData.headquarter_id == entry.id).all()
        branches_list = [SwiftEntry.model_validate(b) for b in branches]

        return SwiftEntryHeadquarter(
            **SwiftEntryHeadquarter.model_validate(entry).model_dump(exclude = {"branches"}),
            branches=branches_list
        )

    return SwiftEntryBranch(**SwiftEntryBranch.model_validate(entry).model_dump())


@router.get("/country/{country_iso2}", response_model=SwiftCodesByCountry)
async def get_codes_by_country(country_iso2: str, db: Session = Depends(get_db)):
    entries = db.query(SwiftData).filter(SwiftData.country_iso2 == country_iso2.upper()).all()

    if not entries:
        raise HTTPException(status_code=404, detail=f"No entries found for code {country_iso2}")

    swift_entries = [SwiftEntry.model_validate(entry).model_dump() for entry in entries]

    return SwiftCodesByCountry(
        countryISO2= country_iso2,
        countryName= entries[0].country_name,
        swiftCodes=swift_entries

    )

@router.post("", response_model=MessageResponse) ###################
async def add_swift_code(payload: SwiftCodeCreateRequest, db: Session = Depends(get_db)):
    if db.query(SwiftData).filter(SwiftData.swift_code == payload.swift_code).first():
        raise HTTPException(status_code=409, detail=f"SWIFT code: {payload.swift_code} already exists!")

    correct_is_hq = payload.swift_code.upper()[-3:] == "XXX"

    if payload.is_headquarter and payload.is_headquarter != correct_is_hq:
        correction_msg = f"isHeadquarter does not math SWIFT code format and was set to {correct_is_hq}"
        logger.warning(correction_msg)


    try:
        entry = create_swift(db, payload.model_dump(exclude_none=False))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if entry is None:
        raise HTTPException(status_code=400, detail="Failed to insert entry.")

    return MessageResponse(message=f"SWIFT {payload.swift_code} has been added successfully.")

@router.delete("/{swift_code}", response_model=MessageResponse)
async def delete_swift_code(swift_code: str, db: Session = Depends(get_db)):
    success = delete_swift(db, swift_code)

    if not success:
        raise HTTPException(status_code=404, detail=f"SWIFT code {swift_code} not found in database!")

    return MessageResponse(message= "SWIFT code has been deleted.")

app.include_router(router)