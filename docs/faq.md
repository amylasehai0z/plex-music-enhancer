# FAQ

## 1. Was macht Plex Music Enhancer?

Es erzeugt und prüft deutsche Album- und Künstlerbeschreibungen für Plex-Musikbibliotheken.

## 2. Wird automatisch in Plex geschrieben?

Nein. Geschrieben wird nur bei ausdrücklichem Apply.

## 3. Warum wird nichts in Plex geschrieben?

Vorschau, Planung, Audit und Review sind zunächst sicher. Verwenden Sie `apply` oder wählen Sie im Review `A`.

## 4. Ist ein Backup vorhanden?

Ja. Vor Apply wird der bisherige Text im persistenten Exportpfad gespeichert,
im Docker-Standard unter `/config/exports/backups/`.

## 5. Was ist ein Audit?

Ein Audit ist ein JSON-Protokoll eines Apply-Vorgangs. Im Docker-Standard liegt
es unter `/config/exports/audit/`.

## 6. Warum ist GPT so vorsichtig?

Die Prompts verlangen faktenbasierte, neutrale Sprache und verbieten erfundene Informationen.

## 7. Warum fehlen Chartpositionen?

Sie werden nur erwähnt, wenn sie aus Quellen vorhanden sind.

## 8. Warum ist MusicBrainz wichtig?

MusicBrainz liefert stabile IDs, Release Groups und strukturierte Metadaten.

## 9. Was ist eine MBID?

Eine MusicBrainz Identifier ID. Sie identifiziert Künstler, Releases oder Release Groups eindeutig.

## 10. Warum erscheint Wikipedia manchmal nicht?

Es gibt eventuell keinen passenden Artikel oder die Suche ist nicht eindeutig.

## 11. Was passiert ohne Discogs Token?

Discogs wird übersprungen.

## 12. Was passiert ohne Last.fm API Key?

Last.fm wird übersprungen.

## 13. Kann ich nur lokal testen?

Ja. Verwenden Sie den `dummy` AI-Anbieter.

## 14. Erzeugt Dummy echte Texte?

Nein. Er erzeugt deterministische Testausgaben.

## 15. Wie aktiviere ich OpenAI?

Setzen Sie `PLEX_ENHANCER_AI__PROVIDER=openai` und `OPENAI_API_KEY`.

## 16. Welches Modell wird genutzt?

Standard ist `gpt-5.5`, sofern so konfiguriert.

## 17. Kann ich ein anderes Modell verwenden?

Ja, mit `--model` oder `PLEX_ENHANCER_AI__MODEL`.

## 18. Warum lehnt Review eine Zusammenfassung ab?

Weil Qualitätsregeln verletzt wurden, etwa leere Ausgabe, Markdown, Bullet-Listen oder Platzhalter.

## 19. Warum werden Platzhalter abgelehnt?

Platzhalter deuten auf Testausgaben oder unvollständige Texte hin.

## 20. Kann ich einen Text bearbeiten?

Ja. Wählen Sie im Review `E`.

## 21. Was ist ein Diff?

Ein Diff zeigt, welche Zeilen entfernt und hinzugefügt werden.

## 22. Wie lösche ich den Cache?

```bash
plex-enhancer cache clear
```

## 23. Wie sehe ich den Cache-Status?

```bash
plex-enhancer cache stats
```

## 24. Wie regeneriere ich eine Zusammenfassung?

Führen Sie `preview`, `review` oder `apply` erneut aus. Bei Bedarf Cache löschen.

## 25. Warum dauert der erste Lauf lange?

Der Cache ist kalt und Providerdaten müssen geladen werden.

## 26. Warum ist der zweite Lauf schneller?

Viele Providerdaten kommen aus dem Cache.

## 27. Kann ich eine ganze Bibliothek bearbeiten?

Ja, mit `library plan`, `library review` und `library apply`.

## 28. Kann ich nur fehlende Texte bearbeiten?

Ja, mit `batch review --missing-only`.

## 29. Kann ich einen Lauf fortsetzen?

Ja, mit `--resume` oder `library resume`.

## 30. Was ist `plan`?

`plan` empfiehlt CREATE, TRANSLATE, IMPROVE, REVIEW oder SKIP.

## 31. Was bedeutet CREATE?

Es fehlt ein Text und ein neuer soll erzeugt werden.

## 32. Was bedeutet TRANSLATE?

Ein vorhandener englischer Text soll ins Deutsche übertragen werden.

## 33. Was bedeutet IMPROVE?

Ein vorhandener deutscher Text soll stilistisch verbessert werden.

## 34. Was bedeutet REVIEW?

Die Lage ist unklar und sollte manuell entschieden werden.

## 35. Was bedeutet SKIP?

Der vorhandene Text ist gut genug.

## 36. Kann das Programm falsche Fakten erfinden?

Die Prompts und Prüfungen reduzieren dieses Risiko, aber Review bleibt notwendig.

## 37. Warum wird ein Fakt nicht erwähnt?

Der Prompt priorisiert wichtige und verifizierte Fakten. Nicht jede Information muss im kurzen Text erscheinen.

## 38. Kann ich die Prompts ändern?

Ja, in `prompts/`. Danach sollten Tests und Vorschau geprüft werden.

## 39. Wo liegen Exporte?

Im Container unter `/config/exports/`. Der Pfad kann mit
`PLEX_ENHANCER_EXPORTS` angepasst werden.

## 40. Wo liegen Backups?

Im Container unter `/config/exports/backups/`.

## 41. Wo liegt der lokale Cache?

Unter `~/.plex-enhancer/cache/`.

## 42. Wo liegt die SQLite-Datenbank?

Standardmäßig unter `~/.plex-enhancer/processing.sqlite3`.

## 43. Unterstützt das Tool Windows?

Ja, Python 3.12+ vorausgesetzt. PowerShell-Beispiele sind in der Installationsanleitung enthalten.

## 44. Unterstützt das Tool macOS?

Ja.

## 45. Unterstützt das Tool Linux?

Ja.

## 46. Brauche ich Programmierkenntnisse?

Nein, aber Sie müssen einfache Terminalbefehle ausführen können.

## 47. Kann ich mehrere Plex-Server verwenden?

Ja, indem Sie die Konfiguration oder `.env` wechseln.

## 48. Warum findet Inspect mehr Felder als Preview verwendet?

Inspect zeigt rohe Plex-Daten. Preview nutzt nur relevante, unterstützte Felder.

## 49. Ist Apply rückgängig machbar?

Es gibt Backups. Ein automatischer Rollback-Befehl ist in v1.0 nicht der zentrale Workflow.

## 50. Wie melde ich ein Problem?

Sammeln Sie Befehl, Ausgabe, `doctor`-Ergebnis und relevante JSON-Exporte und öffnen Sie ein Issue.

## 51. Warum ist Review auch bei guten Texten sinnvoll?

Weil nur ein Mensch Kontext, Geschmack und Bibliotheksziel endgültig beurteilen kann.

## 52. Kann ich OpenAI-Kosten begrenzen?

Nutzen Sie kleine Testläufe, `--limit`, Cache und Preview, bevor Sie große Bibliotheken verarbeiten.
