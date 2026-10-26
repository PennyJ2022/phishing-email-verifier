import http.client
import ipaddress
import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request

from .constants import UA, URL_RE
from .helpers import host_of
from .models import Finding


class NetError(Exception):
    pass


def _public_sockaddrs(host: str, port: int):
    try:
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise NetError(f"Could not resolve {host}: {e}") from None
    if not records or any(not ipaddress.ip_address(record[4][0]).is_global for record in records):
        raise NetError("The URL must resolve only to public IP addresses.")
    return records


def _connect_public(host: str, port: int, timeout, source_address=None):
    records = _public_sockaddrs(host, port)
    errors = []
    for family, socktype, proto, _, sockaddr in records:
        sock = socket.socket(family, socktype, proto)
        try:
            if source_address:
                sock.bind(source_address)
            sock.settimeout(timeout)
            sock.connect(sockaddr)
            return sock
        except OSError as e:
            errors.append(e)
            sock.close()
    raise OSError(f"Could not connect to {host}: {errors[-1]}")


def _validate_public_url(url: str) -> None:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        raise NetError("Only public HTTP or HTTPS URLs are allowed.")
    if parts.username or parts.password:
        raise NetError("URLs containing user credentials are not allowed.")
    try:
        port = parts.port or (443 if parts.scheme.lower() == "https" else 80)
    except ValueError:
        raise NetError("The URL has an invalid port.") from None
    if port not in (80, 443):
        raise NetError("Only standard HTTP and HTTPS ports are allowed.")

    host = parts.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".localhost", ".local")):
        raise NetError("Local network destinations are not allowed.")
    _public_sockaddrs(host, port)


class _PublicHTTPConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = _connect_public(self.host, self.port, self.timeout, self.source_address)
        if self._tunnel_host:
            self._tunnel()


class _PublicHTTPSConnection(http.client.HTTPSConnection):
    def connect(self):
        self.sock = _connect_public(self.host, self.port, self.timeout, self.source_address)
        if self._tunnel_host:
            self._tunnel()
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self._tunnel_host or self.host)


class _PublicHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(_PublicHTTPConnection, req)


class _PublicHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_PublicHTTPSConnection, req, context=self._context,
                            check_hostname=self._check_hostname)


class _PublicRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _get(url: str, accept: str = "*/*", timeout: int = 15, max_bytes: int = 600_000,
         safe_public: bool = False) -> str:
    if safe_public:
        _validate_public_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    try:
        opener = (urllib.request.build_opener(urllib.request.ProxyHandler({}), _PublicHTTPHandler(),
                                              _PublicHTTPSHandler(), _PublicRedirectHandler())
                  if safe_public else urllib.request)
        with opener.urlopen(req, timeout=timeout) as r:
            return r.read(max_bytes).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise NetError(f"HTTP {e.code} for {host_of(url)}") from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise NetError(f"{host_of(url)}: {getattr(e, 'reason', e)}") from None


def _get_json(url: str, accept: str = "application/json"):
    body = _get(url, accept).strip()
    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        raise NetError(f"{host_of(url)}: response was not JSON") from None


def _parse_date(s: str):
    import datetime as dt
    try:
        d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except (ValueError, AttributeError):
        return None


def rdap_domain(domain: str) -> dict:
    data = _get_json(f"https://rdap.org/domain/{urllib.parse.quote(domain)}", "application/rdap+json") or {}
    ev = {e.get("eventAction"): e.get("eventDate") for e in data.get("events", [])}
    registrar = ""
    for ent in data.get("entities", []):
        if "registrar" in ent.get("roles", []):
            for item in (ent.get("vcardArray") or [None, []])[1]:
                if item and item[0] == "fn":
                    registrar = item[3]
    blob = json.dumps(data).lower()
    return {"created": _parse_date(ev.get("registration", "")), "expires": _parse_date(ev.get("expiration", "")),
            "updated": _parse_date(ev.get("last changed", "")), "registrar": registrar,
            "privacy": any(w in blob for w in ("privacy", "proxy", "redacted"))}


def doh(name: str, rtype: str) -> list:
    data = _get_json(f"https://dns.google/resolve?name={urllib.parse.quote(name)}&type={rtype}",
                     "application/dns-json") or {}
    return [a.get("data", "") for a in data.get("Answer", [])]


def wayback_first(domain: str):
    import datetime as dt
    body = _get(f"https://web.archive.org/cdx/search/cdx?url={urllib.parse.quote(domain)}&limit=1"
                f"&output=json&fl=timestamp", "application/json").strip()
    if not body:
        return None
    try:
        rows = json.loads(body)
    except json.JSONDecodeError:
        return None
    if len(rows) < 2:
        return None
    return dt.datetime.strptime(rows[1][0][:8], "%Y%m%d").replace(tzinfo=dt.timezone.utc)


def check_domain(domain: str) -> list:
    import datetime as dt
    out = []
    if not domain:
        return out
    from .constants import FREEMAIL, NEW_DAYS, VERY_NEW_DAYS
    now = dt.datetime.now(dt.timezone.utc)
    try:
        r = rdap_domain(domain)
        if r["created"]:
            age = (now - r["created"]).days
            detail = f"registered {r['created']:%Y-%m-%d}, registrar {r['registrar'] or 'unknown'}"
            if r["expires"]:
                detail += f", expires {r['expires']:%Y-%m-%d}"
            if r["privacy"]:
                detail += ", owner hidden by a privacy service (normal)"
            if age < VERY_NEW_DAYS:
                out.append(Finding("domain", "fail", f"Domain is only {age} days old.", detail))
            elif age < NEW_DAYS:
                out.append(Finding("domain", "warn", f"Domain is under a year old ({age} days).", detail))
            else:
                out.append(Finding("domain", "pass", f"Domain is {age // 365} year(s) old.", detail, key="domain_age_ok"))
        else:
            out.append(Finding("domain", "info", "RDAP returned no registration date."))
    except NetError as e:
        out.append(Finding("domain", "info", f"Domain registration lookup failed: {e}"))
    try:
        mx = doh(domain, "MX")
        if not mx:
            out.append(Finding("domain", "warn", "Sender domain has no mail (MX) records.", domain))
        spf = [t for t in doh(domain, "TXT") if "v=spf1" in t]
        dmarc = [t for t in doh("_dmarc." + domain, "TXT") if "DMARC1" in t.upper()]
        out.append(Finding("domain", "info", f"DNS: MX {'present' if mx else 'missing'}, "
                           f"SPF {'present' if spf else 'missing'}, DMARC {'present' if dmarc else 'missing'}",
                           dmarc[0][:80] if dmarc else ""))
    except NetError as e:
        out.append(Finding("domain", "info", f"DNS lookup failed: {e}"))
    try:
        first = wayback_first(domain)
        if first is None:
            out.append(Finding("domain", "warn", "No Wayback Machine history for this domain.", domain))
        else:
            yrs = (now - first).days / 365
            out.append(Finding("domain", "pass" if yrs >= 1 else "info",
                               f"Wayback Machine first saw the site on {first:%Y-%m-%d}.", ""))
    except NetError as e:
        out.append(Finding("domain", "info", f"Wayback lookup failed: {e}"))
    return out


def fetch_company_text(url: str, email_urls: list) -> tuple:
    if not re.match(r"https?://", url, re.I):
        url = "https://" + url
    norm = lambda u: u.rstrip("/").lower()
    if norm(url) in {norm(u) for u in email_urls}:
        return "", ["Refused: that URL appears in the email. Type the company's own address yourself."]
    parts = urllib.parse.urlsplit(url)
    base = f"{parts.scheme}://{parts.netloc}"
    candidates = [url] + ([base + "/careers", base + "/jobs"] if parts.path in ("", "/") else [])
    texts, notes = [], []
    for u in candidates:
        try:
            raw = _get(u, "text/html,text/plain", max_bytes=400_000, safe_public=True)
        except NetError as e:
            notes.append(f"Could not fetch {u}: {e}")
            continue
        from .parsing import html_parse
        t, _, _ = html_parse(raw) if "<" in raw[:2000] else (raw, [], [])
        if len(t) < 300:
            notes.append(f"{u} returned little text; it may be rendered by JavaScript. Copy the listing text into a file and use --page-file.")
        texts.append(f"[source: {u}]\n{t}")
    return "\n".join(texts), notes
