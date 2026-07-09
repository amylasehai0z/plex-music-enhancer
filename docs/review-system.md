# Review-System

Das Review-System ist die Sicherheitsstufe zwischen Texterzeugung und Plex-Schreibvorgang.

## Ziel

Vor jeder Änderung sollen Sie sehen:

- was aktuell in Plex steht
- was generiert wurde
- welche Zeilen sich ändern
- ob Qualität und Faktenlage ausreichen

## Review starten

```bash
plex-enhancer review --artist "Jennifer Rush" --album "Credo"
```

Für Künstler:

```bash
plex-enhancer review artist --artist "Jennifer Rush"
```

## Abschnitte

### Current Summary

Der aktuelle Text aus Plex.

### Generated Summary

Der neu erzeugte oder bearbeitete Text.

### Unified Diff

Zeigt die Änderung:

```diff
- alter Text
+ neuer Text
```

### Quality

Prüft grundlegende Regeln:

- nicht leer
- Deutsch erkennbar
- Länge im Rahmen
- kein Markdown
- keine Bullet-Liste
- keine Platzhalter

### Style Analysis

Bewertet:

- Satzvariation
- Wortvielfalt
- Wiederholungen
- Lesbarkeit
- passive Konstruktionen
- typische KI-Floskeln

### Editorial Quality

Der QA-Bericht bewertet:

- Metadatenabdeckung
- Faktenabdeckung
- Verifikationsvertrauen
- Struktur
- Sprache
- Formatierung

## Quality Score

Der Score liegt zwischen `0` und `100`.

| Bereich | Bedeutung |
| --- | --- |
| 90-100 | sehr gut bis exzellent |
| 80-89 | gut |
| 70-79 | brauchbar, aber prüfen |
| unter 70 | problematisch |

Eine konfigurierte Mindestschwelle kann Apply blockieren.

## Platzhaltererkennung

Texte mit Platzhalterbegriffen, Template-Markern oder DummyProvider-Hinweisen werden abgelehnt.

## Deutsche Sprache

Die Prüfung ist heuristisch. Sie erkennt typische deutsche Wörter und Zeichen. Bei Fachnamen oder sehr kurzen Texten kann ein Text zur manuellen Prüfung markiert werden.

## Längenprüfung

Albumtexte sollen nicht zu kurz und nicht unnötig lang sein. Die Prüfung schützt vor leeren, abgeschnittenen oder ausufernden Ergebnissen.

## Approval-Prozess

Nach der Anzeige fragt das Programm:

```text
[A] Apply  [E] Edit  [S] Skip  [Q] Quit
```

| Taste | Aktion |
| --- | --- |
| `A` | Text sicher anwenden |
| `E` | Text im Editor bearbeiten |
| `S` | Album überspringen |
| `Q` | Sitzung beenden |

Bei `Apply` wird weiterhin Backup, Schreibvorgang, Reload-Verifikation und Audit durchgeführt.

## Best Practices

- Lesen Sie jeden neuen Text beim ersten Einsatz vollständig.
- Verwenden Sie `--verbose`, wenn Quellen oder Fakten unklar sind.
- Nutzen Sie `Edit`, um kleine Stilprobleme direkt zu korrigieren.
- Verwenden Sie `Apply` erst, wenn Text und Diff plausibel sind.
