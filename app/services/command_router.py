import re


class CommandRouter:
    def normalize_command(self, raw_command: str) -> str:
        """Normalize inputted command

        Args:
            raw_command (str): an inputted command, whose type is natural language in korean

        Returns:
            str: a normalized command
        """

        # 앞뒤 공백 제거, 소문자 변환
        normalized_command = raw_command.strip().lower()

        # 한국어 불용어/종결어미, 조사 제거
        endings = re.compile(
            r"(부탁해|봐줘|보여줘|확인해줘|알려줘|줄래|볼래|주세요|해봐|줘|좀)\s*$"
        )
        particle = re.compile(r"\b(을|를|이|가|은|는|에|에서|으로|로|와|과|도|만|까지|부터)\b")

        normalized_command = endings.sub("", normalized_command)
        normalized_command = particle.sub("", normalized_command)

        #  연속된 공백을 단일 공백으로 치환
        normalized_command = re.sub(r"\s+", " ", normalized_command)

        # 앞뒤 공백 제거 후 반환
        return normalized_command.strip()

    def tokenize_command(self, normalized_command: str) -> list[str]:
        """Tokenize normalized command by space
        Args:
            normalized_command (str): a normalized command

        Returns:
            list: a list of tokens
        """

        return normalized_command.split(" ")
