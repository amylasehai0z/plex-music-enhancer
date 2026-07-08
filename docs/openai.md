# OpenAI Provider

The OpenAI provider is the first real AI provider for Plex Music Enhancer. It uses the official
OpenAI Python SDK through the existing provider-independent AI abstraction.

## Configuration

Select the provider:

```text
PLEX_ENHANCER_AI__PROVIDER=openai
```

Select a model:

```text
PLEX_ENHANCER_AI__MODEL=gpt-5.5
```

Optional request controls:

```text
PLEX_ENHANCER_AI__TIMEOUT_SECONDS=30
PLEX_ENHANCER_AI__MAX_RETRIES=2
PLEX_ENHANCER_AI__MAX_PROMPT_CHARACTERS=20000
```

## API Key

The provider reads the API key from:

```text
OPENAI_API_KEY
```

It also supports the nested project setting:

```text
PLEX_ENHANCER_AI__API_KEY=...
```

Prefer `OPENAI_API_KEY` for local shells and deployment secrets. Never commit API keys to `.env`,
test fixtures, logs, or exported JSON.

## Model Selection

The default model is `gpt-5.5`. You can choose any OpenAI model available to your API account by
setting `PLEX_ENHANCER_AI__MODEL`.

The provider sends rendered Markdown prompts from the prompt engine. It does not stream responses.

## Expected Costs

Costs are usage based. Each preview request stores token usage in `GeneratedSummary.metadata`:

- `prompt_tokens`
- `completion_tokens`
- `finish_reason`

Estimate cost as:

```text
(prompt_tokens / 1_000_000 * input_token_price)
+ (completion_tokens / 1_000_000 * output_token_price)
```

OpenAI pricing changes over time and can vary by model. Check the official pricing page before
running large batches:

```text
https://openai.com/api/pricing/
```

## Error Handling

The provider validates:

- API key presence
- non-empty prompts
- maximum prompt length

Transient failures such as rate limits, timeouts, and server errors are retried according to
`PLEX_ENHANCER_AI__MAX_RETRIES`. SDK errors are mapped to project AI exceptions so CLI callers can
show helpful messages without exposing secrets.

## Troubleshooting

If preview fails with a configuration error:

- confirm `OPENAI_API_KEY` is set
- confirm `PLEX_ENHANCER_AI__PROVIDER=openai`
- confirm the configured model is available to your account

If preview fails with rate limits:

- reduce batch size
- increase time between requests
- lower retry count if you want failures to surface faster

If costs are higher than expected:

- inspect `prompt_tokens` and `completion_tokens`
- shorten prompt templates
- choose a lower-cost model
- avoid running large batches until token usage looks reasonable

## Safety

The OpenAI provider only generates preview text. It does not modify Plex, apply metadata, create
backups, or implement rollback.
