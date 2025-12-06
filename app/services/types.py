from dataclasses import dataclass


@dataclass
class UsageInfo:
    """OpenAI API 사용량 정보."""

    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0


@dataclass
class GeneratedCommand:
    """구성된 kubectl 명령과 부가 설명."""

    command: str
    reason: str
    title: str
    usage: UsageInfo | None = None
