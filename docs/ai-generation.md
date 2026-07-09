# KI-Erzeugung

Plex Music Enhancer erzeugt Texte nicht direkt aus einem Albumnamen. Vor der KI-Erzeugung wird ein strukturierter Kontext gesammelt und geprüft.

## Pipeline

```text
Plex
↓
Metadatenanbieter
↓
AlbumContext oder ArtistContext
↓
Fact Verification
↓
Editorial Composer
↓
Prompt Builder
↓
GPT-5.5 oder konfiguriertes Modell
↓
Editorial Quality Engine
↓
Review
↓
Apply
```

## 1. Plex

Plex liefert:

- Titel
- Künstler
- Jahr
- vorhandene Zusammenfassung
- Genres
- Rating Key

Diese Daten sind die Grundlage. Plex Music Enhancer verändert sie erst beim ausdrücklichen Apply.

## 2. Metadatenanbieter

| Anbieter | Rolle |
| --- | --- |
| MusicBrainz | IDs, Release Groups, Datum, Genres, Credits |
| Wikipedia | enzyklopädischer Kontext |
| Discogs | Label, Katalognummer, Produktions- und Creditdaten |
| Last.fm | Community-Tags, Biografien, Hörkontext |

Fehler eines optionalen Anbieters blockieren nicht den gesamten Ablauf.

## 3. Kontextaufbau

Der `AlbumContext` oder `ArtistContext` bündelt alle Informationen in einem einheitlichen Modell.

Beispiele für Albumfelder:

- `artist`
- `album`
- `release_date`
- `genres`
- `producer`
- `label`
- `previous_album`
- `notable_tracks`
- `wikipedia.extract`

## 4. Faktenprüfung

Die Verification Engine bewertet Fakten:

- verifiziert
- wahrscheinlich
- schwach
- widersprüchlich
- unbekannt

Widersprüche werden nicht geraten. Sie erscheinen als Warnung oder werden im Prompt zurückhaltend behandelt.

## 5. Editorial Style Engine

Die Editorial-Schicht erzeugt keine Prosa. Sie bereitet Schreibanweisungen vor:

- natürliche Reihenfolge
- wichtige Fakten
- fehlende Fakten
- Themen, die nicht erfunden werden dürfen
- gewünschter deutscher Stil

## 6. Prompt Builder

Der Prompt Builder rendert Markdown-Vorlagen aus `prompts/`.

Wichtige Prompts:

- `album_summary.md`
- `album_translate.md`
- `album_improve.md`
- `artist_biography.md`

Jeder Prompt hat eine Version, die in JSON-Ausgaben und Auditdaten gespeichert wird.

## 7. GPT-5.5 oder anderes Modell

Wenn `PLEX_ENHANCER_AI__PROVIDER=openai` gesetzt ist, wird der OpenAI Provider genutzt.

Beispiel:

```bash
export PLEX_ENHANCER_AI__PROVIDER=openai
export PLEX_ENHANCER_AI__MODEL=gpt-5.5
export OPENAI_API_KEY="sk-..."
```

## Warum Halluzinationen reduziert werden

Plex Music Enhancer reduziert erfundene Inhalte durch:

- strukturierte Fakten statt freier Suche
- explizite Prompt-Regeln
- Verifikationsstatus
- Warnung vor fehlenden Fakten
- Verbot von erfundenen Charts, Auszeichnungen und Kritiken
- Review vor Apply
- Qualitätsprüfung nach der Erzeugung

> **Wichtig:** Kein KI-System kann Halluzinationen absolut ausschließen. Deshalb bleibt der Review-Schritt zentral.

## DummyProvider

Der Standardanbieter `dummy` erzeugt einen deterministischen Testtext und ruft keine externe API auf. Er ist nützlich für Installation, Tests und Dokumentationsbeispiele.

Für echte Inhalte verwenden Sie `openai`.

