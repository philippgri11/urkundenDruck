# certificate_generator.py

import os
import subprocess
import tempfile
import shutil
from utilities import sanitize_filename
from typing import Dict, Optional
from PyPDF2 import PdfMerger

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
    latex_content = '\\documentclass{article}\n'
    latex_content += '\\usepackage[a4paper, left=8cm]{geometry}\n'
    latex_content += '\\usepackage[ngerman]{babel}\n'
    latex_content += '\\usepackage[utf8]{inputenc}\n'
    latex_content += '\\usepackage[T1]{fontenc}\n'
    latex_content += '\\usepackage{graphicx}\n'
    latex_content += '\\pagestyle{empty}\n'
    latex_content += '\\begin{document}\n'

    # Platzhalter in der Vorlage ersetzen
    urkunde = selected_template.replace('<<VORNAME>>', participant['vorname'])
    urkunde = urkunde.replace('<<NAME>>', participant['name'])
    urkunde = urkunde.replace('<<VEREIN>>', participant['verein'])
    urkunde = urkunde.replace('<<PLATZ>>', f"{participant['platz']}" if participant['platz'] is not None else 'Teilnehmer')
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

def generate_master_certificates(output_dir: str) -> None:
    """
    Generiert eine Master-PDF-Datei für jede Gewichtsklasse und eine Master-PDF für jede Altersklasse,
    die alle Master-PDFs der jeweiligen Gewichtsklassen enthält.
    """
    # Traversieren des Ausgabeordners
    for altersklasse in os.listdir(output_dir):
        altersklasse_path = os.path.join(output_dir, altersklasse)
        if not os.path.isdir(altersklasse_path):
            continue

        gewichtsklassen_masters = []  # Liste zur Speicherung der Master-PDFs der Gewichtsklassen

        for gewichtsklasse in os.listdir(altersklasse_path):
            gewichtsklasse_path = os.path.join(altersklasse_path, gewichtsklasse)
            if not os.path.isdir(gewichtsklasse_path):
                continue

            # Liste aller PDF-Dateien in der Gewichtsklasse, außer 'master.pdf'
            pdf_files = [
                os.path.join(gewichtsklasse_path, f)
                for f in os.listdir(gewichtsklasse_path)
                if f.lower().endswith('.pdf') and f != 'master.pdf'
            ]
            pdf_files_sorted = sorted(pdf_files)  # Optional: sortieren nach Name

            if not pdf_files_sorted:
                continue

            # Erstellen einer Master-PDF-Datei für die Gewichtsklasse
            master_pdf_path = os.path.join(gewichtsklasse_path, 'master.pdf')
            merger = PdfMerger()
            for pdf in pdf_files_sorted:
                merger.append(pdf)
            merger.write(master_pdf_path)
            merger.close()
            print(f"Master-PDF für {altersklasse} - {gewichtsklasse} erstellt: {master_pdf_path}")

            # Hinzufügen der Master-PDF der Gewichtsklasse zur Liste für die Altersklasse
            gewichtsklassen_masters.append(master_pdf_path)

        # Erstellen einer Master-PDF für die Altersklasse, falls es Master-PDFs der Gewichtsklassen gibt
        if gewichtsklassen_masters:
            file_name = "master_altersklasse" +  altersklasse + ".pdf"
            altersklasse_master_pdf = os.path.join(altersklasse_path,file_name)
            merger_altersklasse = PdfMerger()
            for master_pdf in sorted(gewichtsklassen_masters):  # Optional: sortieren nach Pfad
                merger_altersklasse.append(master_pdf)
            merger_altersklasse.write(altersklasse_master_pdf)
            merger_altersklasse.close()
            print(f"Master-PDF für Altersklasse {altersklasse} erstellt: {altersklasse_master_pdf}")