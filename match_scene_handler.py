import os
import json

# =============================================================================
# TEAM CLASS
# =============================================================================
class Team:
    def __init__(self, team_name: str, helm_tup: tuple[str, str] = None, flex_tup: tuple[str, str] = None, 
                 mc_tup: tuple[str, str] = None, bilge_tup: tuple[str, str] = None):
        # tuples formatted as ({pos}_name, {pos}_twitch_link)
        self.name = team_name
        self.helm = helm_tup
        self.flex = flex_tup
        self.mc = mc_tup
        self.bilge = bilge_tup


# =============================================================================
# ROSTER MANAGEMENT
# =============================================================================
ROSTER_FILE = os.path.join(os.path.dirname(__file__), "roster.json")
TEAM_ROSTER: dict[str, Team] = {}

def load_roster():
    """Load team roster from JSON file."""
    global TEAM_ROSTER
    
    try:
        with open(ROSTER_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        TEAM_ROSTER.clear()
        for team_name, team_data in data["teams"].items():
            TEAM_ROSTER[team_name] = Team(
                team_name=team_name,
                helm_tup=tuple(team_data["helm"].values()) if team_data.get("helm") and team_data["helm"].get("name") else None,
                mc_tup=tuple(team_data["mc"].values()) if team_data.get("mc") and team_data["mc"].get("name") else None,
                flex_tup=tuple(team_data["flex"].values()) if team_data.get("flex") and team_data["flex"].get("name") else None,
                bilge_tup=tuple(team_data["bilge"].values()) if team_data.get("bilge") and team_data["bilge"].get("name") else None,
            )
        print(f"[Tournament] Loaded {len(TEAM_ROSTER)} teams from roster.json")
    except FileNotFoundError:
        print(f"[Tournament] roster.json not found at {ROSTER_FILE}")
    except json.JSONDecodeError as e:
        print(f"[Tournament] Invalid JSON in roster.json: {e}")


def get_team(team_name: str) -> Team | None:
    """Get a team by name from the roster."""
    return TEAM_ROSTER.get(team_name)


def get_team_names() -> list[str]:
    """Get sorted list of team names."""
    return sorted(TEAM_ROSTER.keys())


# =============================================================================
# SOURCE CONFIGURATION
# =============================================================================
# Text sources for team names
T1_NAME_SOURCE = "Team 1"
T2_NAME_SOURCE = "Team 2"

# Browser source prefixes (script will find sources starting with these)
T1_HELM_PREFIX =  "T1H -"
T1_MC_PREFIX =    "T1MC -"
T1_FLEX_PREFIX =  "T1F -"
T1_BILGE_PREFIX = "T1B -"

T2_HELM_PREFIX =  "T2H -"
T2_MC_PREFIX =    "T2MC -"
T2_FLEX_PREFIX =  "T2F -"
T2_BILGE_PREFIX = "T2B -"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def build_twitch_url(channel: str) -> str:
    """Construct the Twitch player embed URL from a channel name."""
    if not channel:
        return ""
    return (
        f"https://player.twitch.tv/?channel={channel}"
        f"&enableExtensions=true&muted=false&parent=twitch.tv"
        f"&player=popout&quality=480p30&volume=0.69"
    )


def get_twitch_link(position_tup: tuple[str, str] | None) -> str | None:
    """Extract Twitch link from a position tuple, handling None values."""
    if position_tup is None:
        return None
    return position_tup[1]


def get_player_name(position_tup: tuple[str, str] | None) -> str | None:
    """Extract player name from a position tuple, handling None values."""
    if position_tup is None:
        return None
    return position_tup[0]


# =============================================================================
# OBS SOURCE MANIPULATION (requires obs module to be passed in)
# =============================================================================
def find_source_by_prefix(obs, prefix: str) -> str | None:
    """Find a source whose name starts with the given prefix."""
    sources = obs.obs_enum_sources()
    found_source_name = None
    
    if sources:
        for source in sources:
            name = obs.obs_source_get_name(source)
            if name and name.startswith(prefix):
                found_source_name = name
                break
    
    obs.source_list_release(sources)
    return found_source_name


def set_browser_source_url(obs, prefix: str, player_name: str | None, twitch_username: str | None):
    """Update a browser source with a Twitch embed URL, or clear if None. Also renames the source."""
    if not prefix:
        return
    
    source_name = find_source_by_prefix(obs, prefix)
    print(f"[Tournament] Found Source {source_name} from {prefix}")
    if not source_name:
        print(f"[Tournament] No source found with prefix: {prefix}")
        return
    
    source = obs.obs_get_source_by_name(source_name)
    if source is None:
        print(f"[Tournament] Source not found: {source_name}")
        return
    
    # Build new source name with player name
    if player_name:
        new_name = f"{prefix} {player_name}"
    else:
        new_name = prefix
    
    # Rename the source
    obs.obs_source_set_name(source, new_name)
    
    # If no twitch username, clear the source URL
    if not twitch_username:
        url = ""
        print(f"[Tournament] Clearing {new_name}")
    else:
        url = build_twitch_url(twitch_username)
        print(f"[Tournament] Updated {new_name} -> {twitch_username}")
    
    settings = obs.obs_data_create()
    obs.obs_data_set_string(settings, "url", url)
    obs.obs_source_update(source, settings)
    obs.obs_data_release(settings)
    obs.obs_source_release(source)


def set_text_source(obs, source_name: str, text: str):
    """Update a text source with new text."""
    if not source_name:
        return
    
    source = obs.obs_get_source_by_name(source_name)
    if source is None:
        print(f"[Tournament] Text source not found: {source_name}")
        return
    
    settings = obs.obs_data_create()
    obs.obs_data_set_string(settings, "text", text)
    obs.obs_source_update(source, settings)
    obs.obs_data_release(settings)
    obs.obs_source_release(source)
    print(f"[Tournament] Updated text {source_name} -> {text}")


def apply_team_to_sources(obs, team: Team, name_source: str, helm_prefix: str, 
                          mc_prefix: str, flex_prefix: str, bilge_prefix: str):
    """Apply a Team's data to the corresponding OBS sources."""
    set_text_source(obs, name_source, team.name)
    set_browser_source_url(obs, helm_prefix, get_player_name(team.helm), get_twitch_link(team.helm))
    set_browser_source_url(obs, mc_prefix, get_player_name(team.mc), get_twitch_link(team.mc))
    set_browser_source_url(obs, flex_prefix, get_player_name(team.flex), get_twitch_link(team.flex))
    set_browser_source_url(obs, bilge_prefix, get_player_name(team.bilge), get_twitch_link(team.bilge))


def execute_transition(obs, team1_name: str, team2_name: str):
    """Apply the selected teams to all sources."""
    print(f"[Tournament] Executing transition: {team1_name} vs {team2_name}")
    
    # Update Team 1
    team1 = get_team(team1_name)
    if team1:
        apply_team_to_sources(
            obs,
            team1, 
            T1_NAME_SOURCE, 
            T1_HELM_PREFIX, 
            T1_MC_PREFIX, 
            T1_FLEX_PREFIX, 
            T1_BILGE_PREFIX
        )
    else:
        print(f"[Tournament] Team 1 not found in roster: {team1_name}")
    
    # Update Team 2
    team2 = get_team(team2_name)
    if team2:
        apply_team_to_sources(
            obs,
            team2, 
            T2_NAME_SOURCE, 
            T2_HELM_PREFIX, 
            T2_MC_PREFIX, 
            T2_FLEX_PREFIX, 
            T2_BILGE_PREFIX
        )
    else:
        print(f"[Tournament] Team 2 not found in roster: {team2_name}")
    
    print("[Tournament] Transition complete!")