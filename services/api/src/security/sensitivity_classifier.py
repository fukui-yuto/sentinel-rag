"""Document sensitivity classification based on DLP findings and metadata."""

from src.security.dlp_scanner import DLPFinding, classify_sensitivity, scan_text


def classify_document(
    text: str,
    filename: str = "",
    manual_override: str | None = None,
) -> tuple[str, list[DLPFinding]]:
    """Classify a document's sensitivity level.

    Returns:
        (sensitivity_level, dlp_findings)
    """
    if manual_override:
        return manual_override, []

    findings = scan_text(text)
    auto_sensitivity = classify_sensitivity(findings)

    # Filename-based heuristics
    lower_name = filename.lower()
    if any(kw in lower_name for kw in ("confidential", "機密", "secret", "restricted")):
        if auto_sensitivity in ("public", "internal"):
            auto_sensitivity = "confidential"

    return auto_sensitivity, findings
