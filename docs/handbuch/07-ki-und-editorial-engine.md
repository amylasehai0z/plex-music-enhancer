# 7. KI und Editorial Engine

Plex Music Enhancer nutzt KI nicht isoliert. Die KI erhält einen geprüften Kontext und klare Schreibregeln.

## 7.1 Gesamtarchitektur

```text
Plex
↓
Metadata Providers
↓
MusicBrainz
↓
Wikipedia
↓
Discogs
↓
Last.fm
↓
Context Builder
↓
Editorial Style Engine
↓
GPT-5.5
↓
Review Engine
↓
Apply
```

## 7.2 Plex

Plex liefert den lokalen Ausgangspunkt:

- Künstler
- Album
- Jahr
- vorhandene Beschreibung
- Genres
- Rating Key

## 7.3 Metadata Providers

Externe Quellen ergänzen Fakten. Optional nicht verfügbare Quellen blockieren den Ablauf nicht.

## 7.4 MusicBrainz

MusicBrainz liefert stabile IDs und Release-Informationen. Es ist besonders wichtig für korrekte Albumzuordnung.

## 7.5 Wikipedia

Wikipedia liefert enzyklopädischen Kontext. Wenn kein Artikel existiert, wird der Workflow fortgesetzt.

## 7.6 Discogs

Discogs kann Labels, Katalognummern, Credits und Produktionsinformationen liefern. Dafür ist ein Token erforderlich.

## 7.7 Last.fm

Last.fm kann Tags, Hörerzahlen und Biografieinformationen liefern. Dafür ist ein API Key erforderlich.

## 7.8 Context Builder

Der Context Builder erstellt:

- `AlbumContext`
- `ArtistContext`

Diese Modelle sind die strukturierte Grundlage für Prompt und Qualitätssicherung.

## 7.9 Editorial Style Engine

Die Editorial Style Engine analysiert:

- Satzanfänge
- Wortwiederholungen
- Lesbarkeit
- typische KI-Floskeln
- Listenstil
- passive Sprache

## 7.10 GPT-5.5 oder anderes Modell

Das Modell erzeugt die finale Formulierung. Es erhält keine freie Aufgabe, sondern einen Prompt mit Fakten und Grenzen.

## 7.11 Prompt Engineering

Prompts enthalten:

- Ziel: deutscher enzyklopädischer Stil
- gewünschte Länge
- Faktenregeln
- Verbote gegen erfundene Charts, Preise oder Kritiken
- Variablen aus dem Kontext

## 7.12 Prompt-Versionen

Prompt-Versionen werden gespeichert, damit nachvollziehbar bleibt, welche Vorlage einen Text erzeugt hat.

## 7.13 Warum Texte factual bleiben

Das System nutzt:

- Quellenkontext
- Fact Verification
- Prompt-Regeln
- Review
- QA

> **Wichtig:** Das System reduziert Halluzinationen, ersetzt aber keine menschliche Prüfung.

