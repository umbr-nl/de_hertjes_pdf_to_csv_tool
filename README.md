# de_hertjes_pdf_to_csv_tool

Lokaal Python-script dat een quizboek PDF inleest via OCR en exporteert naar een CSV die direct geïmporteerd kan worden in de [Hertjes App](https://github.com/umbr-nl/de_hertjes_apps).

## Waarom los van de app?

OCR op een grote PDF is te zwaar voor een webserver (timeouts). Dit script draait lokaal, zonder tijdslimiet, en levert een nette CSV op die je vervolgens uploadt.

## Vereisten

### Systeempakketten (macOS)
```bash
brew install tesseract tesseract-lang poppler
```

### Python packages
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Gebruik

Activeer eerst de venv (eenmalig per terminalsessie):
```bash
cd /pad/naar/de_hertjes_pdf_to_csv_tool
source venv/bin/activate
```

Daarna het script starten:
```bash
python3 pdf_to_csv.py mijn_quizboek.pdf
```

### Opties

| Optie | Beschrijving | Default |
|---|---|---|
| `--output BESTAND` | Pad naar het output CSV bestand | `output.csv` |
| `--eerste-pagina-leeg` | Eerste PDF-pagina is leeg (verschuif nummering) | uit |
| `--dpi GETAL` | Kwaliteit van OCR scan (hoger = beter, trager) | `300` |
| `--taal TAAL` | Tesseract taalcode | `nld+eng` |

### Voorbeelden

```bash
# Standaard gebruik
python3 pdf_to_csv.py quizboek_2026.pdf

# Eerste pagina is leeg, hogere kwaliteit, eigen bestandsnaam
python3 pdf_to_csv.py quizboek_2026.pdf --eerste-pagina-leeg --dpi 400 --output import_2026.csv
```

## CSV formaat

Het script produceert een CSV met de volgende kolommen, zoals verwacht door de Hertjes App:

| Kolom | Type | Beschrijving |
|---|---|---|
| `pagina` | integer | PDF-paginanummer (met eventuele offset) |
| `bladzijde` | integer of leeg | Gedrukt bladzijdenummer onderaan de pagina |
| `opdrachtnummer` | integer | Vraagnummer op die pagina |
| `omschrijving` | tekst | Volledige vraagtekst |
| `punten` | integer | Aantal punten voor de opdracht |
| `is_teamcaptain` | True/False | Bevat het woord "teamcaptain" |
| `is_teamnummer` | True/False | Bevat het woord "teamnummer" |
| `is_tijdopdracht` | True/False | Bevat een tijdsaanduiding |

## PDF formaat

Het script verwacht dat vragen in de PDF de volgende structuur hebben:

```
Vraag 3 (2 punten)
Wat is de hoofdstad van Nederland?
```

of met een tussenkopje:

```
Vraag 3 (Muziek) (2 punten)
...
```
