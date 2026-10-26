# Security Policy

## Scope

This project analyzes recruiter emails without opening email links or attachments. Security reports may cover the application, its dependencies, its handling of email data, or its network behavior. The implementation and its current limitations are described in [README.md](../README.md) and [docs/privacy-and-limitations.md](privacy-and-limitations.md); [REQUIREMENTS.md](REQUIREMENTS.md) records the intended behavior.

## Reporting a vulnerability

Please do not put real emails, personal information, credentials, API keys, or exploitable details in a public issue.

No dedicated security contact is configured yet. If this repository is hosted on a service with private vulnerability reporting, use that private channel. Otherwise, contact the maintainer privately through a verified channel. Share only the minimum information needed to explain the issue, along with affected versions and safe reproduction steps.

Please allow maintainers reasonable time to investigate and coordinate a fix before publicly disclosing a vulnerability. No response-time commitment is currently established.

## Safe handling

- Use synthetic or thoroughly redacted email samples in bug reports and tests.
- Never commit email files, credentials, or provider keys. The repository `../.gitignore` excludes common local email samples and secret files, but it is not a substitute for checking changes before publishing.
- Do not test against systems or accounts you do not own or have permission to assess.
