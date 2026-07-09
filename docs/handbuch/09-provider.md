# 9. Provider

Provider sind Datenquellen. Sie liefern Fakten, aber schreiben nichts nach Plex.

## 9.1 Plex

| Aspekt | Beschreibung |
| --- | --- |
| Zweck | lokale Bibliotheksdaten lesen und Ziel für Apply |
| Metadaten | Titel, Künstler, Jahr, Genres, Zusammenfassung |
| Zuverlässigkeit | hoch für lokale Bibliothek |
| Grenze | vorhandene Daten können unvollständig sein |

## 9.2 MusicBrainz

| Aspekt | Beschreibung |
| --- | --- |
| Zweck | stabile Identifikation von Künstlern und Alben |
| Metadaten | MBIDs, Release Groups, Daten, Genres, Credits |
| Zuverlässigkeit | hoch für strukturierte Musikdaten |
| Grenze | nicht jedes Release ist vollständig gepflegt |

## 9.3 Wikipedia

| Aspekt | Beschreibung |
| --- | --- |
| Zweck | enzyklopädischer Kontext |
| Metadaten | Titel, Sprache, Auszug, URL, Thumbnail |
| Zuverlässigkeit | gut, abhängig vom Artikel |
| Grenze | Artikel können fehlen oder unvollständig sein |

## 9.4 Discogs

| Aspekt | Beschreibung |
| --- | --- |
| Zweck | Release- und Creditdaten |
| Metadaten | Label, Katalognummer, Credits, Formate |
| Zuverlässigkeit | gut für physische Releases |
| Grenze | Token erforderlich, Rollen können uneinheitlich sein |

## 9.5 Last.fm

| Aspekt | Beschreibung |
| --- | --- |
| Zweck | Community-Kontext |
| Metadaten | Tags, Biografien, Hörerzahlen |
| Zuverlässigkeit | unterstützend |
| Grenze | Communitydaten sind nicht immer neutral |

## 9.6 OpenAI

| Aspekt | Beschreibung |
| --- | --- |
| Zweck | Textgenerierung |
| Eingabe | gerenderter Prompt |
| Ausgabe | generierte Zusammenfassung |
| Grenze | Ausgabe muss geprüft werden |

## 9.7 Fehlerbehandlung

Providerfehler werden isoliert. Ein fehlender optionaler Provider soll den gesamten Workflow nicht unnötig abbrechen.

