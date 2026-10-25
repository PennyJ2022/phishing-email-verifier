import argparse
import html
import re
import sys
import urllib.parse
import urllib.request

from .core import verify_recruiter_email
from .parsing import parse_eml
from .rules import build_prompt_packet


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check whether a recruiter email looks legitimate.")
    ap.add_argument("eml", help="path to a saved .eml file")
    ap.add_argument("--ai", choices=["off", "anthropic", "openai", "ollama"], default="off",
                    help="optional AI for claim extraction and the page cross-check (default: off)")
    ap.add_argument("--model", help="model name for the chosen AI provider")
    ap.add_argument("--base-url", help="API base URL (openai-compatible or ollama)")
    ap.add_argument("--network", dest="network", action="store_true",
                    help="opt in to RDAP/DNS/Wayback lookups and company-page fetching")
    ap.add_argument("--no-network", dest="network", action="store_false", help=argparse.SUPPRESS)
    ap.set_defaults(network=False)
    ap.add_argument("--company-url", help="the company's own site, typed by you (never taken from the email)")
    ap.add_argument("--page-file", help="text file with a careers/listing page you copied")
    ap.add_argument("--search", action="store_true",
                    help="perform a basic non-AI search using only user-approved company and role details")
    ap.add_argument("--packet", help="write a ready-to-paste prompt for a chat AI to this file")
    ap.add_argument("--out", help="save the Markdown report to this file")
    ap.add_argument(
        "--yes",
        action="store_true",
        help="skip confirmation before sharing redacted email/page text with AI or search terms with DuckDuckGo",
    )
    a = ap.parse_args(argv)

    def confirm(provider: str, data_kind: str, n: int) -> bool:
        if a.yes:
            return True
        if not sys.stdin.isatty():
            print(f"Not sending to {provider}: run interactively or pass --yes.", file=sys.stderr)
            return False
        ans = input(f"Send {n} characters of {data_kind} to '{provider}'? [y/N] ")
        return ans.strip().lower() in ("y", "yes")

    def search_fn(query: str):
        if not a.search:
            return []
        try:
            params = urllib.parse.urlencode({"q": query, "hl": "en", "num": 5})
            with urllib.request.urlopen(f"https://duckduckgo.com/html/?{params}", timeout=15) as r:
                html_text = r.read(200_000).decode("utf-8", "replace")
        except Exception:
            return []
        items = []
        for match in re.finditer(r'<a rel="nofollow" class="result-link" href="(.*?)".*?>(.*?)</a>', html_text, re.S):
            url = html.unescape(re.sub(r"^//", "https://", match.group(1)))
            title = re.sub(r"<.*?>", "", match.group(2))
            title = html.unescape(re.sub(r"\s+", " ", title).strip())
            if url and title:
                items.append({"title": title, "url": url})
        return items

    try:
        report = verify_recruiter_email(a.eml, ai=a.ai, model=a.model, base_url=a.base_url,
                                       network=a.network, company_url=a.company_url,
                                       page_file=a.page_file, confirm_send=confirm,
                                       search_provider=search_fn if a.search else None)
    except OSError as e:
        print(f"Could not read file: {e}", file=sys.stderr)
        return 1
    md = report.to_markdown()
    print(md)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(md)
    if a.packet:
        p = parse_eml(a.eml)
        page = open(a.page_file, encoding="utf-8", errors="replace").read() if a.page_file else ""
        with open(a.packet, "w", encoding="utf-8") as fh:
            fh.write(build_prompt_packet(p, report.claims, page))
        print(f"\nPrompt packet written to {a.packet}", file=sys.stderr)
    return 0
