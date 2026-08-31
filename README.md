# NRW Lagebild

Ein statisches, täglich kuratiertes Dashboard für relevante Nachrichten und länger laufende Themen in Nordrhein-Westfalen.

## Was die App zeigt

- Leitstory und Signale des Tages
- länger laufende NRW-Dossiers statt eines reinen Tagesfeeds
- Landespolitik, Regionen und Nischenthemen
- einen bewusst kleinen Bundesblick mit direkter NRW-Relevanz
- den WDR-Newsletter **„Politik für 18 Millionen“**
- direkte Links und klar benannte Quellen

## Architektur

Die App braucht keinen eigenen Server und keine Datenbank:

- `index.html`, `assets/` – statisches Frontend
- `data/news.json` – veröffentlichte, kuratierte Ausgabe
- `data/history/` – tägliche Ausgaben als Git-Historie und lesbare Momentaufnahmen
- `scripts/discover_news.py` – Kandidatensuche; veröffentlicht nichts automatisch
- `scripts/discover_wdr_sections.py` – direkte WDR-Regionalquellen
- `scripts/validate_data.py` – Schema- und Plausibilitätsprüfung
- GitHub Pages veröffentlicht den Stand des `main`-Branches direkt

## Redaktionelle Methode

Eine Meldung wird nicht allein wegen Reichweite ausgewählt. Gewichtet werden:

1. **Folgen:** konkrete Auswirkungen auf Menschen, Kommunen, Infrastruktur oder politische Entscheidungen in NRW
2. **Dynamik:** neue Beschlüsse, Konflikte, Messwerte oder belastbare Wendungen
3. **Dauer:** wichtige Themen bleiben als Dossier sichtbar, solange sie sich entwickeln
4. **Regionale Breite:** Düsseldorf und Köln sind wichtig, aber nicht das gesamte Bundesland
5. **Quellenqualität:** direkte Artikel-URLs, Primärquellen und seriöse regionale Medien werden bevorzugt

Meinung und Prognose müssen als solche erkennbar bleiben. Kriminalitätskleinmeldungen werden nur aufgenommen, wenn sie strukturelle Bedeutung haben.

## Lokal starten

```bash
python3 -m http.server 4173
```

Dann `http://localhost:4173` öffnen.

## Daten prüfen

```bash
python3 scripts/validate_data.py
python3 scripts/validate_data.py --check-links
```

## Aktualisierung

Hermes kuratiert täglich um 08:00 Uhr Europe/Berlin eine neue Ausgabe, validiert sie und pusht sie auf `main`. GitHub Pages veröffentlicht den Branch anschließend automatisch. Im Repository liegen keine Mail-, Google- oder sonstigen privaten Zugangsdaten.

## Rechte und Transparenz

Die App reproduziert keine vollständigen Artikel. Bilder werden als öffentlich angegebene Open-Graph-Vorschaubilder der Quellen eingebunden; Urheber- und Nutzungsrechte verbleiben bei den jeweiligen Rechteinhabern. Bei Ladefehlern zeigt die App einen neutralen Fallback.

Dieses Projekt ist weder ein Angebot der Landesregierung Nordrhein-Westfalen noch des WDR.
