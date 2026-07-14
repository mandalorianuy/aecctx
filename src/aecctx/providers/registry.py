from __future__ import annotations

from .models import ProviderExecutionError, ProviderRegistration


class ProviderRegistry:
    def __init__(self, *, allowed_worker_modules: set[str] | frozenset[str]) -> None:
        self._allowed_worker_modules = frozenset(allowed_worker_modules)
        self._registrations: dict[str, ProviderRegistration] = {}

    def register(self, registration: ProviderRegistration) -> None:
        provider_id = registration.descriptor.provider_id
        if (registration.remote_origin is None) != (registration.remote_spki_sha256 is None):
            raise ProviderExecutionError(
                "AECCTX_REMOTE_REGISTRATION_INVALID",
                "Remote registration must bind both origin and SPKI digest",
            )
        if registration.worker_module not in self._allowed_worker_modules:
            raise ProviderExecutionError(
                "AECCTX_PROVIDER_LAUNCH_TARGET_UNREVIEWED",
                f"Provider launch target is not reviewed: {registration.worker_module}",
            )
        if provider_id in self._registrations:
            raise ProviderExecutionError("AECCTX_PROVIDER_DUPLICATE", f"Provider is already registered: {provider_id}")
        self._registrations[provider_id] = registration

    def resolve(self, provider_id: str) -> ProviderRegistration:
        try:
            return self._registrations[provider_id]
        except KeyError as error:
            raise ProviderExecutionError("AECCTX_PROVIDER_NOT_REGISTERED", f"Provider is not registered: {provider_id}") from error
