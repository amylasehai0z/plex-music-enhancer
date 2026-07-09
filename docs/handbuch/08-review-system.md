# 8. Review-System

Das Review-System schützt vor ungeprüften Änderungen.

## 8.1 Quality Score

Der Quality Score bewertet den generierten Text von 0 bis 100.

| Score | Bedeutung |
| --- | --- |
| 90-100 | sehr gut |
| 80-89 | gut |
| 70-79 | prüfen |
| unter 70 | problematisch |

## 8.2 Checks

Geprüft werden:

- nicht leer
- Deutsch erkennbar
- Länge im Zielbereich
- kein Markdown
- keine Bullet-Listen
- keine offenen Template- oder Testtexte

## 8.3 Language Detection

Die Spracherkennung ist eine Heuristik. Sie prüft typische deutsche Wörter und Zeichen.

## 8.4 Length Validation

Zu kurze Texte enthalten meist zu wenig Kontext. Zu lange Texte passen schlecht in Plex und wirken schnell überladen.

## 8.5 Editorial Validation

Die Editorial-Prüfung achtet auf:

- Wiederholungen
- schwache Übergänge
- generische Satzanfänge
- abruptes Ende
- Listenstil

## 8.6 Diff Viewer

Der Diff zeigt Unterschiede:

```diff
- alter Text
+ neuer Text
```

## 8.7 Approval Process

```text
[A] Apply  [E] Edit  [S] Skip  [Q] Quit
```

| Taste | Bedeutung |
| --- | --- |
| `A` | anwenden |
| `E` | bearbeiten |
| `S` | überspringen |
| `Q` | beenden |

## 8.8 Manuelle Bearbeitung

Bei `E` öffnet sich der konfigurierte Terminaleditor. Nach dem Speichern wird erneut geprüft.

## 8.9 Warum Summaries scheitern können

Gründe:

- leere Ausgabe
- falsche Sprache
- zu kurz
- Markdown
- Liste statt Fließtext
- schwacher Stil
- unklare Faktenlage

## 8.10 Typischer Review Workflow

1. Text lesen.
2. Diff prüfen.
3. Qualitätswarnungen ansehen.
4. Bei Bedarf bearbeiten.
5. Apply nur bei plausibler Ausgabe.

