"""DLP scanner tests."""

from src.security.dlp_scanner import classify_sensitivity, luhn_check, scan_text


def test_luhn_valid():
    assert luhn_check("4111111111111111") is True


def test_luhn_invalid():
    assert luhn_check("4111111111111112") is False


def test_scan_credit_card():
    text = "Card number: 4111111111111111"
    findings = scan_text(text)
    names = {f.pattern_name for f in findings}
    assert "credit_card" in names


def test_scan_email():
    text = "Contact: user@example.com for info"
    findings = scan_text(text)
    names = {f.pattern_name for f in findings}
    assert "email_address" in names


def test_scan_api_key():
    text = "token: sk-abc123def456ghi789jkl012mno345pqr678"
    findings = scan_text(text)
    names = {f.pattern_name for f in findings}
    assert "api_key" in names


def test_scan_no_findings():
    text = "This is a normal document with no sensitive data."
    findings = scan_text(text)
    assert len(findings) == 0


def test_classify_critical():
    findings = scan_text("Card: 4111111111111111")
    result = classify_sensitivity(findings)
    assert result == "restricted"


def test_classify_no_findings():
    result = classify_sensitivity([])
    assert result == "internal"
