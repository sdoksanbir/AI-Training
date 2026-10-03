"""In-memory lookup and context resolution for specialty profiles."""

from educoach.models.learner import LearningContext

from .models import SpecialtyProfile


class SpecialtyProfileRegistryError(Exception):
    """Base error for deterministic registry failures."""


class DuplicateSpecialtyProfileError(SpecialtyProfileRegistryError):
    """Raised when an existing profile code and version is registered again."""


class SpecialtyProfileNotFoundError(SpecialtyProfileRegistryError):
    """Raised when a required profile cannot be found."""


class AmbiguousSpecialtyProfileError(SpecialtyProfileRegistryError):
    """Raised when a profile code has multiple versions and none was requested."""


class SpecialtyProfileFamilyMismatchError(SpecialtyProfileRegistryError):
    """Raised when a context and its resolved profile have different families."""


class SpecialtyProfileRegistry:
    """Register and resolve versioned specialty profiles deterministically."""

    def __init__(self) -> None:
        self._profiles: dict[tuple[str, int], SpecialtyProfile] = {}

    def register(self, profile: SpecialtyProfile) -> None:
        key = (profile.profile_code, profile.profile_version)

        if key in self._profiles:
            raise DuplicateSpecialtyProfileError(
                f"Specialty profile already registered: {profile.profile_code} "
                f"version {profile.profile_version}"
            )

        self._profiles[key] = profile.model_copy(deep=True)

    def get(
        self, profile_code: str, version: int | None = None
    ) -> SpecialtyProfile | None:
        normalized_code = self._normalize_profile_code(profile_code)

        if version is not None:
            return self._copy_profile(self._profiles.get((normalized_code, version)))

        matches = [
            profile
            for (code, _), profile in self._profiles.items()
            if code == normalized_code
        ]

        if len(matches) > 1:
            versions = sorted(profile.profile_version for profile in matches)
            raise AmbiguousSpecialtyProfileError(
                f"Multiple versions registered for {normalized_code}: {versions}"
            )

        return self._copy_profile(matches[0]) if matches else None

    def require(
        self, profile_code: str, version: int | None = None
    ) -> SpecialtyProfile:
        profile = self.get(profile_code, version)

        if profile is None:
            version_text = f" version {version}" if version is not None else ""
            raise SpecialtyProfileNotFoundError(
                f"Specialty profile not found: {profile_code.strip()}{version_text}"
            )

        return profile

    def resolve_context(self, context: LearningContext) -> SpecialtyProfile:
        profile = self.require(context.program_code)

        if profile.profile_family != context.context_type:
            raise SpecialtyProfileFamilyMismatchError(
                f"Context family {context.context_type.value} does not match "
                f"profile family {profile.profile_family.value} for "
                f"{context.program_code}"
            )

        return profile

    def list_profiles(self) -> tuple[SpecialtyProfile, ...]:
        return tuple(
            self._profiles[key].model_copy(deep=True)
            for key in sorted(self._profiles)
        )

    @staticmethod
    def _normalize_profile_code(profile_code: str) -> str:
        normalized_code = profile_code.strip()

        if not normalized_code:
            raise ValueError("profile_code boş olamaz")

        return normalized_code

    @staticmethod
    def _copy_profile(profile: SpecialtyProfile | None) -> SpecialtyProfile | None:
        return profile.model_copy(deep=True) if profile is not None else None
