"""Tests for local allow/force redaction rule library."""

from pathlib import Path

from fastapi.testclient import TestClient

import rule_library
import server
from pii_engine import PIITracker, redact_text


def _init_tmp_rules(tmp_path: Path):
    (tmp_path / "user_allow_list.txt").write_text("Alice\n", encoding="utf-8")
    (tmp_path / "user_redact_list.txt").write_text("SecretTerm\n", encoding="utf-8")
    rule_library.initialize(tmp_path)


def test_initialize_bootstraps_from_legacy_txt(tmp_path):
    _init_tmp_rules(tmp_path)

    rules = rule_library.list_rules()
    assert any(r["term"] == "Alice" and r["mode"] == "ALLOW" for r in rules)
    assert any(r["term"] == "SecretTerm" and r["mode"] == "FORCE" for r in rules)
    assert (tmp_path / "rules_library.json").exists()


def test_create_update_delete_rule(tmp_path):
    _init_tmp_rules(tmp_path)

    created = rule_library.create_rule("Top Secret", "FORCE", True)
    assert created["term"] == "Top Secret"

    updated = rule_library.update_rule(created["id"], term="Top Secret Name", mode="ALLOW", enabled=False)
    assert updated["term"] == "Top Secret Name"
    assert updated["mode"] == "ALLOW"
    assert updated["enabled"] is False

    assert rule_library.delete_rule(created["id"]) is True
    assert rule_library.delete_rule(created["id"]) is False


def test_redaction_precedence_allow_and_force(tmp_path, monkeypatch):
    _init_tmp_rules(tmp_path)

    # Avoid model-loading side effects; this test targets allow/force precedence only.
    monkeypatch.setattr("pii_engine._redact_names", lambda text, tracker, ctx, config=None: text)
    monkeypatch.setattr("pii_engine._run_final_qa", lambda text, tracker, context: text)
    monkeypatch.setattr(server.nlp_engine, "run_second_pass", lambda text, tracker, legal_nlp, indic_pipeline, context: text)

    # Seed one ALLOW and one FORCE rule for deterministic behavior.
    rule_library.create_rule("DoNotRedact", "ALLOW", True)
    rule_library.create_rule("MustHide", "FORCE", True)

    text = "DoNotRedact met MustHide in Bangalore."
    tracker = PIITracker()
    out = redact_text(text, tracker, "Paragraph 1")

    assert "DoNotRedact" in out
    assert "MustHide" not in out
    assert "[REDACTED_INDIVIDUAL" in out


def test_rules_api_crud(tmp_path, monkeypatch):
    # Repoint library storage to isolated temp area.
    (tmp_path / "user_allow_list.txt").write_text("", encoding="utf-8")
    (tmp_path / "user_redact_list.txt").write_text("", encoding="utf-8")
    rule_library.initialize(tmp_path)

    monkeypatch.setattr(server.nlp_engine, "initialize_models", lambda: None)
    client = TestClient(server.app)

    create_resp = client.post("/api/rules", json={"term": "NeverThis", "mode": "ALLOW", "enabled": True})
    assert create_resp.status_code == 200
    rule_id = create_resp.json()["rule"]["id"]

    list_resp = client.get("/api/rules")
    assert list_resp.status_code == 200
    assert any(r["id"] == rule_id for r in list_resp.json()["rules"])

    update_resp = client.put(f"/api/rules/{rule_id}", json={"mode": "FORCE"})
    assert update_resp.status_code == 200
    assert update_resp.json()["rule"]["mode"] == "FORCE"

    delete_resp = client.delete(f"/api/rules/{rule_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["deleted"] is True
