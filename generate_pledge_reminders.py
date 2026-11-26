import csv
import io
import re
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth

BASE_DIR = Path(__file__).resolve().parent
ASSET_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
TEMPLATE_PDF = "Pledge Reminder Blank Template.pdf"
OUTPUT_BATCH_PDF = "Merged_Pledge_Reminders_Batch_Signed.pdf"


def find_asset(filename: str, csv_path: Path | None = None) -> Path:
    """Find an asset beside the CSV, application, or bundled docs folder."""
    path = Path(filename)
    candidates = [path] if path.is_absolute() else [
        *([csv_path.parent / path] if csv_path else []),
        ASSET_DIR / path, ASSET_DIR / "docs" / path,
        BASE_DIR / path, BASE_DIR / "docs" / path,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Could not find {filename!r}; checked: {', '.join(map(str, candidates))}")


def create_output_directory(destination: Path, reminder_count: int) -> Path:
    """Reserve a new folder for this run without replacing an earlier batch."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    stem = f"{datetime.now():%Y-%m-%d_%H-%M-%S} Pledge Reminders - {reminder_count} Donors"
    for suffix in range(1000):
        folder = destination / (stem if suffix == 0 else f"{stem} ({suffix + 1})")
        try:
            folder.mkdir()
            return folder
        except FileExistsError:
            continue
    raise FileExistsError("Could not reserve a unique output folder")


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    """Convert the CSV's merge-tag headers and combined payments to script fields."""
    normalized = {
        key.replace("<<", "").replace(">>", "").rstrip(","): value
        for key, value in row.items()
    }
    for key in list(normalized):
        match = re.fullmatch(r"Payment_Date_(\d+) Payment_Amount_\1", key)
        if match:
            payment = normalized.pop(key).strip()
            date, _, amount = payment.partition(" ")
            normalized[f"Payment_Date_{match[1]}"] = date
            normalized[f"Payment_Amount_{match[1]}"] = amount.strip()
    return normalized


def format_currency(val: str) -> str:
    """Ensure dollar formatting ($50,000.00) whether CSV has raw numbers or formatted strings."""
    if not val or not str(val).strip():
        return ""
    cleaned = str(val).replace("$", "").replace(",", "").strip()
    try:
        return f"${Decimal(cleaned):,.2f}"
    except InvalidOperation as exc:
        raise ValueError(f"Invalid currency amount: {val!r}") from exc


def draw_wrapped_text(c, text, x, y, max_width, font_name, font_size, leading):
    """Draw word-wrapped text downward from (x, y) and return the final y coordinate."""
    c.setFont(font_name, font_size)
    lines = simpleSplit(text, font_name, font_size, max_width)
    for line in lines:
        c.drawString(x, y, line)
        y -= leading
    return y


def build_front_overlay(row: dict, page_w: float, page_h: float, signature_path: Path | None = None) -> io.BytesIO:
    """Create a transparent vector PDF layer aligned to Page 1 of Pledge Reminder Blank Template.pdf."""
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_w, page_h))

    # --- SECTION 1A: UPPER LETTER BODY (PDF origin is bottom-left: 0,0) ---
    # Letterhead occupies y = 715..766; mission tagline sits at y = 275..283.
    font_body = "Helvetica"
    font_bold = "Helvetica-Bold"
    payment_indices = sorted(
        int(match[1])
        for key in row
        if (match := re.fullmatch(r"Payment_Date_(\d+)", key))
        and row[key].strip()
    )
    # Four payment rows need a little less line spacing to clear the fold tagline.
    size_body = 10.0 if len(payment_indices) >= 4 else 10.5
    leading = 12.5 if len(payment_indices) >= 4 else 14.0

    # Recipient Address Block (Top Left) & Letter Date (Top Right)
    y = 682
    c.setFont(font_body, size_body)
    name = row.get("Addressee_Full_Name", "").strip()
    letter_date = row.get("Letter_Date", "").strip()
    if 42 + stringWidth(name, font_body, size_body) + 10 > 565 - stringWidth(letter_date, font_body, size_body):
        raise ValueError(f"Recipient name overlaps letter date for donor {row.get('Donor_ID', '?')}")
    c.drawString(42, y, name)
    c.drawRightString(565, y, letter_date)
    y -= leading
    c.drawString(42, y, row.get("Address_Line_1", "").strip())
    y -= leading
    c.drawString(42, y, row.get("City_State_ZIP", "").strip())

    # Salutation
    y -= 24
    salutation = row.get("Salutation_Name", "").strip().rstrip(",")
    c.drawString(42, y, f"Dear {salutation},")

    # Opening Paragraph (dynamically merges Gift_Type, Total_Pledge_Amount, Fund_Description)
    y -= 22
    gift_type = row.get("Gift_Type", "pledge").strip()
    total_amt = format_currency(row.get("Total_Pledge_Amount", ""))
    fund_desc = row.get("Fund_Description", "").strip()
    # Avoid duplicate "the The ..." if Fund_Description starts with "The "
    fund_phrase = fund_desc if fund_desc.lower().startswith("the ") else f"the {fund_desc}"

    para_1 = (
        f"On behalf of the entire New Jersey Institute of Technology community, I write to thank you "
        f"for your continued support. Your generous {gift_type} of {total_amt} to {fund_phrase} "
        f"has helped us strengthen, in many critically important ways, the NJIT experience for our "
        f"hardworking and high-achieving students. On their behalf, in particular, please accept my "
        f"deepest and most sincere thanks."
    )
    y = draw_wrapped_text(c, para_1, 42, y, max_width=525, font_name=font_body, font_size=size_body, leading=leading)

    # Second Paragraph (Static Pledge Instructions)
    y -= 8
    para_2 = (
        'Below, I have outlined a summary of your pledge status. There are several options for making '
        'your next pledge installment. You may return by mail the payment slip below, along with a check '
        'made payable to the "Foundation at New Jersey Institute of Technology." Credit card payments can '
        'be made on our secure website at www.njit.edu/givenow. I have also enclosed information about '
        'transferring gifts of securities to the university.'
    )
    y = draw_wrapped_text(c, para_2, 42, y, max_width=525, font_name=font_body, font_size=size_body, leading=leading)

    # Variable Payment History Rows (supports 1 to N payments without blank lines)
    y -= 8
    c.setFont(font_body, size_body)
    for idx in payment_indices:
        p_date = row.get(f"Payment_Date_{idx}", "").strip()
        p_amt = format_currency(row.get(f"Payment_Amount_{idx}", ""))
        if p_date or p_amt:
            c.drawString(42, y, f"Payments received: {p_date}  {p_amt}".strip())
            y -= leading

    # Closing Paragraph
    y -= 8
    para_3 = (
        "If you have recently sent in your pledge payment, thank you for your generosity. You may "
        "disregard this reminder. As always, please feel free to contact me with any questions or concerns "
        "at the phone number or email address noted below. Thank you, once again, for your support of NJIT."
    )
    y = draw_wrapped_text(c, para_3, 42, y, max_width=525, font_name=font_body, font_size=size_body, leading=leading)

    # Sign-off & Signatory Block
    y -= 10
    c.drawString(42, y, "With gratitude and appreciation,")

    if signature_path:
        c.drawImage(str(signature_path), 42, y - 34, width=110, height=28, mask="auto", preserveAspectRatio=True)
    y -= 42

    c.setFont(font_bold, size_body)
    c.drawString(42, y, row.get("Signatory_Name", "").strip())
    y -= 13
    c.setFont(font_body, 9.5)
    c.drawString(42, y, row.get("Signatory_Title_1", "").strip())
    y -= 12
    c.drawString(42, y, row.get("Signatory_Title_2", "").strip())
    if y < 295:
        raise ValueError(f"Letter body reaches the fold tagline for donor {row.get('Donor_ID', '?')}")

    # --- SECTION 1B: LOWER PERFORATED REMITTANCE SLIP ---
    # Summary Table Cell Centers measured from Blank Template:
    # Col 1 (TOTAL PLEDGED): x = 142.2..251.3 -> center = 196.75
    # Col 2 (AMOUNT PAID):   x = 251.3..362.2 -> center = 306.75
    # Col 3 (AMOUNT DUE):    x = 362.5..471.6 -> center = 417.05
    # Value row vertical center: y = 165.5
    c.setFont(font_bold, 9.5)
    c.drawCentredString(196.75, 165.5, format_currency(row.get("Total_Pledged", "")))
    c.drawCentredString(306.75, 165.5, format_currency(row.get("Amount_Paid", "")))
    c.drawCentredString(417.05, 165.5, format_currency(row.get("Amount_Due", "")))

    # Pledge Date (Right of table, beneath NJIT logo)
    c.setFont(font_bold, 8.5)
    c.drawCentredString(542.0, 187.0, "Pledge Date")
    c.setFont(font_body, 8.5)
    c.drawCentredString(542.0, 176.0, row.get("Pledge_Date", "").strip())

    # Fund / Designation Line (Centered below summary box)
    c.setFont(font_bold, 8.5)
    fund_lines = simpleSplit(row.get("Slip_Fund_Description", "").strip(), font_bold, 8.5, 260)
    if len(fund_lines) > 4:
        raise ValueError(f"Slip fund description is too long for donor {row.get('Donor_ID', '?')}")
    for line_index, line in enumerate(fund_lines):
        c.drawCentredString(285.0, 136.0 - 10.0 * line_index, line)

    # Raiser's Edge Tracking Code Line
    donor_id = row.get("Donor_ID", "").strip()
    cn1 = row.get("Constituent_ID_1", "").strip()
    cn2 = row.get("Constituent_ID_2", "").strip()
    ac = row.get("Appeal_Code", "").strip()
    pc = row.get("Package_Code", "").strip()
    fn = row.get("Fund_ID", "").strip()
    tracking_line = f"DI:{donor_id} CN:{cn1} and {cn2} AC:{ac} PC:{pc} FN:{fn}"
    if 65 + stringWidth(tracking_line, font_body, 8.0) > 410:
        raise ValueError(f"Tracking code line is too wide for donor {donor_id}")

    c.setFont(font_body, 8.0)
    c.drawString(65, 92.0, tracking_line)

    # Remittance Slip Window-Envelope Mailing Block
    c.setFont(font_body, 9.0)
    c.drawString(65, 78.0, row.get("Slip_Addressee_Name", "").strip())
    c.drawString(65, 67.0, row.get("Slip_Address_Line_1", "").strip())
    c.drawString(65, 56.0, row.get("Slip_City_State_ZIP", "").strip())

    c.save()
    packet.seek(0)
    return packet


def load_rows(input_csv: Path) -> list[dict[str, str]]:
    with Path(input_csv).open(mode="r", newline="", encoding="utf-8-sig") as stream:
        rows = [normalize_row(row) for row in csv.DictReader(stream)]
    if not rows:
        raise ValueError(f"No donor records found in {input_csv}")
    return rows


def generate_batch(input_csv: Path, destination: Path) -> Path:
    input_csv = Path(input_csv).resolve()
    template_path = find_asset(TEMPLATE_PDF)
    base_reader = PdfReader(template_path)
    if len(base_reader.pages) < 2:
        raise ValueError("The reminder template must have at least two pages")
    front_box = base_reader.pages[0].mediabox
    page_w, page_h = float(front_box.width), float(front_box.height)

    batch_writer = PdfWriter()
    rows = load_rows(input_csv)
    signatures = [
        find_asset(row["Signatory_Signature_Image"].strip(), input_csv)
        if row.get("Signatory_Signature_Image", "").strip() else None
        for row in rows
    ]
    output_dir = create_output_directory(destination, len(rows))

    for idx, row in enumerate(rows, start=1):
        # Re-read fresh template pages per donor so overlays never stack onto prior donors.
        fresh_template = PdfReader(template_path)
        # pypdf 7 requires a page to belong to a writer before merge_page().
        front_page = batch_writer.add_page(fresh_template.pages[0])
        back_page = batch_writer.add_page(fresh_template.pages[1])

        overlay_pdf = PdfReader(build_front_overlay(row, page_w, page_h, signatures[idx - 1]))
        front_page.merge_page(overlay_pdf.pages[0])
        # pypdf 7.1.1 leaves a one-shot iterator in the merged clipping path.
        # Reparse it now so later writes to batch and individual PDFs keep the text visible.
        front_page.replace_contents(front_page.get_contents())

        single_writer = PdfWriter()
        single_writer.add_page(front_page)
        single_writer.add_page(back_page)
        donor_id = row.get("Donor_ID", f"row_{idx}").strip()
        safe_name = "".join(ch for ch in row.get("Salutation_Name", "Donor") if ch.isalnum())
        out_single = output_dir / f"{donor_id}_{safe_name}_Pledge_Reminder.pdf"
        with out_single.open("wb") as sf:
            single_writer.write(sf)

    batch_path = output_dir / OUTPUT_BATCH_PDF
    with batch_path.open("wb") as out_f:
        batch_writer.write(out_f)

    print(f"Done! Created {output_dir} with {len(rows)} reminders and a {len(batch_writer.pages)}-page batch PDF.")
    return output_dir


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate pledge reminders from a CSV")
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    generate_batch(args.input_csv, args.destination)
