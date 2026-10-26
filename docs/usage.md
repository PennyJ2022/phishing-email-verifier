# Usage Guide

The verifier analyzes a saved email file (`.eml`). It prints a Markdown report to the terminal. Local rule-based
analysis is the default; network lookups and AI are optional.

Run commands from the project directory. Use `python` instead of `python3` if that is the Python command on your
system.

## Basic use

```bash
python3 verify_recruiter.py path/to/message.eml
```

This runs local checks without AI or network lookups. The email file is not modified.

Show all command-line options:

```bash
python3 verify_recruiter.py --help
```

## Common workflows

### Save the report

The report is always printed to the terminal. Add `--out` to also save it:

```bash
python3 verify_recruiter.py message.eml --out report.md
```

### Compare against copied company-page text

Copy the relevant careers or job-listing page text into a plain-text file, then run:

```bash
python3 verify_recruiter.py message.eml --page-file careers.txt
```

This does not require network access. The verifier compares the extracted email claims with the supplied text, but
does not verify that the text really came from the company's website.

### Fetch a company page you typed yourself

```bash
python3 verify_recruiter.py message.eml --network --company-url https://www.example.com
```

`--network` enables sender-domain lookups and is required to fetch `--company-url`. The verifier may also try the
site's `/careers` and `/jobs` pages when the URL is the home page. Only enter a company URL obtained independently;
links in the email are not fetched. This feature makes external network requests.

### Search company and role terms without AI

```bash
python3 verify_recruiter.py message.eml --search
```

After you approve, the search sends extracted company, job-title, and location terms to DuckDuckGo. Search results
are unverified candidates, not proof that a listing or recruiter is legitimate. Search is a separate opt-in from
`--network`.

### Use a configured AI provider

Choose one provider with `--ai`:

```bash
python3 verify_recruiter.py message.eml --ai anthropic
python3 verify_recruiter.py message.eml --ai openai --model MODEL_NAME
python3 verify_recruiter.py message.eml --ai ollama --model MODEL_NAME
```

AI is off by default. Before sharing redacted email text—and, when supplied, company-page text—the CLI asks for
confirmation. The confirmation identifies the provider and data type. Recipient details and URLs are redacted
where detected, but redaction is incomplete; inspect the message and consider the provider's data policies before
approving.

Configure credentials and defaults through environment variables:

| Provider | Required or useful environment variables |
|---|---|
| Anthropic | `ANTHROPIC_API_KEY`; optional `ANTHROPIC_MODEL` |
| OpenAI-compatible API | `LLM_API_KEY` if the endpoint requires authentication; optional `LLM_MODEL`, `LLM_BASE_URL` |
| Ollama | `OLLAMA_MODEL`; optional `OLLAMA_HOST` |

You can instead pass `--model MODEL_NAME`. `--base-url URL` overrides the configured base URL for an
OpenAI-compatible endpoint or Ollama server:

```bash
python3 verify_recruiter.py message.eml --ai openai --model MODEL_NAME \
  --base-url https://api.example.com/v1

python3 verify_recruiter.py message.eml --ai ollama --model MODEL_NAME \
  --base-url http://localhost:11434
```

The OpenAI-compatible provider defaults to `https://api.openai.com/v1`; Ollama defaults to
`http://localhost:11434`. Anthropic uses its standard API endpoint. Follow your provider's instructions for
creating credentials and selecting a model.

### Combine a copied page with AI comparison

```bash
python3 verify_recruiter.py message.eml --ai ollama --model MODEL_NAME --page-file careers.txt
```

AI claim extraction uses the redacted email text. If page text is available, AI comparison separately asks before
sending that text. If AI comparison is unavailable or declined, the verifier falls back to local heuristic checks.

### Create a prompt for manual use with a chat AI

```bash
python3 verify_recruiter.py message.eml --packet prompt.txt
```

This writes a ready-to-paste prompt containing extracted claims and redacted email text. To include copied company
page text:

```bash
python3 verify_recruiter.py message.eml --page-file careers.txt --packet prompt.txt
```

The packet is written locally; the verifier does not send it to a chat AI. Review it before sharing. When using
`--packet` with a fetched `--company-url` instead of `--page-file`, fetched page text is not included in the packet.

### Skip interactive approval prompts

```bash
python3 verify_recruiter.py message.eml --search --yes
python3 verify_recruiter.py message.eml --ai anthropic --yes
```

`--yes` automatically approves both AI data sharing and DuckDuckGo search terms when those features are enabled.
It does not enable AI, search, or network lookups by itself. Use it only when you intend to approve the applicable
disclosures. Without a terminal prompt, sharing is declined unless `--yes` is set.

### Combine features and save outputs

```bash
python3 verify_recruiter.py message.eml \
  --network \
  --company-url https://www.example.com \
  --search \
  --out report.md
```

The example performs network lookups, fetches the typed company page, and asks before sending approved search terms
to DuckDuckGo. Add `--ai PROVIDER` if you also want AI claim extraction and page comparison. Add `--packet prompt.txt`
to write a separate manual prompt packet.

## Command-line options

| Option | What it does |
|---|---|
| `message.eml` | Required positional argument: path to the saved email file to analyze. |
| `-h`, `--help` | Display the command help and exit. |
| `--ai {off,anthropic,openai,ollama}` | Select an AI provider. Defaults to `off`. |
| `--model MODEL` | Set the model name for the selected provider. |
| `--base-url URL` | Set an OpenAI-compatible API or Ollama base URL. |
| `--network` | Opt in to RDAP, DNS, and Wayback lookups; also enables fetching `--company-url`. |
| `--company-url URL` | Company URL typed by you, never taken from the email. Requires `--network` to fetch. |
| `--page-file FILE` | Read copied company-page text from a local plain-text file for cross-checking. |
| `--search` | Opt in to a basic non-AI DuckDuckGo search using approved company and role terms. |
| `--packet FILE` | Write a redacted, ready-to-paste prompt packet to a file. |
| `--out FILE` | Save the Markdown report to a file as well as printing it. |
| `--yes` | Skip confirmation before sharing redacted text with AI or search terms with DuckDuckGo. |

Network access is off by default; the internal `--no-network` switch is hidden from help because it is redundant
with the default.

## Important privacy notes

- `--network`, `--search`, and AI use can contact external services. Read each workflow above before enabling them.
- Search and AI sharing require confirmation unless `--yes` is used.
- `--packet` creates a local file that you may choose to share; inspect it first.
- Email links are not opened or fetched, and attachments are not opened or executed.
- Results are evidence and suggestions, not proof. Independently contact the company using contact information
  obtained outside the email.

See [Privacy and Limitations](privacy-and-limitations.md) for more detail.
