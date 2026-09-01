# NRW Lagebild

Ein statisches, täglich kuratiertes Dashboard für relevante Nachrichten und länger laufende Themen in Nordrhein-Westfalen.

## Was die App zeigt

- Leitstory und Signale des Tages
- länger laufende NRW-Dossiers statt eines reinen Tagesfeeds
- Landespolitik, Regionen und Nischenthemen
- einen bewusst kleinen Bundesblick mit direkter NRW-Relevanz
- den WDR-Newsletter **„Politik für 18 Millionen“**
- die aktuellste belastbare NRW-Sonntagsfrage mit Trendvergleich und Methodik
- einen quellengebundenen Kritikmonitor zur schwarz-grünen Landesregierung
- einen Social-Media-Radar für die öffentlichen Grünen-NRW-Kanäle; TikTok mit Postmetriken, Meta-Datenlücken ausdrücklich gekennzeichnet
- direkte Links und klar benannte Quellen

## Architektur

Die App braucht keinen eigenen Server und keine Datenbank:

- `index.html`, `assets/` – statisches Frontend
- `data/news.json` – veröffentlichte, kuratierte Ausgabe
- `data/history/` – tägliche Ausgaben als Git-Historie und lesbare Momentaufnahmen
- `scripts/discover_news.py` – Kandidatensuche; veröffentlicht nichts automatisch
- `scripts/discover_wdr_sections.py` – direkte WDR-Regionalquellen
- `scripts/validate_data.py` – Schema-, URL-, Datums- und Plausibilitätsprüfung einschließlich nachgerechneter Social-Aggregate
- `scripts/test_validate_data.py` – Regressionstests mit gezielt beschädigten Feeds
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
python3 -m unittest -v scripts/test_validate_data.py
```

## Aktualisierung

Hermes kuratiert täglich um 08:00 Uhr Europe/Berlin eine neue Ausgabe, validiert sie und pusht sie auf `main`. GitHub Pages veröffentlicht den Branch anschließend automatisch. Im Repository liegen keine Mail-, Google- oder sonstigen privaten Zugangsdaten.

## Rechte und Transparenz

Die App reproduziert keine vollständigen Artikel. Bilder werden grundsätzlich als öffentlich angegebene Open-Graph-Vorschaubilder der Quellen eingebunden. Das lokal ausgelieferte Leitbild von Mona Neubaur stammt von Wikimedia Commons und ist in der App mit Urheber, Lizenz und Originalseite attribuiert. Urheber- und Nutzungsrechte verbleiben bei den jeweiligen Rechteinhabern. Bei Ladefehlern zeigt die App einen neutralen Fallback.

Social-Media-Kennzahlen sind zeitgestempelte, volatile Momentaufnahmen. Fehlende Instagram-/Facebook-Werte werden nicht geschätzt; weitergehende Meta-Insights benötigen eine autorisierte Kontoverbindung.

Dieses Projekt ist weder ein Angebot der Landesregierung Nordrhein-Westfalen noch des WDR.
