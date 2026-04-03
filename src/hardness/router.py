from __future__ import annotations

from hardness.config import HardnessConfig, ModelProfile, ProviderConfig
from hardness.types import RoutingDecision


DEFAULT_ROLE = "default"


class ModelRouter:
    def __init__(self, config: HardnessConfig) -> None:
        self.config = config

    def route(self, task: str, reason: str = "default", opportunistic: bool = False) -> tuple[ProviderConfig, RoutingDecision]:
        profile, routing_reason = self._select_profile(task=task, reason=reason, opportunistic=opportunistic)
        provider = ProviderConfig(
            name=profile.provider if profile else self.config.provider.name,
            model=profile.model if profile else self.config.provider.model,
            api_key=self.config.provider.api_key,
            base_url=self.config.provider.base_url,
            timeout_seconds=self.config.provider.timeout_seconds,
        )
        decision = RoutingDecision(
            profile_name=profile.name if profile else "direct-provider",
            provider=provider.name,
            model=provider.model,
            reason=routing_reason,
        )
        return provider, decision

    def _select_profile(self, task: str, reason: str, opportunistic: bool) -> tuple[ModelProfile | None, str]:
        if not self.config.model_profiles:
            return None, "direct-provider"

        if opportunistic and reason == DEFAULT_ROLE:
            opportunistic_profile = self._find_profile("opportunistic")
            if opportunistic_profile and self._is_low_risk_task(task):
                return opportunistic_profile, "opportunistic_low_risk"

        for profile in self.config.model_profiles:
            if reason != DEFAULT_ROLE and reason in profile.escalation_triggers:
                return profile, f"escalation:{reason}"
        for profile in self.config.model_profiles:
            if profile.role == DEFAULT_ROLE:
                return profile, "default_profile"
        return self.config.model_profiles[0], "fallback_first_profile"

    def _find_profile(self, role: str) -> ModelProfile | None:
        for profile in self.config.model_profiles:
            if profile.role == role:
                return profile
        return None

    def _is_low_risk_task(self, task: str) -> bool:
        normalized = task.lower()
        hard_block_tokens = [
            "write ",
            "refactor",
            "ambiguous",
            "uncertainty",
            "critical",
            "sensitive",
            "decision",
        ]
        if any(token in normalized for token in hard_block_tokens):
            return False
        low_risk_prefixes = ("read ", "search ")
        return normalized.startswith(low_risk_prefixes)
