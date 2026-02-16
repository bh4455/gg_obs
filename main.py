import os
import sys
import obspython as obs

# Add script directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Import modules (with reload for development)
import importlib
import match_scene_handler
import bracket_handler
importlib.reload(match_scene_handler)
importlib.reload(bracket_handler)

from match_scene_handler import (
    load_roster,
    get_team_names,
    execute_transition,
)

from bracket_handler import (
    set_credentials,
    refresh_bracket,
    get_bracket_text_sources,
)

# =============================================================================
# SCRIPT STATE
# =============================================================================
hotkey_id = obs.OBS_INVALID_HOTKEY_ID
bracket_hotkey_id = obs.OBS_INVALID_HOTKEY_ID
selected_team1 = ""
selected_team2 = ""

# Dropdown property references for reloading
t1_list_prop = None
t2_list_prop = None


# =============================================================================
# UI HELPERS
# =============================================================================
def populate_team_dropdowns():
    """Populate both team dropdowns with current roster."""
    global t1_list_prop, t2_list_prop
    
    for dropdown in [t1_list_prop, t2_list_prop]:
        if dropdown:
            obs.obs_property_list_clear(dropdown)
            obs.obs_property_list_add_string(dropdown, "-- Select Team --", "")
            for team_name in get_team_names():
                obs.obs_property_list_add_string(dropdown, team_name, team_name)


# =============================================================================
# BRACKET HELPERS
# =============================================================================
def set_text_source(source_name: str, text: str):
    """Update text content of a text source."""
    source = obs.obs_get_source_by_name(source_name)
    if source:
        settings = obs.obs_data_create()
        obs.obs_data_set_string(settings, "text", text)
        obs.obs_source_update(source, settings)
        obs.obs_data_release(settings)
        obs.obs_source_release(source)
    else:
        print(f"[Bracket] Source not found: {source_name}")


def update_bracket_sources():
    """Fetch bracket data and update all bracket text sources."""
    refresh_bracket()
    
    source_map = get_bracket_text_sources()
    
    for source_name, team_name in source_map.items():
        set_text_source(source_name, team_name)
    
    print(f"[Bracket] Updated {len(source_map)} text sources")


# =============================================================================
# CALLBACKS
# =============================================================================
def on_hotkey(pressed):
    """Hotkey callback - triggers transition when pressed."""
    if pressed:
        execute_transition(obs, selected_team1, selected_team2)


def on_bracket_hotkey(pressed):
    """Hotkey callback - refreshes bracket when pressed."""
    if pressed:
        update_bracket_sources()


def on_apply_button(props, prop):
    """Button callback to manually trigger transition."""
    execute_transition(obs, selected_team1, selected_team2)
    return True


def on_refresh_bracket_button(props, prop):
    """Button callback to manually refresh bracket."""
    update_bracket_sources()
    return True


# =============================================================================
# OBS SCRIPT INTERFACE
# =============================================================================
def script_description():
    return (
        "<h2>Tournament Team Overlay</h2>"
        "<p>Select teams from the dropdowns and press the hotkey/button to update all sources.</p>"
        "<p>Use 'Refresh Bracket' to pull latest bracket data from Challonge.</p>"
    )


def script_properties():
    """Create the properties UI with team dropdowns."""
    global t1_list_prop, t2_list_prop
    
    props = obs.obs_properties_create()
    
    # --- Team Selection ---
    # Team 1 dropdown
    t1_list_prop = obs.obs_properties_add_list(
        props, "team1_select", "Team 1",
        obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING
    )
    
    # Team 2 dropdown
    t2_list_prop = obs.obs_properties_add_list(
        props, "team2_select", "Team 2",
        obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING
    )
    
    # Populate dropdowns with current roster
    populate_team_dropdowns()
    
    # Manual trigger button
    obs.obs_properties_add_button(
        props, "apply_button", "Apply Teams Now", on_apply_button
    )
    
    # Info text
    obs.obs_properties_add_text(
        props, "info", 
        "Tip: Set hotkeys in OBS Settings -> Hotkeys",
        obs.OBS_TEXT_INFO
    )
    
    # --- Challonge Settings ---
    obs.obs_properties_add_text(
        props, "api_key", "Challonge API Key",
        obs.OBS_TEXT_PASSWORD
    )
    obs.obs_properties_add_text(
        props, "tournament_id", "Tournament ID/URL",
        obs.OBS_TEXT_DEFAULT
    )
    
    # Refresh bracket button
    obs.obs_properties_add_button(
        props, "refresh_bracket_button", "Refresh Bracket", on_refresh_bracket_button
    )
    
    
    return props


def script_update(settings):
    """Called when settings are changed."""
    global selected_team1, selected_team2
    
    selected_team1 = obs.obs_data_get_string(settings, "team1_select")
    selected_team2 = obs.obs_data_get_string(settings, "team2_select")
    
    # Update Challonge credentials
    api_key = obs.obs_data_get_string(settings, "api_key")
    tournament_id = obs.obs_data_get_string(settings, "tournament_id")
    set_credentials(api_key, tournament_id)
    
    print(f"[Tournament] Settings updated: {selected_team1} vs {selected_team2}")


def script_load(settings):
    """Called when the script is loaded."""
    global hotkey_id, bracket_hotkey_id
    
    # Load roster from JSON
    load_roster()
    
    # Register the team switch hotkey
    hotkey_id = obs.obs_hotkey_register_frontend(
        "tournament_team_switch",
        "Tournament Team Switch",
        on_hotkey
    )
    
    # Register the bracket refresh hotkey
    bracket_hotkey_id = obs.obs_hotkey_register_frontend(
        "tournament_bracket_refresh",
        "Tournament Bracket Refresh",
        on_bracket_hotkey
    )
    
    # Load saved hotkey bindings
    hotkey_save_array = obs.obs_data_get_array(settings, "tournament_hotkey")
    obs.obs_hotkey_load(hotkey_id, hotkey_save_array)
    obs.obs_data_array_release(hotkey_save_array)
    
    bracket_hotkey_array = obs.obs_data_get_array(settings, "bracket_hotkey")
    obs.obs_hotkey_load(bracket_hotkey_id, bracket_hotkey_array)
    obs.obs_data_array_release(bracket_hotkey_array)
    
    print("[Tournament] Script loaded!")


def script_save(settings):
    """Called when OBS saves settings."""
    global hotkey_id, bracket_hotkey_id
    
    # Save team switch hotkey binding
    hotkey_save_array = obs.obs_hotkey_save(hotkey_id)
    obs.obs_data_set_array(settings, "tournament_hotkey", hotkey_save_array)
    obs.obs_data_array_release(hotkey_save_array)
    
    # Save bracket refresh hotkey binding
    bracket_hotkey_array = obs.obs_hotkey_save(bracket_hotkey_id)
    obs.obs_data_set_array(settings, "bracket_hotkey", bracket_hotkey_array)
    obs.obs_data_array_release(bracket_hotkey_array)


def script_unload():
    """Called when the script is unloaded."""
    print("[Tournament] Script unloaded!")