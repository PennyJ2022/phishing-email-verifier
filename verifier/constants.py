import re

UA = "Mozilla/5.0 (compatible; recruiter-verifier/0.1)"
URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.I)
PAY_RE = re.compile(r"\$\s?(\d{2,3})(?:,\d{3})?\s?[kK]?\s?(?:-|\u2013|\u2014|to)\s?\$?\s?(\d{2,3})(?:,\d{3})?\s?[kK]?")
TITLE_RE = re.compile(
    r"((?:(?:Senior|Sr\.?|Staff|Principal|Lead|Head of)\s+)*(?:Tech Lead(?: Manager)?|Engineering Manager|"
    r"(?:Software|Backend|Back-end|Frontend|Front-end|Full[- ]Stack|Data|Platform|DevOps|ML|AI) Engineer|"
    r"Staff Engineer|Principal Engineer|Director of Engineering|VP of Engineering|Developer))",
    re.I,
)
CAPITALIZED_PHRASE_RE = r"([A-Z][\w&.\-]*(?:\s+[A-Z][\w&.\-]*){0,3})"

FREEMAIL = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "yahoo.com",
    "icloud.com", "proton.me", "protonmail.com", "aol.com", "gmx.com", "mail.com", "qq.com", "163.com",
}
SECOND_LEVEL = {"co.uk", "org.uk", "ac.uk", "com.au", "net.au", "co.jp", "com.br", "co.in", "co.nz",
                "com.cn", "co.za", "com.mx", "com.sg"}
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "buff.ly", "rebrand.ly", "cutt.ly",
              "is.gd", "lnkd.in", "shorturl.at", "tiny.cc"}
TRACKER_HINTS = ("tracking", "track.", "click.", "clicks.", "links.", "trk.", "redirect", "nylas.com",
                "sendgrid.net", "list-manage.com", "mandrillapp.com", "mailgun.org", "hubspotlinks.com",
                "hubspotemail.net", "sparkpostmail.com", "brevo.com", "mailjet.com", "customeriomail.com",
                "ct.sendgrid.net", "e.mail.", "email.mg.")
AUTOMATION_HEADERS = ("x-nylas", "x-mailgun", "x-sg-", "x-mailchimp", "x-campaign", "x-mandrill",
                      "x-sendgrid", "x-jbx", "x-mailer-campaign", "list-unsubscribe")
DANGEROUS_EXT = (".exe", ".scr", ".js", ".vbs", ".iso", ".docm", ".xlsm", ".bat", ".cmd", ".jar", ".lnk")
VERY_NEW_DAYS = 60
NEW_DAYS = 365
