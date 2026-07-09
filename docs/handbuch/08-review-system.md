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
- kein Markdown
- keine Bullet-Listen
- keine offenen Template- oder Testtexte

Diese Punkte sind kritische Validierungen. Sie blockieren Apply.

## 8.3 Quality Summary

Die Review-Ausgabe zeigt zusätzlich:

| Feld | Bedeutung |
| --- | --- |
| Critical validation | harte Regeln zu Sprache, Leertext, Format und Fakten |
| Editorial validation | redaktionelle Qualität und Stil |
| Publishable | ob der Text angewendet werden darf |

`PASS` bedeutet, dass keine Probleme gefunden wurden. `WARNINGS` bedeutet, dass Apply erlaubt ist, aber stilistische Verbesserungen möglich sind. `FAILED` bedeutet, dass Apply blockiert wird.

## 8.4 Language Detection

Die Spracherkennung ist eine Heuristik. Sie prüft typische deutsche Wörter und Zeichen.

## 8.5 Length Validation

Zu kurze Texte enthalten meist zu wenig Kontext. Zu lange Texte passen schlecht in Plex und wirken schnell überladen.

## 8.6 Editorial Validation

Die Editorial-Prüfung achtet auf:

- Wiederholungen
- schwache Übergänge
- generische Satzanfänge
- abruptes Ende
- Listenstil

Diese Hinweise sind Empfehlungen. Sie blockieren Apply nicht, wenn der Text insgesamt publizierbar ist.

## 8.7 Apply-Policy

Apply ist erlaubt, wenn:

- alle kritischen Validierungen bestehen
- keine faktischen Konflikte vorliegen
- das Verifikationsvertrauen ausreichend ist
- der redaktionelle Score mindestens 85 beträgt oder das Qualitätslevel `GOOD`, `VERY GOOD` oder `EXCELLENT` ist

Wenn nur redaktionelle Warnungen vorhanden sind, zeigt das Programm:

```text
Editorial warnings detected.
The generated summary is considered publishable.
You may still Apply this summary.

Continue? [Y/n]
```

Wenn der Score zu niedrig ist, wird Apply mit dieser Meldung blockiert:

```text
Generated summary does not yet meet the required editorial quality.
```

## 8.8 Diff Viewer

Der Diff zeigt Unterschiede:

```diff
- alter Text
+ neuer Text
```

## 8.9 Approval Process

```text
[A] Apply  [E] Edit  [S] Skip  [Q] Quit
```

| Taste | Bedeutung |
| --- | --- |
| `A` | anwenden |
| `E` | bearbeiten |
| `S` | überspringen |
| `Q` | beenden |

## 8.10 Manuelle Bearbeitung

Bei `E` öffnet sich der konfigurierte Terminaleditor. Nach dem Speichern wird erneut geprüft.

## 8.11 Warum Summaries scheitern können

Gründe:

- leere Ausgabe
- falsche Sprache
- zu kurz
- Markdown
- Liste statt Fließtext
- schwacher Stil
- unklare Faktenlage

## 8.12 Typischer Review Workflow

```bash
plex-enhancer review album --artist "Jennifer Rush" --album "Credo" --provider openai
plex-enhancer review artist --artist "Jennifer Rush" --provider openai
```

1. Text lesen.
2. Diff prüfen.
3. Qualitätswarnungen ansehen.
4. Bei Bedarf bearbeiten.
5. Apply nur bei plausibler Ausgabe.

## 8.13 Debug-Dateien

Für die Fehlersuche werden während interaktiver Reviews temporäre Dateien unter `/tmp` erzeugt und
bei jedem Lauf überschrieben:

| Datei | Inhalt |
| --- | --- |
| `/tmp/openai_prompt.txt` | exakt der an OpenAI gesendete Prompt |
| `/tmp/openai_prompt_meta.json` | Zeitstempel, Provider, Modell, Ziel, Prompt-Länge und Budgetdaten |
| `/tmp/plex_review.log` | Review-Ausgabe, Diff, QA, Stilprüfung, Verifikation, Token-Nutzung und Kontext |

Der Review-Log enthält außerdem `PROMPT BUDGET`, `USED SOURCES`, `PROMPT DECISIONS`,
`EVIDENCE RANKING`, `PROMPT QUALITY`, `EVIDENCE COVERAGE`, `EDITORIAL BALANCE`,
`EDITORIAL COVERAGE`, `PROMPT UTILIZATION`, `PROMPT META` und `RESPONSE META`.
Diese Abschnitte zeigen, welche Quellen im Prompt vertreten waren, welcher Anteil des Budgets auf
Wikipedia, Discogs, Last.fm, aktuelle Plex-Biografie, Regeln und Sicherheitsanweisungen entfiel,
welche Evidenz adaptiv gekürzt wurde und welche vorhandenen Themen die generierte Biografie noch
nicht genutzt hat. `PROMPT QUALITY` fasst zusätzlich Prompt-Redundanz, Quellenbalance, historische
Abdeckung und Prompt Efficiency zusammen. `EVIDENCE RANKING` bewertet die Evidenz nach historischem
Wert, wichtigen Werken, Karriereentwicklung, Legacy, internationaler Anerkennung, Einzigartigkeit
und Informationsdichte. `EVIDENCE COVERAGE` zeigt, wie viel hochwertige Evidenz in der Ausgabe
angekommen ist, während `EDITORIAL BALANCE` die erzählerische Ausgewogenheit der Biografie prüft.
Die Prompt-Kompression entfernt bevorzugt Wiederholungen und redundante Erfolgsaussagen, bevor
historisch relevante Informationen gekürzt werden.
