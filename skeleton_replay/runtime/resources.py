"""Resource-call classification for standard-library runtime evidence."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import ClassVar

from skeleton_replay.runtime.events import Endpoint, ResourceCategory


@dataclass(frozen=True)
class ResourceCall:
    """A classified C-level resource call observed while project code is active."""

    callable_id: int
    endpoint: Endpoint


@dataclass(frozen=True)
class RuntimeResourceClassifier:
    """Classifies selected standard-library C calls as architecture resources."""

    file_modules: ClassVar[frozenset[str]] = frozenset({"_io", "io", "builtins", "os", "posix"})
    file_functions: ClassVar[frozenset[str]] = frozenset({"open", "read", "write", "close", "flush", "mkdir", "remove", "unlink", "stat"})
    database_modules: ClassVar[frozenset[str]] = frozenset({"_sqlite3", "sqlite3"})
    database_functions: ClassVar[frozenset[str]] = frozenset({"connect", "execute", "executemany", "executescript", "commit", "rollback", "cursor", "fetchone", "fetchall", "fetchmany", "close"})
    network_modules: ClassVar[frozenset[str]] = frozenset({"_socket", "socket", "ssl"})
    network_functions: ClassVar[frozenset[str]] = frozenset({"connect", "send", "sendall", "recv", "request", "getresponse"})

    def classify(self, c_callable: object) -> ResourceCall | None:
        """Return resource-call evidence for a supported C-level callable."""
        name = self._callable_name(c_callable)
        module = self._callable_module(c_callable)
        owner = getattr(c_callable, "__self__", None)
        category = self._category(module=module, name=name, owner=owner)
        if category is None:
            return None
        return ResourceCall(callable_id=id(c_callable), endpoint=self._endpoint(category=category, name=name))

    def _category(self, *, module: str, name: str, owner: object) -> ResourceCategory | None:
        if self._is_stdout_call(module=module, name=name, owner=owner):
            return "stdout"
        if self._is_database_call(module=module, name=name, owner=owner):
            return "db"
        if self._is_file_call(module=module, name=name, owner=owner):
            return "file"
        if self._is_network_call(module=module, name=name):
            return "network"
        return None

    @staticmethod
    def _is_stdout_call(*, module: str, name: str, owner: object) -> bool:
        return (module == "builtins" and name == "print") or owner is sys.stdout or owner is sys.stderr

    def _is_file_call(self, *, module: str, name: str, owner: object) -> bool:
        if module in self.file_modules and name in self.file_functions:
            return True
        owner_module = type(owner).__module__ if owner is not None else ""
        return owner_module in {"_io", "io"} and name in self.file_functions

    def _is_database_call(self, *, module: str, name: str, owner: object) -> bool:
        owner_module = type(owner).__module__ if owner is not None else ""
        return (module in self.database_modules or owner_module in self.database_modules) and name in self.database_functions

    def _is_network_call(self, *, module: str, name: str) -> bool:
        return module in self.network_modules and name in self.network_functions

    @staticmethod
    def _callable_name(c_callable: object) -> str:
        return str(getattr(c_callable, "__name__", type(c_callable).__name__)).lower()

    @staticmethod
    def _callable_module(c_callable: object) -> str:
        module = getattr(c_callable, "__module__", "")
        if isinstance(module, str) and module:
            return module
        owner = getattr(c_callable, "__self__", None)
        if owner is not None:
            return type(owner).__module__
        objclass = getattr(c_callable, "__objclass__", None)
        objclass_module = getattr(objclass, "__module__", "")
        return str(objclass_module) if objclass_module else ""

    @staticmethod
    def _endpoint(*, category: ResourceCategory, name: str) -> Endpoint:
        del name
        resource_name = {
            "file": "filesystem",
            "stdout": "stdout",
            "db": "database",
            "network": "network",
        }[category]
        qualified_name = f"resource.{resource_name}"
        return Endpoint(
            module="resource",
            function=resource_name,
            qualified_name=qualified_name,
            file="",
            line=0,
            node_id=f"resource:{category}:{qualified_name}",
            endpoint_type="resource",
            resource_category=category,
        )
