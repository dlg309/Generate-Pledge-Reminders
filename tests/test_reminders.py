"""Repeatable checks for the stress-test CSV and signed PDF output."""

import csv
import re
import tempfile
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader

from generate_pledge_reminders import (
    BASE_DIR,
    OUTPUT_BATCH_PDF,
    create_output_directory,
    find_asset,
    format_currency,
    generate_batch,
    normalize_row,
)

INPUT_CSV = BASE_DIR / "INPUT_CSV" / "NJIT_Pledge_Reminders_Dummy_Data_30_Donors.csv"


def amount(value):
    return Decimal(value.replace("$", "").replace(",", ""))


class ReminderChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not INPUT_CSV.is_file():
            raise unittest.SkipTest("Office sample CSV is not included in the public repository")
        cls.temp = tempfile.TemporaryDirectory()
        with open(INPUT_CSV, newline="", encoding="utf-8-sig") as stream:
            cls.rows = [normalize_row(row) for row in csv.DictReader(stream)]
        cls.output_dir = generate_batch(INPUT_CSV, Path(cls.temp.name))
        cls.batch = PdfReader(cls.output_dir / OUTPUT_BATCH_PDF)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_dated_output_folder(self):
        self.assertTrue(self.output_dir.is_dir())
        self.assertIn("Pledge Reminders - 30 Donors", self.output_dir.name)
        second = create_output_directory(Path(self.temp.name), 30)
        self.assertNotEqual(second, self.output_dir)
        third = create_output_directory(Path(self.temp.name), 30)
        self.assertNotEqual(third, second)

    def test_csv_records_and_finances(self):
        self.assertEqual(len(self.rows), 30)
        self.assertEqual(len({row["Donor_ID"] for row in self.rows}), 30)
        required = (
            "Addressee_Full_Name", "Address_Line_1", "City_State_ZIP",
            "Salutation_Name", "Fund_Description", "Slip_Fund_Description",
            "Signatory_Name", "Donor_ID", "Pledge_Date", "Letter_Date",
        )
        for row in self.rows:
            with self.subTest(donor=row["Donor_ID"]):
                for field in required:
                    self.assertTrue(row.get(field, "").strip(), field)
                self.assertTrue(find_asset(row["Signatory_Signature_Image"]).is_file())
                self.assertEqual(amount(row["Total_Pledge_Amount"]), amount(row["Total_Pledged"]))
                payments = [
                    amount(value) for key, value in row.items()
                    if re.fullmatch(r"Payment_Amount_\d+", key) and value.strip()
                ]
                self.assertEqual(sum(payments, Decimal(0)), amount(row["Amount_Paid"]))
                self.assertGreaterEqual(amount(row["Amount_Due"]), 0)
                self.assertLessEqual(
                    amount(row["Amount_Due"]),
                    amount(row["Total_Pledged"]) - amount(row["Amount_Paid"]),
                )
                pledge_date = datetime.strptime(row["Pledge_Date"], "%m/%d/%Y")
                letter_date = datetime.strptime(row["Letter_Date"], "%B %d, %Y")
                self.assertLessEqual(pledge_date, letter_date)
                for key, value in row.items():
                    if re.fullmatch(r"Payment_Date_\d+", key) and value.strip():
                        self.assertLessEqual(pledge_date, datetime.strptime(value, "%m/%d/%Y"))
                        self.assertLessEqual(datetime.strptime(value, "%m/%d/%Y"), letter_date)

    def test_four_payment_columns_and_exact_currency(self):
        four_payment = self.rows[13]
        self.assertEqual(four_payment["Payment_Date_4"], "10/15/2026")
        self.assertEqual(four_payment["Payment_Amount_4"], "$6,000.00")
        self.assertEqual(format_currency("12345.67"), "$12,345.67")
        with self.assertRaises(ValueError):
            format_currency("bad amount")

    def test_signed_batch_and_individual_reminders(self):
        self.assertEqual(len(self.batch.pages), len(self.rows) * 2)
        individual_files = [
            path for path in self.output_dir.glob("*.pdf") if path.name != OUTPUT_BATCH_PDF
        ]
        self.assertEqual(len(individual_files), len(self.rows))
        for index, row in enumerate(self.rows):
            with self.subTest(donor=row["Donor_ID"]):
                front = self.batch.pages[index * 2]
                text = front.extract_text()
                self.assertIn(row["Addressee_Full_Name"], text)
                self.assertIn(row["Donor_ID"], text)
                self.assertIn(format_currency(row["Total_Pledged"]), text)
                self.assertIn(format_currency(row["Amount_Due"]), text)
                payment_count = sum(
                    bool(value.strip()) for key, value in row.items()
                    if re.fullmatch(r"Payment_Date_\d+", key)
                )
                self.assertEqual(text.count("Payments received:"), payment_count)
                images = front["/Resources"]["/XObject"]
                self.assertGreaterEqual(
                    sum(obj.get_object().get("/Subtype") == "/Image" for obj in images.values()), 2
                )
                safe_name = "".join(ch for ch in row["Salutation_Name"] if ch.isalnum())
                individual = PdfReader(
                    self.output_dir / f"{row['Donor_ID']}_{safe_name}_Pledge_Reminder.pdf"
                )
                self.assertEqual(len(individual.pages), 2)
                self.assertEqual(individual.pages[0].extract_text(), text)


if __name__ == "__main__":
    unittest.main()

