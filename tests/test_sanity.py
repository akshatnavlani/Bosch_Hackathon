from agent import __version__
from agent.main import main


def test_version_present() -> None:
    assert __version__


def test_cli_help_exits_zero() -> None:
    assert main([]) == 0
