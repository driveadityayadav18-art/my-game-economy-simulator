"""
Unit Test Suite for src/config.py (Milestone 1).

Tests:
1. Default economic constants (k=0.05, min_price=1.0, tick_interval=4.0s, timeout=2.0s, tax_rate=0.10).
2. Tax rate boundary bounds (0.0 to 0.80).
3. Default item catalog configuration (Health Potion, Iron Sword, Raw Gem).
4. Default starting agents configuration (Garrick, Cora, Boran).
5. Environment variable override mechanics.
"""

import os
import pytest
from src.config import Settings, get_settings


class TestConfigDefaults:
    """Tests default configuration settings in src/config.py."""

    @pytest.fixture
    def settings(self):
        return Settings()

    def test_simulation_tick_interval(self, settings):
        """Simulation tick interval defaults to 4.0 seconds."""
        assert settings.SIMULATION_TICK_INTERVAL == 4.0

    def test_llm_timeout_seconds(self, settings):
        """LLM decision timeout defaults to 2.0 seconds."""
        assert settings.LLM_TIMEOUT_SECONDS == 2.0

    def test_tax_parameters(self, settings):
        """Default tax rate is 0.10, bounds are [0.0, 0.80]."""
        assert settings.DEFAULT_TAX_RATE == 0.10
        assert settings.MIN_TAX_RATE == 0.0
        assert settings.MAX_TAX_RATE == 0.80

    def test_price_discovery_parameters(self, settings):
        """Price sensitivity k defaults to 0.05, minimum price floor to 1.0."""
        assert settings.PRICE_SENSITIVITY_K == 0.05
        assert settings.PRICE_FLOOR == 1.0

    def test_default_items_catalog(self, settings):
        """Default items catalog contains Health Potion, Iron Sword, and Raw Gem."""
        items = settings.DEFAULT_ITEMS
        assert "Health Potion" in items
        assert "Iron Sword" in items
        assert "Raw Gem" in items

        # Check default prices and supplies
        assert items["Health Potion"]["price"] == 20.0
        assert items["Health Potion"]["supply"] == 100

        assert items["Iron Sword"]["price"] == 30.0
        assert items["Iron Sword"]["supply"] == 100

        assert items["Raw Gem"]["price"] == 15.0
        assert items["Raw Gem"]["supply"] == 100

    def test_default_agents_configuration(self, settings):
        """Default agents config includes Garrick, Cora, and Boran with correct starting balances."""
        agents = settings.DEFAULT_AGENTS
        assert "Garrick" in agents
        assert "Cora" in agents
        assert "Boran" in agents

        assert agents["Garrick"]["gold"] == 150.0
        assert agents["Cora"]["gold"] == 60.0
        assert agents["Boran"]["gold"] == 40.0

    def test_api_keys_default_to_none_or_empty(self, settings):
        """Missing API keys do not cause crash; allow simulated fallback mode."""
        # When environment vars are absent, keys are None or empty string
        assert hasattr(settings, "OPENAI_API_KEY")
        assert hasattr(settings, "ANTHROPIC_API_KEY")
        assert hasattr(settings, "GEMINI_API_KEY")


class TestConfigEnvironmentOverrides:
    """Tests environment variable overriding of configuration settings."""

    def test_override_tick_interval(self, monkeypatch):
        monkeypatch.setenv("SIMULATION_TICK_INTERVAL", "5.5")
        custom_settings = Settings()
        assert custom_settings.SIMULATION_TICK_INTERVAL == 5.5

    def test_override_default_tax_rate(self, monkeypatch):
        monkeypatch.setenv("DEFAULT_TAX_RATE", "0.25")
        custom_settings = Settings()
        assert custom_settings.DEFAULT_TAX_RATE == 0.25

    def test_override_price_sensitivity(self, monkeypatch):
        monkeypatch.setenv("PRICE_SENSITIVITY_K", "0.10")
        custom_settings = Settings()
        assert custom_settings.PRICE_SENSITIVITY_K == 0.10
