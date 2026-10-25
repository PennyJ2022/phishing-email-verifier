import email
import re
from html.parser import HTMLParser

from email import policy
from email.utils import getaddresses, parseaddr

from .constants import AUTOMATION_HEADERS, URL_RE
from .helpers import addr_domain, host_of
from .models import Link, ParsedEmail


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.images, self.parts = [], [], []
        self._href, self._buf, self._skip = None, [], 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style"):
            self._skip += 1
        elif tag == "a" and a.get("href"):
            self._href, self._buf = a["href"], []
        elif tag == "img":
            self.images.append(a)
        if tag in ("br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        elif tag == "a" and self._href is not None:
            self.links.append(Link(self._href, "".join(self._buf).strip()))
            self._href = None
        if tag in ("p", "div", "li", "tr"):
            self.parts.append("\n")

    def handle_data(self, data):
        if self._skip:
            return
        self.parts.append(data)
        if self._href is not None:
            self._buf.append(data)


def html_parse(html_text: str):
    p = _TextParser()
    try:
        p.feed(html_text)
    except Exception:
        pass
    text = re.sub(r"[ \t\r\f\v]+", " ", "".join(p.parts))
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    return text, p.links, p.images


def parse_eml(path: str) -> ParsedEmail:
    with open(path, "rb") as fh:
        msg = email.message_from_binary_file(fh, policy=policy.default)
    p = ParsedEmail()
    p.subject = str(msg.get("Subject", ""))
    p.date_str = str(msg.get("Date", ""))
    p.from_name, p.from_addr = parseaddr(str(msg.get("From", "")))
    p.from_domain = addr_domain(p.from_addr)
    p.return_path_domain = addr_domain(parseaddr(str(msg.get("Return-Path", "")))[1])
    p.reply_to_domain = addr_domain(parseaddr(str(msg.get("Reply-To", "")))[1])

    recips = []
    for h in ("To", "Cc", "Delivered-To", "X-Original-To", "Envelope-To"):
        recips += getaddresses([str(v) for v in msg.get_all(h, [])])
    p.recipient_addrs = sorted({a.lower() for _, a in recips if a})
    p.recipient_names = sorted({n for n, _ in recips if n})

    auth = {"spf": None, "dkim": None, "dmarc": None}
    headers = [str(h) for h in msg.get_all("Authentication-Results", [])]
    headers += [str(h) for h in msg.get_all("ARC-Authentication-Results", [])]
    for h in headers:
        for k in auth:
            if auth[k] is None:
                m = re.search(rf"\b{k}=(\w+)", h, re.I)
                if m:
                    auth[k] = m.group(1).lower()
    if auth["spf"] is None:
        m = re.match(r"\s*(\w+)", str(msg.get("Received-SPF", "")))
        if m:
            auth["spf"] = m.group(1).lower()
    p.auth = auth
    for sig in msg.get_all("DKIM-Signature", []):
        m = re.search(r"\bd=([^;\s]+)", str(sig))
        if m:
            p.dkim_domains.append(m.group(1).lower())
    p.automation_headers = sorted({k for k in msg.keys() if any(k.lower().startswith(a) for a in AUTOMATION_HEADERS)})

    text_parts, html_parts = [], []
    for part in msg.walk():
        disp = part.get_content_disposition()
        fn = part.get_filename()
        if fn:
            p.attachments.append(fn)
        if disp == "attachment":
            continue
        ct = part.get_content_type()
        if ct in ("text/plain", "text/html"):
            try:
                content = part.get_content()
            except Exception:
                content = (part.get_payload(decode=True) or b"").decode("utf-8", "replace")
            (text_parts if ct == "text/plain" else html_parts).append(content)

    links, images, html_text = [], [], ""
    for h in html_parts:
        t, l, i = html_parse(h)
        html_text += t + "\n"
        links += l
        images += i
    plain = "\n".join(text_parts).strip()
    p.text = plain or html_text.strip()
    seen = {l.href for l in links}
    for u in URL_RE.findall(plain):
        u = u.rstrip(".,;")
        if u not in seen:
            links.append(Link(u, ""))
            seen.add(u)
    p.links, p.images = links, images
    return p


def redact(text: str, p: ParsedEmail) -> str:
    out = text
    for addr in p.recipient_addrs:
        local = addr.split("@")[0]
        out = re.sub(re.escape(addr), "[RECIPIENT_EMAIL]", out, flags=re.I)
        if len(local) >= 4:
            out = re.sub(re.escape(local), "[RECIPIENT]", out, flags=re.I)
    for name in p.recipient_names:
        for part in [name] + name.split():
            if len(part) >= 3:
                out = re.sub(rf"\b{re.escape(part)}\b", "[RECIPIENT]", out, flags=re.I)
    out = URL_RE.sub(lambda m: f"[link:{host_of(m.group(0))}]", out)
    return re.sub(r"\n{3,}", "\n\n", out).strip()
