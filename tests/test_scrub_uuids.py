import pytest
import logging
from prepdir import scrub_uuids, restore_uuids
from unittest.mock import Mock

hyphenated_uuid = "12345678-1234-5678-1234-567812345678"
hyphenless_uuid = "aaaaaaaa111111111111111111111111"
partial_uuid = "2345678-1234-5678-1234-567812345678"

@pytest.fixture
def sample_content():
    """Provide sample content with UUIDs."""
    return (
        "print('Hello')\n"
        f"# UUID: {hyphenated_uuid}\n"                  # Should match hyphenated/regular UUIDs for replacement
        f"# Hyphenless: {hyphenless_uuid}\n"            # Should match hyphenless UUIDs for replacement
        f"# Partial: prefix-{partial_uuid}-suffix\n"    # Should not match any UUIDs for replacement
        f"# Embedded: 0{hyphenated_uuid}90"             # Should not match any UUIDs for replacement
    )

def test_scrub_hyphenated_uuids(sample_content):
    """Test scrubbing only hyphenated UUIDs."""
    content, is_scrubbed, uuid_mapping, counter = scrub_uuids(
        content=sample_content,
        use_unique_placeholders=True,
        replacement_uuid="00000000-0000-0000-0000-000000000000",
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=False,
        verbose=True,
    )
    print(f"{content=}\n{is_scrubbed=}\n{uuid_mapping=}\n{counter=}")
    assert f"UUID: PREPDIR_UUID_PLACEHOLDER_1" in content  # Hyphenated should be scrubbed
    assert f"Hyphenless: {hyphenless_uuid}" in content     # Hyphenless should not be scrubbed
    assert f"Partial: prefix-{partial_uuid}-suffix" in content  # Partial not scrubbed
    assert f"Embedded: 0{hyphenated_uuid}90" in content    # Embedded not scrubbed
    assert uuid_mapping == {
        "PREPDIR_UUID_PLACEHOLDER_1": f"{hyphenated_uuid}"
    }
    assert is_scrubbed is True
    assert counter == 2

def test_scrub_hyphenless_uuids(sample_content):
    """Test scrubbing only hyphenless UUIDs."""
    content, is_scrubbed, uuid_mapping, counter = scrub_uuids(
        content=sample_content,
        use_unique_placeholders=True,
        replacement_uuid="00000000-0000-0000-0000-000000000000",
        scrub_hyphenated_uuids=False,
        scrub_hyphenless_uuids=True,
        verbose=True,
    )
    print(f"{content=}\n{is_scrubbed=}\n{uuid_mapping=}\n{counter=}")
    assert f"UUID: {hyphenated_uuid}" in content           # Hyphenated not scrubbed
    assert f"Hyphenless: PREPDIR_UUID_PLACEHOLDER_1" in content  # Hyphenless should be scrubbed
    assert f"Partial: prefix-{partial_uuid}-suffix" in content  # Partial not scrubbed
    assert f"Embedded: 0{hyphenated_uuid}90" in content    # Embedded not scrubbed
    assert uuid_mapping == {
        "PREPDIR_UUID_PLACEHOLDER_1": f"{hyphenless_uuid}"
    }
    assert is_scrubbed is True
    assert counter == 2

def test_scrub_both_uuids(sample_content):
    """Test scrubbing both hyphenated and hyphenless UUIDs."""
    content, is_scrubbed, uuid_mapping, counter = scrub_uuids(
        content=sample_content,
        use_unique_placeholders=True,
        replacement_uuid="00000000-0000-0000-0000-000000000000",
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=True,
        verbose=True,
    )
    print(f"{content=}\n{is_scrubbed=}\n{uuid_mapping=}\n{counter=}")
    assert f"UUID: PREPDIR_UUID_PLACEHOLDER_1" in content  # Hyphenated should be scrubbed
    assert f"Hyphenless: PREPDIR_UUID_PLACEHOLDER_2" in content  # Hyphenless should be scrubbed
    assert f"Partial: prefix-{partial_uuid}-suffix" in content  # Partial not scrubbed
    assert f"Embedded: 0{hyphenated_uuid}90" in content    # Embedded not scrubbed
    assert uuid_mapping == {
        "PREPDIR_UUID_PLACEHOLDER_1": f"{hyphenated_uuid}",
        "PREPDIR_UUID_PLACEHOLDER_2": f"{hyphenless_uuid}",
    }
    assert is_scrubbed is True
    assert counter == 3

def test_scrub_with_fixed_uuid(sample_content):
    """Test scrubbing with a fixed replacement UUID."""
    content, is_scrubbed, uuid_mapping, counter = scrub_uuids(
        content=sample_content,
        use_unique_placeholders=False,
        replacement_uuid="11111111-2222-3333-4444-555555555555",
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=True,
        verbose=True,
    )
    print(f"{content=}\n{is_scrubbed=}\n{uuid_mapping=}\n{counter=}")
    assert f"UUID: 11111111-2222-3333-4444-555555555555" in content
    assert f"Hyphenless: 11111111222233334444555555555555" in content
    assert f"Partial: prefix-{partial_uuid}-suffix" in content
    assert f"Embedded: 0{hyphenated_uuid}90" in content
    assert uuid_mapping == {
        "11111111-2222-3333-4444-555555555555": f"{hyphenated_uuid}",
        "11111111222233334444555555555555": f"{hyphenless_uuid}",
    }
    assert is_scrubbed is True
    assert counter == 1

def test_no_scrubbing(sample_content):
    """Test when no UUIDs are scrubbed."""
    content, is_scrubbed, uuid_mapping, counter = scrub_uuids(
        content=sample_content,
        use_unique_placeholders=True,
        replacement_uuid="00000000-0000-0000-0000-000000000000",
        scrub_hyphenated_uuids=False,
        scrub_hyphenless_uuids=False,
        verbose=True,
    )
    print(f"{content=}\n{is_scrubbed=}\n{uuid_mapping=}\n{counter=}")
    assert content == sample_content
    assert f"UUID: {hyphenated_uuid}" in content
    assert f"Hyphenless: {hyphenless_uuid}" in content
    assert f"Partial: prefix-{partial_uuid}-suffix" in content
    assert f"Embedded: 0{hyphenated_uuid}90" in content
    assert is_scrubbed is False
    assert uuid_mapping == {}
    assert counter == 1

def test_reuse_uuid_mapping():
    """Test reusing uuid_mapping across multiple calls with reverse dictionary."""
    shared_mapping = {}
    content1 = f"UUID: {hyphenated_uuid}"
    content2 = f"Another: {hyphenated_uuid}"
    
    content1, is_scrubbed1, mapping1, counter = scrub_uuids(
        content=content1,
        use_unique_placeholders=True,
        replacement_uuid="00000000-0000-0000-0000-000000000000",
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=False,
        verbose=True,
        uuid_mapping=shared_mapping,
    )
    print(f"{content1=}\n{is_scrubbed1=}\n{mapping1=}\n{counter=}")
    assert "PREPDIR_UUID_PLACEHOLDER_1" in content1
    assert is_scrubbed1 is True
    assert mapping1 == {"PREPDIR_UUID_PLACEHOLDER_1": f"{hyphenated_uuid}"}
    assert counter == 2
    
    content2, is_scrubbed2, mapping2, counter = scrub_uuids(
        content=content2,
        use_unique_placeholders=True,
        replacement_uuid="00000000-0000-0000-0000-000000000000",
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=False,
        verbose=True,
        uuid_mapping=shared_mapping,
    )
    print(f"{content2=}\n{is_scrubbed2=}\n{mapping2=}\n{counter=}")
    assert "PREPDIR_UUID_PLACEHOLDER_1" in content2  # Same placeholder reused
    assert is_scrubbed2 is True
    assert mapping2 == {"PREPDIR_UUID_PLACEHOLDER_1": f"{hyphenated_uuid}"}
    assert counter == 2  # Counter doesn't increment since UUID was reused

def test_reuse_uuid_mapping_fixed():
    """Test reusing uuid_mapping with fixed replacement_uuid."""
    shared_mapping = {}
    content1 = f"UUID: {hyphenated_uuid}"
    content2 = f"Another: {hyphenated_uuid}"
    
    content1, is_scrubbed1, mapping1, counter = scrub_uuids(
        content=content1,
        use_unique_placeholders=False,
        replacement_uuid="11111111-2222-3333-4444-555555555555",
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=False,
        verbose=True,
        uuid_mapping=shared_mapping,
    )
    print(f"{content1=}\n{is_scrubbed1=}\n{mapping1=}\n{counter=}")
    assert "11111111-2222-3333-4444-555555555555" in content1
    assert is_scrubbed1 is True
    assert mapping1 == {"11111111-2222-3333-4444-555555555555": f"{hyphenated_uuid}"}
    assert counter == 1
    
    content2, is_scrubbed2, mapping2, counter = scrub_uuids(
        content=content2,
        use_unique_placeholders=False,
        replacement_uuid="11111111-2222-3333-4444-555555555555",
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=False,
        verbose=True,
        uuid_mapping=shared_mapping,
    )
    print(f"{content2=}\n{is_scrubbed2=}\n{mapping2=}\n{counter=}")
    assert "11111111-2222-3333-4444-555555555555" in content2
    assert is_scrubbed2 is True
    assert mapping2 == {"11111111-2222-3333-4444-555555555555": f"{hyphenated_uuid}"}
    assert counter == 1

def test_reuse_uuid_mapping_multiple_uuids():
    """Test reusing uuid_mapping with multiple UUIDs."""
    shared_mapping = {}
    content1 = f"UUID1: {hyphenated_uuid}\nUUID2: aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    content2 = f"UUID1: {hyphenated_uuid}\nUUID2: aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    
    content1, is_scrubbed1, mapping1, counter = scrub_uuids(
        content=content1,
        use_unique_placeholders=True,
        replacement_uuid="00000000-0000-0000-0000-000000000000",
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=False,
        verbose=True,
        uuid_mapping=shared_mapping,
    )
    print(f"{content1=}\n{is_scrubbed1=}\n{mapping1=}\n{counter=}")
    assert "PREPDIR_UUID_PLACEHOLDER_1" in content1
    assert "PREPDIR_UUID_PLACEHOLDER_2" in content1
    assert is_scrubbed1 is True
    assert mapping1 == {
        "PREPDIR_UUID_PLACEHOLDER_1": f"{hyphenated_uuid}",
        "PREPDIR_UUID_PLACEHOLDER_2": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    }
    assert counter == 3
    
    content2, is_scrubbed2, mapping2, counter = scrub_uuids(
        content=content2,
        use_unique_placeholders=True,
        replacement_uuid="00000000-0000-0000-0000-000000000000",
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=False,
        verbose=True,
        uuid_mapping=shared_mapping,
    )
    print(f"{content2=}\n{is_scrubbed2=}\n{mapping2=}\n{counter=}")
    assert "PREPDIR_UUID_PLACEHOLDER_1" in content2
    assert "PREPDIR_UUID_PLACEHOLDER_2" in content2
    assert is_scrubbed2 is True
    assert mapping2 == {
        "PREPDIR_UUID_PLACEHOLDER_1": f"{hyphenated_uuid}",
        "PREPDIR_UUID_PLACEHOLDER_2": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    }
    assert counter == 3  # Counter doesn't increment since UUIDs were reused

def test_reuse_uuid_mapping_large():
    """Test reusing uuid_mapping with a large number of UUIDs and correct placeholder_counter."""
    shared_mapping = {
        f"PREPDIR_UUID_PLACEHOLDER_{i}": f"{i:08x}-0000-0000-0000-000000000000"
        for i in range(1, 1001)  # 1 to 1000
    }
    content = f"UUID: 00000001-0000-0000-0000-000000000000\nNew: {hyphenated_uuid}"
    
    content, is_scrubbed, mapping, counter = scrub_uuids(
        content=content,
        use_unique_placeholders=True,
        replacement_uuid="00000000-0000-0000-0000-000000000000",
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=False,
        verbose=True,
        uuid_mapping=shared_mapping,
    )
    print(f"{content=}\n{is_scrubbed=}\n{mapping=}\n{counter=}")
    assert "PREPDIR_UUID_PLACEHOLDER_1" in content  # Reuses existing placeholder
    assert "PREPDIR_UUID_PLACEHOLDER_1001" in content  # New UUID gets next counter
    assert is_scrubbed is True
    assert mapping["PREPDIR_UUID_PLACEHOLDER_1"] == "00000001-0000-0000-0000-000000000000"
    assert mapping["PREPDIR_UUID_PLACEHOLDER_1001"] == f"{hyphenated_uuid}"
    assert counter == 1002  # Counter increments correctly

def test_logging_all_replacements(caplog):
    """Test that all UUID replacements (new and reused) are logged when verbose=True."""
    caplog.set_level(logging.INFO)
    shared_mapping = {
        "PREPDIR_UUID_PLACEHOLDER_1": f"{hyphenated_uuid}"
    }
    content = (
        f"UUID1: {hyphenated_uuid}\n"
        f"UUID2: {hyphenated_uuid}\n"  # Same UUID, should reuse placeholder
        "UUID3: aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    )
    
    content, is_scrubbed, mapping, counter = scrub_uuids(
        content=content,
        use_unique_placeholders=True,
        replacement_uuid="00000000-0000-0000-0000-000000000000",
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=False,
        verbose=True,
        uuid_mapping=shared_mapping,
    )
    print(f"{content=}\n{is_scrubbed=}\n{mapping=}\n{counter=}")
    assert "PREPDIR_UUID_PLACEHOLDER_1" in content
    assert "PREPDIR_UUID_PLACEHOLDER_2" in content
    assert is_scrubbed is True
    assert len(caplog.records) == 3  # Log all replacements (two for UUID1/UUID2, one for UUID3)
    assert f"Scrubbed UUID: {hyphenated_uuid} -> PREPDIR_UUID_PLACEHOLDER_1" in caplog.text
    assert f"Scrubbed UUID: aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa -> PREPDIR_UUID_PLACEHOLDER_2" in caplog.text

def test_restore_uuids(sample_content):
    """Test restoring UUIDs."""
    content, is_scrubbed, uuid_mapping, counter = scrub_uuids(
        content=sample_content,
        use_unique_placeholders=True,
        replacement_uuid="00000000-0000-0000-0000-000000000000",
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=True,
        verbose=True,
    )
    print(f"{content=}\n{is_scrubbed=}\n{uuid_mapping=}\n{counter=}")
    restored = restore_uuids(content, uuid_mapping, is_scrubbed)
    assert restored == sample_content
    assert f"UUID: {hyphenated_uuid}" in restored
    assert f"Hyphenless: {hyphenless_uuid}" in restored
    assert f"Partial: prefix-{partial_uuid}-suffix" in restored
    assert f"Embedded: 0{hyphenated_uuid}90" in restored
    assert "PREPDIR_UUID_PLACEHOLDER" not in restored

def test_restore_no_scrubbing(sample_content):
    """Test restoring when no scrubbing occurred."""
    content, is_scrubbed, uuid_mapping, counter = scrub_uuids(
        content=sample_content,
        use_unique_placeholders=True,
        replacement_uuid="00000000-0000-0000-0000-000000000000",
        scrub_hyphenated_uuids=False,
        scrub_hyphenless_uuids=False,
        verbose=True,
    )
    print(f"{content=}\n{is_scrubbed=}\n{uuid_mapping=}\n{counter=}")
    restored = restore_uuids(content, uuid_mapping, is_scrubbed)
    assert restored == sample_content
    assert f"UUID: {hyphenated_uuid}" in restored
    assert f"Hyphenless: {hyphenless_uuid}" in restored
    assert f"Partial: prefix-{partial_uuid}-suffix" in restored
    assert f"Embedded: 0{hyphenated_uuid}90" in restored

def test_invalid_replacement_uuid(sample_content):
    """Test invalid replacement_uuid."""
    with pytest.raises(ValueError, match="replacement_uuid must be a valid UUID"):
        content, is_scrubbed, uuid_mapping, counter = scrub_uuids(
            content=sample_content,
            use_unique_placeholders=False,
            replacement_uuid="invalid-uuid",
            scrub_hyphenated_uuids=True,
            scrub_hyphenless_uuids=False,
            verbose=True,
        )
        print(f"{content=}\n{is_scrubbed=}\n{uuid_mapping=}\n{counter=}")