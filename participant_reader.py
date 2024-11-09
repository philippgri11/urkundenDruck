# participant_reader.py

import json
import re
from typing import List, Dict, Optional

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