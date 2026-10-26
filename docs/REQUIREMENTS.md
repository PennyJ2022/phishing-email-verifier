# Project Requirements

## Purpose

Help a person assess a recruiter email by collecting and presenting evidence. The tool must not claim to prove that a recruiter, agency, or job is legitimate.

## Functional Requirements

### Email analysis

- Accept a saved email message and extract its sender, headers, text, links, attachments, and recruiting claims where available.
- Provide useful rule-based checks without requiring an AI provider or AI account.
- Report findings with the relevant evidence and distinguish warnings, failures, informational results, and inconclusive checks.
- Treat missing data as unknown, not as proof of legitimacy.

### Optional AI

- Keep AI disabled by default; users can run the core checks without AI.
- Allow an AI provider to be selected through a small interchangeable backend interface.
- Use AI only to extract or compare claims; do not let it make unsupported claims of legitimacy.
- Require AI findings to include evidence from the email or supplied company-page text, and reject or mark unsupported quotations.
- Make external AI use explicit and obtain user confirmation before sending email-derived text to a hosted provider.
- Redact recipient names, email addresses, and email URLs before sending content to an AI provider. Clearly disclose that redaction may not remove every identifying detail.

### Company and job verification

- Support comparing email claims with company careers-page text provided by the user or fetched from a company URL the user supplies.
- Support basic internet search without requiring AI, using only user-approved company and role details as search terms.
- Prefer official company sources and show the source URL and quoted evidence for any reported match.
- Never use URLs extracted from the recruiter email as fetch or search destinations. Do not click, resolve, or follow email links on the user's behalf.
- Treat search results and a matching job listing as supporting evidence only; neither establishes that the sender is authorized to recruit.

### Report

- Present a cautious, understandable result with evidence, uncertainty, and checks that could not be completed.
- Include practical next steps for verifying the recruiter with the company through independently obtained contact information.
- Avoid a positive verdict when essential evidence is absent or conflicting.

## Privacy and Security Requirements

- Provide a fully offline mode that performs no network requests.
- Make network lookups and hosted AI requests explicit, with clear indication of what information leaves the device and which services receive it.
- Do not log or transmit full email contents, credentials, or API keys unnecessarily.
- Read provider credentials from environment variables or another secure credential mechanism; never store secrets in source control.
- Validate user-supplied URLs and restrict fetching to safe public web destinations; handle redirects and network failures safely.
- Treat email contents and fetched page text as untrusted input, including possible prompt-injection instructions.
- Do not execute or open email attachments.

## Quality Requirements

- Keep rule-based analysis usable if network access or an AI provider is unavailable.
- Keep tests deterministic and offline by default; tests must not contact external services.
- Cover parsing, privacy redaction, link handling, inconclusive results, and AI failure/fallback behavior with tests.
- Document setup, usage, network behavior, data handling, limitations, and test commands.
