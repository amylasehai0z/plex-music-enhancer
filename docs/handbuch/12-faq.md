# 12. Häufig gestellte Fragen

Dieses Kapitel beantwortet typische Fragen aus Einrichtung, täglicher Nutzung und Fehleranalyse.

## Grundlagen

### 1. Was macht Plex Music Enhancer?

Plex Music Enhancer sammelt vorhandene Plex-Metadaten, ergänzt sie mit externen Quellen und kann daraus deutschsprachige Album- und Künstlertexte erzeugen. Änderungen an Plex passieren nur im Apply-Workflow.

### 2. Verändert das Programm meine Plex-Bibliothek automatisch?

Nein. Preview, Review, Scan, Plan, Audit, Context, Match, Inspect, Cache und die Provider-Abfragen sind lesend. Geschrieben wird erst mit `plex-enhancer apply` oder einem bestätigten Apply-Schritt.

### 3. Brauche ich Programmierkenntnisse?

Nein. Sie benötigen nur ein Terminal, Python, die Plex-Zugangsdaten und bei echter KI-Nutzung einen OpenAI API Key.

### 4. Kann ich das Programm ohne OpenAI nutzen?

Ja. Viele Befehle funktionieren ohne OpenAI, zum Beispiel `doctor`, `scan`, `audit`, `plan`, `match`, `context`, `inspect` und `cache`.

### 5. Warum gibt es einen DummyProvider?

Der DummyProvider erzeugt deterministische Testtexte. Er ist nützlich für Installation, Tests und Abläufe ohne echte KI-Kosten.

### 6. Warum nutzt Preview nicht OpenAI, obwohl ein API Key gesetzt ist?

Prüfen Sie `plex-enhancer doctor`. Wenn `ai.provider` auf `dummy` steht, bleibt der DummyProvider aktiv, auch wenn `OPENAI_API_KEY` vorhanden ist.

### 7. Welche Python-Version brauche ich?

Python 3.12 oder neuer.

### 8. Funktioniert das auf macOS, Windows und Linux?

Das Projekt ist als Python-CLI plattformübergreifend angelegt. Pfade, virtuelle Umgebungen und Shell-Befehle unterscheiden sich je nach System leicht.

### 9. Muss Plex lokal laufen?

Nein. Die konfigurierte Plex URL muss vom Rechner erreichbar sein, auf dem Plex Music Enhancer läuft.

### 10. Funktioniert das mit Plexamp?

Plexamp nutzt dieselbe Plex-Bibliothek. Plex Music Enhancer arbeitet gegen den Plex Server, nicht direkt gegen Plexamp.

## Installation und Einrichtung

### 11. Wie prüfe ich, ob die Installation funktioniert?

Führen Sie `plex-enhancer version` und danach `plex-enhancer doctor` aus.

### 12. Was macht `plex-enhancer login`?

Der Befehl fragt die Plex Server URL und das Plex Token ab, prüft die Verbindung und speichert die Werte in `.env`, ohne das Token auszugeben.

### 13. Wird mein Plex Token angezeigt?

Nein. Das Token wird verborgen abgefragt und nicht in der Ausgabe angezeigt.

### 14. Darf ich `.env` in Git speichern?

Nein. `.env` enthält Zugangsdaten und gehört nicht in ein öffentliches Repository.

### 15. Woher bekomme ich mein Plex Token?

Das Plex Token wird über Plex selbst ermittelt. Die genaue Vorgehensweise hängt von Ihrer Plex-Oberfläche ab.

### 16. Was bedeutet "configuration missing"?

Meist fehlen Plex URL, Plex Token oder ein erforderlicher API Key für einen aktivierten Provider.

### 17. Warum schlägt `doctor` fehl?

Häufige Gründe sind falsche URL, ungültiges Token, nicht erreichbarer Server oder fehlende KI-Konfiguration.

### 18. Kann ich mehrere Plex Server nutzen?

Die CLI verwendet die aktuell gesetzte Konfiguration. Für mehrere Server können Sie getrennte Arbeitsverzeichnisse oder unterschiedliche Umgebungsvariablen verwenden.

### 19. Welche Datei ist wichtiger: `.env` oder Umgebungsvariablen?

Beide werden über die Anwendungskonfiguration gelesen. Für reproduzierbare Skripte sind explizite Umgebungsvariablen oft klarer.

### 20. Warum wird mein OpenAI Key nicht erkannt?

Prüfen Sie, ob `OPENAI_API_KEY` in derselben Shell gesetzt ist, in der Sie `plex-enhancer` ausführen.

## Plex und Bibliotheken

### 21. Welche Plex-Bibliotheken werden verarbeitet?

Die Workflows betrachten Musikbibliotheken. Andere Bibliothekstypen werden für Musikfunktionen ignoriert.

### 22. Wie finde ich heraus, welche Musikbibliotheken erkannt werden?

Nutzen Sie `plex-enhancer scan`.

### 23. Wie exportiere ich Bibliotheksstatistiken?

Führen Sie `plex-enhancer scan --export-json` aus. Die Datei landet unter `exports/libraries.json`.

### 24. Warum wird ein Album nicht gefunden?

Titel oder Künstler können in Plex anders geschrieben sein. Prüfen Sie mit `plex-enhancer scan albums --export-json` oder `plex-enhancer inspect album --name "Titel"`.

### 25. Was ist ein Rating Key?

Ein Rating Key ist eine Plex-interne Kennung für ein Objekt.

### 26. Kann ich nach ID statt nach Name suchen?

Inspect-Befehle unterstützen `--id <ratingKey>` oder `--name "<Titel>"`.

### 27. Werden Tracks verändert?

Die beschriebenen Apply-Workflows schreiben Zusammenfassungen für Alben oder Künstler. Track-Metadaten werden im Handbuch nicht als Schreibziel beschrieben.

### 28. Kann Plex Music Enhancer Playlists bearbeiten?

Nein. Das Handbuch dokumentiert keine Playlist-Bearbeitung.

### 29. Kann ich nur eine bestimmte Bibliothek planen?

Ja, viele Bibliotheksbefehle unterstützen `--library`.

### 30. Was passiert bei doppelten Albumtiteln?

Der Workflow muss ein eindeutiges Objekt finden. Bei Mehrdeutigkeiten sollten Sie die Plex-Metadaten prüfen und genauer suchen.

## KI und Texte

### 31. Warum erfindet GPT keine Chartpositionen?

Der Prompt verbietet nicht belegte Fakten. Chartpositionen werden nur verwendet, wenn sie im Kontext vorhanden sind.

### 32. Warum sind Produzenten manchmal nicht enthalten?

Produzenten erscheinen nur, wenn sie aus den vorhandenen Quellen geliefert und in den Kontext übernommen wurden.

### 33. Warum sind die Texte konservativ?

Das System bevorzugt belegbare Aussagen gegenüber spekulativen Formulierungen.

### 34. Warum ist ein Text kürzer als erwartet?

Wenn wenig belastbarer Kontext vorhanden ist, soll die KI keine Lücken füllen.

### 35. Warum klingt ein Text manchmal allgemein?

Das passiert vor allem bei schwacher Quellenlage oder fehlendem Wikipedia-, Discogs- oder MusicBrainz-Kontext.

### 36. Kann ich einen Text neu erzeugen?

Ja. Führen Sie Preview oder Review erneut aus. Bei echten KI-Anbietern kann das erneut Kosten verursachen.

### 37. Kann ich manuell bearbeiten?

Ja. Im Review-Workflow kann die generierte Fassung bearbeitet werden.

### 38. Warum wird Markdown abgelehnt?

Plex-Zusammenfassungen sollen als klare Fließtexte gespeichert werden, nicht als Markdown-Dokumente.

### 39. Warum werden Bullet-Listen abgelehnt?

Die Qualitätssicherung erwartet enzyklopädische Prosa.

### 40. Kann ich englische Texte übersetzen?

Ja. Nutzen Sie Preview mit `--translate` oder entsprechende Review- und Apply-Workflows.

### 41. Kann ich deutsche Texte verbessern?

Ja. Nutzen Sie Preview mit `--improve`.

### 42. Wird beim Übersetzen zusammengefasst?

Der Übersetzungsprompt ist darauf ausgelegt, Fakten zu erhalten und nicht frei zu kürzen.

### 43. Was passiert, wenn der vorhandene Text schon gut ist?

Der Planner kann `SKIP` empfehlen.

### 44. Was bedeutet `REVIEW` im Plan?

Der Text ist nicht eindeutig schlecht, aber eine menschliche Entscheidung ist sinnvoll.

### 45. Warum lehnt Review einen Text ab?

Mögliche Gründe sind falsche Sprache, zu kurze Länge, Listenstil, wiederholende Formulierungen oder offene Testtexte.

## Provider

### 46. Was ist MusicBrainz?

MusicBrainz ist eine strukturierte Musikdatenbank und besonders hilfreich für MBIDs, Release Groups und Veröffentlichungsdaten.

### 47. Was ist eine MBID?

Eine MBID ist eine MusicBrainz Identifier, also eine stabile Kennung für Künstler, Releases oder Release Groups.

### 48. Was ist eine Release Group?

Eine Release Group bündelt verschiedene Veröffentlichungen desselben Albums.

### 49. Was liefert Wikipedia?

Wikipedia liefert enzyklopädische Auszüge und Links, sofern ein passender Artikel gefunden wird.

### 50. Warum findet Wikipedia keinen Artikel?

Nicht jedes Album hat einen Artikel. Außerdem können Schreibweise, Sprache und Mehrdeutigkeit eine Rolle spielen.

### 51. Was liefert Discogs?

Discogs kann Labels, Katalognummern, Formate und Credits liefern, wenn der Provider konfiguriert ist.

### 52. Was liefert Last.fm?

Last.fm kann Tags, Hörerdaten und biografische Hintergrundinformationen liefern, wenn der Provider konfiguriert ist.

### 53. Sind Last.fm-Tags objektive Fakten?

Nein. Sie sind Community-Signale und werden als unterstützender Kontext behandelt.

### 54. Werden Providerfehler abgefangen?

Ja. Optionale Provider sollen den gesamten Workflow nicht stoppen.

### 55. Muss ich alle Provider konfigurieren?

Nein. Plex und die gewählte KI-Konfiguration sind für die jeweiligen Workflows entscheidend. Zusätzliche Provider verbessern die Quellenlage.

## Cache und Performance

### 56. Warum gibt es einen Cache?

Der Cache reduziert wiederholte Provider-Abfragen und beschleunigt spätere Läufe.

### 57. Wo liegt der Cache?

Der lokale Knowledge Cache liegt im Benutzerverzeichnis unter `.plex-enhancer/cache`.

### 58. Wie sehe ich Cache-Statistiken?

Mit `plex-enhancer cache stats`.

### 59. Wie liste ich Cache-Einträge?

Mit `plex-enhancer cache list`.

### 60. Wie lösche ich den Cache?

Mit `plex-enhancer cache clear`.

### 61. Wann sollte ich den Cache löschen?

Wenn veraltete Providerdaten vermutet werden oder Sie einen frischen Lauf erzwingen möchten.

### 62. Wird ein fehlgeschlagener Provider dauerhaft gecacht?

Fehlschläge sollen den Cache nicht dauerhaft vergiften. Erfolgreiche Antworten werden bevorzugt gespeichert.

### 63. Warum ist der erste Lauf langsam?

Beim ersten Lauf müssen Plex und externe Provider abgefragt werden. Spätere Läufe profitieren vom Cache.

### 64. Warum ist ein großer Bibliothekslauf langsam?

Mehrere hundert oder tausend Alben erzeugen viele Plex-, Provider- und KI-Schritte. Nutzen Sie Limits, Planung und Resume.

### 65. Kann ich parallelisieren?

Das Projekt enthält Performance-Optionen, aber Provider-Grenzen und Sicherheit sind wichtiger als maximale Geschwindigkeit.

## Review und Apply

### 66. Was ist der Unterschied zwischen Preview und Review?

Preview zeigt eine Vorschau. Review ergänzt Vergleich, Qualitätsprüfung und Entscheidung.

### 67. Was ist der Unterschied zwischen Review und Apply?

Review verändert Plex nicht. Apply schreibt eine genehmigte Zusammenfassung mit Backup, Reload und Verifikation.

### 68. Kann ich Änderungen rückgängig machen?

Apply legt Backups unter `exports/backups/` an. Diese Backups sind die Grundlage für eine manuelle Wiederherstellung.

### 69. Wo liegen Audit-Dateien?

Audit-Daten des Apply-Workflows liegen unter `exports/audit/`.

### 70. Was passiert, wenn Verifikation fehlschlägt?

Dann wird kein Erfolg gemeldet. Der Backup bleibt erhalten.

### 71. Kann Apply den falschen Datensatz ändern?

Apply sucht anhand der übergebenen Angaben. Arbeiten Sie bei Mehrdeutigkeiten vorsichtig und prüfen Sie Preview und Review.

### 72. Warum gibt es keine automatische Massenänderung ohne Review?

Die Sicherheitsphilosophie verlangt menschliche Kontrolle vor dauerhaften Plex-Änderungen.

### 73. Kann ich Batch-Verarbeitung abbrechen?

Ja. Interaktive Batch-Workflows bieten Skip und Quit.

### 74. Was macht Resume?

Resume setzt eine unterbrochene Sitzung anhand gespeicherter Jobdaten fort.

### 75. Wo sehe ich eine Zusammenfassung eines Bibliothekslaufs?

Mit `plex-enhancer library report`.

## JSON, Exporte und Fehlersuche

### 76. Wo werden JSON-Dateien gespeichert?

Unter `exports/`, je nach Befehl in passenden Unterordnern.

### 77. Kann ich JSON-Ausgaben weiterverarbeiten?

Ja. Viele Befehle bieten `--json` oder `--export-json`.

### 78. Warum unterscheiden sich Rich-Ausgabe und JSON?

Rich ist für Menschen optimiert. JSON enthält strukturierte Daten für Analyse, Archivierung und Automatisierung.

### 79. Wie finde ich heraus, welcher Prompt verwendet wurde?

Preview und gespeicherte Vorschauen enthalten Prompt-Name und Prompt-Version.

### 80. Warum stimmen Prompt-Versionen im Text nicht mit alten Ausgaben überein?

Alte Preview- oder Audit-Dateien behalten die damals verwendete Version. Neue Läufe nutzen die aktuelle Vorlage.

### 81. Was mache ich bei unverständlichen Fehlern?

Starten Sie mit `plex-enhancer doctor`, prüfen Sie danach den konkreten Befehl mit `--help`.

### 82. Wann soll ich `--verbose` nutzen?

Wenn Sie Providerdiagnosen, Promptdetails oder zusätzliche Ursacheninformationen sehen möchten.

### 83. Sind Stack Traces normal?

Im normalen Betrieb sollten nutzerfreundliche Fehlermeldungen erscheinen. Technische Details sind vor allem für Debugging gedacht.

### 84. Kann ich die Dokumentation als PDF bauen?

Ja. Nutzen Sie das Skript unter `docs/pdf/build.sh`, wenn Pandoc installiert ist.

### 85. Ist das Handbuch auch für gedruckte Nutzung gedacht?

Ja. Die Kapitelstruktur ist bewusst linear und PDF-freundlich.

