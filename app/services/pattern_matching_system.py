import re

from app.services.complex_command_processor import ComplexCommandProcessor

SIMPLE_COMMAND_DEFINITION = [
    {
        "intent_key": "pod_list",
        "kubectl_template": "kubectl get pods -l app={target}",
        "keywords": ["pod 목록", "파드 목록", "pod 리스트", "파드 리스트"],
    },
    {
        "intent_key": "service_status",
        "kubectl_template": "kubectl get services {target}",
        "keywords": ["서비스 상태", "서비스 목록", "service 상태", "서비스 리스트"],
    },
    {
        "intent_key": "pod_logs",
        "kubectl_template": "kubectl logs -f --tail=10 {target}",
        "keywords": ["로그 조회", "log 확인", "로그 보기", "로그좀"],
    },
]


class PatternMatchingSystem:
    """
    정규화된 명령어를 기반으로 단순 명령 패턴을 매칭하고 파라미터를 추출하여
    단순 kubectl 명령어를 반환하거나 복잡 명령어는 ComplexCommandProcessor로 전달하는 클래스
    """

    def __init__(
        self,
        complex_command_handler: ComplexCommandProcessor,
    ) -> None:
        self.complex_command_handler = complex_command_handler

        # intent_key 기준으로 keyword 패턴 구성
        # 예: "pod_list" -> /(pod 목록|파드 목록|...)/
        self.patterns: dict[str, re.Pattern[str]] = {}
        for cmd_def in SIMPLE_COMMAND_DEFINITION:
            intent_key = str(cmd_def["intent_key"])
            keywords = list(cmd_def["keywords"])

            pattern_str = "|".join(re.escape(kw) for kw in keywords)
            self.patterns[intent_key] = re.compile(pattern_str)

        # 필터링 옵션 패턴 정의
        self.filter_patterns: dict[str, re.Pattern[str]] = {
            # 특정 네임스페이스 (-n) 추출
            "namespace": re.compile(r"(?:네임스페이스|nm|ns)\s*([가-힣a-zA-Z0-9_-]+)"),
            # 모든 네임스페이스 (-A) 매칭
            "all_namespaces": re.compile(r"(모든|전체)\s*(네임스페이스)"),
            # 레이블 필터 (-l) 값 추출 (예: app=api)
            "label": re.compile(r"(?:앱|서비스|이름)\s*([가-힣a-zA-Z0-9_-]+)"),
            # 컨테이너 지정 (-c) 값 추출
            "container": re.compile(r"(?:컨테이너|c)\s*([가-힣a-zA-Z0-9_-]+)"),
        }

    def _extract_filters(
        self,
        command: str,
    ) -> dict[str, str]:
        """
        명령어에서 필터링 옵션(-n, -A, -l, -c) 및 해당 값을 추출
        """
        filters: dict[str, str] = {}

        # 네임스페이스 추출
        ns_match = self.filter_patterns["namespace"].search(command)
        if ns_match:
            filters["-n"] = ns_match.group(1)

        # 모든 네임스페이스 매칭
        if self.filter_patterns["all_namespaces"].search(command) and "-n" not in filters:
            filters["-A"] = ""

        # 레이블 필터 추출
        label_match = self.filter_patterns["label"].search(command)
        if label_match:
            filters["-l"] = label_match.group(1)

        # 컨테이너 지정 추출
        container_match = self.filter_patterns["container"].search(command)
        if container_match:
            filters["-c"] = container_match.group(1)

        return filters

    def _build_command(
        self,
        intent: str,
        resource: str,
        filters: dict[str, str],
    ) -> str:
        """
        추출된 인텐트, 리소스, 필터를 기반으로 kubectl 명령어를 조합
        """
        base_command = f"kubectl {intent}".strip()
        if resource:
            base_command += f" {resource}"

        options: list[str] = []

        if "-A" in filters:
            options.append("-A")
        elif "-n" in filters:
            options.append(f"-n {filters['-n']}")

        if "-l" in filters:
            options.append(f"-l {filters['-l']}")

        if "-c" in filters and intent == "logs":
            options.append(f"-c {filters['-c']}")

        if options:
            return f"{base_command} {' '.join(options)}"
        return base_command

    def process_command(
        self,
        normalized_command: str,
    ) -> str:
        """
        정규화된 명령어를 분석하여 kubectl 명령어를 반환
        """
        intent_map: dict[str, tuple[str, str | None]] = {
            "pod_list": ("get", "pods"),
            "service_status": ("get", "services"),
            "pod_logs": ("logs", None),
        }

        best_match: str | None = None
        for key, pattern in self.patterns.items():
            if pattern.search(normalized_command):
                best_match = key
                break

        if best_match is None:
            # 단순 패턴 매칭 실패 시 ComplexCommandProcessor로 위임
            return self.complex_command_handler.process(normalized_command)

        intent, resource = intent_map[best_match]
        resource_name: str = resource or ""

        filters = self._extract_filters(normalized_command)

        # 로그 명령어는 반드시 어떤 파드를 대상으로 할지 지정해야 함 (레이블 필터 또는 파드 이름)
        if intent == "logs" and "-l" not in filters:
            return self.complex_command_handler.process(normalized_command)

        return self._build_command(intent, resource_name, filters)
