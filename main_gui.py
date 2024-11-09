import json
import argparse
import subprocess
import os
import tempfile
import shutil
from typing import List, Dict, Optional
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

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

def main(args):
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
        raise FileNotFoundError(f"Die LaTeX-Vorlagendatei '{args.template}' wurde nicht gefunden.")

    # Alternatives LaTeX-Template für lange Namen einlesen
    try:
        with open(args.long_name_template, 'r', encoding='utf-8') as f:
            long_name_template = f.read()
    except FileNotFoundError:
        print(f"Die LaTeX-Vorlagendatei für lange Namen '{args.long_name_template}' wurde nicht gefunden.")
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

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Urkunden Generator")
        self.geometry("500x700")
        self.create_widgets()

    def create_widgets(self):
        # Standardwerte für Pfade
        default_json = 'competitors.json'
        default_template = 'urkunde_template.tex'
        default_long_template = 'urkunde_template_long.tex'
        default_output_dir = 'Urkunden'

        # Eingabedatei (JSON)
        self.json_label = tk.Label(self, text="JSON-Datei:")
        self.json_label.pack(pady=(10, 0))
        self.json_entry = tk.Entry(self, width=50)
        self.json_entry.pack()
        self.json_entry.insert(0, default_json)
        self.json_button = tk.Button(self, text="Durchsuchen", command=self.browse_json)
        self.json_button.pack()

        # LaTeX-Vorlage
        self.template_label = tk.Label(self, text="LaTeX-Vorlagendatei:")
        self.template_label.pack(pady=(10, 0))
        self.template_entry = tk.Entry(self, width=50)
        self.template_entry.pack()
        self.template_entry.insert(0, default_template)
        self.template_button = tk.Button(self, text="Durchsuchen", command=self.browse_template)
        self.template_button.pack()

        # Alternatives LaTeX-Template
        self.long_template_label = tk.Label(self, text="LaTeX-Vorlage für lange Namen:")
        self.long_template_label.pack(pady=(10, 0))
        self.long_template_entry = tk.Entry(self, width=50)
        self.long_template_entry.pack()
        self.long_template_entry.insert(0, default_long_template)
        self.long_template_button = tk.Button(self, text="Durchsuchen", command=self.browse_long_template)
        self.long_template_button.pack()

        # Ausgabeordner
        self.output_label = tk.Label(self, text="Ausgabeverzeichnis:")
        self.output_label.pack(pady=(10, 0))
        self.output_entry = tk.Entry(self, width=50)
        self.output_entry.pack()
        self.output_entry.insert(0, default_output_dir)
        self.output_button = tk.Button(self, text="Durchsuchen", command=self.browse_output_dir)
        self.output_button.pack()

        # Mindestanzahl an Zeichen für langes Template
        self.min_chars_label = tk.Label(self, text="Minimale Zeichen für langes Template:")
        self.min_chars_label.pack(pady=(10, 0))
        self.min_chars_entry = tk.Entry(self)
        self.min_chars_entry.pack()
        self.min_chars_entry.insert(0, "20")  # Standardwert

        # Button zum Einblenden der Filter
        self.show_filters = False
        self.filter_button = tk.Button(self, text="Filter einblenden", command=self.toggle_filters)
        self.filter_button.pack(pady=10)

        # Filterkriterien (zunächst versteckt)
        self.filter_frame = tk.Frame(self)
        # self.filter_frame.pack(pady=(10, 0))

        self.vorname_label = tk.Label(self.filter_frame, text="Vorname:")
        self.vorname_label.grid(row=0, column=0, padx=5, pady=5)
        self.vorname_entry = tk.Entry(self.filter_frame)
        self.vorname_entry.grid(row=0, column=1, padx=5, pady=5)

        self.name_label = tk.Label(self.filter_frame, text="Nachname:")
        self.name_label.grid(row=1, column=0, padx=5, pady=5)
        self.name_entry = tk.Entry(self.filter_frame)
        self.name_entry.grid(row=1, column=1, padx=5, pady=5)

        self.altersklasse_label = tk.Label(self.filter_frame, text="Altersklasse:")
        self.altersklasse_label.grid(row=2, column=0, padx=5, pady=5)
        self.altersklasse_entry = tk.Entry(self.filter_frame)
        self.altersklasse_entry.grid(row=2, column=1, padx=5, pady=5)

        self.gewichtsklasse_label = tk.Label(self.filter_frame, text="Gewichtsklasse:")
        self.gewichtsklasse_label.grid(row=3, column=0, padx=5, pady=5)
        self.gewichtsklasse_entry = tk.Entry(self.filter_frame)
        self.gewichtsklasse_entry.grid(row=3, column=1, padx=5, pady=5)

        # Statuslabel
        self.status_label = tk.Label(self, text="", fg="green")
        self.status_label.pack(pady=(10, 0))

        # Start-Button
        self.start_button = tk.Button(self, text="Urkunden generieren", command=self.start_generation)
        self.start_button.pack(pady=20)

    def toggle_filters(self):
        if self.show_filters:
            # Filter verstecken
            self.filter_frame.pack_forget()
            self.filter_button.config(text="Filter einblenden")
            self.show_filters = False
        else:
            # Filter anzeigen
            self.filter_frame.pack(pady=(10, 0))
            self.filter_button.config(text="Filter ausblenden")
            self.show_filters = True

    def browse_json(self):
        filename = filedialog.askopenfilename(filetypes=[("JSON-Dateien", "*.json")])
        if filename:
            self.json_entry.delete(0, tk.END)
            self.json_entry.insert(0, filename)

    def browse_template(self):
        filename = filedialog.askopenfilename(filetypes=[("TeX-Dateien", "*.tex")])
        if filename:
            self.template_entry.delete(0, tk.END)
            self.template_entry.insert(0, filename)

    def browse_long_template(self):
        filename = filedialog.askopenfilename(filetypes=[("TeX-Dateien", "*.tex")])
        if filename:
            self.long_template_entry.delete(0, tk.END)
            self.long_template_entry.insert(0, filename)

    def browse_output_dir(self):
        dirname = filedialog.askdirectory()
        if dirname:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, dirname)

    def start_generation(self):
        # Button deaktivieren und Status anzeigen
        self.start_button.config(state=tk.DISABLED, text="Generiere...")
        self.status_label.config(text="Generiere PDFs...")
        self.update_idletasks()

        # Eingaben sammeln
        args = argparse.Namespace(
            json_file=self.json_entry.get(),
            template=self.template_entry.get(),
            long_name_template=self.long_template_entry.get(),
            output_dir=self.output_entry.get(),
            min_chars_for_long_template=int(self.min_chars_entry.get()),
            vorname=self.vorname_entry.get() or None,
            name=self.name_entry.get() or None,
            altersklasse=self.altersklasse_entry.get() or None,
            gewichtsklasse=self.gewichtsklasse_entry.get() or None,
        )

        # Generierung in einem separaten Thread ausführen
        threading.Thread(target=self.run_generation, args=(args,)).start()

    def run_generation(self, args):
        try:
            main(args)
            self.status_label.config(text="Generierung abgeschlossen.")
            messagebox.showinfo("Erfolg", "Urkunden wurden erfolgreich generiert!")
        except Exception as e:
            self.status_label.config(text="Fehler bei der Generierung.")
            messagebox.showerror("Fehler", f"Es ist ein Fehler aufgetreten:\n{e}")
        finally:
            # Button wieder aktivieren und Text zurücksetzen
            self.start_button.config(state=tk.NORMAL, text="Urkunden generieren")

    def update_status(self, message):
        self.status_label.config(text=message)
        self.update_idletasks()

if __name__ == '__main__':
    app = Application()
    app.mainloop()