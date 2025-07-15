import pytest
from prepdir.main import main, run
from prepdir.prepdir_processor import PrepdirProcessor
from prepdir.config import __version__
from unittest.mock import patch
import sys
import yaml
import logging
from pathlib import Path
from unittest.mock import mock_open, MagicMock

HYPHENATED_UUID = "87654321-abcd-0000-0000-eeeeeeeeeeee"
UNHYPHENATED_UUID = "87654321abcd00000000ffffffffffff"
REPLACEMENT_UUID = "12340000-1234-0000-0000-000000000000"


@pytest.fixture(autouse=True)
def reset_loggers():
    """Reset logger levels to avoid interference."""
    logging.getLogger("prepdir.prepdir_processor").setLevel(logging.NOTSET)
    logging.getLogger("prepdir.prepdir_output_file").setLevel(logging.NOTSET)
    logging.getLogger("prepdir.prepdir_file_entry").setLevel(logging.NOTSET)
    logging.getLogger("prepdir").setLevel(logging.NOTSET)
    yield


@pytest.fixture
def custom_config(tmp_path):
    """Create a custom config file with exclusions for tests."""
    config_dir = tmp_path / ".prepdir"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_content = {
        "EXCLUDE": {
            "DIRECTORIES": [],
            "FILES": ["*.pyc"],
        },
        "SCRUB_HYPHENATED_UUIDS": True,
        "REPLACEMENT_UUID": REPLACEMENT_UUID,
        "SCRUB_HYPHENLESS_UUIDS": True,
    }
    config_file.write_text(yaml.safe_dump(config_content))
    return config_file


@pytest.fixture
def uuid_test_file(tmp_path):
    """Create a test file with UUIDs."""
    file = tmp_path / "test.txt"
    file.write_text(f"UUID: {HYPHENATED_UUID}\nHyphenless: {UNHYPHENATED_UUID}")
    return file


def test_main_version(capsys):
    """Test main() with --version flag."""
    with patch.object(sys, "argv", ["prepdir", "--version"]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
    captured = capsys.readouterr()
    from importlib.metadata import version

    assert "prepdir " + version("prepdir") in captured.out


def test_main_no_scrub_hyphenless_uuids(tmp_path, capsys, custom_config, uuid_test_file):
    """Test main() with --no-scrub-hyphenless-uuids preserves hyphenless UUIDs."""
    output_file = tmp_path / "prepped_dir.txt"
    with patch.object(
        sys,
        "argv",
        [
            "prepdir",
            str(tmp_path),
            "--no-scrub-hyphenless-uuids",
            "-o",
            str(output_file),
            "--config",
            str(custom_config),
        ],
    ):
        main()
    content = output_file.read_text()
    assert f"Hyphenless: {UNHYPHENATED_UUID}" in content
    assert f"UUID: {REPLACEMENT_UUID}" in content


def test_main_default_hyphenless_uuids(tmp_path, capsys, custom_config, uuid_test_file):
    """Test main() with default hyphenless UUID scrubbing from config."""
    output_file = tmp_path / "prepped_dir.txt"
    with patch.object(sys, "argv", ["prepdir", str(tmp_path), "-o", str(output_file), "--config", str(custom_config)]):
        main()
    content = output_file.read_text()
    assert f"Hyphenless: {str(REPLACEMENT_UUID).replace('-', '')}" in content
    assert f"UUID: {REPLACEMENT_UUID}" in content


def test_main_init_config(tmp_path, caplog):
    """Test main() with --init creates a config file."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    with caplog.at_level(logging.INFO, logger="prepdir"):
        with patch.object(sys, "argv", ["prepdir", "--init", "--config", str(config_path)]):
            main()
    assert f"Created '{config_path}' with default configuration." in caplog.text
    assert config_path.exists()
    content = config_path.read_text()
    assert "EXCLUDE" in content


def test_main_init_config_force(tmp_path, caplog):
    """Test main() with --init and force=True overwrites existing config."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir(exist_ok=True)
    config_path.write_text("existing: content")
    with caplog.at_level(logging.INFO, logger="prepdir"):
        with patch.object(sys, "argv", ["prepdir", "--init", "--config", str(config_path), "--force"]):
            main()
    assert f"Created '{config_path}' with default configuration." in caplog.text
    assert config_path.exists()
    content = config_path.read_text()
    assert "EXCLUDE" in content


def test_main_init_config_exists(tmp_path, capsys, caplog):
    """Test main() with --init fails if config exists without force=True."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir(exist_ok=True)
    config_path.write_text("existing: content")

    with caplog.at_level(logging.ERROR, logger="prepdir"):
        with patch.object(sys, "argv", ["prepdir", "--init", "--config", str(config_path)]):
            with pytest.raises(SystemExit):
                main()

    captured = capsys.readouterr()
    print(f"caplog.text is:\n{caplog.text}\n--")

    expected_message = f"Config file '{config_path}' already exists. Use force=True to overwrite"
    assert expected_message in caplog.text
    print(f"captured.out is:\n{captured.out}\n--")
    # print(f"captured.err is:\n{captured.err}\n--")
    assert expected_message in captured.out

    print(f"caplog.text is:\n{caplog.text}\n--")
    assert f"Config file '{config_path}' already exists. Use force=True to overwrite" in caplog.text


def test_main_init_config_invalid_path(tmp_path, capsys, caplog):
    """Test main() with --init and invalid config path."""
    invalid_path = "/invalid/path/config.yaml"
    with caplog.at_level(logging.ERROR, logger="prepdir"):
        with patch.object(sys, "argv", ["prepdir", "--init", "--config", invalid_path]):
            with pytest.raises(SystemExit) as exc:
                main()
            assert "Permission denied" in str(exc.value)
    print(f"caplog.text is {caplog.text}")
    assert f"Failed to create config file '{invalid_path}'" in caplog.text


def test_main_verbose_mode(tmp_path, capsys, custom_config, caplog, uuid_test_file):
    """Test main() with --verbose logs skipped files and prints to stdout."""
    test_file = tmp_path / "test.pyc"
    test_file.write_text("compiled")
    with caplog.at_level(logging.INFO, logger="prepdir"):
        with patch.object(sys, "argv", ["prepdir", str(tmp_path), "-v", "--config", str(custom_config)]):
            main()
    captured = capsys.readouterr()
    assert f"Starting prepdir in {tmp_path}" in captured.out
    assert "Skipping file: test.pyc (excluded in config)" in caplog.text


def test_main_custom_replacement_uuid(tmp_path, capsys, custom_config, uuid_test_file):
    """Test main() with --replacement-uuid uses custom UUID."""
    test_file = tmp_path / "test.txt"
    original_uuid = "12345678-1234-5678-1234-567812345678"
    replacement_uuid = "abcd1234-0000-0000-0000-000000000000"
    test_file.write_text(f"UUID: {original_uuid}")
    output_file = tmp_path / "prepped_dir.txt"
    with patch.object(
        sys,
        "argv",
        [
            "prepdir",
            str(tmp_path),
            "--replacement-uuid",
            replacement_uuid,
            "-o",
            str(output_file),
            "--config",
            str(custom_config),
        ],
    ):
        main()
    content = output_file.read_text()
    assert replacement_uuid in content
    assert original_uuid not in content


def test_main_invalid_directory(tmp_path, capsys, caplog):
    """Test main() with a non-existent directory."""
    invalid_dir = str(tmp_path / "nonexistent")
    with caplog.at_level(logging.ERROR, logger="prepdir"):
        with patch.object(sys, "argv", ["prepdir", invalid_dir]):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 1
    captured = capsys.readouterr()
    print(f"captured.err is:\n{captured.err}\n--")
    print(f"captured.out is:\n{captured.out}\n--")
    assert f"Error: Directory '{invalid_dir}' does not exist" in captured.err


def test_run_basic(tmp_path, uuid_test_file, custom_config):
    """Test run() with basic directory processing."""
    output = run(
        directory=str(tmp_path),
        extensions=["txt"],
        config_path=str(custom_config),
        quiet=True,
    )
    assert "test.txt" in output.content
    assert f"UUID: {REPLACEMENT_UUID}" in output.content
    assert f"Hyphenless: {str(REPLACEMENT_UUID).replace('-', '')}" in output.content
    assert output.metadata["base_directory"] == str(tmp_path)


def test_run_with_output_file(tmp_path, uuid_test_file, custom_config, tmp_path_factory):
    """Test run() with output file."""
    output_file = tmp_path_factory.mktemp("output") / "prepped_dir.txt"
    output = run(
        directory=str(tmp_path),
        extensions=["txt"],
        output_file=str(output_file),
        config_path=str(custom_config),
        quiet=True,
    )
    assert output_file.exists()
    content = output_file.read_text()
    assert "test.txt" in content
    assert f"UUID: {REPLACEMENT_UUID}" in content
    assert f"Hyphenless: {str(REPLACEMENT_UUID).replace('-', '')}" in content


def test_run_quiet_no_output_file(tmp_path, uuid_test_file, custom_config, capsys, caplog):
    """Test run() with quiet=False and no output file prints to stdout."""
    with caplog.at_level(logging.DEBUG, logger="prepdir"):
        with patch("prepdir.config.load_config", return_value=MagicMock()):
            output = run(
                directory=str(tmp_path),
                extensions=["txt"],
                config_path=str(custom_config),
                quiet=False,
            )
    captured = capsys.readouterr()
    print(f"captured.err is:\n{captured.err}\n--")
    print(f"captured.out is:\n{captured.out}\n--")
    print(f"caplog.text is:\n{caplog.text}\n--")
    assert "test.txt" in output.content
    assert f"UUID: {REPLACEMENT_UUID}" in output.content
    assert "Starting prepdir in" in captured.out
    assert output.content in captured.out


def test_main_debug_logging(tmp_path, caplog, uuid_test_file):
    """Test main() with -vv enables DEBUG logging."""
    with caplog.at_level(logging.DEBUG, logger="prepdir"):
        with patch.object(sys, "argv", ["prepdir", str(tmp_path), "-vv"]):
            main()
    assert "args are:" in caplog.text


def test_main_no_scrub_uuids(tmp_path, capsys, custom_config, uuid_test_file):
    """Test main() with --no-scrub-uuids preserves all UUIDs."""
    output_file = tmp_path / "prepped_dir.txt"
    with patch.object(
        sys,
        "argv",
        [
            "prepdir",
            str(tmp_path),
            "--no-scrub-uuids",
            "-o",
            str(output_file),
            "--config",
            str(custom_config),
        ],
    ):
        main()
    content = output_file.read_text()
    assert f"UUID: {HYPHENATED_UUID}" in content
    assert f"Hyphenless: {UNHYPHENATED_UUID}" in content


def test_main_all_flag(tmp_path, capsys, custom_config, uuid_test_file):
    """Test main() with --all ignores exclusions."""
    test_file = tmp_path / "test.pyc"
    test_file.write_text("compiled")
    output_file = tmp_path / "prepped_dir.txt"
    with patch.object(
        sys,
        "argv",
        [
            "prepdir",
            str(tmp_path),
            "--all",
            "-o",
            str(output_file),
            "--config",
            str(custom_config),
        ],
    ):
        main()
    content = output_file.read_text()
    assert "test.pyc" in content
    assert "compiled" in content


def test_main_quiet_suppresses_stdout(tmp_path, capsys, caplog, custom_config, uuid_test_file):
    """Test main() with --quiet suppresses stdout but logs errors."""
    invalid_file = tmp_path / "invalid.txt"
    invalid_file.write_text("content")

    def open_side_effect(*args, **kwargs):
        path_obj = args[0] if args and isinstance(args[0], (str, Path)) else None
        mode = kwargs.get("mode", "r") if not args or len(args) < 2 else args[1]
        path_resolved = Path(path_obj).resolve() if path_obj else None
        print(f"open_side_effect: args={args}, kwargs={kwargs}")
        print(f"open_side_effect: path={path_obj}, resolved={path_resolved}, mode={mode}")
        if path_resolved and path_resolved == invalid_file.resolve() and "r" in mode:
            print(f"Raising PermissionError for {path_obj}")
            raise PermissionError(f"[Errno 13] Permission denied: '{invalid_file}'")
        read_data = ""
        if path_resolved and path_resolved == uuid_test_file.resolve():
            read_data = f"UUID: {HYPHENATED_UUID}\nHyphenless: {UNHYPHENATED_UUID}"
        elif path_resolved and path_resolved == custom_config.resolve():
            read_data = yaml.safe_dump(
                {
                    "EXCLUDE": {"DIRECTORIES": [], "FILES": ["*.pyc"]},
                    "SCRUB_HYPHENATED_UUIDS": True,
                    "REPLACEMENT_UUID": REPLACEMENT_UUID,
                    "SCRUB_HYPHENLESS_UUIDS": True,
                }
            )
        return mock_open(read_data=read_data)(*args, **kwargs)

    with patch("builtins.open", side_effect=open_side_effect):
        with caplog.at_level(logging.DEBUG, logger="prepdir"):
            with patch.object(
                sys,
                "argv",
                [
                    "prepdir",
                    str(tmp_path),
                    "-o",
                    str(tmp_path / "prepped_dir.txt"),
                    "--config",
                    str(custom_config),
                    "-q",
                ],
            ):
                main()
    captured = capsys.readouterr()

    print(f"captured.out is:\n{captured.out}\n--")
    print(f"captured.err is:\n{captured.err}\n--")
    assert "Starting prepdir in" not in captured.out  # Suppressed by --quiet
    assert f"Failed to read {invalid_file}: [Errno 13] Permission denied: '{invalid_file}'" in caplog.text
    output_file = tmp_path / "prepped_dir.txt"
    assert output_file.exists()
    output_content = output_file.read_text()
    assert f"[Error reading file: [Errno 13] Permission denied: '{invalid_file}']" in output_content


def test_main_include_prepdir_files(tmp_path, capsys, custom_config):
    """Test main() with --include-prepdir-files includes prepdir-generated files."""
    test_file = tmp_path / "prepped_dir_previous.txt"
    test_file.write_text("previous prepdir output")
    output_file = tmp_path / "prepped_dir.txt"
    with patch.object(
        sys,
        "argv",
        [
            "prepdir",
            str(tmp_path),
            "--include-prepdir-files",
            "-o",
            str(output_file),
            "--config",
            str(custom_config),
        ],
    ):
        main()
    content = output_file.read_text()
    assert "prepped_dir_previous.txt" in content
    assert "previous prepdir output" in content
