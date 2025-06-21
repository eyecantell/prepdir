import json
import pytest
import os
from prepdir import validate_output_file


def test_validate_output_file_empty_file(tmp_path):
    """Test validate_output_file with an empty file."""
    output_file = tmp_path / "empty.txt"
    output_file.write_text("")
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is False
    assert len(result["errors"]) == 1
    assert "File is empty." in result["errors"][0]
    assert result["warnings"] == []
    assert result["files"] == {}


def test_validate_output_file_valid_complete(tmp_path):
    """Test validate_output_file with a valid, complete prepdir output."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0 (pip install prepdir)\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= Begin File: 'file1.txt' =-=-=-=-=-=-=-=\n"
        "Content of file1\n"
        "Line 2\n"
        "=-=-=-=-=-=-=-= End File: 'file1.txt' =-=-=-=-=-=-=-=\n"
        "=-=-=-=-=-=-=-= Begin File: 'file2.py' =-=-=-=-=-=-=-=\n"
        "print('hello')\n"
        "=-=-=-=-=-=-=-= End File: 'file2.py' =-=-=-=-=-=-=-=\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["files"] == {"file1.txt": "Content of file1\nLine 2", "file2.py": "print('hello')"}


def test_validate_output_file_missing_base_directory(tmp_path):
    """Test validate_output_file with missing base directory line."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "=-=-=-=-=-=-=-= Begin File: 'test.txt' =-=-=-=-=-=-=-=\n"
        "content\n"
        "=-=-=-=-=-=-=-= End File: 'test.txt' =-=-=-=-=-=-=-=\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert len(result["warnings"]) == 1
    assert "Missing or invalid base directory line" in result["warnings"][0]
    assert result["files"] == {"test.txt": "content"}


def test_validate_output_file_unmatched_footer(tmp_path):
    """Test validate_output_file with footer without matching header."""
    output_file = tmp_path / "invalid.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= End File: 'test.txt' =-=-=-=-=-=-=-=\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is False
    assert len(result["errors"]) == 1
    assert "Footer for 'test.txt' without matching header" in result["errors"][0]
    assert result["files"] == {}


def test_validate_output_file_unclosed_header(tmp_path):
    """Test validate_output_file with header that has no matching footer."""
    output_file = tmp_path / "invalid.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= Begin File: 'test.txt' =-=-=-=-=-=-=-=\n"
        "content without footer\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is False
    assert len(result["errors"]) == 1
    assert "Header for 'test.txt' has no matching footer" in result["errors"][0]
    assert result["files"] == {"test.txt": "content without footer"}


def test_validate_output_file_malformed_delimiters(tmp_path):
    """Test validate_output_file with malformed header/footer delimiters."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= Begin File:\n"  # Missing filename in header
        "content\n"
        "=-=-=-=-=-=-=-= End File:\n"  # Missing filename in footer
        "=-=-=-=-=-=-=-= Begin File: 'good.txt' =-=-=-=-=-=-=-=\n"
        "good content\n"
        "=-=-=-=-=-=-=-= End File: 'good.txt' =-=-=-=-=-=-=-=\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is False
    assert any("Malformed header" in error for error in result["errors"])
    assert any("Malformed footer" in error for error in result["errors"])
    assert len(result["warnings"]) == 0
    assert result["files"] == {"good.txt": "good content"}


def test_validate_output_file_large_file(tmp_path):
    """Test validate_output_file with a large file to ensure performance."""
    output_file = tmp_path / "large.txt"
    content = "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\nBase directory is '/test'\n"
    # Generate a large file with 10,000 lines across 10 files
    for i in range(10):
        content += f"=-=-=-=-=-=-=-= Begin File: 'file{i}.txt' =-=-=-=-=-=-=-=\n"
        content += "\n".join(f"Line {j}" for j in range(1000)) + "\n"
        content += f"=-=-=-=-=-=-=-= End File: 'file{i}.txt' =-=-=-=-=-=-=-=\n"
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert len(result["files"]) == 10
    for i in range(10):
        assert f"file{i}.txt" in result["files"]
        assert result["files"][f"file{i}.txt"].count("\n") == 999  # 1000 lines minus one for joining


def test_validate_output_file_empty_files(tmp_path):
    """Test validate_output_file with files that have no content."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= Begin File: 'empty.txt' =-=-=-=-=-=-=-=\n"
        "=-=-=-=-=-=-=-= End File: 'empty.txt' =-=-=-=-=-=-=-=\n"
        "=-=-=-=-=-=-=-= Begin File: 'whitespace.txt' =-=-=-=-=-=-=-=\n"
        "   \n"
        "\t\n"
        "=-=-=-=-=-=-=-= End File: 'whitespace.txt' =-=-=-=-=-=-=-=\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["files"]["empty.txt"] == ""
    assert result["files"]["whitespace.txt"] == "   \n\t"


def test_validate_output_file_with_blank_lines(tmp_path):
    """Test validate_output_file preserves blank lines within file content."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= Begin File: 'test.txt' =-=-=-=-=-=-=-=\n"
        "line 1\n"
        "\n"
        "line 3\n"
        "\n"
        "\n"
        "line 6\n"
        "=-=-=-=-=-=-=-= End File: 'test.txt' =-=-=-=-=-=-=-=\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    expected_content = "line 1\n\nline 3\n\n\nline 6"
    assert result["files"]["test.txt"] == expected_content
    assert result["files"]["test.txt"].count("\n") == 5


def test_validate_output_file_unicode_error(tmp_path):
    """Test validate_output_file handles UnicodeDecodeError."""
    output_file = tmp_path / "invalid.bin"
    output_file.write_bytes(b"\xff\xfe\x00\x01")
    with pytest.raises(UnicodeDecodeError, match="Invalid encoding"):
        validate_output_file(str(output_file))


def test_validate_output_file_file_not_found(tmp_path):
    """Test validate_output_file with non-existent file."""
    with pytest.raises(FileNotFoundError, match="File '.*' does not exist"):
        validate_output_file(str(tmp_path / "nonexistent.txt"))


def test_validate_output_file_multiple_files_complex(tmp_path):
    """Test validate_output_file with multiple files and complex content."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 12:00:00.000000 by prepdir version 0.13.0\n"
        "Base directory is '/complex/test'\n"
        "Note: Valid UUIDs in file contents will be scrubbed\n"
        "\n"
        "=-=-=-=-=-=-=-= Begin File: 'src/main.py' =-=-=-=-=-=-=-=\n"
        "#!/usr/bin/env python3\n"
        "def main():\n"
        "    print('Hello, World!')\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    main()\n"
        "=-=-=-=-=-=-=-= End File: 'src/main.py' =-=-=-=-=-=-=-=\n"
        "=-=-=-=-=-=-=-= Begin File: 'README.md' =-=-=-=-=-=-=-=\n"
        "# Project Title\n"
        "\n"
        "This is a sample project.\n"
        "\n"
        "## Usage\n"
        "\n"
        "```bash\n"
        "python main.py\n"
        "```\n"
        "=-=-=-=-=-=-=-= End File: 'README.md' =-=-=-=-=-=-=-=\n"
        "=-=-=-=-=-=-=-= Begin File: 'config.json' =-=-=-=-=-=-=-=\n"
        "{\n"
        '  "name": "test",\n'
        '  "version": "1.0.0"\n'
        "}\n"
        "=-=-=-=-=-=-=-= End File: 'config.json' =-=-=-=-=-=-=-=\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert len(result["files"]) == 3
    assert "def main():" in result["files"]["src/main.py"]
    assert "# Project Title" in result["files"]["README.md"]
    assert '"name": "test"' in result["files"]["config.json"]
    assert result["files"]["src/main.py"].count("\n") == 5
    assert result["files"]["README.md"].count("\n") == 8
    assert result["files"]["config.json"].count("\n") == 3


def test_validate_output_file_malformed_timestamp(tmp_path):
    """Test validate_output_file with a malformed timestamp in header."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-13-99 25:99:99.999999 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= Begin File: 'test.txt' =-=-=-=-=-=-=-=\n"
        "content\n"
        "=-=-=-=-=-=-=-= End File: 'test.txt' =-=-=-=-=-=-=-=\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["files"] == {"test.txt": "content"}


def test_validate_output_file_missing_version(tmp_path):
    """Test validate_output_file with missing version in header."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= Begin File: 'test.txt' =-=-=-=-=-=-=-=\n"
        "content\n"
        "=-=-=-=-=-=-=-= End File: 'test.txt' =-=-=-=-=-=-=-=\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["files"] == {"test.txt": "content"}


def test_validate_output_file_mismatched_header_footer(tmp_path):
    """Test validate_output_file with mismatched header and footer."""
    output_file = tmp_path / "invalid.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= Begin File: 'file1.txt' =-=-=-=-=-=-=-=\n"
        "content\n"
        "=-=-=-=-=-=-=-= End File: 'file2.txt' =-=-=-=-=-=-=-=\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is False
    assert len(result["errors"]) == 2
    assert "Footer for 'file2.txt' does not match open header 'file1.txt'" in result["errors"][0]
    assert "Header for 'file1.txt' has no matching footer" in result["errors"][1]
    assert result["files"] == {"file1.txt": "content"}


def test_validate_output_file_partial_content(tmp_path):
    """Test validate_output_file with partial file content (incomplete delimiters)."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= Begin File: 'test.txt' =-=-=-=-=-=-=-=\n"
        "partial content\n"
        "incomplete delimiter =-=-=-\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is False
    assert len(result["errors"]) == 1
    assert "Header for 'test.txt' has no matching footer" in result["errors"][0]
    assert result["files"] == {"test.txt": "partial content\nincomplete delimiter =-=-=-"}


def test_validate_output_file_lenient_delimiters(tmp_path):
    """Test validate_output_file with lenient delimiters (various =/- combinations and whitespace)."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=== Begin File: 'file1.txt' ===\n"  # Short delimiter, equal signs
        "Content of file1\n"
        "--- End File: 'file1.txt' ---\n"  # Short delimiter, dashes
        "=-=-=  Begin File: 'file2.py'  =-=-=\n"  # Mixed delimiter with extra whitespace
        "print('hello')\n"
        "===== End File: 'file2.py' =====\n"  # Equal signs only
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["files"] == {"file1.txt": "Content of file1", "file2.py": "print('hello')"}


def test_validate_output_file_lenient_delimiters_with_extra_whitespace(tmp_path):
    """Test validate_output_file with lenient delimiters and excessive whitespace."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "==-==-==   Begin File: 'test.txt'    ==--==\n"  # Mixed delimiter, extra spaces
        "content\n"
        "--==--   End File: 'test.txt'   --==--\n"  # Mixed delimiter, extra spaces
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["files"] == {"test.txt": "content"}


def test_validate_output_file_mixed_lenient_malformed_delimiters(tmp_path):
    """Test validate_output_file with a mix of lenient and malformed delimiters."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=== Begin File: 'test.txt' ===\n"  # Valid lenient delimiter
        "content\n"
        "=== End File: 'test.txt' =--=\n"  # Valid lenient delimiters
        "==- Begin File:\n"  # Malformed header (no filename)
        "malformed content\n"
        "--==-- End File: 'other.txt' ---\n"  # Valid footer but no matching header
        "===== Begin File: 'valid.txt' ====-\n"  # Valid lenient delimiter
        "valid content\n"
        "=== End File: 'valid.txt' ---\n"  # Valid lenient delimiter
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    print(f"{result['errors']=}")
    print(f"{result['warnings']=}")
    assert result["is_valid"] is False
    assert len(result["errors"]) == 2
    assert any("Footer for 'other.txt' without matching header" in error for error in result["errors"])
    assert any("Malformed header" in error for error in result["errors"])
    assert len(result["warnings"]) == 0
    assert result["files"] == {"test.txt": "content", "valid.txt": "valid content"}


def test_validate_output_file_lenient_header_variations(tmp_path):
    """Test validate_output_file with variations in generated header."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010\n"  # No version or pip
        "Base directory is '/test'\n"
        "==-== Begin File: 'test.txt' ==-==\n"
        "content\n"
        "==--== End File: 'test.txt' ==--==\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["files"] == {"test.txt": "content"}


def test_validate_output_file_single_character_delimiters(tmp_path):
    """Test validate_output_file with single-character delimiters."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "= Begin File: 'test.txt' =\n"  # Single = delimiter is not recognized
        "content\n"
        "- End File: 'test.txt' -\n"  # Single - delimiter is not recognized
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is False
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["files"] == {}


def test_validate_output_file_first_line_header(tmp_path):
    """Test validate_output_file with a header on the first line."""
    output_file = tmp_path / "output.txt"
    content = "=== Begin File: 'test.txt' ===\ncontent\n=== End File: 'test.txt' ===\n"
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert any(
        "Missing or invalid file listing header" in warning for warning in result["warnings"]
    )  # No generated header
    assert result["files"] == {"test.txt": "content"}


def test_validate_output_file_creation_complete_header(tmp_path):
    """Test validate_output_file parses complete generated header into creation dict."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139876 by prepdir version 0.13.0 (pip install prepdir)\n"
        "Base directory is '/test'\n"
        "=== Begin File: 'test.txt' ===\n"
        "content\n"
        "=== End File: 'test.txt' ===\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["files"] == {"test.txt": "content"}
    assert result["creation"] == {"date": "2025-06-16 01:36:06.139876", "creator": "prepdir", "version": "0.13.0"}


def test_validate_output_file_creation_no_version(tmp_path):
    """Test validate_output_file parses header with no version into creation dict."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06 by some-tool\n"
        "Base directory is '/test'\n"
        "=== Begin File: 'test.txt' ===\n"
        "content\n"
        "=== End File: 'test.txt' ===\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["files"] == {"test.txt": "content"}
    assert result["creation"] == {"date": "2025-06-16 01:36:06", "creator": "some-tool", "version": "unknown"}


def test_validate_output_file_creation_starts_with_basedir(tmp_path):
    """Test validate_output_file parses header with base dir header but no main header line into creation dict."""
    output_file = tmp_path / "output.txt"
    content = "Base directory is '/test'\n=== Begin File: 'test.txt' ===\ncontent\n=== End File: 'test.txt' ===\n"
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert len(result["warnings"]) == 1
    assert any("Missing or invalid file listing header" in warning for warning in result["warnings"])
    assert result["files"] == {"test.txt": "content"}
    assert result["creation"] == {"date": "unknown", "creator": "unknown", "version": "unknown"}


def test_validate_output_file_creation_no_header(tmp_path):
    """Test validate_output_file with no generated header returns empty creation dict."""
    output_file = tmp_path / "output.txt"
    content = "=== Begin File: 'test.txt' ===\ncontent\n=== End File: 'test.txt' ===\n"
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert any("Missing or invalid file listing header" in warning for warning in result["warnings"])
    assert result["files"] == {"test.txt": "content"}
    assert result["creation"] == {"date": "unknown", "creator": "unknown", "version": "unknown"}
