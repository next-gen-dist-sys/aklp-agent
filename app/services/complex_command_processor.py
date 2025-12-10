from __future__ import annotations

from openai import OpenAI
from openai.types.responses import ParsedResponse
from pydantic import BaseModel

from app.core.config import settings
from app.services.types import GeneratedCommand, UsageInfo


class KubectlStructuredOutput(BaseModel):
    """Responses API structured output 모델."""

    command: str
    reason: str
    title: str
    model_config = {"extra": "forbid"}


class ComplexCommandProcessor:
    """단순 패턴 매칭에 실패한 자연어 명령어를 LLM을 활용해 kubectl 명령어로 변환하는 프로세서."""

    def __init__(self, client: OpenAI | None = None) -> None:
        api_key = settings.OPENAI_API_KEY
        self.client = client or OpenAI(api_key=api_key)
        self.model = settings.OPENAI_MODEL
        self.timeout = settings.OPENAI_TIMEOUT
        self.max_output_tokens = 512

    def _build_system_prompt(self) -> str:
        """system 프롬프트 정의"""
        return (
            "You are an expert Kubernetes operator and kubectl command generator\n\n"
            "# ROLE\n"
            "Convert natural language requests (Korean or English) into precise kubectl commands.\n\n"
            "# INPUT FORMAT\n"
            "Users will provide requests, which may include:\n"
            "- Resource types: 파드/pod, 서비스/service, 디플로이먼트/deployment, 네임스페이스/namespace\n"
            "- Actions: 조회/list/get, 삭제/delete, 생성/create, 수정/edit, 로그/logs\n"
            "- Filters: 네임스페이스 이름, 레이블, 리소스 이름\n"
            "- Modifiers: 모든/all, 상세/detailed, 실시간/watch\n\n"
            "# OUTPUT REQUIREMENTS\n"
            "Generate a structured response with three fields:\n"
            "1. **command**: A single, executable kubectl command (no explanations, no markdown)\n"
            "2. **reason**: Brief explanation in Korean of what the command does (1-2 sentences)\n"
            "3. **title**: Concise English summary (3-5 words)\n\n"
            "# KUBECTL COMMAND RULES\n"
            "## Safety First\n"
            "- Default to READ-ONLY operations (get, describe, logs) when intent is unclear\n"
            "- NEVER generate destructive commands (delete, drain, cordon) unless explicitly requested\n"
            "- For ambiguous requests, prefer the safest interpretation\n\n"
            "## Namespace Handling\n"
            "- '모든 네임스페이스' / '전체 네임스페이스' / 'all namespaces' → use `-A` or `--all-namespaces`\n"
            "- Specific namespace mentioned (e.g., 'default', 'kube-system') → use `-n <namespace>`\n"
            "- No namespace mentioned → omit namespace flag (uses current context)\n\n"
            "## Resource Selection\n"
            "- App/service name mentioned → use label selector: `-l app=<name>`\n"
            "- Specific resource name → use direct reference: `<resource-type> <name>`\n"
            "- '모든' / 'all' / '전체' without resource name → list all of that type\n\n"
            "## Common Patterns\n"
            "- List pods: `kubectl get pods [-n <ns>] [-A] [-l app=<name>]`\n"
            "- Pod logs: `kubectl logs [-f] [-n <ns>] <pod-name> [-c <container>]` (add -f for '실시간')\n"
            "- Describe resource: `kubectl describe <type> <name> [-n <ns>]`\n"
            "- Watch resources: `kubectl get <type> [-w] [-A]` (add -w for '실시간' / 'watch')\n"
            "- Service details: `kubectl get svc <name> [-n <ns>] [-o wide]` or `kubectl describe svc <name>`\n\n"
            "## Output Formatting\n"
            "- Add `-o wide` for more details when user asks for '상세' / 'detailed' / '자세히'\n"
            "- Add `-o yaml` or `-o json` when user explicitly asks for YAML/JSON format\n"
            "- Default to table output (no -o flag) for simple listings\n\n"
            "## Korean Keyword Mappings\n"
            "- 조회/목록/리스트/보기/확인 → get\n"
            "- 로그/기록 → logs\n"
            "- 상세/자세히/설명 → describe\n"
            "- 실시간/지켜보기 → -f (for logs) or -w (for get)\n"
            "- 파드/팟 → pod/pods\n"
            "- 서비스 → service/svc\n"
            "- 디플로이먼트/배포 → deployment/deploy\n"
            "- 노드 → node\n"
            "- 네임스페이스/ns → namespace\n\n"
            "# EXAMPLES\n"
            "Input: '모든 파드 목록 보여줘'\n"
            "Output: {command: 'kubectl get pods -A', reason: '전체 네임스페이스의 모든 파드 목록 조회', title: 'List all pods'}\n\n"
            "Input: 'default 네임스페이스의 nginx 서비스 상태 확인'\n"
            "Output: {command: 'kubectl get svc nginx -n default', reason: 'default 네임스페이스의 nginx 서비스 상태 조회', title: 'Get nginx service'}\n\n"
            "Input: 'api 파드 로그 실시간으로'\n"
            "Output: {command: 'kubectl logs -f api', reason: 'api 파드의 로그를 실시간으로 출력', title: 'Stream api pod logs'}\n\n"
            "# ERROR HANDLING\n"
            "If the request is truly impossible to convert to kubectl (e.g., unrelated to Kubernetes):\n"
            "- Set command to: 'kubectl # UNABLE_TO_GENERATE'\n"
            "- Explain why in the reason field\n"
            "- Set title to: 'Unable to generate'\n\n"
            "# FINAL REMINDER\n"
            "- Generate ONLY valid kubectl commands that can be executed directly\n"
            "- Be conservative: when in doubt, use read-only commands\n"
            "- Always fill all three fields: command, reason, title"
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
        """사용자 입력 콘텐츠 생성."""
        return f"다음 요청을 하나의 kubectl 명령어로 변환해 주세요.\n요청: {command}"

    def _extract_structured_payload(
        self, response: object
    ) -> tuple[KubectlStructuredOutput | str | None, bool]:
        """
        Responses API 결과에서 Structured Output을 추출.

        반환:
            payload: KubectlStructuredOutput | str | None - 파싱된 모델 또는 거절 메시지
            refused: bool - 거절 여부
        """
        parsed = getattr(response, "output_parsed", None)
        if parsed:
            return parsed, False

        output_items = getattr(response, "output", None) or []
        for item in output_items:
            contents = getattr(item, "content", None) or []
            for content in contents:
                if getattr(content, "type", None) == "refusal":
                    return (
                        f"kubectl # REFUSED: {getattr(content, 'refusal', 'Unknown reason')}",
                        True,
                    )

        return None, False

    def _call_responses(
        self, command: str
    ) -> tuple[KubectlStructuredOutput | None | str, UsageInfo | None]:
        """Responses API 호출을 수행하고 BaseModel로 파싱."""
        usage_info: UsageInfo | None = None

        def _invoke(
            max_tokens: int,
        ) -> tuple[ParsedResponse[KubectlStructuredOutput], UsageInfo | None]:
            resp = self.client.responses.parse(
                model=self.model,
                instructions=self._build_system_prompt(),
                input=self._build_user_input(command),
                max_output_tokens=max_tokens,
                timeout=self.timeout,
                text_format=KubectlStructuredOutput,
            )
            usage: UsageInfo | None = None
            if hasattr(resp, "usage") and resp.usage:
                u = resp.usage
                cached_tokens = 0
                if hasattr(u, "input_tokens_details") and u.input_tokens_details:
                    cached_tokens = getattr(u.input_tokens_details, "cached_tokens", 0) or 0
                usage = UsageInfo(
                    input_tokens=getattr(u, "input_tokens", 0) or 0,
                    output_tokens=getattr(u, "output_tokens", 0) or 0,
                    cached_tokens=cached_tokens,
                )
            return resp, usage

        try:
            response, usage_info = _invoke(self.max_output_tokens)

            if getattr(response, "status", None) == "incomplete":
                details = getattr(response, "incomplete_details", None)
                reason = getattr(details, "reason", "unknown")
                if reason == "max_output_tokens":
                    response, usage_info = _invoke(self.max_output_tokens * 2)
                else:
                    return f"kubectl # INCOMPLETE: {reason}", usage_info

            if getattr(response, "status", None) == "incomplete":
                details = getattr(response, "incomplete_details", None)
                reason = getattr(details, "reason", "unknown")
                return f"kubectl # INCOMPLETE: {reason}", usage_info

            payload, refused = self._extract_structured_payload(response)
            if refused:
                return payload or "kubectl # REFUSED", usage_info

            if isinstance(payload, KubectlStructuredOutput):
                return payload, usage_info

            return "kubectl # UNABLE_TO_GENERATE: empty response", usage_info

        except Exception as e:
            return f"kubectl # LLM_CALL_FAILED: {e}", usage_info

    def process(
        self,
        command: str,
    ) -> GeneratedCommand | str:
        """자연어 명령어를 kubectl 명령어로 변환."""
        structured, usage_info = self._call_responses(command)

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
            usage=usage_info,
        )
