

from typing import (
    Protocol,
    TypeAlias,
)

JsonValue: TypeAlias = object


class Service(Protocol):
    pass


class Context(Protocol):
    def resolve_store_url(self, url: str, as_output: bool = False) -> str:
        ...
