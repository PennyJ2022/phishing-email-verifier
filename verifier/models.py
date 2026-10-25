import dataclasses


@dataclasses.dataclass
class Finding:
    area: str
    status: str
    message: str
    evidence: str = ""
    key: str = ""


@dataclasses.dataclass
class Link:
    href: str
    text: str = ""


@dataclasses.dataclass
class ParsedEmail:
    subject: str = ""
    date_str: str = ""
    from_name: str = ""
    from_addr: str = ""
    from_domain: str = ""
    return_path_domain: str = ""
    reply_to_domain: str = ""
    recipient_addrs: list = dataclasses.field(default_factory=list)
    recipient_names: list = dataclasses.field(default_factory=list)
    auth: dict = dataclasses.field(default_factory=dict)
    dkim_domains: list = dataclasses.field(default_factory=list)
    automation_headers: list = dataclasses.field(default_factory=list)
    attachments: list = dataclasses.field(default_factory=list)
    text: str = ""
    links: list = dataclasses.field(default_factory=list)
    images: list = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Report:
    tier: str
    tier_reason: str
    findings: list
    claims: dict
    claim_sources: dict
    questions: list
    draft_message: str
    meta: dict

    def to_markdown(self) -> str:
        def esc(s: str) -> str:
            return str(s).replace("|", "\\|").replace("\n", " ")

        L = ["# Recruiter email check", "",
             f"**Verdict: {self.tier}** - {self.tier_reason}", "",
             "This is evidence, not proof. Confirm any role with the company through its own website or "
             "contact details, never through links in the email.", ""]
        for k, v in self.meta.items():
            L.append(f"- {k}: {v}")
        L += ["", "## Evidence", "", "| Status | Area | Finding | Evidence |", "|---|---|---|---|"]
        order = {"fail": 0, "warn": 1, "info": 2, "pass": 3}
        for f in sorted(self.findings, key=lambda x: order.get(x.status, 9)):
            L.append(f"| {f.status.upper()} | {f.area} | {esc(f.message)} | {esc(f.evidence)} |")
        L += ["", "## Claims in the email", ""]
        for k, v in self.claims.items():
            if k in ("asks", "concerns"):
                v = "; ".join(v) if v else None
            src = self.claim_sources.get(k, "")
            L.append(f"- {k}: {v if v else 'not found'}" + (f" ({src})" if v and src else ""))
        L += ["", "## Questions to ask the recruiter", ""] + [f"{i}. {q}" for i, q in enumerate(self.questions, 1)]
        L += ["", "## Draft message to the company", "", "```", self.draft_message, "```", "",
              "## Checks this tool cannot do for you", "",
              "- Find the recruiter on LinkedIn with the agency as employer (automating LinkedIn is not reliable).",
              "- Check the agency's own website for named people, an address and a phone number.",
              "- Ask the company directly whether the agency is authorized.",
              "- Do not click links in the email. Do not send ID numbers or bank details at any stage.", ""]
        return "\n".join(L)
