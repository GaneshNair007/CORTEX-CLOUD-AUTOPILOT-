"""Deterministic aliases, exact operational signatures and failure taxonomy."""
import re

ALIASES = {"postgres": "postgresql", "pg": "postgresql", "postgresql": "postgresql",
           "k8s": "kubernetes", "kube": "kubernetes", "kubernetes": "kubernetes",
           "pgbouncer": "pgbouncer", "redis": "redis", "mysql": "mysql", "nginx": "nginx",
           "docker": "docker", "kafka": "kafka", "coredns": "coredns", "envoy": "envoy"}
SIGNATURES = {
    "postgres_too_many_connections": r"sqlstate\s*53300|too\s*many\s*(?:clients|connections)|too_many_clients|toomanyconnections",
    "k8s_crashloopbackoff": r"crashloopbackoff",
    "k8s_oomkilled": r"oomkilled|out of memory|oom killer",
    "econnrefused": r"econnrefused|connection refused",
    "connection_reset_error": r"connectionreseterror|connection reset",
}
FAILURES = {
    "connection_pool_exhaustion": r"pool.{0,35}(?:exhaust|saturat)|too many (?:clients|connections)|sqlstate\s*53300",
    "pod_crash_loop": r"crashloopbackoff|crash loop",
    "memory_exhaustion": r"oomkilled|out of memory|memory leak|memory exhaust",
    "bad_deployment": r"bad deploy|faulty deploy|deployment regression|recent deploy|new deploy|bad release",
    "cpu_saturation": r"cpu.{0,25}(?:high|saturat|100%|exhaust)|high cpu",
    "dns_failure": r"dns.{0,25}(?:fail|resol|timeout)|nxdomain|servfail",
    "token_expiry": r"token.{0,20}expir|expired token",
    "authentication_failure": r"authentication fail|invalid credentials|unauthorized",
    "cache_eviction": r"cache.{0,20}evict|redis.{0,25}evict|eviction",
    "database_replication_lag": r"replication lag|replica lag",
    "network_partition": r"network partition|split brain",
    "dependency_timeout": r"dependency.{0,20}timeout|upstream.{0,20}timeout|http\s*504",
    "rate_limit_exceeded": r"rate limit|http\s*429|throttl",
    "configuration_error": r"misconfig|configuration error|invalid config",
    "service_unavailable": r"http\s*503|service unavailable",
}
STOP_WORDS = set("the a an and or is are to of for with from on in by at as this that incident service symptoms cause resolution document type report title error errors".split())


def normalize(value: str) -> str:
    value = value.strip().lower()
    return ALIASES.get(value, re.sub(r"[\s-]+", "_", value))


def technologies(text: str) -> list[str]:
    return sorted({ALIASES[token] for token in re.findall(r"[a-z0-9]+", text.lower()) if token in ALIASES})


def error_signatures(text: str) -> list[str]:
    signatures = {name for name, pattern in SIGNATURES.items() if re.search(pattern, text, re.I)}
    signatures.update(f"http_{code}" for code in re.findall(r"\b(?:http[ /:_-]*)?([45]\d{2})\b", text, re.I))
    signatures.update(f"sqlstate_{code.lower()}" for code in re.findall(r"sqlstate[\s:_-]*([0-9A-Z]{5})", text, re.I))
    return sorted(signatures)


def failure_mode(text: str) -> str:
    return next((name for name, pattern in FAILURES.items() if re.search(pattern, text, re.I)), "unknown")


def tokens(text: str) -> list[str]:
    words = {normalize(t) for t in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(t) > 1 and t not in STOP_WORDS}
    return sorted(words | set(error_signatures(text)))
