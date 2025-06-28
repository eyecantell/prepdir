from typing import Dict, Tuple
import logging
import re

logger = logging.getLogger(__name__)

HYPHENATED_UUID_PATTERN = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
UNHYPHENATED_UUID_PATTERN = re.compile(r"\b[0-9a-fA-F]{32}\b")
EITHER_UUID_PATTERN = re.compile(f"{HYPHENATED_UUID_PATTERN.pattern}|{UNHYPHENATED_UUID_PATTERN.pattern}")


def is_valid_uuid(
    value: str,
) -> bool:  # PRW consider making sure uuids that are scrubbed are actually valid UUIDs in additiona to matching the uuid pattern.
    """Check if a string is a valid UUID."""
    try:
        import uuid

        uuid.UUID(value)
        return True
    except ValueError:
        return False


def scrub_uuids(
    content: str,
    use_unique_placeholders: bool = False,
    replacement_uuid: str = "00000000-0000-0000-0000-000000000000",
    scrub_hyphenated_uuids: bool = False,
    scrub_hyphenless_uuids: bool = False,
    verbose: bool = False,
    placeholder_counter: int = 1,
    uuid_mapping: Dict[str, str] = None,
) -> Tuple[str, bool, Dict[str, str], int]:
    """Scrub UUIDs in content, replacing with a fixed UUID or unique placeholders.

    Args:
        content: The input string to process.
        use_unique_placeholders: If True, use unique placeholders (e.g., PREPDIR_UUID_PLACEHOLDER_n).
        replacement_uuid: UUID to use as replacement when use_unique_placeholders=False.
        scrub_hyphenated_uuids: If True, scrub standard UUIDs (e.g., 123e4567-e89b-12d3-a456-426614174000).
        scrub_hyphenless_uuids: If True, scrub hyphen-less UUIDs (e.g., 123e4567e89b12d3a456426614174000).
        verbose: If True, log scrubbing details.
        placeholder_counter: Starting counter for unique placeholders.
        uuid_mapping: Optional existing mapping of placeholders to original UUIDs for reuse.

    Returns:
        Tuple of (scrubbed content, is_scrubbed flag, UUID mapping, updated placeholder counter).

    Raises:
        ValueError: If replacement_uuid is invalid.
    """
    is_scrubbed = False
    uuid_mapping = {} if uuid_mapping is None else uuid_mapping.copy()  # Use copy to avoid modifying input
    reverse_uuid_mapping = {v: k for k, v in uuid_mapping.items()}  # Reverse lookup for O(1) checks

    # Initialize placeholder_counter to avoid collisions with existing placeholders
    if use_unique_placeholders and uuid_mapping:
        max_counter = max(
            (int(k.split("_")[-1]) for k in uuid_mapping if k.startswith("PREPDIR_UUID_PLACEHOLDER_")), default=0
        )
        placeholder_counter = max(max_counter + 1, placeholder_counter)

    # Validate replacement_uuid
    if not HYPHENATED_UUID_PATTERN.fullmatch(replacement_uuid):
        raise ValueError(
            "replacement_uuid must be a valid UUID with hyphens (e.g., 123e4567-e89b-12d3-a456-426614174000)"
        )

    def replacement_uuid_to_use(match):
        nonlocal is_scrubbed, placeholder_counter
        original_uuid = match.group(0)
        # Check if UUID is already mapped
        placeholder = reverse_uuid_mapping.get(original_uuid)
        if placeholder is None:
            is_scrubbed = True
            if use_unique_placeholders:
                # Ensure we don't reuse a placeholder by checking all existing ones
                while f"PREPDIR_UUID_PLACEHOLDER_{placeholder_counter}" in uuid_mapping:
                    placeholder_counter += 1
                placeholder = f"PREPDIR_UUID_PLACEHOLDER_{placeholder_counter}"
                logger.debug(f"Setting new unique mapping {placeholder} -> {original_uuid}")
                uuid_mapping[placeholder] = original_uuid
                reverse_uuid_mapping[original_uuid] = placeholder
                placeholder_counter += 1
            else:
                placeholder = replacement_uuid if "-" in original_uuid else replacement_uuid.replace("-", "")
                if original_uuid not in reverse_uuid_mapping:
                    logger.debug(f"Setting new regular replacement mapping {placeholder} -> {original_uuid}")
                    uuid_mapping[placeholder] = original_uuid
                    reverse_uuid_mapping[original_uuid] = placeholder
        if verbose:
            logger.info(f"Scrubbed UUID: {original_uuid} -> {placeholder}")
        return placeholder

    new_content = content

    # Apply scrubbing only for enabled flags
    if scrub_hyphenated_uuids and scrub_hyphenless_uuids:
        new_content = EITHER_UUID_PATTERN.sub(replacement_uuid_to_use, new_content)
    else:
        if scrub_hyphenated_uuids:
            new_content = HYPHENATED_UUID_PATTERN.sub(replacement_uuid_to_use, new_content)
        if scrub_hyphenless_uuids:
            new_content = UNHYPHENATED_UUID_PATTERN.sub(replacement_uuid_to_use, new_content)

    return new_content, is_scrubbed, uuid_mapping, placeholder_counter


def restore_uuids(content: str, uuid_mapping: Dict[str, str], is_scrubbed: bool = False) -> str:
    """Restore original UUIDs in content using the provided UUID mapping.

    Args:
        content: The input string with placeholders.
        uuid_mapping: Mapping of placeholders to original UUIDs.
        is_scrubbed: If True, indicates UUIDs were scrubbed.

    Returns:
        Content with placeholders replaced by original UUIDs.
    """
    if not is_scrubbed or not uuid_mapping:
        return content
    result = content
    for placeholder, original_uuid in uuid_mapping.items():
        pattern = rf"\b{re.escape(placeholder)}\b"
        result = re.sub(pattern, original_uuid, result)
    return result
