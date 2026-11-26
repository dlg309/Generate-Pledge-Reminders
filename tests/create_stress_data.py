"""Build a reproducible, fictional 30-donor CSV from the supplied 10-donor sample."""

import csv
from decimal import Decimal
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "INPUT_CSV"
SOURCE = DATA_DIR / "NJIT_Pledge_Reminders_Dummy_Data_10_Donors.csv"
OUTPUT = DATA_DIR / "NJIT_Pledge_Reminders_Dummy_Data_30_Donors.csv"


def money(value):
    return f"${Decimal(str(value)):,.2f}"


# name, salutation, street, city/state/ZIP, designation, total, installment due,
# payment amounts, gift type. Dates are assigned in order below.
CASES = [
    ("Ms. Anne-Marie Reed", "Ms. Reed", "14 Willow St Apt 3A", "Newark, NJ 07102-1804", "The NJIT Student Emergency Fund", "12000", "2000", ["2000"], "pledge"),
    ("Mr. Daniel O'Neal Jr.", "Mr. O'Neal", "509 Maple Ave", "Jersey City, NJ 07302-2641", "The Engineering Design Studio Fund", "18000", "3000", ["3000", "3000"], "pledge"),
    ("Dr. Jose Rivera", "Dr. Rivera", "81 South Orange Ave Unit 4", "South Orange, NJ 07079-1720", "The Biomedical Research Scholars Fund", "24000", "4000", ["4000", "4000", "4000"], "pledge"),
    ("Ms. Lena Wu", "Ms. Wu", "240 Harbor View Dr", "Hoboken, NJ 07030-4102", "The Ying Wu College of Computing Opportunity Fund", "36000", "6000", ["6000", "6000", "6000", "6000"], "pledge"),
    ("Horizon Systems LLC", "Friends at Horizon Systems", "700 Innovation Way Ste 210", "Princeton, NJ 08540-6321", "The Corporate Partners Student Internship Fund", "50000", "10000", [], "pledge"),
    ("Mr. & Mrs. Malik and Aisha Brooks", "Mr. and Mrs. Brooks", "98 Garden Terrace", "Montclair, NJ 07042-3905", "The First-Generation Highlanders Scholarship", "75000", "15000", ["15000", "15000"], "pledge"),
    ("Ms. Priya Shah", "Ms. Shah", "12 Cedar Ln Apt 12", "Edison, NJ 08817-2244", "The Newark College of Engineering Annual Fund", "12345.67", "2345.67", ["1000", "2000"], "pledge"),
    ("Dr. Marcus Bell", "Dr. Bell", "463 Broad St", "Newark, NJ 07102-5510", "The Campus Food Pantry and Basic Needs Fund", "5000", "1000", [], "recurring commitment"),
    ("Mrs. Evelyn Carter", "Mrs. Carter", "2 Birch Ct", "Summit, NJ 07901-1806", "The Albert Dorman Honors College Research Fund", "1000000", "200000", ["200000", "200000"], "pledge"),
    ("Mr. Noah Kim", "Mr. Kim", "101 River Rd Unit 6B", "Edgewater, NJ 07020-1129", "The Hillier College of Architecture and Design Materials Laboratory Fund", "85000", "17000", ["17000"], "pledge"),
    ("Ms. Sofia Alvarez", "Ms. Alvarez", "29 Park Place", "New Brunswick, NJ 08901-1309", "THE Women in Technology Scholarship Fund", "16000", "4000", ["4000", "4000"], "pledge"),
    ("Mr. Theo Martin", "Mr. Martin", "35 Walnut St Apt 2", "Bloomfield, NJ 07003-2121", "The Martin Tuchman School of Management Analytics Fund", "32000", "8000", ["8000", "8000", "8000"], "pledge"),
    ("Dr. Isabel Chen", "Dr. Chen", "800 University Ave", "Newark, NJ 07102-1901", "The Applied Mathematics and Data Science Undergraduate Research Fellowship", "48000", "12000", ["12000"], "pledge"),
    ("Mr. Patrick Doyle", "Mr. Doyle", "7 Hillcrest Dr", "West Orange, NJ 07052-4411", "The Veterans and Military Connected Student Support Fund", "9000", "1500", ["1500", "1500"], "pledge"),
    ("Ms. Maya Thompson", "Ms. Thompson", "66 Oak St Ste 4", "East Orange, NJ 07018-2906", 'The "Highlander Promise" Community Scholarship', "22000", "5500", ["5500"], "pledge"),
    ("Dr. Samuel Price", "Dr. Price", "1050 Lakeside Ave", "Burlington, VT 05401-3812", "The Sustainable Infrastructure and Resilient Cities Research Fund", "64000", "16000", ["16000", "16000"], "pledge"),
    ("Ms. Renee Foster", "Ms. Foster", "222 Pine St Apt 5C", "Philadelphia, PA 19106-1730", "The NJIT Athletics and Wellness Annual Fund", "7000", "1000", ["1000", "1000", "1000", "1000"], "pledge"),
    ("Mr. Carlos Vega", "Mr. Vega", "14 Academy St", "Newark, NJ 07102-3014", "The Newark Public School Pipeline and College Access Scholarship Fund", "41000", "8200", [], "pledge"),
    ("Dr. Naomi Ellis", "Dr. Ellis", "91 Observatory Rd", "Cambridge, MA 02138-4402", "The Quantum Computing and Emerging Technologies Student Research Fund", "125000", "25000", ["25000", "25000", "25000"], "pledge"),
    ("Ms. Olivia Grant", "Ms. Grant", "5 Orchard Rd Apt 7", "New York, NY 10002-4812", 'The "Build the Future" Endowed Scholarship for First-Generation Engineering Students', "96000", "12000", ["12000", "12000", "12000", "12000"], "pledge"),
]


def main():
    with SOURCE.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        headers = list(reader.fieldnames or [])
        original = list(reader)
    assert len(original) == 10
    assert len(CASES) == 20
    for index in (3, 4):
        headers.append(f"<<Payment_Date_{index}>> <<Payment_Amount_{index}>>")

    rows = original[:]
    payment_dates = ["2/15/2026", "5/15/2026", "8/15/2026", "10/15/2026"]
    for index, (name, salutation, street, city, fund, total, due, payments, gift_type) in enumerate(CASES, start=1):
        row = {key: "" for key in headers}
        row.update({
            "<<Addressee_Full_Name>>": name,
            "<<Address_Line_1>>": street,
            "<<City_State_ZIP>>": city,
            "<<Letter_Date>>": "November 25, 2026",
            "<<Salutation_Name>>," : salutation + ",",
            "<<Gift_Type>>": gift_type,
            "<<Total_Pledge_Amount>>": money(total),
            "<<Fund_Description>>": fund,
            "<<Signatory_Signature_Image>>": "alan_kelly_sig.png",
            "<<Signatory_Name>>": "Alan Kelly",
            "<<Signatory_Title_1>>": "Senior Vice President, University Advancement",
            "<<Signatory_Title_2>>": "President, Foundation at NJIT",
            "<<Pledge_Date>>": "11/15/2025",
            "<<Total_Pledged>>": money(total),
            "<<Amount_Paid>>": money(sum(Decimal(amount) for amount in payments)),
            "<<Amount_Due>>": money(due),
            "<<Slip_Fund_Description>>": fund,
            "<<Donor_ID>>": str(30000000 + index),
            "<<Constituent_ID_1>>": str(30000 + index),
            "<<Constituent_ID_2>>": str(30000 + index + (1 if index == 6 else 0)),
            "<<Appeal_Code>>": str(2700 + index),
            "<<Package_Code>>": f"{1 + index % 3:02d}",
            "<<Fund_ID>>": str(92000 + index),
            "<<Slip_Addressee_Name>>": name,
            "<<Slip_Address_Line_1>>": street,
            "<<Slip_City_State_ZIP>>": city,
        })
        for payment_index, amount in enumerate(payments, start=1):
            row[f"<<Payment_Date_{payment_index}>> <<Payment_Amount_{payment_index}>>"] = (
                f"{payment_dates[payment_index - 1]} {money(amount)}"
            )
        rows.append(row)

    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Created {OUTPUT} with {len(rows)} fictional test donors")


if __name__ == "__main__":
    main()
