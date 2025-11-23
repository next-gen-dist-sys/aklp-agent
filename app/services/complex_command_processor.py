from __future__ import annotations

from openai import OpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.services.types import GeneratedCommand


class KubectlStructuredOutput(BaseModel):
    """Responses API structured output 모델."""

    command: str
    reason: str
    title: str


class ComplexCommandProcessor:
    """단순 패턴 매칭에 실패한 자연어 명령어를 LLM을 활용해 kubectl 명령어로 변환하는 프로세서."""

    def __init__(self, client: OpenAI | None = None) -> None:
        api_key = settings.OPENAI_API_KEY
        self.client = client or OpenAI(api_key=api_key)
        self.model = settings.OPENAI_MODEL
        self.timeout = settings.OPENAI_TIMEOUT

    def _build_instructions(self) -> str:
        """instructions 프롬프트 정의"""
        return (
            "You are an expert Kubernetes operator and kubectl CLI generator.\n"
            "The user will give you a request in Korean (sometimes mixed with English).\n"
            "Your job is to convert the request into EXACTLY ONE kubectl command line.\n\n"
            "Requirements:\n"
            "- Output ONLY the kubectl command, nothing else (no explanation, no comments).\n"
            "- Do not wrap the command in quotes or code fences.\n"
            "- Prefer safe, read-only operations when ambiguous (e.g., 'kubectl get ...').\n"
            "- If a namespace is clearly mentioned, add '-n <namespace>'.\n"
            "- If the user mentions '모든 네임스페이스' or '전체 네임스페이스', use '-A'.\n"
            "- If the user refers to an app/service name, use label selectors when appropriate (e.g., '-l app=<name>').\n"
            "- If you truly cannot generate a kubectl command, return exactly: 'kubectl # UNABLE_TO_GENERATE'.\n"
            "- You must always populate the fields: command (kubectl line), reason (brief reasoning, in korean), title (concise summary, in korean)."
        )

    def _extract_kubectl_command(self, raw: str) -> str:
        """모델 응답에서 실제 kubectl 한 줄 추출."""
        text = raw.strip()

        if "```" in text:
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1].strip()

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("kubectl "):
                return line

        if text.startswith("kubectl "):
            return text

        return text

    def _build_user_input(self, command: str) -> str:
        """Responses API input 문자열 생성."""
        return f"다음 요청을 하나의 kubectl 명령어로 변환해 주세요.\n요청: {command}"

    def _call_responses(self, command: str) -> KubectlStructuredOutput | None | str:
        """Responses API 호출을 수행하고 BaseModel로 파싱."""
        user_input = self._build_user_input(command)
        instructions = self._build_instructions()

        try:
            response = self.client.responses.parse(
                model='gpt-5-mini',
                input=user_input,
                instructions=instructions,
                text_format=KubectlStructuredOutput,
                reasoning={ "effort": "low" },
                text={ "verbosity": "low" },
            )

            return response.output_parsed
            # # output[0] -> message -> content[0] -> output_text -> parsed
            # for item in response.output:
            #     if item.type == "message":
            #         for content in item.content:
            #             if content.type == "output_text" and content.parsed:
            #                 return content.parsed
            # return None

        except Exception as e:
            return f"kubectl # LLM_CALL_FAILED: {e}"

    def process(
        self,
        command: str,
    ) -> GeneratedCommand | str:
        """자연어 명령어를 kubectl 명령어로 변환."""
        structured = self._call_responses(command)

        if isinstance(structured, str):
            return structured  # 에러 메시지

        if not isinstance(structured, KubectlStructuredOutput):
            return "kubectl # UNABLE_TO_GENERATE: missing fields command,reason,title"

        kubectl_cmd = self._extract_kubectl_command(structured.command)

        if not kubectl_cmd.startswith("kubectl "):
            return "kubectl # UNABLE_TO_GENERATE"

        return GeneratedCommand(
            command=kubectl_cmd,
            reason=structured.reason,
            title=structured.title,
        )
