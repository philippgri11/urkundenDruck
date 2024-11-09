# main.py

import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from argparse import Namespace
from participant_reader import read_participants, filter_participants
from certificate_generator import generate_certificate, generate_master_certificates
import config
import queue

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Urkunden Generator")
        self.create_widgets()
        self.queue = queue.Queue()
        self.check_queue()

    def create_widgets(self):
        # Hauptframe erstellen
        self.main_frame = tk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Inhalt in main_frame hinzufügen
        self.add_content_widgets()

        # Bottom frame für Start-Button und Statuslabel
        self.bottom_frame = tk.Frame(self)
        self.bottom_frame.pack(fill=tk.X)

        # Start-Button immer unten
        self.start_button = tk.Button(self.bottom_frame, text="Urkunden generieren", command=self.start_generation)
        self.start_button.pack(side=tk.LEFT, padx=10, pady=10)

        # Statuslabel
        self.status_label = tk.Label(self.bottom_frame, text="", fg="green")
        self.status_label.pack(side=tk.LEFT, padx=10, pady=10)

    def add_content_widgets(self):
        # Standardwerte für Pfade aus config.py
        default_json = config.DEFAULT_JSON_FILE
        default_template = config.DEFAULT_TEMPLATE_FILE
        default_long_template = config.DEFAULT_LONG_TEMPLATE_FILE
        default_output_dir = config.DEFAULT_OUTPUT_DIR

        row = 0

        # Eingabedatei (JSON)
        self.json_label = tk.Label(self.main_frame, text="JSON-Datei:")
        self.json_label.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")
        row += 1

        self.json_entry = tk.Entry(self.main_frame, width=50)
        self.json_entry.grid(row=row, column=0, padx=10, pady=5, sticky="w")
        self.json_entry.insert(0, default_json)
        self.json_button = tk.Button(self.main_frame, text="Durchsuchen", command=self.browse_json)
        self.json_button.grid(row=row, column=1, padx=10, pady=5, sticky="w")
        row += 1

        # LaTeX-Vorlage
        self.template_label = tk.Label(self.main_frame, text="LaTeX-Vorlagendatei:")
        self.template_label.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")
        row += 1

        self.template_entry = tk.Entry(self.main_frame, width=50)
        self.template_entry.grid(row=row, column=0, padx=10, pady=5, sticky="w")
        self.template_entry.insert(0, default_template)
        self.template_button = tk.Button(self.main_frame, text="Durchsuchen", command=self.browse_template)
        self.template_button.grid(row=row, column=1, padx=10, pady=5, sticky="w")
        row += 1

        # Alternatives LaTeX-Template
        self.long_template_label = tk.Label(self.main_frame, text="LaTeX-Vorlage für lange Namen:")
        self.long_template_label.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")
        row += 1

        self.long_template_entry = tk.Entry(self.main_frame, width=50)
        self.long_template_entry.grid(row=row, column=0, padx=10, pady=5, sticky="w")
        self.long_template_entry.insert(0, default_long_template)
        self.long_template_button = tk.Button(self.main_frame, text="Durchsuchen", command=self.browse_long_template)
        self.long_template_button.grid(row=row, column=1, padx=10, pady=5, sticky="w")
        row += 1

        # Ausgabeordner
        self.output_label = tk.Label(self.main_frame, text="Ausgabeverzeichnis:")
        self.output_label.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")
        row += 1

        self.output_entry = tk.Entry(self.main_frame, width=50)
        self.output_entry.grid(row=row, column=0, padx=10, pady=5, sticky="w")
        self.output_entry.insert(0, default_output_dir)
        self.output_button = tk.Button(self.main_frame, text="Durchsuchen", command=self.browse_output_dir)
        self.output_button.grid(row=row, column=1, padx=10, pady=5, sticky="w")
        row += 1

        # Mindestanzahl an Zeichen für langes Template
        self.min_chars_label = tk.Label(self.main_frame, text="Minimale Zeichen für langes Template:")
        self.min_chars_label.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")
        row += 1

        self.min_chars_entry = tk.Entry(self.main_frame)
        self.min_chars_entry.grid(row=row, column=0, padx=10, pady=5, sticky="w")
        self.min_chars_entry.insert(0, str(config.DEFAULT_MIN_CHARS_FOR_LONG_TEMPLATE))
        row += 1

        # Button zum Einblenden der Filter
        self.show_filters = False
        self.filter_button = tk.Button(self.main_frame, text="Filter einblenden", command=self.toggle_filters)
        self.filter_button.grid(row=row, column=0, padx=10, pady=10, sticky="w")
        row += 1

        # Filterkriterien (zunächst versteckt)
        self.filter_frame = tk.Frame(self.main_frame)
        # Wird später eingeblendet

    def toggle_filters(self):
        if self.show_filters:
            # Filter verstecken
            self.filter_frame.grid_forget()
            self.filter_button.config(text="Filter einblenden")
            self.show_filters = False
        else:
            # Filter anzeigen
            self.show_filters = True
            self.filter_button.config(text="Filter ausblenden")

            # Filterfelder erstellen, falls noch nicht geschehen
            if not hasattr(self, 'vorname_entry'):
                self.create_filter_fields()

            self.filter_frame.grid(row=self.filter_button.grid_info()['row'] + 1, column=0, columnspan=2, padx=10, pady=5, sticky="w")

    def create_filter_fields(self):
        self.vorname_label = tk.Label(self.filter_frame, text="Vorname:")
        self.vorname_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.vorname_entry = tk.Entry(self.filter_frame)
        self.vorname_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.name_label = tk.Label(self.filter_frame, text="Nachname:")
        self.name_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.name_entry = tk.Entry(self.filter_frame)
        self.name_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.altersklasse_label = tk.Label(self.filter_frame, text="Altersklasse:")
        self.altersklasse_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.altersklasse_entry = tk.Entry(self.filter_frame)
        self.altersklasse_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        self.gewichtsklasse_label = tk.Label(self.filter_frame, text="Gewichtsklasse:")
        self.gewichtsklasse_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.gewichtsklasse_entry = tk.Entry(self.filter_frame)
        self.gewichtsklasse_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")

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
        self.args = Namespace(
            json_file=self.json_entry.get(),
            template=self.template_entry.get(),
            long_name_template=self.long_template_entry.get(),
            output_dir=self.output_entry.get(),
            min_chars_for_long_template=int(self.min_chars_entry.get()),
            vorname=self.vorname_entry.get() if self.show_filters and self.vorname_entry.get() else None,
            name=self.name_entry.get() if self.show_filters and self.name_entry.get() else None,
            altersklasse=self.altersklasse_entry.get() if self.show_filters and self.altersklasse_entry.get() else None,
            gewichtsklasse=self.gewichtsklasse_entry.get() if self.show_filters and self.gewichtsklasse_entry.get() else None,
        )

        # Starten des Worker-Threads
        self.worker_thread = threading.Thread(target=self.generate_certificates_in_thread)
        self.worker_thread.start()

    def generate_certificates_in_thread(self):
        try:
            # Teilnehmerdaten einlesen
            participants = read_participants(self.args.json_file)
            if not participants:
                self.queue.put(('warning', "Keine Teilnehmerdaten gefunden."))
                self.queue.put(('finished', None))
                return

            # LaTeX-Vorlagen einlesen
            try:
                with open(self.args.template, 'r', encoding='utf-8') as f:
                    template = f.read()
            except FileNotFoundError:
                self.queue.put(('error', f"LaTeX-Vorlagendatei '{self.args.template}' nicht gefunden."))
                self.queue.put(('finished', None))
                return

            try:
                with open(self.args.long_name_template, 'r', encoding='utf-8') as f:
                    long_name_template = f.read()
            except FileNotFoundError:
                self.queue.put(('warning', f"LaTeX-Vorlagendatei für lange Namen '{self.args.long_name_template}' nicht gefunden. Standardvorlage wird verwendet."))
                long_name_template = template

            # Teilnehmer filtern
            filtered_participants = filter_participants(participants,
                                                        vorname=self.args.vorname,
                                                        name=self.args.name,
                                                        altersklasse=self.args.altersklasse,
                                                        gewichtsklasse=self.args.gewichtsklasse)
            if not filtered_participants:
                self.queue.put(('warning', "Keine Teilnehmer entsprechen den Filterkriterien."))
                self.queue.put(('finished', None))
                return

            # Urkunden generieren
            for participant in filtered_participants:
                try:
                    generate_certificate(participant, template, long_name_template,
                                         self.args.output_dir, self.args.min_chars_for_long_template)
                except Exception as e:
                    self.queue.put(('error', f"Fehler beim Generieren der Urkunde für {participant['vorname']} {participant['name']}:\n{e}"))

            # Master-PDFs generieren
            generate_master_certificates(self.args.output_dir)

            # Generierung abgeschlossen
            self.queue.put(('info', "Urkunden wurden erfolgreich generiert!"))
        except Exception as e:
            self.queue.put(('error', f"Es ist ein Fehler aufgetreten:\n{e}"))
        finally:
            # Signalisiert, dass die Generierung abgeschlossen ist
            self.queue.put(('finished', None))

    def check_queue(self):
        try:
            while True:
                msg_type, content = self.queue.get_nowait()
                if msg_type == 'warning':
                    messagebox.showwarning("Warnung", content)
                elif msg_type == 'error':
                    messagebox.showerror("Fehler", content)
                    self.status_label.config(text="Fehler bei der Generierung.", fg="red")
                elif msg_type == 'info':
                    self.status_label.config(text="Generierung abgeschlossen.", fg="green")
                    messagebox.showinfo("Erfolg", content)
                elif msg_type == 'finished':
                    self.finish_generation()
        except queue.Empty:
            pass
        self.after(100, self.check_queue)

    def finish_generation(self):
        self.start_button.config(state=tk.NORMAL, text="Urkunden generieren")
        # Optional: Reset des Statuslabels, falls gewünscht
        # self.status_label.config(text="", fg="green")

if __name__ == '__main__':
    app = Application()
    app.mainloop()