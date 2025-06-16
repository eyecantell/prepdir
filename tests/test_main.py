import pytest
from prepdir.main import main
from unittest.mock import patch
import sys

def test_main_version(capsys):
    with patch.object(sys, 'argv', ['prepdir', '--version']):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "prepdir 0.13.0" in captured.out