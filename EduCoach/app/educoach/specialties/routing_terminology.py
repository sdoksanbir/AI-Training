"""Typed specialty terminology used by message context routing."""

from dataclasses import dataclass
import re
import unicodedata

from .models import SpecialtyProfile


_WORD_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)
_ROUTING_FIELDS = ("explicit_terms", "support_terms", "explicit_phrases")
_MISSING = object()


def normalize_context_routing_text(value: str) -> str:
    """Return a canonical, punctuation-safe sequence of Unicode words."""

    if not isinstance(value, str):
        raise ValueError("context routing values must be strings")

    normalized = unicodedata.normalize("NFKC", value).translate(
        str.maketrans({"I": "ı", "İ": "i"})
    )
    return " ".join(_WORD_PATTERN.findall(normalized.casefold()))


@dataclass(frozen=True)
class ContextRoutingTerminology:
    explicit_terms: tuple[str, ...] = ()
    support_terms: tuple[str, ...] = ()
    explicit_phrases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in _ROUTING_FIELDS:
            values = getattr(self, field_name)
            if not isinstance(values, tuple):
                raise ValueError(f"{field_name} must be a tuple")
            if any(not isinstance(value, str) for value in values):
                raise ValueError(f"{field_name} must contain strings")
            if any(not value for value in values):
                raise ValueError(f"{field_name} cannot contain empty values")
            if any(normalize_context_routing_text(value) != value for value in values):
                raise ValueError(f"{field_name} values must be normalized")
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} cannot contain duplicates")
            if values != tuple(sorted(values)):
                raise ValueError(f"{field_name} must use canonical order")

        for field_name in ("explicit_terms", "support_terms"):
            if any(" " in value for value in getattr(self, field_name)):
                raise ValueError(f"{field_name} must contain single terms")
        if set(self.explicit_terms) & set(self.support_terms):
            raise ValueError("explicit_terms and support_terms must be disjoint")
        if any(" " not in value for value in self.explicit_phrases):
            raise ValueError("explicit_phrases must contain multi-word phrases")


def get_context_routing_terminology(
    profile: SpecialtyProfile,
) -> ContextRoutingTerminology:
    """Parse the optional context-routing subsection of a specialty profile."""

    terminology = profile.terminology
    if not isinstance(terminology, dict):
        raise ValueError("terminology must be an object")

    configured = terminology.get("context_routing", _MISSING)
    if configured is _MISSING:
        return ContextRoutingTerminology()
    if not isinstance(configured, dict):
        raise ValueError("terminology.context_routing must be an object")

    unknown_fields = set(configured) - set(_ROUTING_FIELDS)
    if unknown_fields:
        raise ValueError(
            "terminology.context_routing contains unknown fields: "
            + ", ".join(sorted(unknown_fields))
        )

    parsed: dict[str, tuple[str, ...]] = {}
    for field_name in _ROUTING_FIELDS:
        raw_values = configured.get(field_name, [])
        if not isinstance(raw_values, list):
            raise ValueError(f"terminology.context_routing.{field_name} must be an array")
        if any(not isinstance(value, str) for value in raw_values):
            raise ValueError(
                f"terminology.context_routing.{field_name} must contain strings"
            )

        values = tuple(normalize_context_routing_text(value) for value in raw_values)
        if any(not value for value in values):
            raise ValueError(
                f"terminology.context_routing.{field_name} cannot contain empty values"
            )
        if len(set(values)) != len(values):
            raise ValueError(
                f"terminology.context_routing.{field_name} cannot contain duplicates"
            )
        parsed[field_name] = tuple(sorted(values))

    return ContextRoutingTerminology(**parsed)
