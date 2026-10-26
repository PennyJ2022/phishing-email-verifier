# Privacy and Limitations

## Local analysis

Network access and AI are off by default. In that default mode, the program parses the selected `.eml` file and applies local rules without making network requests. It reads attachment names for warning signs but does not open or execute attachments. Reports and prompt packets are written only to the destinations you choose.

Rule-based extraction is approximate: a claim that is missing or incorrectly extracted is not proof that it was absent from the email. A verdict is a summary of available signals, not proof that an email, recruiter, or job is legitimate.

## Optional network features

- `--network` enables domain-registration, DNS, and Wayback lookups, and is required for fetching a company page with `--company-url`. These lookups contact RDAP, Google DNS-over-HTTPS, and the Internet Archive. A typed company URL is checked for public addresses on each connection, redirects are checked, and environment proxy settings are bypassed. These safeguards do not establish that a site belongs to the company.
- `--search` submits only extracted company, job-title, and location terms to DuckDuckGo, after confirmation. Search results are unverified candidates. Results whose host contains a company-name token are ranked first as a weak heuristic; this does not establish that a domain is official or that a role exists. The report includes result titles and URLs, but does not treat search hits as role confirmation.
- URLs found in the email are not fetched, opened, resolved, or used as search destinations. The company URL must be supplied separately by the user.

`--yes` skips the interactive confirmation for AI sharing and DuckDuckGo search terms. Use it only if you intend to approve those disclosures.

## Optional AI and prompt packets

AI is disabled by default. Before sending text to a configured provider, the program asks for confirmation unless `--yes` is supplied. AI claim extraction sends redacted email text; AI page comparison sends page text. Recipient names and email addresses are replaced when detected, and email URLs are replaced with labels that retain the hostname. Redaction is incomplete and cannot guarantee anonymity. Review the text and consider the provider's data-handling terms before approving.

AI is used to extract or compare claims, not to establish legitimacy. For page comparisons, the program checks that the quoted evidence appears in the supplied text, that the quoted page value appears in the evidence, and that the reported email claim matches the extracted claim. A title match is not counted as role confirmation unless the company name also appears in the supplied page text. These checks cannot fully validate the AI's reasoning or prove that the page is an official company source.

`--packet FILE` writes a redacted prompt for you to review and share manually; it does not send the packet to an AI service.

## Limitations and safe handling

Search providers and company pages can be incomplete, misleading, or out of date. A company name in page text and a matching title do not prove page ownership. Authentication results show a message's relationship to a sending domain, not whether its recruiter or job is genuine. Independently contact the company using contact details obtained outside the email.

Use synthetic or thoroughly redacted email samples in tests and bug reports. Do not commit email files, API keys, credentials, or generated reports containing personal information.
