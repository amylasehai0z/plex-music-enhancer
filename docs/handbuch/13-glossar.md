# 13. Glossar

Dieses Glossar erklärt Begriffe, die in Plex Music Enhancer und im Handbuch häufig vorkommen.

| Begriff | Erklärung |
| --- | --- |
| Album Context | Strukturierter Datensatz, der Plex-, Provider-, Prüf- und Kontextinformationen zu einem Album bündelt. |
| Artist Context | Strukturierter Datensatz für Künstlerbiografien und Künstlerinformationen. |
| Apply | Workflow, der eine genehmigte Zusammenfassung nach Backup und Verifikation in Plex schreibt. |
| Audit | Lesende Analyse der vorhandenen Plex-Metadaten. |
| Backup | Sicherung des alten Plex-Textes vor einer Schreiboperation. |
| Batch | Interaktiver Ablauf für mehrere Alben. |
| Cache | Lokaler Zwischenspeicher für Providerdaten. |
| CLI | Command Line Interface, also die Bedienung über Terminalbefehle. |
| Context Builder | Teil der Pipeline, der aus Plex und Providerdaten einen einheitlichen Kontext erstellt. |
| Discogs | Externe Musikdatenbank mit Labels, Katalognummern, Formaten und Credits. |
| Doctor | Diagnosebefehl für Installation, Konfiguration, Plex und KI. |
| DummyProvider | Testanbieter, der deterministische Texte ohne Netzwerk erzeugt. |
| Editorial Composer | Schicht, die Fakten in sinnvolle Schreibanweisungen und Prioritäten überführt. |
| Editorial Style Engine | Analyse- und Polierschicht für deutschen enzyklopädischen Stil. |
| Export | JSON-Datei, die aus einem Befehl unter `exports/` geschrieben wird. |
| Fact Verification | Bewertung der Zuverlässigkeit einzelner Fakten anhand vorhandener Quellen. |
| GeneratedSummary | Modell für einen erzeugten Text inklusive Provider, Modell, Prompt und Metadaten. |
| Halluzination | Nicht belegte oder erfundene Aussage eines Sprachmodells. |
| Improve | Workflow zur sprachlichen Verbesserung eines vorhandenen deutschen Textes. |
| Inspect | Lesender Befehl zur Anzeige eines Plex-Objekts mit Attributen, Medien, Bildern und Kindern. |
| Knowledge Cache | Lokaler Cache für Künstler- und Albumwissen aus externen Quellen. |
| Last.fm | Provider für Community-Tags, Hörerzahlen und biografische Hintergrunddaten. |
| Library | Plex-Bibliothek, zum Beispiel eine Musikbibliothek. |
| Library Workflow | Plan-, Review-, Apply-, Resume- und Report-Ablauf für eine ganze Bibliothek. |
| Match | Zuordnung eines Plex-Albums zu MusicBrainz-Daten. |
| MBID | MusicBrainz Identifier, eine stabile ID für Musikobjekte. |
| Metadata | Beschreibende Daten wie Titel, Jahr, Genre, Label, Zusammenfassung oder Credits. |
| MusicBrainz | Strukturierte Musikdatenbank für Künstler, Releases und Release Groups. |
| OpenAIProvider | KI-Anbieter, der über die OpenAI Python SDK verwendet wird. |
| Pipeline | Abfolge von Verarbeitungsschritten von Plex über Provider bis zum finalen Kontext. |
| Planner | Analysekomponente, die CREATE, TRANSLATE, IMPROVE, REVIEW oder SKIP empfiehlt. |
| Preview | Vorschau auf generierte Inhalte ohne Plex-Änderung. |
| Prompt | Textvorlage mit Anweisungen und Variablen für das KI-Modell. |
| Prompt Engine | System zum Laden, Prüfen und Rendern von Prompt-Vorlagen. |
| Prompt Version | Versionsnummer einer Prompt-Vorlage, wichtig für Nachvollziehbarkeit. |
| Provider | Datenquelle oder KI-Anbieter, zum Beispiel MusicBrainz, Wikipedia, Discogs, Last.fm oder OpenAI. |
| QA | Quality Assurance, also Qualitätsprüfung des erzeugten Textes. |
| Rating Key | Plex-interne Kennung für ein Objekt. |
| Release | Eine konkrete Veröffentlichung eines Albums. |
| Release Group | MusicBrainz-Gruppe mehrerer Veröffentlichungen desselben Albums. |
| Resume | Fortsetzen eines unterbrochenen Jobs. |
| Review | Interaktive Prüfung mit Vergleich, Qualitätsanalyse und Entscheidung. |
| Rich | Terminalbibliothek für Tabellen, Panels und formatierte Ausgaben. |
| Scan | Lesende Erfassung von Plex-Bibliotheken, Künstlern oder Alben. |
| Style Analysis | Analyse von Satzanfängen, Wiederholungen, Lesbarkeit und typischen KI-Floskeln. |
| Summary | Zusammenfassung oder Beschreibung in Plex. |
| Translate | Workflow zur Übersetzung vorhandener englischer Texte ins Deutsche. |
| Verification State | Zustand eines geprüften Fakts: verified, probable, weak, conflicting oder unknown. |
| Wikipedia | Enzyklopädische Quelle für Künstler- und Albumkontext. |

## 13.1 Empfohlene deutsche Begriffe

| Englisch | Im Handbuch bevorzugt |
| --- | --- |
| Preview | Vorschau oder Preview |
| Review | Review oder Prüfung |
| Apply | Apply oder Schreiben |
| Provider | Provider oder Datenquelle |
| Prompt | Prompt |
| Summary | Zusammenfassung |
| Cache | Cache |

Einige englische Begriffe bleiben erhalten, weil sie auch in den CLI-Befehlen verwendet werden.

