"""
de_hertjes_pdf_to_csv_tool
==========================
Lokaal script dat een quizboek PDF inleest via OCR en exporteert naar een CSV
die direct geïmporteerd kan worden in de Hertjes App.

Gebruik:
    python pdf_to_csv.py <pad-naar-pdf> [opties]

Opties:
    --output BESTAND    Pad naar het output CSV bestand (default: output.csv)
    --eerste-pagina-leeg  Eerste PDF-pagina is leeg (offset paginanummers met 1)
    --dpi GETAL         DPI voor OCR scan (default: 300)
    --taal TAAL         Tesseract taalcode (default: nld+eng)

Vereisten:
    - Tesseract OCR geïnstalleerd (brew install tesseract tesseract-lang)
    - Poppler geïnstalleerd (brew install poppler)
    - pip install -r requirements.txt
"""

import argparse
import csv
import re
import sys
from pathlib import Path


def extract_tijden(text: str) -> list[str]:
    """Extraheer tijden uit tekst (bijv. '10:00', '5 minuten')."""
    tijd_pattern = r'\b(\d{1,2}[:\.]\d{2})\b|(\d+)\s*(min(?:uten)?|sec(?:onden)?)\b'
    tijden = re.findall(tijd_pattern, text, re.IGNORECASE)
    return [next(g for g in match if g) for match in tijden if any(match)]


def parse_ocr_text(ocr_text: str, eerste_pagina_leeg: bool = False) -> list[dict]:
    """
    Parseer de OCR-tekst naar een lijst van opdracht-dicts.

    Verwacht paginamarkeringen in de vorm:
        === PAGINA 1/20 ===
    en vraagblokken in de vorm:
        Vraag 3 (2 punten)
    """
    pages = re.split(r'=== PAGINA (\d+)/\d+ ===', ocr_text)
    offset = 1 if eerste_pagina_leeg else 0
    opdrachten = []

    for i in range(1, len(pages), 2):
        raw_page_num = int(pages[i])
        page_num = raw_page_num - offset

        if page_num < 0:
            continue

        page_text = pages[i + 1] if i + 1 < len(pages) else ''

        # Patroon: "Vraag X (optioneel iets) (Y punten)"
        vraag_pattern = r'Vraag\s+(\d+)\s*(?:\([^)]*\))?\s*\((\d+)\s*punten?\)'

        matches = list(re.finditer(vraag_pattern, page_text, re.IGNORECASE))

        for idx, match in enumerate(matches):
            vraag_num = int(match.group(1))
            punten = int(match.group(2))

            # Tekst van dit vraagblok: tot de volgende vraag of einde pagina
            einde = matches[idx + 1].start() if idx + 1 < len(matches) else len(page_text)
            vraag_tekst = page_text[match.end():einde].strip()

            is_teamcaptain = 'teamcaptain' in vraag_tekst.lower()
            is_teamnummer = 'teamnummer' in vraag_tekst.lower()
            is_tijdopdracht = len(extract_tijden(vraag_tekst)) > 0

            opdrachten.append({
                'pagina': page_num,
                'opdrachtnummer': vraag_num,
                'omschrijving': vraag_tekst,
                'punten': punten,
                'is_teamcaptain': is_teamcaptain,
                'is_teamnummer': is_teamnummer,
                'is_tijdopdracht': is_tijdopdracht,
            })

    return opdrachten


def pdf_to_ocr_text(
    pdf_path: Path,
    dpi: int = 300,
    taal: str = 'nld+eng',
    progress_callback=None,
    cancel_event=None,
) -> str | None:
    """
    Converteer een PDF naar OCR-tekst via pdf2image + pytesseract.

    Args:
        progress_callback: optioneel callable(message: str, percentage: float)
        cancel_event:      optioneel threading.Event; als set() wordt gezet, stopt de OCR.

    Returns:
        De volledige OCR-tekst, of None als geannuleerd.
    """
    def log(msg):
        if progress_callback:
            progress_callback(msg, None)
        else:
            print(msg)

    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError as e:
        log(f"Fout: vereiste library niet gevonden: {e}")
        log("Installeer met: pip install -r requirements.txt")
        sys.exit(1)

    log(f"PDF laden: {pdf_path}")
    images = convert_from_path(str(pdf_path), dpi=dpi)
    total = len(images)
    log(f"{total} pagina's gevonden, OCR starten...")

    full_text = []

    for i, image in enumerate(images, start=1):
        if cancel_event and cancel_event.is_set():
            return None

        msg = f"Pagina {i}/{total} scannen..."
        pct = (i - 1) / total * 90  # 0–90% voor OCR, rest voor parsen/schrijven
        if progress_callback:
            progress_callback(msg, pct)
        else:
            print(f"  {msg}", end='\r')

        text = pytesseract.image_to_string(image, lang=taal, config='--psm 6')
        full_text.append(f"\n=== PAGINA {i}/{total} ===\n{text}")

    log(f"OCR klaar: {total} pagina's verwerkt.")
    return ''.join(full_text)


def schrijf_csv(opdrachten: list[dict], output_path: Path) -> None:
    """Schrijf de opdrachtenlijst naar een CSV bestand."""
    velden = ['pagina', 'opdrachtnummer', 'omschrijving', 'punten',
              'is_teamcaptain', 'is_teamnummer', 'is_tijdopdracht']

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=velden)
        writer.writeheader()
        writer.writerows(opdrachten)

    print(f"CSV opgeslagen: {output_path} ({len(opdrachten)} opdrachten)")


def main():
    parser = argparse.ArgumentParser(
        description='Converteer een quizboek PDF naar een importeerbare CSV voor de Hertjes App.'
    )
    parser.add_argument('pdf', type=Path, help='Pad naar het PDF bestand')
    parser.add_argument('--output', type=Path, default=Path('output.csv'),
                        help='Pad naar het output CSV bestand (default: output.csv)')
    parser.add_argument('--eerste-pagina-leeg', action='store_true',
                        help='Eerste PDF-pagina is leeg, verschuif paginanummers met 1')
    parser.add_argument('--dpi', type=int, default=300,
                        help='DPI voor OCR kwaliteit (default: 300, hoger = beter maar trager)')
    parser.add_argument('--taal', type=str, default='nld+eng',
                        help='Tesseract taalcode (default: nld+eng)')

    args = parser.parse_args()

    if not args.pdf.exists():
        print(f"Fout: PDF bestand niet gevonden: {args.pdf}")
        sys.exit(1)

    # Stap 1: OCR
    ocr_text = pdf_to_ocr_text(args.pdf, dpi=args.dpi, taal=args.taal)

    if ocr_text is None:
        print("Geannuleerd.")
        sys.exit(0)

    # Stap 2: Parsen
    opdrachten = parse_ocr_text(ocr_text, eerste_pagina_leeg=args.eerste_pagina_leeg)
    print(f"{len(opdrachten)} opdrachten gevonden.")

    if not opdrachten:
        print("Waarschuwing: geen opdrachten gevonden. Controleer het PDF formaat.")
        sys.exit(1)

    # Stap 3: CSV exporteren
    schrijf_csv(opdrachten, args.output)


if __name__ == '__main__':
    main()
