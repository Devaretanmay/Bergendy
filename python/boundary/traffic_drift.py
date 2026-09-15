from dataclasses import dataclass, field
from typing import Any


"""Traffic drift abstraction: changes detected from live JSON payloads."""
NO_IMPACT = "NO_IMPACT"
IMPACT_AI = "IMPACT_AI"
IMPACT_QUARANTINE = "IMPACT_QUARANTINE"
class TrafficDriftSource:
    """A system/contract the repository depends upon, at a detected drift."""
    
    endpoint: str
    diff_summary: str
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def provider(self) -> str:
        return self.metadata.get("provider", self.endpoint.lower() if self.endpoint else "unknown")

    @classmethod
    def sdk(cls, provider: str, version_from: str = "", version_to: str = "") -> "TrafficDriftSource":
        return cls(
            endpoint=provider,
            diff_summary=f"{version_from}->{version_to}",
            metadata={"provider": provider.lower(), "version_from": version_from, "version_to": version_to},
        )

    def key(self) -> str:
        vf = self.metadata.get("version_from", "")
        vt = self.metadata.get("version_to", "")
        return f"sdk/{self.provider}/{vf}__{vt}"
class Detection:
    source: TrafficDriftSource
    outcome: str
    reason: str = ""
    affected_files: list[str] = field(default_factory=list)