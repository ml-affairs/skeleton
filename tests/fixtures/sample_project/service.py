class Greeter:
    def __init__(self, name: str) -> None:
        self.name = name

    def greet(self, subject: str, *, token: str) -> str:
        return self._format(subject, token=token)

    def _format(self, subject: str, *, token: str) -> str:
        return f"{self.name} says hello to {subject}"
