import json
import argparse
import subprocess
import os
import tempfile
import shutil
from typing import List, Dict, Optional
import re

def sanitize_filename(filename: str) -> str:
    """Entfernt ungültige Zeichen aus Dateinamen."""
    return "".join(c for c in filename if c.isalnum() or c in " ._-").rstrip()

def read_participants(json_file: str, encoding: str = 'utf-8') -> List[Dict[str, Optional[str]]]:
    """Liest Teilnehmerdaten aus einer JSON-Datei und gibt eine Liste von Teilnehmern zurück."""
    participants = []
    try:
        with open(json_file, 'r', encoding=encoding) as f:
            data = json.load(f)
            for item in data:
                participant = {
                    'name': item.get('last', '').strip().capitalize(),
                    'vorname': item.get('first', '').strip().capitalize(),
                    'verein': item.get('club', '').strip(),
                    'altersklasse': '',
                    'gewichtsklasse': '',
                    'platz': int(str(item.get('pos', '0')).strip()) if str(item.get('pos', '0')).strip().isdigit() else None
                }
                category = item.get('category', '').strip()
                # 'category' parsen, wobei '-' oder '+' zur Gewichtsklasse gehören
                match = re.match(r'^(.+?)([-+].+)$', category)
                if match:
                    participant['altersklasse'] = match.group(1).strip()
                    participant['gewichtsklasse'] = match.group(2).strip()
                else:
                    # Falls kein Match, versuchen wir es mit einem Leerzeichen als Trennzeichen
                    category_parts = category.split(' ', 1)
                    if len(category_parts) == 2:
                        participant['altersklasse'] = category_parts[0].strip()
                        participant['gewichtsklasse'] = category_parts[1].strip()
                    else:
                        participant['altersklasse'] = category.strip()
                        participant['gewichtsklasse'] = ''
                participants.append(participant)
    except FileNotFoundError:
        print(f"Die JSON-Datei '{json_file}' wurde nicht gefunden.")
    except Exception as e:
        print(f"Fehler beim Einlesen der JSON-Datei: {e}")
    return participants

def generate_certificate(participant: Dict[str, Optional[str]], template: str, long_name_template: str,
                         output_dir: str, min_chars_for_long_template: int) -> None:
    """Generiert eine Urkunde für einen einzelnen Teilnehmer."""
    altersklasse = sanitize_filename(participant['altersklasse']) or 'unbekannt'
    gewichtsklasse = sanitize_filename(participant['gewichtsklasse']) or 'unbekannt'

    # Ordnerstruktur erstellen: output_dir/altersklasse/gewichtsklasse/
    output_path = os.path.join(output_dir, altersklasse, gewichtsklasse)
    os.makedirs(output_path, exist_ok=True)

    # Gesamtlänge von Vorname und Name berechnen
    full_name_length = len(participant['vorname'] + participant['name'])

    # Passendes Template auswählen
    if full_name_length >= min_chars_for_long_template:
        selected_template = long_name_template
    else:
        selected_template = template

    # LaTeX-Inhalt vorbereiten
    latex_content = '\\documentclass[a4paper]{article}\n'
    latex_content += '\\usepackage[utf8]{inputenc}\n'
    latex_content += '\\usepackage[T1]{fontenc}\n'
    latex_content += '\\usepackage[margin=1in]{geometry}\n'
    latex_content += '\\usepackage[ngerman]{babel}\n'
    latex_content += '\\begin{document}\n'

    # Platzhalter in der Vorlage ersetzen
    urkunde = selected_template.replace('<<VORNAME>>', participant['vorname'])
    urkunde = urkunde.replace('<<NAME>>', participant['name'])
    urkunde = urkunde.replace('<<VEREIN>>', participant['verein'])
    urkunde = urkunde.replace('<<PLATZ>>', f"{participant['platz']}. Platz" if participant['platz'] is not None else 'Teilnehmer')
    urkunde = urkunde.replace('<<GEWICHTSKLASSE>>', participant['gewichtsklasse'])
    urkunde = urkunde.replace('<<ALTERSKLASSE>>', participant['altersklasse'])

    latex_content += urkunde + '\n'
    latex_content += '\\end{document}\n'

    # Temporäres Verzeichnis für LaTeX-Dateien erstellen
    with tempfile.TemporaryDirectory() as tempdir:
        tex_filename = os.path.join(tempdir, 'urkunde.tex')

        # LaTeX-Datei schreiben
        with open(tex_filename, 'w', encoding='utf-8') as f:
            f.write(latex_content)

        # LaTeX-Datei kompilieren
        try:
            subprocess.run(['pdflatex', '-interaction=nonstopmode', tex_filename],
                           cwd=tempdir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Kompiliertes PDF in das Zielverzeichnis kopieren
            pdf_source = os.path.join(tempdir, 'urkunde.pdf')
            pdf_filename = sanitize_filename(f"{participant['vorname']}_{participant['name']}.pdf")
            pdf_destination = os.path.join(output_path, pdf_filename)
            shutil.move(pdf_source, pdf_destination)
            print(f"Urkunde für {participant['vorname']} {participant['name']} wurde generiert und in '{pdf_destination}' gespeichert.")
        except subprocess.CalledProcessError:
            print(f"Fehler beim Kompilieren der Urkunde für {participant['vorname']} {participant['name']}.")
            # Optional: LaTeX-Logdatei ausgeben
            log_file = os.path.join(tempdir, 'urkunde.log')
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as logf:
                    print(logf.read())

def filter_participants(participants: List[Dict[str, Optional[str]]],
                        vorname: Optional[str] = None,
                        name: Optional[str] = None,
                        altersklasse: Optional[str] = None,
                        gewichtsklasse: Optional[str] = None) -> List[Dict[str, Optional[str]]]:
    """Filtert die Teilnehmerliste nach den angegebenen Kriterien."""
    filtered = participants
    if vorname:
        filtered = [p for p in filtered if p['vorname'].lower() == vorname.lower()]
    if name:
        filtered = [p for p in filtered if p['name'].lower() == name.lower()]
    if altersklasse:
        filtered = [p for p in filtered if p['altersklasse'] == altersklasse]
    if gewichtsklasse:
        filtered = [p for p in filtered if p['gewichtsklasse'] == gewichtsklasse]
    return filtered

def main():
    parser = argparse.ArgumentParser(description='Generiere Urkunden für Teilnehmer.')
    parser.add_argument('--json_file', help='Eingabedatei im JSON-Format mit Teilnehmerdaten', default='competitors.json')
    parser.add_argument('--template', help='LaTeX-Vorlagendatei', default='urkunde_template.tex')
    parser.add_argument('--long_name_template', help='LaTeX-Vorlagendatei für lange Namen',
                        default='urkunde_template_long.tex')
    parser.add_argument('--output_dir', help='Ausgabeverzeichnis für die Urkunden', default='Urkunden')
    parser.add_argument('--min-chars-for-long-template', type=int, default=10,
                        help='Mindestanzahl an Zeichen für die Verwendung des alternativen Templates')
    parser.add_argument('--vorname', help='Vorname des Teilnehmers', default=None)
    parser.add_argument('--name', help='Nachname des Teilnehmers', default=None)
    parser.add_argument('--altersklasse', help='Altersklasse zum Filtern', default=None)
    parser.add_argument('--gewichtsklasse', help='Gewichtsklasse zum Filtern', default=None)

    args = parser.parse_args()

    # Teilnehmerdaten einlesen
    participants = read_participants(args.json_file)

    if not participants:
        print('Keine Teilnehmer in der JSON-Datei gefunden oder Fehler beim Einlesen.')
        return

    # LaTeX-Vorlagen einlesen
    try:
        with open(args.template, 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        print(f"Die LaTeX-Vorlagendatei '{args.template}' wurde nicht gefunden.")
        return
    except Exception as e:
        print(f"Fehler beim Einlesen der LaTeX-Vorlage: {e}")
        return

    # Alternatives LaTeX-Template für lange Namen einlesen
    try:
        with open(args.long_name_template, 'r', encoding='utf-8') as f:
            long_name_template = f.read()
    except FileNotFoundError:
        print(f"Die LaTeX-Vorlagendatei für lange Namen '{args.long_name_template}' wurde nicht gefunden.")
        long_name_template = template  # Fallback auf Standardtemplate
    except Exception as e:
        print(f"Fehler beim Einlesen der LaTeX-Vorlage für lange Namen: {e}")
        long_name_template = template  # Fallback auf Standardtemplate

    # Teilnehmer filtern
    filtered_participants = filter_participants(participants,
                                                vorname=args.vorname,
                                                name=args.name,
                                                altersklasse=args.altersklasse,
                                                gewichtsklasse=args.gewichtsklasse)

    if not filtered_participants:
        print('Keine Teilnehmer entsprechen den Filterkriterien.')
        return

    # Urkunden für gefilterte Teilnehmer generieren
    for participant in filtered_participants:
        generate_certificate(participant, template, long_name_template, args.output_dir, args.min_chars_for_long_template)

if __name__ == '__main__':
    main()