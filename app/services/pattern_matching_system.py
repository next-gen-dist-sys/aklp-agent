import re
from typing import TypedDict  # TypedDict와 List를 추가로 임포트했습니다.

from app.services.complex_command_processor import ComplexCommandProcessor


# 1. 딕셔너리 구조를 명확히 정의하는 TypedDict를 생성합니다.
#    mypy가 각 키의 타입을 정확히 인식하도록 돕습니다.
class CommandDefinition(TypedDict):
    intent_key: str
    kubectl_template: str
    keywords: list[str]


# 2. SIMPLE_COMMAND_DEFINITION의 타입을 TypedDict 리스트로 지정합니다.
SIMPLE_COMMAND_DEFINITION: list[CommandDefinition] = [
    {
        "intent_key": "pod_list",
        "kubectl_template": "kubectl get pods",  # 기본: 전체 파드 목록
        "keywords": ["pod 목록", "파드 목록", "pod 리스트", "파드 리스트"],
    },
    {
        "intent_key": "service_status",
        "kubectl_template": "kubectl get services",  # 기본: 전체 서비스 목록
        "keywords": ["서비스 상태", "서비스 목록", "service 상태", "서비스 리스트"],
    },
    {
        "intent_key": "pod_logs",
        "kubectl_template": "kubectl logs -f --tail=10 {target}",
        "keywords": ["로그 조회", "log 확인", "로그 보기", "로그좀"],
    },
]

# 자연어 토큰 → kubectl-friendly 토큰 정규화
CANONICAL_TARGET_MAP: dict[str, str] = {
    # 파드
    "파드": "pod",
    "파드들": "pod",
    "pod": "pod",
    "pods": "pod",
    # 서비스
    "서비스": "service",
    "서비스들": "service",
    "service": "service",
    "services": "service",
    # 로그
    "로그": "logs",
    "로그들": "logs",
    "log": "logs",
    "logs": "logs",
}


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
        # 3. definition의 타입을 CommandDefinition으로 명시하여 mypy 오류를 방지합니다.
        for cmd_def in SIMPLE_COMMAND_DEFINITION:
            # cmd_def는 이제 CommandDefinition 타입으로 인식됩니다.
            intent_key = cmd_def["intent_key"]
            keywords = cmd_def["keywords"]

            pattern_str = "|".join(re.escape(kw) for kw in keywords)
            self.patterns[intent_key] = re.compile(pattern_str)

        # 필터링 옵션 패턴 정의
        self.filter_patterns: dict[str, re.Pattern[str]] = {
            # 특정 네임스페이스 (-n) 추출
            "namespace": re.compile(r"(?:네임스페이스|nm|ns)\s*([가-힣a-zA-Z0-9_-]+)"),
            # 모든 네임스페이스 (-A) 매칭
            "all_namespaces": re.compile(r"(모든|전체)\s*(네임스페이스)"),
            # 레이블 필터 값 추출 (예: 서비스 api → label=api 로 쓸 수 있게)
            "label": re.compile(r"(?:앱|서비스|이름)\s*([가-힣a-zA-Z0-9_-]+)"),
            # 컨테이너 지정 (-c) 값 추출
            "container": re.compile(r"(?:컨테이너|c)\s*([가-힣a-zA-Z0-9_-]+)"),
        }

    def _canonicalize_target(
        self,
        value: str | None,
    ) -> str | None:
        """
        파드/서비스 같은 자연어 토큰을 영어 토큰으로 정규화
        """
        if value is None:
            return None
        return CANONICAL_TARGET_MAP.get(value, value)

    def _extract_filters(
        self,
        command: str,
    ) -> dict[str, str]:
        """
        명령어에서 필터링 옵션(-n, -A, -l, -c) 및 해당 값을 추출
        """
        filters: dict[str, str] = {}

        # 1) "모든/전체 네임스페이스" 먼저 처리 → -A
        if self.filter_patterns["all_namespaces"].search(command):
            # -A만 쓰고, -n은 강제로 안 씀
            filters["all_namespaces"] = "true"
        else:
            # 2) 그 외의 경우에만 특정 네임스페이스 추출 → -n
            ns_match = self.filter_patterns["namespace"].search(command)
            if ns_match:
                filters["namespace"] = ns_match.group(1)

        # 3) 레이블 필터 추출
        label_match = self.filter_patterns["label"].search(command)
        if label_match:
            filters["label"] = label_match.group(1)

        # 4) 컨테이너 지정 추출
        container_match = self.filter_patterns["container"].search(command)
        if container_match:
            filters["container"] = container_match.group(1)

        return filters

    def _build_command(
        self,
        intent_key: str,
        resource: str | None,
        filters: dict[str, str],
    ) -> str:
        """
        intent_key 와 필터 정보를 바탕으로 최종 kubectl 명령어 생성
        """
        # definition은 CommandDefinition 타입으로 인식됩니다.
        definition = next(
            (d for d in SIMPLE_COMMAND_DEFINITION if d["intent_key"] == intent_key),
            None,
        )
        if definition is None:
            # 정의 안 된 인텐트면 그냥 fallback
            return f"kubectl {intent_key}"

        # label 값 정규화 (서비스 / 파드 이름 등)
        raw_label = filters.get("label")
        label_value = self._canonicalize_target(raw_label)

        # 1) intent 별 기본 base command
        if intent_key == "pod_list":
            # 파드 목록
            if label_value:
                base_cmd = f"kubectl get pods -l app={label_value}"
            else:
                base_cmd = "kubectl get pods"

        elif intent_key == "service_status":
            # 서비스 목록 / 상태
            if label_value:
                # 특정 서비스만 보고 싶다면: kubectl get services <name>
                base_cmd = f"kubectl get services {label_value}"
            else:
                base_cmd = "kubectl get services"

        elif intent_key == "pod_logs":
            # 로그는 target 필수 (사전 체크 있음)
            base_cmd = f"kubectl logs -f --tail=10 {label_value}"
        else:
            # 혹시 모를 확장용 fallback (템플릿 그대로 사용)
            # TypedDict 덕분에 mypy는 definition["kubectl_template"]이 str임을 압니다.
            kubectl_template: str = definition["kubectl_template"]
            base_cmd = kubectl_template.format(target=label_value or "")

        parts: list[str] = [base_cmd]

        # 2) 옵션들 부착 (-n, -A, -c)
        namespace = filters.get("namespace")
        if namespace:
            parts.append(f"-n {namespace}")

        if filters.get("all_namespaces"):
            parts.append("-A")

        container = filters.get("container")
        if container:
            parts.append(f"-c {container}")

        return " ".join(parts)

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

        filters = self._extract_filters(normalized_command)

        # 로그는 타겟이 없으면 ComplexCommandProcessor로 넘김
        if intent == "logs" and not filters.get("label"):
            return self.complex_command_handler.process(normalized_command)

        return self._build_command(
            intent_key=best_match,
            resource=resource,
            filters=filters,
        )
