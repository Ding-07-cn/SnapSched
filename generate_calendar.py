# Import necessary modules
from parser import parse_event_fields
from validator import validate_event
from ics_generator import generate_ics_content, load_existing_ics
from import_validator import validate_import
from exceptions import EventValidationError, ICSGenerationError, ICSImportValidationError

def generate_ics(event_data: dict, existing_ics_str: str = None) -> str:
    """
    Generate merged ICS content
    Parameters:
        event_data: dictionary data of the new event
        existing_ics_str: content of the old ICS file (string), can be empty
    Returns:
        ICS format string
    Exceptions:
        Raised when event validation fails, generation fails, or import validation fails
    """
    try:
        # 1. Parse input event fields
        event = parse_event_fields(event_data)
        
        # 2. Validate event data
        validate_event(event)
        
        # 3. Process old ICS (if exists)
        if existing_ics_str:
            # Parse old ICS, extract event list
            old_events = load_existing_ics(existing_ics_str)
        else:
            # Create empty event list
            old_events = []

        # 4. Build new event object
        new_event = create_event_obj(event)
        new_event_id = get_event_id(new_event, event)  # According to rule: prefer UID, otherwise use combination

        # 5. Merge events
        # Build mapping from ID to event
        events_map = {}
        for ev in old_events:
            ev_id = get_event_id(ev, None)  # ID of old event
            events_map[ev_id] = ev
        # Replace or add new event
        events_map[new_event_id] = new_event

        # 6. Generate ICS content
        merged_events = list(events_map.values())
        ics_content = generate_ics_content(merged_events)

        # 7. Import validation (ensure format is correct)
        validate_import(ics_content)

        # 8. Return ICS string
        return ics_content

    except EventValidationError as e:
        # Event validation failed
        raise
    except ICSGenerationError as e:
        # Content generation failed
        raise
    except Exception as e:
        # Other exceptions
        raise RuntimeError(f"Failed to generate ICS: {str(e)}")


# Helper function: get event ID
def get_event_id(event_obj, event_dict):
    """
    Get event ID
    Priority: UID field of the event object (if exists)
    Otherwise: combination of event name + date + start_time
    """
    if hasattr(event_obj, 'uid') and event_obj.uid:
        return event_obj.uid
    elif event_dict:
        name = event_dict.get('event_name', '')
        date = event_dict.get('event_date', '')
        start_time = event_dict.get('start_time', '')
        return f"{name}_{date}_{start_time}"
    else:
        # Fallback: use some attribute of the event object or generate a unique ID
        return f"{event_obj.name}_{event_obj.begin}_{event_obj.end}"
