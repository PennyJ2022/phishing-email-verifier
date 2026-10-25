import urllib.parse

from .constants import SECOND_LEVEL


def registrable(host: str) -> str:
    host = (host or "").lower().strip(".")
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    last2 = ".".join(labels[-2:])
    if last2 in SECOND_LEVEL:
        return ".".join(labels[-3:])
    return last2


def same_org(a: str, b: str) -> bool:
    return bool(a) and bool(b) and registrable(a) == registrable(b)


def host_of(url: str) -> str:
    try:
        return (urllib.parse.urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def is_tracker(host: str) -> bool:
    from .constants import TRACKER_HINTS
    return any(h in host for h in TRACKER_HINTS)


def addr_domain(addr: str) -> str:
    return addr.rsplit("@", 1)[-1].lower().strip(">") if "@" in addr else ""
