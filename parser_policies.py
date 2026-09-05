"""Strategies for values referenced but not defined in a reaction file."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Mapping, Optional, Union


class UnresolvedValueError(ValueError):
    """Raised by a policy that requires every referenced value to be defined."""


class UnresolvedValuePolicy(ABC):
    """Strategy interface for resolving missing model parameters."""

    name: str

    @abstractmethod
    def coefficient(self, symbol: str, values: Mapping[str, float]) -> Union[float, str]:
        raise NotImplementedError

    @abstractmethod
    def rate(self, symbol: str, values: Mapping[str, float]) -> Optional[float]:
        raise NotImplementedError


class SymbolicValuePolicy(UnresolvedValuePolicy):
    name = "symbolic"

    def coefficient(self, symbol: str, values: Mapping[str, float]):
        return values.get(symbol, symbol)

    def rate(self, symbol: str, values: Mapping[str, float]):
        return values.get(symbol)


class StrictValuePolicy(UnresolvedValuePolicy):
    name = "error"

    def coefficient(self, symbol: str, values: Mapping[str, float]):
        if symbol not in values:
            raise UnresolvedValueError(f"Undefined stoichiometric coefficient {symbol!r}")
        return values[symbol]

    def rate(self, symbol: str, values: Mapping[str, float]):
        if symbol not in values:
            raise UnresolvedValueError(f"Undefined rate constant {symbol!r}")
        return values[symbol]


class UnitValuePolicy(UnresolvedValuePolicy):
    name = "one"

    def coefficient(self, symbol: str, values: Mapping[str, float]):
        return values.get(symbol, 1.0)

    def rate(self, symbol: str, values: Mapping[str, float]):
        return values.get(symbol, 1.0)


class UnresolvedValuePolicyFactory:
    """Factory that isolates public option names from strategy construction."""

    _policies = {
        "symbolic": SymbolicValuePolicy,
        "error": StrictValuePolicy,
        "one": UnitValuePolicy,
    }

    @classmethod
    def create(cls, name: str) -> UnresolvedValuePolicy:
        try:
            return cls._policies[name]()
        except KeyError:
            choices = ", ".join(repr(choice) for choice in cls._policies)
            raise ValueError(f"unresolved must be one of {choices}") from None
