"""Alembic revision chain sanity — no database writes."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

API_ROOT = Path(__file__).resolve().parents[1]
HEAD = "0082_user_mfa_foundation"
MATCHES = "0081_crm_matches_workspace"
LEADS = "0080_crm_leads_workspace"


def _script() -> ScriptDirectory:
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "alembic"))
    return ScriptDirectory.from_config(cfg)


def test_alembic_has_single_head() -> None:
    heads = _script().get_heads()
    assert heads == [HEAD]


def test_0081_0082_revision_chain_is_linear() -> None:
    script = _script()
    matches = script.get_revision(MATCHES)
    mfa = script.get_revision(HEAD)
    assert matches is not None
    assert mfa is not None
    assert matches.down_revision == LEADS
    assert mfa.down_revision == MATCHES


def test_revision_files_exist_on_disk() -> None:
    versions = API_ROOT / "alembic" / "versions"
    assert (versions / "0081_crm_matches_workspace.py").is_file()
    assert (versions / "0082_user_mfa_foundation.py").is_file()
    assert (versions / "0080_crm_leads_workspace.py").is_file()
