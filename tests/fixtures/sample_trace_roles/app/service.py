"""Application service used by trace-role fixture scenarios."""


class Service:
    """Small system-under-test service."""

    def __init__(self, name: str) -> None:
        """Initialize the service with a scenario name."""
        self.name = name

    def run(self) -> str:
        """Run the service behavior under inspection."""
        return self.render()

    def render(self) -> str:
        """Return a stable application result."""
        return f"service:{self.name}"
