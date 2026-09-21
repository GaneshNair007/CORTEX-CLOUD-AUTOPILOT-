"""Local configuration setup must be repeatable and preserve provider credentials."""
from dotenv import dotenv_values
import pytest

from backend.scripts.setup_local import TOKEN_NAMES, setup_local


def test_setup_creates_distinct_tokens_without_changing_provider(tmp_path):
    template = tmp_path / ".env.example"
    template.write_text("LLM_PRIMARY_PROVIDER=nvidia\nNVIDIA_API_KEY=FAKE_PRESERVED_VALUE\n")
    target = tmp_path / ".env"
    assert set(setup_local(target, template)) == set(TOKEN_NAMES)
    original = target.read_bytes()
    values = dotenv_values(target)
    assert values["NVIDIA_API_KEY"] == "FAKE_PRESERVED_VALUE"
    assert len({values[name] for name in TOKEN_NAMES}) == 3
    assert all(len(values[name]) >= 32 for name in TOKEN_NAMES)
    assert setup_local(target, template) == []
    assert target.read_bytes() == original


def test_setup_preserves_custom_config_and_existing_token(tmp_path):
    target = tmp_path / ".env"
    original = "CORTEX_ADMIN_TOKEN=" + "a" * 40 + "\nCORTEX_OPERATOR_TOKEN=\nCUSTOM_SETTING=yes\n"
    target.write_text(original)
    generated = setup_local(target, tmp_path / "unused")
    assert set(generated) == {"CORTEX_OPERATOR_TOKEN", "CORTEX_VIEWER_TOKEN"}
    assert target.read_text().startswith(original)
    assert dotenv_values(target)["CORTEX_ADMIN_TOKEN"] == "a" * 40


def test_setup_rejects_weak_existing_token_without_overwriting(tmp_path):
    target = tmp_path / ".env"
    target.write_text("CORTEX_ADMIN_TOKEN=FAKE_SHORT\n")
    before = target.read_bytes()
    with pytest.raises(ValueError, match="too short"):
        setup_local(target, tmp_path / "unused")
    assert target.read_bytes() == before
    assert not (tmp_path / ".env.setup.lock").exists()
