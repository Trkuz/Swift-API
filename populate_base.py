import pandas as pd
from Database.utilities.crud import create_swift
from Database.db_models import SessionLocal, SwiftData

def import_data():

    db = SessionLocal()
    try:
        count = db.query(SwiftData).count()

        if count > 0:
            print(f"{count} records found in database. Skipping import.")
            return

        print("Starting data import...")


        try:
            df = pd.read_excel("Swift data/Swift_Entries.xlsx")
        except FileNotFoundError as e:
            return e

        for column in df.columns:
            if df[column].dtype == "object":
                df[column] = df[column].str.strip()
                df[column] = df[column].replace("", None)


        # swift_pattern = re.compile("^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$")
        # all_match = df['SWIFT CODE'].str.match(swift_pattern).all()
        #
        # ISO_CODES = {country.alpha_2: [country.name.upper(),
        #                                country.official_name.upper() if hasattr(country, "official_name") else None] for country
        #              in pycountry.countries}

        # l= []
        #
        # for _, row in df.iterrows():
        #     if (row["COUNTRY ISO2 CODE"] in ISO_CODES.keys()) and ISO_CODES.get(row["COUNTRY ISO2 CODE"]):
        #         l.append(True)
        #     else:
        #         l.append(False)
        #
        # print(all(l))


        df = df.drop(columns = [ "TIME ZONE", "TOWN NAME", "CODE TYPE"])

        df = df.rename(columns = {
            'SWIFT CODE': 'swift_code',
            'COUNTRY NAME': 'country_name',
            'COUNTRY ISO2 CODE': 'country_iso2',
            'NAME': 'bank_name',
            'ADDRESS': 'address',
        })

        df = df[['bank_name', 'country_iso2', 'country_name', 'swift_code', 'address']]

        success_count = 0
        for _, row in df.iterrows():
            try:
                create_swift(
                    db=db,
                    row=row.to_dict()
                )
                success_count += 1
            except Exception as e:
                print(f"Failed adding entry to database: {str(e)}")

        print(f"{success_count} SWIFT codes added succesfully!")
    except Exception as e:
        print(f"Error during data import: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    import_data()
