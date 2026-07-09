# Wikipedia Provider

The Wikipedia provider retrieves read-only encyclopedic summaries for artists and albums.
It does not write to Plex and does not use AI-generated content.

## API Endpoints

The provider uses the official Wikipedia REST API for each configured language edition:

- `GET /w/rest.php/v1/search/title`
- `GET /api/rest_v1/page/summary/{title}`

Artist lookup searches for the artist name. Album lookup searches for the album title plus
artist name to improve disambiguation.

## Language Fallback

The default language order is:

1. German (`de`)
2. English (`en`)

If no German title search result is available, or the German summary cannot be resolved, the
provider tries English. The selected summary records the language reported by Wikipedia.

## Returned Fields

Provider lookups normalize Wikipedia responses into:

- `title`
- `page_id`
- `language`
- `extract`
- `url`
- `thumbnail`

The provider also implements the common `MetadataProvider` interface, so `ProviderManager`
can merge Wikipedia summaries with other providers.

## Caching

Successful summaries are cached under:

```text
~/.plex-enhancer/cache/wikipedia/
```

Cache entries are keyed by lookup kind, language, and normalized query. Entries expire after
30 days. Failed lookups are not cached, so a later run can discover newly created articles.
