from dataclasses import dataclass


@dataclass
class GeneratedCommand:
    """구성된 kubectl 명령과 부가 설명."""

    command: str
    reason: str
    title: str
