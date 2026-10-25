import os

from .ai import LLM, LLMError, ai_crosscheck, ai_extract_claims
from .models import Finding, Report
from .network import NetError, check_domain, fetch_company_text
from .parsing import parse_eml, redact
from .rules import build_draft, build_prompt_packet, build_questions, crosscheck_heuristic, decide_tier, extract_claims


def _safe_search_terms(claims: dict) -> list:
    terms = []
    for key in ("company", "title", "location"):
        value = (claims or {}).get(key)
        if value:
            terms.append(value)
    cleaned = []
    seen = set()
    for term in terms:
        item = str(term).strip()
        if item and item.lower() not in seen:
            cleaned.append(item)
            seen.add(item.lower())
    return cleaned


def search_company_role(claims: dict, *, search_fn=None, max_results: int = 5, confirm=None) -> list:
    if search_fn is None:
        return []
    terms = _safe_search_terms(claims)
    if not terms:
        return []
    queries = []
    for term in terms:
        queries.append(f"{term} careers")
        queries.append(f"{term} jobs")
    queries = queries[:5]
    disclosure = "; ".join(queries)
    if confirm is None or not confirm("DuckDuckGo", disclosure, len(disclosure)):
        return None
    results = []
    seen = set()
    for query in queries:
        for item in search_fn(query):
            if len(results) >= max_results:
                return results
            key = (item.get("title") or "", item.get("url") or "")
            if key in seen:
                continue
            seen.add(key)
            if item.get("url"):
                results.append(item)
    return results


def verify_recruiter_email(eml_path: str, *, ai: str = "off", model: str = None,
                           base_url: str = None, network: bool = False,
                           company_url: str = None, page_file: str = None,
                           llm: LLM = None,
                           confirm_send=None,
                           search_provider=None,
                           search_results=None) -> Report:
    p = parse_eml(eml_path)
    findings = []
    from .rules import check_headers, check_links, check_content
    findings += check_headers(p) + check_links(p) + check_content(p)
    if network:
        findings += check_domain(p.from_domain)
    else:
        findings.append(Finding("domain", "info", "Network lookups were skipped (--no-network)."))

    claims, sources = extract_claims(p)
    ai_used = "off"
    if ai != "off" or llm is not None:
        try:
            llm = llm or LLM(ai, model, base_url)
            payload = redact(p.subject + "\n\n" + p.text, p)
            if confirm_send is not None and confirm_send(llm.provider, "redacted email text", len(payload)):
                got = ai_extract_claims(llm, payload)
                for k in claims:
                    v = got.get(k)
                    if v not in (None, "", []):
                        claims[k] = v
                        sources[k] = f"AI: {llm.provider}"
                ai_used = llm.provider
            else:
                message = ("AI step cancelled; using rules only." if confirm_send is not None else
                           "AI step skipped because explicit data-sharing confirmation was not provided.")
                findings.append(Finding("ai", "info", message))
                llm = None
        except LLMError as e:
            findings.append(Finding("ai", "info", f"AI step failed, using rules only: {e}"))
            llm = None

    page = ""
    if page_file:
        with open(page_file, encoding="utf-8", errors="replace") as fh:
            page = fh.read()
    elif company_url and network:
        page, notes = fetch_company_text(company_url, [l.href for l in p.links])
        findings += [Finding("crosscheck", "info", n) for n in notes]
    elif company_url:
        findings.append(Finding("crosscheck", "info", "--company-url ignored because network is off. Use --page-file with text you copied."))

    if search_provider is not None:
        if confirm_send is None:
            search_hits = None
        else:
            search_hits = search_company_role(
                claims,
                search_fn=search_provider,
                confirm=confirm_send,
            )
        if search_hits is None:
            findings.append(Finding("search", "info",
                                    "Search was skipped because explicit approval of the search terms was not provided."))
        elif search_hits:
            findings.append(Finding("search", "info",
                                   f"Non-AI search found {len(search_hits)} candidate results for the company/role.",
                                   "; ".join(f"{item.get('title')}: {item.get('url')}" for item in search_hits[:3] if item.get('url')),
                                   key="search_found"))
        else:
            findings.append(Finding("search", "info", "No non-AI search results were returned using the approved company/role terms."))
    elif search_results:
        search_hits = list(search_results)
        if search_hits:
            findings.append(Finding("search", "info",
                                   f"Search results provided: {len(search_hits)} candidate listing(s).",
                                   "; ".join(f"{item.get('title')}: {item.get('url')}" for item in search_hits[:3] if item.get('url')),
                                   key="search_found"))

    if page.strip():
        done = False
        if llm is not None:
            try:
                page_text = page[:12000]
                if confirm_send is not None and confirm_send(llm.provider, "company page text", len(page_text)):
                    findings += ai_crosscheck(llm, claims, page_text)
                    done = True
                else:
                    findings.append(Finding("ai", "info", "AI page comparison cancelled; using rule-based checks."))
            except LLMError as e:
                findings.append(Finding("ai", "info", f"AI cross-check failed, using rules instead: {e}"))
        if not done:
            findings += crosscheck_heuristic(claims, page)
    else:
        findings.append(Finding("crosscheck", "info", "Role not cross-checked. Pass --company-url or --page-file, or use --packet to get a prompt for a chat AI."))

    tier, reason = decide_tier(findings)
    meta = {"file": os.path.basename(eml_path), "from": f"{p.from_name} <{p.from_addr}>".strip(),
            "date": p.date_str, "AI": ai_used, "network lookups": "on" if network else "off"}
    return Report(tier, reason, findings, claims, sources, build_questions(claims, findings),
                  build_draft(claims, p), meta)
