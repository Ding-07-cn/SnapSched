Part C: Calendar Export Module (generate_ics) Integration Notes
Draft v0.1 · Owner: Part C owner · Readers: A (UI, completed), D (coordination)


1. Module Responsibilities

In scope: Receive event data confirmed by Part A → validate → generate iCalendar-compliant .ics content → support pre-export simulated import validation.
Reserved capability for merging existing ICS (currently disabled).
Out of scope: File storage/transfer, UI logic (owned by A), non-export business logic.


3. Interface Contract

def generate_ics(event_data: dict, existing_ics_str: str | None = None) -> str

Output: ICS content string (importable into common calendar apps). On failure, raises an exception; no partial output is returned.
Disconnected state: When the function returned by load_backend is falsy → A disables the export button.


3. Integration with A

Aligned: A loads the module via load_backend("calendar_export", "generate_ics"); after confirmation, calls calendar_file_bytes(calendar.function(dict(confirmed_event)));
disables the button when function is falsy.

No changes needed from A: Call logic, single-event export path.

Needs confirmation from A:
Whether calendar_file_bytes's input shape matches generate_ics's return value (str vs bytes).
Whether error messages need to be differentiated by type (A currently catches all via except Exception).
registration_deadline / registration_method are marked optional in A's form but required in the contract — which takes precedence.
Whether a UI entry point is needed for the future "upload existing ICS to merge" feature.


4. Acceptance Criteria

□ Returned content parses with icalendar / ics without format errors
□ Merge-existing-ICS case passes (once enabled)
□ All exception types are raised correctly, and A shows an error with no downloadable file


5. Risks

Library compatibility
Non-standard existing ICS format
Exception contract not aligned with A

6. Module Structure
generate_calendar.py
    parser.py
        parse_event_fields()
        parse_and_convert_time()
    validator.py
        validate_event()
        validate_time_format()
        validate_time_logic()
        validate_string_content()
    ics_generator.py
        generate_ics_content()
        create_event_obj()
        load_existing_ics() (disabled)

   import_validator.py
        validate_import()

   exceptions.py
        EventValidationError
        ICSGenerationError
        ICSImportValidationError


