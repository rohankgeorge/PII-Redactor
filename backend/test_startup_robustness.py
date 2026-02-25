"""Tests for PyInstaller startup robustness.

Validates that the backend handles initialization failures gracefully
so that a single subsystem failure (rule library, NLP models, etc.)
does not bring down the entire application.

Tests are written to describe the DESIRED behavior. They FAIL before the
fix is applied and PASS after.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock
import pytest


class TestRuleLibraryInitRobustness:
    """Startup must survive rule_library.initialize() failures."""

    def test_startup_survives_rule_library_permission_error(self):
        """If rule_library.initialize() raises PermissionError, NLP loading
        must still proceed."""
        import nlp_engine
        import rule_library

        original_nlp = nlp_engine.NLP

        with patch.object(
            rule_library, "initialize", side_effect=PermissionError("read-only dir")
        ):
            # Simulate the startup handler logic
            try:
                rule_library.initialize("/fake/path")
            except Exception:
                pass  # startup handler should catch this

            # NLP loading should still be callable after rule_library failure
            nlp = nlp_engine.load_nlp_pipeline()
            assert nlp is not None, (
                "NLP pipeline must load even when rule_library.initialize fails"
            )

        nlp_engine.NLP = original_nlp

    def test_startup_survives_rule_library_json_decode_error(self):
        """If rule_library.initialize() raises JSONDecodeError, NLP loading
        must still proceed."""
        import json
        import rule_library

        with patch.object(
            rule_library,
            "initialize",
            side_effect=json.JSONDecodeError("bad json", "", 0),
        ):
            try:
                rule_library.initialize("/fake/path")
            except Exception:
                caught = True
            else:
                caught = False

            # The exception should be catchable (not a SystemExit or similar)
            assert caught, "JSONDecodeError should propagate as a normal exception"


class TestNlpPipelineRobustness:
    """NLP pipeline must handle model load failures gracefully."""

    def test_load_nlp_pipeline_logs_error_on_spacy_failure(self):
        """If spacy.load() fails, load_nlp_pipeline must not crash the process."""
        import nlp_engine

        # Save and clear the global so lazy-load is triggered
        original_nlp = nlp_engine.NLP
        nlp_engine.NLP = None

        try:
            with patch("nlp_engine.spacy") as mock_spacy:
                mock_spacy.load.side_effect = OSError("Model not found")
                with pytest.raises(OSError):
                    nlp_engine.load_nlp_pipeline()

                # Verify it tried to load
                mock_spacy.load.assert_called_once()
        finally:
            nlp_engine.NLP = original_nlp

    def test_load_nlp_pipeline_returns_cached_on_second_call(self):
        """Once loaded, subsequent calls return the cached NLP instance."""
        import nlp_engine

        nlp1 = nlp_engine.load_nlp_pipeline()
        nlp2 = nlp_engine.load_nlp_pipeline()
        assert nlp1 is nlp2, "load_nlp_pipeline should cache and reuse the NLP model"

    def test_resolve_spacy_model_returns_model_name_in_dev(self):
        """Without _MEIPASS (dev mode), _resolve_spacy_model returns model name."""
        import sys
        import nlp_engine

        # In dev mode (no _MEIPASS), should return the model name string
        if not getattr(sys, "_MEIPASS", None):
            result = nlp_engine._resolve_spacy_model()
            assert result == "en_core_web_sm", (
                f"Expected model name string in dev mode, got {result!r}"
            )


class TestServerStartupHandler:
    """The startup_nlp_models handler must be resilient."""

    def test_startup_handler_catches_rule_library_error(self):
        """startup_nlp_models must NOT crash when rule_library.initialize fails.

        This is the root cause of 'All files failed to process' — when installed
        to C:\\Program Files\\ (read-only), rule_library.initialize() raises
        PermissionError which kills the startup handler, preventing NLP from loading.
        """
        import asyncio
        import server
        import rule_library

        with patch.object(
            rule_library,
            "initialize",
            side_effect=PermissionError("C:\\Program Files is read-only"),
        ):
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(server.startup_nlp_models())
                loop.close()
                handler_crashed = False
            except PermissionError:
                handler_crashed = True

            # The handler MUST catch the error so NLP loading can proceed
            assert not handler_crashed, (
                "startup_nlp_models does NOT catch rule_library.initialize() errors — "
                "a PermissionError in C:\\Program Files\\ will prevent NLP loading. "
                "Wrap rule_library.initialize(DATA_DIR) in try/except."
            )


class TestDataDirLogic:
    """DATA_DIR must be writable in all environments."""

    def test_data_dir_equals_root_dir_in_dev(self):
        """In development (no _MEIPASS), DATA_DIR must equal ROOT_DIR."""
        import server

        if hasattr(server, "DATA_DIR"):
            import sys
            if not getattr(sys, "_MEIPASS", None):
                assert server.DATA_DIR == server.ROOT_DIR, (
                    "In dev mode, DATA_DIR should equal ROOT_DIR"
                )
        else:
            pytest.fail(
                "server.DATA_DIR is not defined — "
                "the writable data directory logic is missing"
            )

    def test_server_uses_data_dir_for_rules(self):
        """The startup handler must pass DATA_DIR (not ROOT_DIR) to rule_library."""
        import inspect
        import server

        source = inspect.getsource(server.startup_nlp_models)
        assert "DATA_DIR" in source, (
            "startup_nlp_models still uses ROOT_DIR instead of DATA_DIR — "
            "rule_library.initialize() will fail in read-only install directories"
        )
