"""Download official EPRA releases and OCR their Nairobi cost annexes.

The source PDFs are image scans.  This script keeps downloads and raw OCR text
under ``tmp/`` (not version controlled) and writes a compact audit index under
``data/``.  Extraction is deliberately separate from numeric parsing so every
model value can be traced back to the exact official PDF and OCR output.
"""

from __future__ import annotations

import csv
import hashlib
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import fitz
import requests

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "data" / "epra_component_source_inventory.csv"
AUDIT_OUTPUT = ROOT / "data" / "epra_annex_ocr_audit.csv"
PDF_DIR = ROOT / "tmp" / "epra_component_pdfs"
OCR_DIR = ROOT / "tmp" / "epra_component_ocr"


def slugify(value: str, identity: str = "") -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:10] if identity else ""
    return f"{value[:72]}-{suffix}" if suffix else value[:90]


def find_tesseract() -> str:
    executable = shutil.which("tesseract")
    candidates = [
        executable,
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise RuntimeError(
        "Tesseract OCR was not found. Install UB-Mannheim.TesseractOCR on Windows "
        "or make the tesseract executable available on PATH."
    )


def download(row: dict[str, str], session: requests.Session) -> tuple[dict[str, str], Path]:
    # The URL digest prevents similarly worded monthly releases from colliding.
    name = slugify(row["Title"], row["PDF_URL"])
    path = PDF_DIR / f"{name}.pdf"
    if not path.exists() or path.stat().st_size < 10_000:
        response = session.get(row["PDF_URL"], timeout=120)
        response.raise_for_status()
        if not response.content.startswith(b"%PDF"):
            raise ValueError(f"Response is not a PDF: {row['PDF_URL']}")
        path.write_bytes(response.content)
    return row, path


def ocr_last_page(pdf_path: Path, tesseract: str) -> tuple[int, str]:
    document = fitz.open(pdf_path)
    page_number = len(document)
    page = document[-1]
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    image_path = OCR_DIR / f"{pdf_path.stem}.png"
    text_path = OCR_DIR / f"{pdf_path.stem}.txt"
    pixmap.save(image_path)
    completed = subprocess.run(
        [tesseract, str(image_path), "stdout", "--psm", "3", "-l", "eng"],
        check=True,
        capture_output=True,
    )
    text = completed.stdout.decode("utf-8", errors="replace")
    text_path.write_text(text, encoding="utf-8")
    return page_number, text


def main() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    OCR_DIR.mkdir(parents=True, exist_ok=True)
    tesseract = find_tesseract()
    with INVENTORY.open(encoding="utf-8", newline="") as handle:
        source_rows = list(csv.DictReader(handle))

    session = requests.Session()
    session.headers["User-Agent"] = "MafutaPlan academic EPRA annex extraction/1.0"
    downloaded: list[tuple[dict[str, str], Path]] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(download, row, session) for row in source_rows]
        for future in as_completed(futures):
            downloaded.append(future.result())

    audit_rows: list[dict[str, str | int]] = []
    for number, (row, pdf_path) in enumerate(sorted(downloaded, key=lambda item: item[0]["Title"]), 1):
        try:
            page_number, text = ocr_last_page(pdf_path, tesseract)
            status = "OCR complete" if len(text) >= 250 else "Manual review required"
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            error = ""
        except Exception as exc:  # Preserve failures in the audit rather than hiding them.
            page_number, text, digest = 0, "", ""
            status, error = "OCR failed", str(exc)
        audit_rows.append(
            {
                "Title": row["Title"],
                "Release_Page_URL": row["Release_Page_URL"],
                "PDF_URL": row["PDF_URL"],
                "Local_PDF": str(pdf_path.relative_to(ROOT)),
                "Annex_Page": page_number,
                "OCR_Text_SHA256": digest,
                "OCR_Characters": len(text),
                "Extraction_Status": status,
                "Error": error,
            }
        )
        print(f"[{number:02d}/{len(downloaded):02d}] {status}: {row['Title']}", flush=True)

    with AUDIT_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit_rows[0]))
        writer.writeheader()
        writer.writerows(audit_rows)
    print(f"Wrote {len(audit_rows)} OCR audit records to {AUDIT_OUTPUT}")


if __name__ == "__main__":
    main()
