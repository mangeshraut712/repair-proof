"""Bound first, then redact. Not a general-purpose secret detector."""
import re

# Quoted values can contain spaces or escaped quotes and may be truncated.
_SECRET_VALUE = (
    r"(?:\"(?:\\(?:[\s\S]|$)|[^\"\\])*(?:\"|$)|"
    r"'(?:\\(?:[\s\S]|$)|[^'\\])*(?:'|$)|[^\s,;\"'])+"
)


def evidence(raw: str) -> list[dict[str,str]]:
    raw = raw[:24000]
    raw = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', raw)
    raw = re.sub(
        r"([\"']?(?:[\w-]*(?:key|token|secret|password)[\w-]*|"
        r"(?:proxy-)?authorization)[\"']?\s*[:=]\s*)"
        r"(?:(?:Bearer|Basic)\s+)?" + _SECRET_VALUE,
        r'\1[REDACTED]', raw, flags=re.IGNORECASE,
    )
    raw = re.sub(r'(bearer\s+)' + _SECRET_VALUE, r'\1[REDACTED]', raw, flags=re.IGNORECASE)
    raw = re.sub(r'https?://[^\s/@]+:[^\s/@]+@', 'https://[REDACTED]@', raw)
    raw = re.sub(r'(?i)(?:https?://)?hooks\.slack\.com/services/[A-Za-z0-9]+/[A-Za-z0-9]+/[A-Za-z0-9]+', '[REDACTED]', raw)
    raw = re.sub(r'\b(?:(?:sk-|gh[pousr]_|github_pat_|npm_|hf_|glpat-|xox[bapecs]-|gsk_|xai-|sk_live_|sk_test_|dop_v1_|pypi-|sntrys_|whsec_|rk_live_|rk_test_|xoxs-|xapp-)[A-Za-z0-9_-]+|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z\-_]{20,})', '[REDACTED]', raw)
    return [{'id':f'L{i:03d}','text':''.join(c for c in line if c.isprintable())[:300]} for i,line in enumerate(raw.splitlines()[:80],1)]
