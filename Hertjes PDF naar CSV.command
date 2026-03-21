#!/bin/zsh
# Hertjes PDF → CSV converter
# Dubbelklik dit bestand in de Finder om te starten.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Kies PDF via dialoog ─────────────────────────────────────────────── #
PDF=$(osascript -e '
  tell application "Finder"
    set theFile to choose file with prompt "Selecteer een quizboek PDF:" of type {"pdf"}
    return POSIX path of theFile
  end tell
' 2>/dev/null)

if [[ -z "$PDF" ]]; then
  echo "Geannuleerd."
  read -r "?Druk op Enter om te sluiten."
  exit 0
fi

BASE_OUTPUT="$(dirname "$PDF")/$(basename "$PDF" .pdf)"
OUTPUT="${BASE_OUTPUT}.csv"
if [[ -f "$OUTPUT" ]]; then
  COUNTER=2
  while [[ -f "${BASE_OUTPUT}_${COUNTER}.csv" ]]; do
    (( COUNTER++ ))
  done
  OUTPUT="${BASE_OUTPUT}_${COUNTER}.csv"
fi

echo "PDF:    $PDF"
echo "Output: $OUTPUT"
echo ""

# ── Vraag of eerste pagina leeg is ──────────────────────────────────── #
EERSTE_LEEG=""
ANTWOORD=$(osascript -e '
  button returned of (display dialog "Is de eerste pagina van de PDF leeg?" buttons {"Nee", "Ja"} default button "Nee")
')
if [[ "$ANTWOORD" == "Ja" ]]; then
  EERSTE_LEEG="--eerste-pagina-leeg"
  echo "Optie:  eerste pagina leeg aan"
fi

# ── Vraag startpaginanummer ──────────────────────────────────────────── #
START_PAGINA_ARG=()
START_PAGINA=$(osascript -e '
  text returned of (display dialog "Wat is het eerste paginanummer in de CSV?\n(Laat leeg of vul 1 in als de PDF vanaf pagina 1 begint.)" default answer "1" buttons {"OK"} default button "OK")
')
if [[ -n "$START_PAGINA" && "$START_PAGINA" != "1" ]]; then
  START_PAGINA_ARG=(--start-pagina "$START_PAGINA")
  echo "Optie:  startpagina $START_PAGINA"
fi

# ── Vraag DPI ───────────────────────────────────────────────────────── #
DPI=$(osascript -e '
  text returned of (display dialog "Scan kwaliteit (DPI):\n\n• 300 = standaard (sneller)\n• 600 = hogere kwaliteit (trager)\n• 400 / 500 ook mogelijk" default answer "300" buttons {"OK"} default button "OK")
')
if [[ -z "$DPI" || ! "$DPI" =~ ^[0-9]+$ ]]; then
  DPI=300
fi
echo "Optie:  DPI $DPI"

echo ""
echo "OCR starten… (dit kan enkele minuten duren)"
echo "────────────────────────────────────────────"

# ── Activeer venv en start script ───────────────────────────────────── #
source "$SCRIPT_DIR/venv/bin/activate"
python3 "$SCRIPT_DIR/pdf_to_csv.py" "$PDF" --output "$OUTPUT" --dpi "$DPI" $EERSTE_LEEG "${START_PAGINA_ARG[@]}"

EXIT_CODE=$?
echo "────────────────────────────────────────────"
if [[ $EXIT_CODE -eq 0 ]]; then
  echo "✅  Klaar! CSV staat naast de PDF."
  # Open de map in de Finder zodat gebruiker de CSV direct ziet
  open "$(dirname "$PDF")"
else
  echo "❌  Er is iets misgegaan (exitcode $EXIT_CODE)."
fi

echo ""
read -r "?Druk op Enter om dit venster te sluiten."
