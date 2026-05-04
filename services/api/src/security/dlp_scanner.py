"""DLP (Data Loss Prevention) scanner for detecting sensitive information."""

import re
from dataclasses import dataclass


@dataclass
class DLPFinding:
    pattern_name: str
    matched_text: str
    position: int
    severity: str  # low, medium, high, critical


# Japanese personal information patterns
PATTERNS: list[tuple[str, str, str]] = [
    # My Number (Individual Number) - 12 digits
    (r"\b\d{4}\s?\d{4}\s?\d{4}\b", "my_number", "critical"),
    # Credit card numbers (Luhn-checkable)
    (r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b", "credit_card", "critical"),
    # Japanese phone numbers
    (r"\b0[0-9]{1,4}-?[0-9]{1,4}-?[0-9]{4}\b", "phone_number", "medium"),
    # Email addresses
    (r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", "email_address", "medium"),
    # Japanese postal codes
    (r"\b\d{3}-?\d{4}\b", "postal_code", "low"),
    # API keys / tokens (generic pattern)
    (r"\b(?:sk-|pk_|api[_-]?key|token)[a-zA-Z0-9_\-]{20,}\b", "api_key", "critical"),
    # AWS access keys
    (r"\bAKIA[0-9A-Z]{16}\b", "aws_access_key", "critical"),
    # Private key markers
    (r"-----BEGIN\s(?:RSA\s)?PRIVATE KEY-----", "private_key", "critical"),
    # Password patterns
    (r"(?i)(?:password|passwd|pwd)\s*[:=]\s*\S+", "password", "high"),
    # Driver's license numbers (Japan - 12 digits)
    (r"\b\d{12}\b", "drivers_license_candidate", "medium"),
    # Basic Resident Register Code (Japan - 11 digits)
    (r"\b\d{11}\b", "juki_code_candidate", "medium"),
]

# Compiled patterns
_COMPILED = [(re.compile(p), name, sev) for p, name, sev in PATTERNS]


def luhn_check(number: str) -> bool:
    """Validate a credit card number using the Luhn algorithm."""
    digits = [int(d) for d in number if d.isdigit()]
    if len(digits) < 13:
        return False
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def scan_text(text: str) -> list[DLPFinding]:
    """Scan text for sensitive information patterns."""
    findings: list[DLPFinding] = []
    seen_positions: set[tuple[int, int]] = set()

    for pattern, name, severity in _COMPILED:
        for match in pattern.finditer(text):
            pos = (match.start(), match.end())
            if pos in seen_positions:
                continue

            matched = match.group()

            # Extra validation for credit cards
            if name == "credit_card" and not luhn_check(matched):
                continue

            # Skip overly short postal-code false positives
            if name == "postal_code" and len(matched.replace("-", "")) != 7:
                continue

            seen_positions.add(pos)
            findings.append(DLPFinding(
                pattern_name=name,
                matched_text=matched[:10] + "***",  # Redact
                position=match.start(),
                severity=severity,
            ))

    return findings


def classify_sensitivity(findings: list[DLPFinding]) -> str:
    """Determine document sensitivity based on DLP findings."""
    if not findings:
        return "internal"

    max_severity = max(f.severity for f in findings)
    severity_map = {
        "critical": "restricted",
        "high": "confidential",
        "medium": "internal",
        "low": "internal",
    }
    return severity_map.get(max_severity, "internal")
