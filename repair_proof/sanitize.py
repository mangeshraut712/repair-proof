"""Bound first, then redact. Not a general-purpose secret detector."""
import re

def evidence(raw: str) -> list[dict[str,str]]:
    raw = raw[:24000]
    raw = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', raw)
    raw = re.sub(r'(?i)(bearer\s+)[^\s]+', r'\1[REDACTED]', raw)
    raw = re.sub(r'(?i)((?:[\w-]*(?:key|token|secret|password)[\w-]*)\s*[:=]\s*)[^\s,;]+', r'\1[REDACTED]', raw)
    raw = re.sub(r'https?://[^\s/@]+:[^\s/@]+@', 'https://[REDACTED]@', raw)
    raw = re.sub(r'\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]+', '[REDACTED]', raw)
    return [{'id':f'L{i:03d}','text':''.join(c for c in line if c.isprintable())[:300]} for i,line in enumerate(raw.splitlines()[:80],1)]
