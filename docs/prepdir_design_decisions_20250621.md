# Prepdir Design Decisions 2025-06-21

This document outlines the design decisions made for the `prepdir` project, a utility for preparing project directory contents for review by generating a formatted output file (`prepped_dir.txt`). It integrates with partner projects `vibedir` (an orchestrator for LLM interactions) and `applydir` (applies LLM-generated changes back to the codebase). The decisions cover the core components (`PrepdirProcessor`, `PrepdirFileEntry`, `PrepdirOutputFile`), serialization with Pydantic, naming conventions, and future considerations.

## Project Context

- **Prepdir**: Generates `prepped_dir.txt` containing project files' contents, optionally scrubbing UUIDs, and parses LLM-modified versions of this file. It supports specific file selection, exclusion rules, and configuration via `Dynaconf`.
- **Vibedir**: Orchestrates the workflow by using `prepdir` to generate `prepped_dir.txt`, sends it to an LLM with prompts to modify files, and uses `prepdir` to parse the LLM's output (containing only changed files). It passes the parsed results to `applydir`.
- **Applydir**: Applies the LLM-generated changes to the codebase, restoring original UUIDs (if scrubbed) using UUID mappings from `prepdir`.

The design evolved through iterative discussions to create a shared data structure (`PrepdirFileEntry`) for file information, introduce `PrepdirOutputFile` for the output file, and adopt Pydantic for serialization to enhance interoperability and robustness.

## Key Design Decisions

### 1. Introduction of a Shared File Object (`PrepdirFileEntry`)

**Decision**: Create a class to encapsulate file metadata, content, and UUID mappings, shared between `prepdir` and `applydir`.

**Rationale**:
- **Standardization**: A unified data structure simplifies handling file data across `prepdir`, `vibedir`, and `applydir`.
- **UUID Management**: Encapsulating UUID mappings (e.g., `PREPDIR_UUID_PLACEHOLDER_1` to original UUIDs) streamlines restoration in `applydir`.
- **Extensibility**: Supports future subroutine-level changes (e.g., modifying specific functions) via a `subroutines` attribute.
- **Interoperability**: Enables `vibedir` to pass file objects in memory to `applydir`, reducing redundant parsing.

**Evolution**:
- Initially named `PrepdirFile`, it was renamed to `SinglePrepdirFile` to clarify it represents a single project file, not the output file (`prepped_dir.txt`).
- Later renamed to `PrepdirFileEntry` to emphasize its role as an entry in `PrepdirOutputFile`, aligning with the aggregated output's structure and avoiding redundancy in naming.

**Implementation**:
- **Attributes**: `relative_path`, `absolute_path`, `content`, `uuid_mapping`, `is_scrubbed`, `is_binary`, `error`, `subroutines` (placeholder for future use).
- **Methods**: `to_output` (generates formatted output for `prepped_dir.txt`), `restore_uuids` (reverts scrubbed UUIDs), and Pydantic-based serialization.
- **Usage**: Created by `PrepdirProcessor` during output generation, parsed from LLM output, and used by `applydir` to apply changes.

### 2. Creation of `PrepdirOutputFile`

**Decision**: Introduce a `PrepdirOutputFile` class to represent the `prepped_dir.txt` file, encapsulating its content, metadata, and associated `PrepdirFileEntry` objects.

**Rationale**:
- **Encapsulation**: Centralizes operations like saving, parsing, and serializing the output file, improving maintainability.
- **Interoperability**: Simplifies passing the output file to `vibedir` and `applydir` as a single object, reducing API complexity.
- **Future-Proofing**: Supports additional metadata (e.g., LLM prompts, subroutine delimiters) without breaking existing functionality.
- **Clarity**: Distinguishes between individual files (`PrepdirFileEntry`) and the aggregated output (`PrepdirOutputFile`).

**Considerations**:
- Initially deferred due to sufficient functionality in `PrepdirProcessor`'s tuple return (`content, uuid_mapping, files_list, metadata`).
- Added for future-proofing to handle complex metadata and streamline `vibedir`/`applydir` workflows.

**Implementation**:
- **Attributes**: `path` (optional file path), `content`, `files` (list of `PrepdirFileEntry`), `metadata` (version, timestamp, base directory, UUID settings).
- **Methods**: `save`, `parse` (regenerates `PrepdirFileEntry` objects), `from_file` (loads from disk), `from_processor_output` (creates from `PrepdirProcessor`).
- **Integration**: Returned by `PrepdirProcessor.generate_output` and `validate_output`, used by `vibedir` to send content to LLMs and by `applydir` to apply changes.

### 3. Use of Pydantic for Serialization

**Decision**: Adopt Pydantic for serialization of `PrepdirFileEntry` and `PrepdirOutputFile` instead of manual `to_dict`/`from_dict` methods.

**Rationale**:
- **Validation**: Ensures data integrity (e.g., valid `Path`, `Dict[str, str]` for `uuid_mapping`) during creation and deserialization.
- **Simplicity**: Replaces boilerplate serialization code with `model_dump` and `model_validate`, reducing maintenance.
- **Type Safety**: Enhances IDE support and static type checking with type hints.
- **Interoperability**: Produces JSON-compatible output for external tools, debugging, or persistence.
- **Future-Proofing**: Scales for complex structures (e.g., `subroutines`) and nested objects.

**Use Cases for Serialization**:
- Debugging: Save `PrepdirFileEntry` or `PrepdirOutputFile` to JSON for inspecting LLM inputs/outputs.
- Inter-Process Communication: Pass objects between `prepdir`, `vibedir`, and `applydir` in separate processes.
- Caching: Store intermediate results to resume workflows (e.g., after LLM failure).
- Audit Trail: Log serialized objects for traceability of changes.
- External Tools: Export data for CI/CD pipelines or UI dashboards.

**Implementation**:
- Both `PrepdirFileEntry` and `PrepdirOutputFile` inherit from `pydantic.BaseModel`.
- Validators convert strings to `Path` and ensure metadata defaults.
- Dependency added to `setup.py`/`pyproject.toml` (`pydantic>=2.5.0`).

**Trade-Offs**:
- **Con**: Adds a dependency, increasing package size (~200 KB).
- **Mitigation**: Pydantic is lightweight and widely used; made optional via `prepdir[pydantic]` if needed.
- **Con**: Minor performance overhead for validation.
- **Mitigation**: Negligible for `prepdir`’s small-scale data.

### 4. Naming Conventions

**Decision**: Evolve class names to ensure clarity and consistency:
- `PrepdirFile` → `SinglePrepdirFile` → `PrepdirFileEntry`.
- Introduced `PrepdirOutputFile` to complement `PrepdirFileEntry`.

**Rationale**:
- **PrepdirFile to SinglePrepdirFile**:
  - Addressed potential confusion with `prepped_dir.txt` by emphasizing "single" file.
  - Clarified role as an individual project file, not the output file.
- **SinglePrepdirFile to PrepdirFileEntry**:
  - "Entry" reflects its role as a component of `PrepdirOutputFile`, aligning with the output’s structure.
  - More concise, removing redundant "Single."
  - Future-proof for non-file entries (e.g., `PrepdirSubroutineEntry`).
- **PrepdirOutputFile**:
  - Clearly denotes the aggregated output (`prepped_dir.txt`).
  - Pairs intuitively with `PrepdirFileEntry`, forming a cohesive hierarchy.

**Impact**:
- Renaming required updating imports and references across `processor.py`, `main.py`, `output_file.py`, and tests.
- Maintained backward compatibility in `run` with a `return_raw` option to return a tuple for existing users.

### 5. PrepdirProcessor Enhancements

**Decision**: Update `PrepdirProcessor` to use `PrepdirFileEntry` and `PrepdirOutputFile`, streamlining output generation and parsing.

**Rationale**:
- **Centralized Logic**: `PrepdirProcessor` manages file traversal, UUID scrubbing, and output formatting, using `PrepdirFileEntry` for individual files.
- **Output Simplification**: Returning `PrepdirOutputFile` encapsulates all output data, reducing API complexity.
- **Parsing Consistency**: `validate_output` returns `PrepdirOutputFile`, aligning with `generate_output` for `vibedir`/`applydir` workflows.

**Implementation**:
- **generate_output**: Creates `PrepdirFileEntry` objects, assembles them into a `PrepdirOutputFile` with metadata.
- **validate_output**: Parses LLM-modified `prepped_dir.txt` into a `PrepdirOutputFile` using `validate_output_file`.
- **save_output**: Saves `PrepdirOutputFile.content` to disk.
- **Metadata**: Includes version, timestamp, base directory, and UUID settings for traceability.

### 6. Backward Compatibility

**Decision**: Maintain compatibility with existing `prepdir` users by supporting a `return_raw` option in `run`.

**Rationale**:
- Existing scripts may expect a tuple `(content, uuid_mapping, files_list, metadata)`.
- `return_raw=True` allows gradual migration to `PrepdirOutputFile` without breaking workflows.

**Implementation**:
- `run` defaults to returning `PrepdirOutputFile` but supports `return_raw` for the raw tuple.
- CLI unchanged, printing `PrepdirOutputFile.content` when no output file is specified.

### 7. Future Considerations

**Subroutine Support**:
- **Plan**: Extend `PrepdirFileEntry` with a `subroutines` list and define a `PrepdirSubroutineEntry` class.
- **Approach**: Use AST parsing for Python files to identify functions, add `Begin Subroutine`/`End Subroutine` delimiters in `prepped_dir.txt`.
- **Impact**: `PrepdirOutputFile` will store subroutine metadata, and `applydir` will apply subroutine-level changes.

**Enhanced Validation**:
- Add Pydantic validators for `PrepdirFileEntry.relative_path` (e.g., ensure not absolute) or `content` (e.g., format checks).
- Validate `PrepdirOutputFile` metadata for consistency across generation and parsing.

**Applydir Implementation**:
- Draft `applydir` to use `PrepdirOutputFile.files`, calling `restore_uuids` and writing to `absolute_path`.
- Example:
  ```python
  def apply_changes(output: PrepdirOutputFile):
      for entry in output.files:
          content = entry.restore_uuids()
          entry.absolute_path.write_text(content, encoding="utf-8")
  ```

**Testing**:
- Expand tests for edge cases (e.g., malformed `prepped_dir.txt`, binary files, invalid UUIDs).
- Add integration tests for `vibedir`/`applydir` workflows.

## Workflow Example

1. **Prepdir**:
   - `run(directory=".", return_raw=False)` generates a `PrepdirOutputFile` with `PrepdirFileEntry` objects.
   - Saves `prepped_dir.txt` if specified.
2. **Vibedir**:
   - Sends `PrepdirOutputFile.content` to the LLM.
   - Parses LLM output with `PrepdirProcessor.validate_output`, getting a new `PrepdirOutputFile`.
   - Passes the parsed `PrepdirOutputFile` to `applydir`.
3. **Applydir**:
   - Iterates over `PrepdirOutputFile.files`, restores UUIDs, and writes changes to disk.

## Conclusion

The `prepdir` design balances simplicity, extensibility, and interoperability with `vibedir` and `applydir`. Key decisions include:
- Using `PrepdirFileEntry` for individual files, renamed for clarity and future-proofing.
- Introducing `PrepdirOutputFile` to encapsulate the output file and metadata.
- Adopting Pydantic for robust serialization and validation.
- Maintaining backward compatibility for existing users.
- Planning for subroutine support and enhanced validation.

These choices create a cohesive architecture that supports the current workflow and scales for future features like subroutine-level changes and external integrations.