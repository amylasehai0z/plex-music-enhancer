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
- kein Markdown
- keine Bullet-Liste
- keine Platzhalter

Diese Punkte sind kritische Validierungen. Wenn einer dieser Checks fehlschlägt, darf Apply nicht ausgeführt werden.

### Quality Summary

Die Review-Ausgabe unterscheidet drei Zustände:

| Feld | Bedeutung |
| --- | --- |
| Critical validation | harte Sicherheits- und Faktenregeln |
| Editorial validation | redaktionelle Qualität und Stil |
| Publishable | ob Apply erlaubt ist |

Mögliche Ergebnisse:

| Status | Bedeutung |
| --- | --- |
| `PASS` | keine kritischen Fehler und keine redaktionellen Warnungen |
| `WARNINGS` | Apply ist erlaubt, aber stilistische Verbesserungen werden empfohlen |
| `FAILED` | Apply ist blockiert |

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

Ab v1.0.1 gilt zusätzlich: Apply ist erlaubt, wenn alle kritischen Validierungen bestehen und der redaktionelle Gesamtscore mindestens `85` beträgt oder das Qualitätslevel `GOOD`, `VERY GOOD` oder `EXCELLENT` ist. Wenn nur redaktionelle Warnungen vorhanden sind, gilt der Text als publizierbar.

Wenn der redaktionelle Score zu niedrig ist, erscheint:

```text
Generated summary does not yet meet the required editorial quality.
```

## Kritische Validierung und Empfehlungen

Kritische Fehler blockieren Apply immer:

- leerer Text
- nicht deutsch erkannter Text
- Platzhaltertext
- Markdown
- Bullet-Listen
- faktische Konflikte
- zu niedriges Verifikationsvertrauen

Redaktionelle Empfehlungen blockieren Apply nicht:

- schwacher Einstieg
- fehlende Übergänge
- wiederholte Satzanfänge
- Lesbarkeitshinweise
- passive Sprache
- lexikalische Vielfalt
- Satzlänge

Wenn nur solche Warnungen vorliegen, zeigt der Review-Apply-Schritt:

```text
Editorial warnings detected.
The generated summary is considered publishable.
You may still Apply this summary.

Continue? [Y/n]
```

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
