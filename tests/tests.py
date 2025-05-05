from fastapi import HTTPException
from main import app, get_db
from Models.models import SwiftCodeCreateRequest, VALID_COUNTRIES
from Database.db_models import Base, SwiftData
from Database.utilities.crud import create_swift, delete_swift, get_swift_by_country
from Database.utilities.swift_utils import is_headquarter, extract_bank_identifier, get_headquarter_id, process_dataframe_row
from random import choices
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest


engine = create_engine(
    "sqlite:///./test.db",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create session
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up - drop all tables after tests
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    # Override the get_db dependency
    def override_get_db():
        try:
            yield db
        finally:
            pass  # db is closed by the db fixture

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    # Clean up
    app.dependency_overrides.clear()



@pytest.mark.parametrize("swift_code, expected", [
    ("ABCDEFGH", True),
    ("TESVALUEXXX", True),
    ("NOTTESVALUE", False),
    ("AA", False),
    ("SADMKWQDMASDPMWA", False)
])
def test_is_hq(swift_code, expected):
    assert is_headquarter(swift_code) == expected


@pytest.mark.parametrize("swift_code, expected", [
    ("ABCDEFGH", True),
    ("TESVALUEXXX", True),
    ("NOTTESVALUE", False),
    ("AA", False),
    ("SADMKWQDMASDPMWA", False)
])
def extract_bank_id(swift_code, expected):
    assert extract_bank_identifier(swift_code) == expected


def get_hq_id():
    mock_db = Mock()
    mock_uuid = uuid4()

    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_uuid

    result = get_headquarter_id(mock_db, "TESTCASE123")
    assert result == mock_uuid
    mock_db.execute.assert_called_once()

    mock_db.reset_mock()

    result = get_headquarter_id(mock_db, "TESTCASEXXX")
    assert result is None
    mock_db.execute.assert_not_called()


def test_process_dataframe_row():
    mock_uuid = uuid4()

    mock_scalar = Mock()
    mock_scalar.scalar_one_or_none.return_value = mock_uuid

    mock_db = Mock()
    mock_db.execute.return_value = mock_scalar

    #Headquarter
    HQ = {
        "swift_code": "USUSUSUSXXX",
        "bank_name": "Test Bank",
        "country_iso2": "US",
        "country_name": "UNITED STATES",
        "address": "Test Street 21"
    }
    result = process_dataframe_row(mock_db, HQ)

    assert result["is_headquarter"] == True
    assert result["headquarter_id"] is None
    assert result["bank_name"] == "Test Bank"
    assert result["swift_code"] == "USUSUSUSXXX"
    assert result["address"] == "Test Street 21"
    assert result["country_iso2"] == "US"

    #Branch
    Branch = {
        "swift_code": "USUSUSUS123",
        "bank_name": "Test Bank",
        "country_iso2": "US",
        "country_name": "UNITED STATES",
        "address": "Test Street 21"
    }

    result_branch = process_dataframe_row(mock_db, Branch)

    assert result_branch["is_headquarter"] is False
    assert result_branch["headquarter_id"] == mock_uuid


#SWIFT VALIDATION TESTING
@pytest.mark.parametrize("valid_code", [
    "ABCDEFGH",
    "ABCDEFG1",
    "ABCDEFGHXXX",
    "ABCDEFGH123",
    "abshsbas"
])
def test_valid_swift(valid_code):
    with patch("Models.models.HTTPException") as mock_exception:
        result = SwiftCodeCreateRequest.validate_swift(valid_code)
        assert result == valid_code.upper()
        mock_exception.assert_not_called()

@pytest.mark.parametrize("invalid_code",[
    None,
    "",
    "ABC",
    "123123123123"
    "ABCABCABCABAC",
    "A-B-C-D-"
])
def test_invalid_swift(invalid_code):
    with pytest.raises(HTTPException) as exception_info:
        SwiftCodeCreateRequest.validate_swift(invalid_code)

    assert exception_info.value.status_code == 400


#COUNTRY_ISO2 VALIDATION TESTING
@pytest.mark.parametrize("valid_code", choices(list(VALID_COUNTRIES.keys()), k=3))
def test_valid_iso2(valid_code):
    with patch("Models.models.HTTPException") as mock_exception:
        result = SwiftCodeCreateRequest.validate_iso2(valid_code)
        assert result == valid_code.upper()
        mock_exception.assert_not_called()

@pytest.mark.parametrize("invalid_code", ["USA", "", "MaZX"])
def test_invalid_iso2(invalid_code):
    with patch("Models.models.HTTPException") as mock_exception:

        with pytest.raises(Exception):
            SwiftCodeCreateRequest.validate_iso2(invalid_code.upper())
        mock_exception.assert_called_once()



#COUNTRY_NAME VALIDATION TESTING
@pytest.mark.parametrize("valid_country",['POLAND', 'Bermuda', 'aNgoLa'])
def test_valid_country(valid_country):
    with patch("Models.models.HTTPException") as mock_exception:
        result = SwiftCodeCreateRequest.validate_country_name(valid_country)

        assert result == valid_country.upper()
        mock_exception.assert_not_called()

@pytest.mark.parametrize("invalid_country", [None, 'Gambbia', "123"])
def test_invalid_country(invalid_country):
    with patch("Models.models.HTTPException") as mock_exception:
        with pytest.raises(Exception):
            SwiftCodeCreateRequest.validate_country_name(invalid_country)
        mock_exception.assert_called_once()

#VALIDATE ADDRESS AND BANK NAME
@pytest.mark.parametrize("invalid_field",[
{"bank_name": "A" * 501,"address": "Address"},
{"bank_name": "bank name","address": "A" * 501}
])
def test_validate_names_invalid(invalid_field):
    with patch("Models.models.HTTPException") as mock_exception:
        with pytest.raises(Exception):
            SwiftCodeCreateRequest(**invalid_field)
        mock_exception.assert_called_once()


@pytest.mark.parametrize("valid_field",[
{"bank_name": None,"address": "Address"},
{"bank_name": "bank name","address": None},
{"bank_name": "","address": "Address"},
{"bank_name": "bank name","address": ""},
{"bank_name": "bank name","address": "address"},
{"bank_name": "bank name","address": "address"}
])
def test_validate_names_valid(valid_field):
    with patch("Models.models.HTTPException") as mock_exception:
        instance = SwiftCodeCreateRequest(
            swiftCode="AABBPLXXX",
            countryISO2="PL",
            countryName="Poland",
            bankName= valid_field["bank_name"],
            address= valid_field["address"]
        )
        result = SwiftCodeCreateRequest.validate_names(instance)

        expected_bank_name = None if valid_field["bank_name"] == "" else valid_field["bank_name"]
        expected_address = None if valid_field["address"] == "" else valid_field["address"]

        assert result.bank_name == expected_bank_name
        assert result.address == expected_address
        mock_exception.assert_not_called()


@pytest.mark.parametrize("invalid_field",[
{"bank_name":"asd","address":"dsa","swift_code": "ABCDEFGH123","country_iso2": "US","country_name": "CANADA"},
{"bank_name":"asd","address":"dsa","swift_code": "ABCDUSGHXXX","country_iso2": "US","country_name": "UNITED SSTATES"},
{"bank_name":"asd","address":"dsa","swift_code": "ABCDEFGHXXX","country_iso2": "US","country_name": "UNITED STATES"}
])
def test_validate_integrity_invalid(invalid_field):

    with pytest.raises(HTTPException) as exception:
        SwiftCodeCreateRequest(**invalid_field)
    assert exception.value.status_code == 400


@pytest.mark.parametrize("valid_field", [
    {"bank_name":"asd","address":"dsa","swift_code": "ABCDUSGHXXX", "country_iso2": "US", "country_name": "UNITED STATES"},
    {"bank_name":"asd","address":"dsa","swift_code": "ABCDUSGHXXX", "country_iso2": "uS", "country_name": "UNItED STaTeS"}
])
def test_validate_integrity_valid(valid_field):
    with patch("Models.models.HTTPException") as mock_exception:
        result = SwiftCodeCreateRequest(**valid_field)

        assert result.swift_code == valid_field["swift_code"].upper()
        assert result.country_iso2 == valid_field["country_iso2"].upper()
        assert result.country_name == valid_field["country_name"].upper()
        mock_exception.assert_not_called()


#VALIDATE CRUD OPERATIONS
def test_create_swift(db):
    hq =  {
            "swift_code": "TESTUSNKXXX",
            "bank_name": "Test Bank HQ",
            "country_iso2": "US",
            "country_name": "UNITED STATES",
            "address": "123 Test street",
        }

    entry = create_swift(db, hq)

    assert entry.swift_code == hq["swift_code"]
    assert entry.is_headquarter is True
    assert entry.headquarter_id is None
    assert entry.country_name == hq["country_name"]
    assert entry.country_iso2 == hq["country_iso2"]
    assert entry.address == hq["address"]


    branch = {
        "swift_code": "TESTUSNK123",
        "bank_name": "Test Bank Branch",
        "country_iso2": "US",
        "country_name": "UNITED STATES",
        "address": "456 address street",
    }

    branch_entry = create_swift(db, branch)

    assert branch_entry.swift_code == branch["swift_code"]
    assert branch_entry.is_headquarter is False
    assert branch_entry.headquarter_id == entry.id
    assert branch_entry.country_name == branch["country_name"]
    assert branch_entry.country_iso2 == branch["country_iso2"]
    assert branch_entry.address == branch["address"]


def test_get_swift_by_county(db):
    test_data = [
        {
            "swift_code": "TESTUS1XXX",
            "bank_name": "PL Bank 1",
            "country_iso2": "US",
            "country_name": "POLAND",
            "address": "test street 1",
        },
        {
            "swift_code": "TESTUS2XXX",
            "bank_name": "US Bank 2",
            "country_iso2": "US",
            "country_name": "UNITED STATES",
            "address": "test street 2",
        },
        {
            "swift_code": "TESTUK1XXX",
            "bank_name": "GB Bank",
            "country_iso2": "GB",
            "country_name": "UNITED KINGDOM",
            "address": "test street 3",
        }
]

    for case in test_data: create_swift(db, case)

    valid_data = [
        ("US", 2),
        ("GB", 1)
    ]

    for country, count in valid_data:

        entries = get_swift_by_country(db, country)
        assert len(entries) == count
        if count > 0 : assert all(e.country_iso2 == country for e in entries)


def test_delete_swift(db):
    hq_data = {
        "swift_code": "TESTBANKXXX",
        "bank_name": "Test Bank HQ",
        "country_iso2": "US",
        "country_name": "UNITED STATES",
        "address": " 123 address street",
    }
    branch_data = {
        "swift_code": "TESTBANK123",
        "bank_name": "Test Bank Branch",
        "country_iso2": "US",
        "country_name": "UNITED STATES",
        "address": "456 addres street",
    }

    hq = create_swift(db, hq_data)
    branch = create_swift(db, branch_data)

    delete_tests = [
        # Delete HQ and check branch update
        {
            "swift_code": "TESTBANKXXX",
            "expected_result": True,
            "after_check": lambda: (
                db.refresh(branch),
                assert_branch_update(branch)
            )
        },
        # Delete branch and check count
        {
            "swift_code": "TESTBANK123",
            "expected_result": True,
            "after_check": lambda: assert_empty_db(db)
        },
        # Try to delete non-existent code
        {
            "swift_code": "NONEXISTENT",
            "expected_result": False,
            "after_check": lambda: None
        }
    ]

    for test in delete_tests:
        result = delete_swift(db, test["swift_code"])
        assert result == test["expected_result"]

def assert_branch_update(branch):
    assert branch.headquarter_id is None

def assert_empty_db(db):
    count = db.query(SwiftData).count()
    assert count == 0



#API TESTING
@pytest.fixture(scope = "module")
def sample_data():
    return {
        "hq": {
            "swiftCode": "TESTPLSEXXX",
            "bankName": "Test HBank 1",
            "countryISO2": "PL",
            "countryName": "POLAND",
            "address": "213 test street",
            "isHeadquarter": True
        },
        "branch1": {
            "swiftCode": "TESTPLSE123",
            "bankName": "Test BBank",
            "countryISO2": "PL",
            "countryName": "POLAND",
            "address": "2123 test street",
            "isHeadquarter": False
        },
        "branch2": {
            "swiftCode": "TESTPLSE456",
            "bankName": "Test BBank 2",
            "countryISO2": "PL",
            "countryName": "POLAND",
            "address": "4213 test street",
            "isHeadquarter": False
        },
        "hq2": {
            "swiftCode": "EUROLVNKXXX",
            "bankName": "Test HBank 2",
            "countryISO2": "LV",
            "countryName": "LATVIA",
            "address": "2173 test street",
            "isHeadquarter": True
        }
    }

@pytest.fixture(autouse=True)
def seed_data(client,sample_data):
    client.post("/v1/swift-codes", json=sample_data["hq"])
    client.post("/v1/swift-codes", json=sample_data["branch1"])
    client.post("/v1/swift-codes", json=sample_data["branch2"])
    client.post("/v1/swift-codes", json=sample_data["hq2"])
    yield

#GET 1
def test_get_swift_by_details_hq(client, sample_data):
    response = client.get(f"/v1/swift-codes/{sample_data['hq']['swiftCode']}")
    assert response.status_code == 200
    data = response.json()

    assert data["swiftCode"] == sample_data["hq"]["swiftCode"]
    assert data["bankName"] == sample_data["hq"]["bankName"]
    assert data["isHeadquarter"]

    assert(len(data["branches"])) ==2
    codes = {branch["swiftCode"] for branch in data["branches"]}
    assert sample_data["branch1"]["swiftCode"] in codes
    assert sample_data["branch2"]["swiftCode"] in codes


def test_get_swift_by_details_branch(client, sample_data):
    response = client.get(f"/v1/swift-codes/{sample_data['branch1']['swiftCode']}")
    assert response.status_code == 200
    data = response.json()

    assert data["swiftCode"] == sample_data["branch1"]["swiftCode"]
    assert data["bankName"] == sample_data["branch1"]["bankName"]
    assert not data["isHeadquarter"]
    assert "branches" not in data


#GET 2
@pytest.mark.parametrize("country, expected_count, expected_name",[
    ("PL", 3, "POLAND"),
    ("LV", 1, "LATVIA")
])
def test_get_by_country(client, country, expected_count, expected_name):
    response = client.get(f"/v1/swift-codes/country/{country}")
    assert response.status_code == 200
    data = response.json()

    assert data["countryISO2"] == country
    assert data["countryName"] == expected_name
    assert len(data["swiftCodes"]) == expected_count

    assert all(code["countryISO2"] == country for code in data["swiftCodes"])

def test_get_by_country_invalid(client):
    response = client.get("/v1/swift-codes/country/XY")
    assert response.status_code == 404


#POST
def test_swift_add_success(client):
    new_entry = {
        "swift_code": "USUSUSUSXXX",
        "bank_name": "Test Bank",
        "country_iso2": "US",
        "country_name": "UNITED STATES",
        "address": "Test Street 21",
        "isHeadquarter": True
    }

    response = client.post("/v1/swift-codes", json=new_entry)
    assert response.status_code == 200

    get_response = client.get(f"/v1/swift-codes/{new_entry['swift_code']}")
    assert get_response.status_code == 200


def test_add_swift_duplicate(client, sample_data):
    response = client.post("/v1/swift-codes", json=sample_data["hq"])
    assert response.status_code == 409

def test_add_swift_bad_country(client):
    bad = {
        "swift_code": "USUSUSUSXXX",
        "bank_name": "Test Bank",
        "country_iso2": "DE",
        "country_name": "UNITED STATES",
        "address": "Test Street 21",
        "isHeadquarter": True
    }

    response = client.post("/v1/swift-codes", json=bad)
    assert response.status_code == 400

def test_add_swift_missmatch(client):
    mismatch = {
        "swift_code": "USUSDEXXX",
        "bank_name": "Test Bank",
        "country_iso2": "US",
        "country_name": "UNITED STATES",
        "address": "Test Street 21",
        "isHeadquarter": True
    }
    reponse = client.post("/v1/swift-codes", json=mismatch)
    assert reponse.status_code == 400

#DELETE
def test_delete_existing_swift(client, sample_data):
    response_hq = client.delete(f"/v1/swift-codes/{sample_data['hq']['swiftCode']}")
    assert response_hq.status_code == 200

    response_branch1 = client.get(f"/v1/swift-codes/{sample_data['branch1']['swiftCode']}")
    assert response_branch1.status_code == 200

def test_delete_nonexistent_swift(client):
    response = client.delete("/v1/swift-codes/NONEXISTENT")
    assert response.status_code == 404

if __name__ == "__main__":
    unittest.main()