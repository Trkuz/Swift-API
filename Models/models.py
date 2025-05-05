import pycountry
from pydantic import BaseModel, field_validator, model_validator, Field
from typing import Optional, List
from re import compile
from itertools import chain
from fastapi import HTTPException

VALID_COUNTRIES = {country.alpha_2: [country.name.upper(),country.official_name.upper()
                              if hasattr(country, "official_name") else None]
                              for country in pycountry.countries}

class BaseInfo(BaseModel):
     address: Optional[str]
     bank_name: Optional[str] = Field(None, alias = "bankName")
     country_iso2: Optional[str] = Field(None, alias = "countryISO2")
     country_name: Optional[str] = Field(None, alias = "countryName")
     is_headquarter: Optional[bool] = Field(None, alias = "isHeadquarter")
     swift_code: Optional[str] = Field(None, alias = "swiftCode")

     model_config = {
          'from_attributes': True,
          'populate_by_name': True,
     }



#LIST POCKET
class SwiftEntry(BaseInfo):
     country_name: Optional[str] = Field(None, alias = "countryName", exclude=True)


#REPONSE FOR BRANCH
class SwiftEntryBranch(BaseInfo):

     """
     Alias class to increase readability

     """
     pass


#ENDPOINT 1 - GET - GIT
#RESPONSE FOR HEADQUARTER
class SwiftEntryHeadquarter(BaseInfo):
     branches: Optional[List[SwiftEntry]]


#ENDPOINT 2 - GET
class SwiftCodesByCountry(BaseModel):
     country_iso2: Optional[str] = Field(None, alias = "countryISO2")
     country_name: Optional[str] = Field(None, alias="countryName")
     swift_codes: List[Optional[SwiftEntry]] = Field([], alias="swiftCodes")


#ENDPOINT 3 - POST
class SwiftCodeCreateRequest(BaseInfo):


     #SWIFT VALIDATION
     @classmethod
     @field_validator('swift_code')
     def validate_swift(cls, swift_code: str) -> str:
          if not swift_code or swift_code == "":
               raise HTTPException(status_code=400, detail='SWIFT code not specified!')

          swift_pattern = compile("^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$")
          swift_code = swift_code.upper()
          if not swift_pattern.match(swift_code):
               raise HTTPException(status_code=400, detail='Incorrect SWIFT code!')
          return swift_code

     #Country code validation
     @classmethod
     @field_validator('country_iso2')
     def validate_iso2(cls, country_iso2: str) -> str:
          if not country_iso2 or country_iso2 == "":
               raise HTTPException(status_code=400, detail="ISO2 code not specified!")

          country_iso2 = country_iso2.upper()
          if not pycountry.countries.get(alpha_2 =country_iso2):
               raise HTTPException(status_code=400, detail=f"Invalid ISO2 country code!")
          return country_iso2.upper()

     #COUNTRY NAME VALIDATION
     @classmethod
     @field_validator('country_name')
     def validate_country_name(cls, country_name: str) -> str:
          if not country_name or country_name == "":
               raise HTTPException(status_code=400, detail="Country name not specified!")

          country_name = country_name.upper()
          if country_name not in set(chain.from_iterable(VALID_COUNTRIES.values())):
               raise HTTPException(status_code=400, detail="Invalid country name!")
          return country_name.upper()


     #OTHER NAMES VALIDATION
     @model_validator(mode="after")
     def validate_names(self: "SwiftCodeCreateRequest") -> "SwiftCodeCreateRequest":
          for category in ("bank_name", "address"):
               item = getattr(self, category)
               if item is None:
                    continue

               item = item.strip()
               if len(item) > 500:
                    raise HTTPException(status_code=400, detail=f"Field{category} is too long!")
               if len(item) == 0:
                    setattr(self, category, None)

          return self

     @model_validator(mode = "after")
     def check_data_integrity(self: "SwiftCodeCreateRequest") -> "SwiftCodeCreateRequest":
          self.country_name = self.country_name.upper()
          self.country_iso2 = self.country_iso2.upper()
          country_code = self.swift_code[4:6]
          if country_code != self.country_iso2:
               raise HTTPException(status_code=400, detail=f"Country code does not math the SWIFT!")
          if self.country_name.upper() not in VALID_COUNTRIES.get(country_code):
               raise HTTPException(status_code=400, detail=f"Country name does not math the country code!")
          return self


class MessageResponse(BaseModel):
     message: str

