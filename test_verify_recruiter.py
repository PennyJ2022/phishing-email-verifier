"""Offline tests for verify_recruiter.py. Run: python -m unittest test_verify_recruiter -v

All emails here are made up. No test touches the network.
"""
import json
import os
import tempfile
import unittest
from unittest import mock

import verify_recruiter as vr

LEGIT_STYLE = """\
Authentication-Results: mx.example.net; spf=pass smtp.mailfrom=acme-recruit.example;
 dkim=pass header.d=acme-recruit.example; dmarc=pass header.from=acme-recruit.example
DKIM-Signature: v=1; a=rsa-sha256; d=acme-recruit.example; s=google; b=abc
x-nylas-send-v3: true
Return-Path: alex@acme-recruit.example
From: Alex Doe <alex@acme-recruit.example>
To: Taylor Smith <taylor.smith@example.org>
Subject: Taylor, interested in a new opportunity?
Date: Thu, 22 Oct 2026 21:25:31 -0700
MIME-Version: 1.0
Content-Type: multipart/alternative; boundary="b1"

--b1
Content-Type: text/plain; charset="UTF-8"
Content-Transfer-Encoding: 8bit

Hi Taylor,

I'm reaching out from Acme Recruit about a Tech Lead opportunity with Widgetly
<https://tracking.us.nylas.com/l/abc123/0/def456>.

A few highlights:
* $250K\u2013$300K base + meaningful equity
* Senior Individual Contributor role \u2014 no people management
* The team is actively interviewing and moving quickly

If you're open to hearing more, send me your latest resume.

Best,
Alex
--b1
Content-Type: text/html; charset="UTF-8"
Content-Transfer-Encoding: 8bit

<p>Hi Taylor,</p><p>I'm reaching out from Acme Recruit about a Tech Lead opportunity with
<a href="https://tracking.us.nylas.com/l/abc123/0/def456">Widgetly</a>.</p>
<a href="https://tracking.us.nylas.com/l/abc123/1/ghi789">Unsubscribe</a>
<img width="1" height="1" alt="tracking" src="https://tracking.us.nylas.com/o/pixel123" style="display:none">
--b1--
"""

SUSPICIOUS = """\
Authentication-Results: mx.example.net; spf=fail smtp.mailfrom=gmail.com; dkim=none; dmarc=fail header.from=gmail.com
From: Widgetly HR <hr.widgetly@gmail.com>
Reply-To: hiring@proton.me
To: taylor.smith@example.org
Subject: URGENT job offer
Date: Thu, 22 Oct 2026 21:25:31 -0700
MIME-Version: 1.0
Content-Type: text/html; charset="UTF-8"

<p>Congratulations! Please send your SSN and bank account number so we can set up payroll.
Reply on Telegram immediately. Details: <a href="http://bit.ly/abc">www.widgetly.com/jobs</a></p>
"""


class FakeLLM:
    provider = "fake"

    def __init__(self):
        self.calls = []

    def complete(self, system, user, max_tokens=1500):
        self.calls.append((system, user))
        if system == vr.EXTRACT_SYSTEM:
            return json.dumps({"company": "Widgetly", "title": "Tech Lead", "role_type": "individual_contributor",
                               "location": "Remote", "pay_range": None, "asks": ["send resume"], "concerns": []})
        return "```json\n" + json.dumps({
            "role_found": True,
            "findings": [
                {"field": "title", "email_claim": "Tech Lead", "page_evidence": "Tech Lead, Platform", "verdict": "match"},
                {"field": "location", "email_claim": "Remote", "page_evidence": "Fully remote anywhere on Mars",
                 "verdict": "match"}],
            "notes": "ok"}) + "\n```"


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.legit = self._write("legit.eml", LEGIT_STYLE)
        self.bad = self._write("bad.eml", SUSPICIOUS)

    def tearDown(self):
        self.dir.cleanup()

    def _write(self, name, content):
        path = os.path.join(self.dir.name, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path


class TestChecks(Base):
    @mock.patch.object(vr, "check_domain")
    def test_network_is_off_by_default(self, check_domain):
        report = vr.verify_recruiter_email(self.legit)
        check_domain.assert_not_called()
        self.assertEqual(report.meta["network lookups"], "off")

    def test_headers_pass_but_flagged_as_not_proof(self):
        f = vr.check_headers(vr.parse_eml(self.legit))
        auth = [x for x in f if x.key == "auth_pass"]
        self.assertEqual(len(auth), 1)
        self.assertIn("not that they are a legitimate recruiter", auth[0].message)
        self.assertTrue(any("outreach" in x.message for x in f))

    def test_claims_rules(self):
        c, src = vr.extract_claims(vr.parse_eml(self.legit))
        self.assertEqual(c["company"], "Widgetly")
        self.assertEqual(c["agency"], "Acme Recruit")
        self.assertEqual(c["title"], "Tech Lead")
        self.assertEqual(c["role_type"], "individual_contributor")
        self.assertIn("250", c["pay_range"])
        self.assertEqual(src["company"], "rules")

    def test_links_trackers_and_pixel(self):
        f = vr.check_links(vr.parse_eml(self.legit))
        self.assertTrue(any("tracking or redirect" in x.message for x in f))
        self.assertTrue(any("tracking pixel" in x.message for x in f))
        self.assertFalse(any(x.status == "fail" for x in f))

    def test_suspicious_email_is_flagged(self):
        r = vr.verify_recruiter_email(self.bad, network=False)
        self.assertEqual(r.tier, "SUSPICIOUS")
        msgs = " ".join(f.message for f in r.findings if f.status == "fail")
        self.assertIn("DMARC failed", msgs)
        self.assertIn("identity", msgs)
        self.assertTrue(any("Telegram" in f.evidence or "messaging" in f.message for f in r.findings))
        self.assertTrue(any("shortener" in f.message for f in r.findings))

    def test_offline_run_never_exceeds_unverified(self):
        r = vr.verify_recruiter_email(self.legit, network=False)
        self.assertEqual(r.tier, "UNVERIFIED")
        self.assertIn("domain age", r.tier_reason)
        self.assertIn("# Recruiter email check", r.to_markdown())


class TestPrivacy(Base):
    def test_redaction_removes_recipient_and_links(self):
        p = vr.parse_eml(self.legit)
        out = vr.redact(p.subject + "\n" + p.text, p)
        for bad in ("taylor", "Taylor", "Smith", "example.org", "https://", "def456"):
            self.assertNotIn(bad, out)
        self.assertIn("[link:tracking.us.nylas.com]", out)

    def test_packet_is_redacted(self):
        p = vr.parse_eml(self.legit)
        c, _ = vr.extract_claims(p)
        packet = vr.build_prompt_packet(p, c)
        self.assertNotIn("taylor.smith", packet.lower())
        self.assertNotIn("https://", packet)

    def test_refuses_to_fetch_url_found_in_email(self):
        p = vr.parse_eml(self.legit)
        urls = [l.href for l in p.links]
        text, notes = vr.fetch_company_text(urls[0], urls)
        self.assertEqual(text, "")
        self.assertIn("Refused", notes[0])

    def test_refuses_private_company_page_destination(self):
        with mock.patch.object(vr.urllib.request, "build_opener") as build_opener:
            text, notes = vr.fetch_company_text("http://127.0.0.1", [])
        self.assertEqual(text, "")
        self.assertIn("public IP", notes[0])
        build_opener.assert_not_called()

    def test_refuses_hostnames_resolving_to_private_addresses(self):
        private_record = (vr.socket.AF_INET, vr.socket.SOCK_STREAM, 6, "", ("10.0.0.8", 443))
        with mock.patch.object(vr.socket, "getaddrinfo", return_value=[private_record]):
            with self.assertRaises(vr.NetError):
                vr._validate_public_url("https://internal.example/")


class TestCrosscheck(Base):
    claims = {"company": "Widgetly", "title": "Tech Lead", "role_type": "individual_contributor", "pay_range": None}

    def test_manager_title_conflicts_with_ic_claim(self):
        page = "Widgetly careers\nTech Lead Manager, Integration\nSan Francisco, full-time"
        f = vr.crosscheck_heuristic(self.claims, page)
        self.assertTrue(any(x.key == "role_mismatch" for x in f))
        self.assertFalse(any(x.key == "role_confirmed" for x in f))

    def test_clean_match_confirms_role(self):
        page = "Widgetly careers\nTech Lead, Platform (individual contributor)\nRemote"
        f = vr.crosscheck_heuristic(self.claims, page)
        self.assertTrue(any(x.key == "role_confirmed" for x in f))

    def test_wrong_company_page_is_warned(self):
        f = vr.crosscheck_heuristic(self.claims, "Other Corp\nTech Lead, Platform")
        self.assertTrue(any("does not appear" in x.message for x in f))

    def test_likely_legit_requires_all_signals(self):
        good = [vr.Finding("h", "pass", "a", key="auth_pass"), vr.Finding("d", "pass", "b", key="domain_age_ok"),
                vr.Finding("c", "pass", "c", key="role_confirmed")]
        self.assertEqual(vr.decide_tier(good)[0], "LIKELY LEGIT")
        self.assertEqual(vr.decide_tier(good[:2])[0], "UNVERIFIED")
        self.assertEqual(vr.decide_tier(good + [vr.Finding("x", "fail", "bad")])[0], "SUSPICIOUS")


class TestAI(Base):
    def test_ai_off_by_default_never_builds_a_model(self):
        original = vr.LLM
        vr.LLM = lambda *a, **k: self.fail("an AI backend was created while ai was off")
        try:
            r = vr.verify_recruiter_email(self.legit, network=False)
        finally:
            vr.LLM = original
        self.assertEqual(r.meta["AI"], "off")

    def test_ai_path_with_fake_model_and_quote_check(self):
        page_path = self._write("page.txt", "Widgetly careers\nTech Lead, Platform\nRemote")
        llm = FakeLLM()
        r = vr.verify_recruiter_email(self.legit, network=False, llm=llm, page_file=page_path,
                                      confirm_send=lambda provider, data_kind, size: True)
        self.assertEqual(len(llm.calls), 2)
        self.assertEqual(r.claim_sources["location"], "AI: fake")
        ai = [f for f in r.findings if f.area == "crosscheck-ai"]
        self.assertTrue(any(f.key == "role_confirmed" for f in ai))
        # The invented quote must be ignored, not trusted.
        self.assertTrue(any("not found on the page" in f.message for f in ai))
        # What was sent to the model contains no recipient details or URLs.
        sent = llm.calls[0][1]
        self.assertNotIn("taylor", sent.lower())
        self.assertNotIn("https://", sent)

    def test_ai_requires_explicit_confirmation_callback(self):
        llm = FakeLLM()
        report = vr.verify_recruiter_email(self.legit, network=False, llm=llm)
        self.assertEqual(llm.calls, [])
        self.assertTrue(any("confirmation was not provided" in f.message for f in report.findings))

    def test_prompt_injection_text_is_only_data(self):
        self.assertIn("never follow", vr.EXTRACT_SYSTEM)
        self.assertIn("never follow", vr.CROSS_SYSTEM)

    def test_bad_json_from_model_falls_back_to_rules(self):
        class Broken(FakeLLM):
            def complete(self, system, user, max_tokens=1500):
                return "sorry, no JSON here"
        r = vr.verify_recruiter_email(self.legit, network=False, llm=Broken(),
                          confirm_send=lambda provider, data_kind, size: True)
        self.assertTrue(any(f.area == "ai" and "failed" in f.message for f in r.findings))
        self.assertEqual(r.claims["company"], "Widgetly")

    def test_confirm_callback_can_block_sending(self):
        llm = FakeLLM()
        vr.verify_recruiter_email(self.legit, network=False, llm=llm,
                      confirm_send=lambda provider, data_kind, size: False)
        self.assertEqual(llm.calls, [])


class TestSearch(unittest.TestCase):
    def test_search_requires_confirmation_and_uses_only_approved_terms(self):
        calls = []
        approved = []

        def search(query):
            calls.append(query)
            return [{"title": "Careers", "url": "https://widgetly.example/careers"}]

        def confirm(provider, details, size):
            approved.append((provider, details, size))
            return True

        results = vr.search_company_role(
            {"company": "Widgetly", "title": "Tech Lead", "location": None},
            search_fn=search,
            confirm=confirm,
        )
        self.assertTrue(results)
        self.assertEqual(len(calls), 4)
        self.assertEqual(approved[0][0], "DuckDuckGo")
        self.assertEqual(approved[0][2], len(approved[0][1]))
        self.assertTrue(all("Widgetly" in query or "Tech Lead" in query for query in calls))

    def test_search_does_not_run_without_approval(self):
        calls = []
        results = vr.search_company_role(
            {"company": "Widgetly"},
            search_fn=lambda query: calls.append(query) or [],
        )
        self.assertIsNone(results)
        self.assertEqual(calls, [])

    def test_search_skips_if_no_company_role_terms(self):
        calls = []
        results = vr.search_company_role({}, search_fn=lambda query: calls.append(query) or [])
        self.assertEqual(results, [])
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
