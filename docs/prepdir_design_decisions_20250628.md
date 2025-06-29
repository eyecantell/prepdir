# Prepdir Design Decisions 2025-06-28

This document outlines the design decisions for `prepdir`, a utility to prepare project directory contents by generating and parsing a formatted output file (`prepped_dir.txt`). It integrates with `vibedir` (orchestrates LLM interactions) and `applydir` (applies changes to the filesystem) to manage codebase modifications. The design focuses on keeping `prepdir` lightweight and stable, with generation and parsing handled by `PrepdirProcessor`, `PrepdirFileEntry`, and `PrepdirOutputFile`, while `applydir` manages application logic. This document describes the current design, rationale, and integration with `applydir` and `vibedir`.

## Project Context

- **Prepdir**: Generates `prepped_dir.txt` containing project files’ contents, optionally scrubbing UUIDs with unique placeholders or a fixed UUID, and parses modified versions into a `PrepdirOutputFile`. Designed for simplicity and stability to support widespread adoption.
- **Applydir**: A separate repository that applies `PrepdirOutputFile` changes to the filesystem, generates diffs, and lists changed or new files using `PrepdirApplicator`.
- **Vibedir**: Uses `prepdir` to generate and validate `prepped_dir.txt`, sends it to an LLM for modifications, and uses `applydir` to apply changes and report diffs or file lists.
- **Components**:
  - `prepdir`: `PrepdirProcessor`, `PrepdirFileEntry`, `PrepdirOutputFile`, `config`, `scrub_uuids`.
  - `applydir`: `PrepdirApplicator` (depends on `prepdir` for `PrepdirOutputFile` and `PrepdirFileEntry`).

## Design Decisions

### 1. Prepdir Scope and Responsibilities

**Decision**: `prepdir` focuses on generating and parsing `prepped_dir.txt`, ensuring a lightweight, stable tool for directory preparation.

**Rationale**:
- **Adoption**: With ~6k downloads, `prepdir` prioritizes simplicity and reliability for generating and parsing project contents.
- **Modularity**: Separates generation/parsing from application logic, delegating the latter to `applydir`.
- **Interoperability**: Provides `PrepdirOutputFile` for `vibedir` and `applydir` to process and apply changes.

**Implementation**:
- **Components**:
  - `PrepdirProcessor`: Manages file traversal, UUID scrubbing, output generation, and parsing.
  - `PrepdirFileEntry`: Represents a single file’s metadata, content, and UUID mappings.
  - `PrepdirOutputFile`: Encapsulates `prepped_dir.txt` content, metadata, and file entries.
  - `config`: Handles `Dynaconf` configuration for extensions, exclusions, and UUID settings.
  - `scrub_uuids`: Manages UUID scrubbing and restoration.
- **Key Methods**:
  - `PrepdirProcessor.generate_output() -> PrepdirOutputFile`: Generates `prepped_dir.txt`.
  - `PrepdirProcessor.validate_output(content/file_path, highest_base_directory, ...) -> PrepdirOutputFile`: Parses and validates output.
  - `PrepdirProcessor.save_output(output, path)`: Saves `PrepdirOutputFile` to disk.

**Trade-Offs**:
- **Pro**: Lightweight design maximizes adoption and stability.
- **Con**: Users needing to apply changes must install `applydir`.
- **Mitigation**: Clear documentation and `vibedir` integration simplify setup.

### 2. PrepdirFileEntry for File Representation

**Decision**: Use `PrepdirFileEntry` to encapsulate a file’s metadata, content, and UUID mappings, shared with `applydir` and `vibedir`.

**Rationale**:
- **Standardization**: Simplifies handling of file data across tools.
- **UUID Management**: Supports scrubbing/restoration via `uuid_mapping`.
- **Extensibility**: Allows future additions (e.g., subroutine-level changes).
- **Interoperability**: Enables in-memory object passing to `applydir`.

**Implementation**:
- **Attributes**: `relative_path` (str), `absolute_path` (Path), `content` (str), `is_scrubbed` (bool), `is_binary` (bool), `error` (Optional[str]).
- **Methods**:
  - `to_output()`: Formats file content for `prepped_dir.txt`.
  - `restore_uuids(uuid_mapping)`: Restores original UUIDs.
  - `apply_changes(uuid_mapping)`: Writes restored content to disk (used by `applydir`).
- **Validation**: Pydantic ensures `absolute_path` is absolute, `relative_path` is relative.

### 3. PrepdirOutputFile for Aggregated Output

**Decision**: Use `PrepdirOutputFile` to represent `prepped_dir.txt`, encapsulating content, metadata, `uuid_mapping`, and `PrepdirFileEntry` objects.

**Rationale**:
- **Encapsulation**: Centralizes save, parse, and serialize operations.
- **Interoperability**: Simplifies passing to `vibedir` and `applydir`.
- **Metadata Management**: Stores `version`, `date`, `base_directory`, `creator` for context.

**Implementation**:
- **Attributes**: `path` (Optional[Path]), `content` (str), `files` (Dict[Path, PrepdirFileEntry]), `metadata` (Dict[str, str]), `uuid_mapping` (Dict[str, str]), `use_unique_placeholders` (bool), `placeholder_counter` (int).
- **Methods**:
  - `save()`: Writes content to disk.
  - `parse()`: Parses content into `files` and `metadata`.
  - `from_file(path)`: Creates from file.
  - `from_content(content)`: Creates from string.
- **Metadata**: Enforces `METADATA_KEYS` (`date`, `base_directory`, `creator`, `version`) via Pydantic.

### 4. Pydantic for Serialization and Validation

**Decision**: Use Pydantic for `PrepdirFileEntry` and `PrepdirOutputFile`.

**Rationale**:
- **Validation**: Ensures data integrity (e.g., valid paths, non-null metadata).
- **Type Safety**: Enhances IDE support and reduces errors.
- **Interoperability**: JSON-compatible output for debugging or external tools.

**Implementation**:
- Inherit from `pydantic.BaseModel`.
- Validators for `path`, `content`, `metadata`.
- Dependency: `pydantic>=2.5.0` (optional via `prepdir[pydantic]`).

**Trade-Offs**:
- **Pro**: Robust validation and serialization.
- **Con**: ~200 KB dependency.
- **Mitigation**: Optional via `prepdir[pydantic]`.

### 5. Applydir Integration

**Decision**: Move application logic to `applydir` with `PrepdirApplicator`, depending on `prepdir` for `PrepdirOutputFile` and `PrepdirFileEntry`.

**Rationale**:
- **Modularity**: Keeps `prepdir` focused on generation/parsing.
- **Extensibility**: `applydir` supports diffs, file listings, and future features (e.g., backups).
- **Reusability**: `PrepdirApplicator` can be used by `vibedir` or other tools.

**Implementation**:
- **Module**: `applydir.prepdir_applicator.PrepdirApplicator`.
- **Methods**:
  - `apply_changes(output, dry_run)`: Applies changes using `PrepdirFileEntry.apply_changes`.
  - `get_diffs(output)`: Generates unified diffs using `difflib`.
  - `list_changed_files(output)`: Lists modified or new files.
  - `list_new_files(output)`: Lists files not on disk.
- **Dependencies**: `prepdir`, `pydantic`.

**Trade-Offs**:
- **Pro**: Clear separation, supports `applydir` growth.
- **Con**: Users must install both packages.
- **Mitigation**: Clear documentation, `vibedir` simplifies integration.

### 6. Validate Output Design

**Decision**: `PrepdirProcessor.validate_output` parses content or file, enforces `highest_base_directory` for safety.

**Rationale**:
- **Flexibility**: Handles LLM output (string) or files for `vibedir`.
- **Safety**: Ensures `base_directory` and file paths stay within `highest_base_directory`.
- **Reliability**: Validates format and paths for `applydir`.

**Implementation**:
- Accepts `content` or `file_path`, `highest_base_directory`, `validate_files_exist`.
- Returns `PrepdirOutputFile`.
- Raises `ValueError` for invalid formats or path violations.

### 7. Configuration and Logging

**Decision**: Use `Dynaconf` for configuration and Python’s `logging` for output.

**Rationale**:
- **Flexibility**: `Dynaconf` supports `.yaml`, environment variables, and defaults.
- **Debugging**: Logging with `verbose` option aids troubleshooting.
- **Simplicity**: No additional config in `applydir` to keep it lightweight.

**Implementation**:
- Config: `DEFAULT_EXTENSIONS`, `EXCLUDE`, `SCRUB_HYPHENATED_UUIDS`, etc.
- Logging: `logging.getLogger(__name__)` with `DEBUG` level when `verbose=True`.

### 8. Backward Compatibility

**Decision**: Support `PrepdirProcessor.run(return_raw=True)` for tuple output (`content`, `uuid_mapping`, `files_list`, `metadata`).

**Rationale**:
- Ensures compatibility for existing users while defaulting to `PrepdirOutputFile`.

## Workflow Example

1. **Prepdir**:
   - `processor = PrepdirProcessor(directory=".", use_unique_placeholders=True)`
   - `output = processor.generate_output()`: Generates `prepped_dir.txt`.
   - `processor.save_output(output, "prepped_dir.txt")`: Saves to disk.
   - `modified_output = processor.validate_output(content=llm_output, highest_base_directory=".")`: Parses LLM-modified content.

2. **Applydir**:
   - `applicator = PrepdirApplicator(highest_base_directory=".")`
   - `diffs = applicator.get_diffs(modified_output)`: Shows changes.
   - `changed = applicator.list_changed_files(modified_output)`: Lists modified/new files.
   - `new = applicator.list_new_files(modified_output)`: Lists new files.
   - `failed = applicator.apply_changes(modified_output)`: Applies changes.

3. **Vibedir**:
   - Generates `prepped_dir.txt` with `prepdir`.
   - Sends to LLM, receives modified content.
   - Validates with `prepdir`, applies with `applydir`.

## Future Considerations

- **Subroutine Support**:
  - Add `subroutines` to `PrepdirFileEntry` for AST-based parsing.
  - Update `PrepdirOutputFile` to include subroutine metadata.
- **Applydir Enhancements**:
  - Add `apply_changes_with_backup` for backups.
  - Support conflict resolution for file writes.
- **Testing**:
  - Maintain ≥96% coverage for `prepdir` and `applydir`.
  - Add `vibedir` integration tests.

## Conclusion

`prepdir` is a lightweight, stable tool for generating and parsing `prepped_dir.txt`, currently serving ~6k users. By moving application logic to `applydir`, `prepdir` remains focused, while `applydir` enables advanced features for `vibedir`. The design ensures modularity, interoperability, and extensibility.