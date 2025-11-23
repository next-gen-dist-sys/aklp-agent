from __future__ import annotations

from openai import OpenAI

from app.core.config import settings


class ComplexCommandProcessor:
    """단순 패턴 매칭에 실패한 자연어 명령어를 LLM을 활용해 kubectl 명령어로 변환하는 프로세서

    - 입력: 한국어 자연어 명령어 (정규화된 문자열)
    - 출력: 'kubectl ...' 한 줄짜리 CLI 명령어 문자열

    실제 명령 실행(서브프로세스 호출 등)은 ExecutorService 쪽에서 담당하고,
    이 클래스는 "자연어 → kubectl 문자열" 변환에만 집중한다.
    """

    def __init__(self, client: OpenAI | None = None) -> None:
        # OPENAI_API_KEY 환경 변수 기반으로 기본 클라이언트 생성
        api_key = settings.OPENAI_API_KEY
        self.client = client or OpenAI(api_key=api_key)

    def _build_system_prompt(self) -> str:
        """system 프롬프트 정의"""
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
            "- If you truly cannot generate a kubectl command, return exactly: 'kubectl # UNABLE_TO_GENERATE'."
        )

    def _extract_kubectl_command(self, raw: str) -> str:
        """모델 응답에서 실제 kubectl 한 줄 추출

        - 코드 블록(```` ... ````)이 섞여 있어도 회수
        - 여러 줄이 와도 'kubectl '로 시작하는 첫 번째 줄을 사용
        """
        text = raw.strip()

        # 코드 펜스 제거 시도
        if "```" in text:
            parts = text.split("```")
            # ```kubectl\n...\n``` 형태를 단순하게 정리
            if len(parts) >= 2:
                text = parts[1].strip()

        # 줄 단위로 kubectl 로 시작하는 첫 줄 찾기
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("kubectl "):
                return line

        # 전체가 한 줄이고 kubectl 로 시작하면 그대로 사용
        if text.startswith("kubectl "):
            return text

        # 모델이 규칙을 안 지킨 경우 최소한 원본을 돌려준다
        return text

    def process(
        self,
        command: str,
    ) -> str:
        """자연어 명령어를 kubectl 명령어로 변환

        Args:
            command: pattern_matching_system에서 처리하지 못한 자연어 명령어(정규화된 문자열)

        Returns:
            str: 'kubectl ...' 형식의 명령어 문자열.
                 생성에 실패하면 'kubectl # UNABLE_TO_GENERATE' 또는
                 모델 응답 원문 일부가 반환될 수 있다.
        """
        """
        system_prompt = self._build_system_prompt()

        # LLM 호출 (동기 클라이언트 사용)
        response = self.client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"다음 요청을 하나의 kubectl 명령어로 변환해 주세요.\n요청: {command}"
                    ),
                },
            ],
            temperature=0.0,
        )

        content = response.choices[0].message.content or ""
        kubectl_cmd = self._extract_kubectl_command(content)

        # 완전히 실패한 경우 최소한의 fallback 제공
        if not kubectl_cmd:
            return "kubectl # UNABLE_TO_GENERATE"

        return kubectl_cmd
        """
        return f"[MOCK] 복잡한 명령으로 판단되어 LLM 처리 필요: {command}"
