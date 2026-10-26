# Phishing Email Verifier

A local-first tool for assessing recruiter emails by collecting and presenting evidence. It is intended to help users decide what to verify next; it cannot prove that a recruiter, agency, or job is legitimate.

## What it does

- Parses a saved `.eml` file and extracts sender details, headers, subject, text, links, and attachments.
- Performs local, rule-based checks for authentication, tracking links, suspicious content, and recruiter claims.
- Supports optional AI claim extraction and comparison, but only after explicit user confirmation and with redaction of recipient names, addresses, and email URLs.
- Allows a user-supplied company page or text file to be compared against the email's role claims.
- Supports a basic non-AI web search using only approved company and role terms.
- Never fetches links found inside the email and never opens attachments.

## Setup

1. Create and activate a virtual environment if needed.
2. Install the project requirements (if a requirements file or package install is added later).
3. Run the CLI on a saved email:

   python verify_recruiter.py path/to/email.eml

## Usage

See the [Usage Guide](docs/usage.md) for every command-line option and examples covering offline analysis, page
cross-checking, network lookups, search, AI providers, prompt packets, and saving reports.

## Privacy and data handling

- Offline mode makes no network requests.
- Network access and hosted AI use are explicit and must be confirmed by the user.
- Recipient names, addresses, and email URLs are redacted before any AI payload is sent.
- Email text, fetched page text, and search queries are treated as untrusted input.
- The tool reports uncertainty and recommends independently contacting the company through contact info obtained outside the email.

## Testing

Run the deterministic offline test suite with:

python -m unittest -q

## Project documents

- [Requirements](docs/REQUIREMENTS.md)
- [Security policy](docs/SECURITY.md)
- [Usage guide](docs/usage.md)
- [Privacy and limitations](docs/privacy-and-limitations.md)
