"""
Challonge API integration for tournament bracket management.
"""
import urllib.request
import urllib.error
import json

# =============================================================================
# CREDENTIALS (set from main script in OBS overlay)
# =============================================================================
API_KEY = ""
TOURNAMENT_ID = ""
# Dict containing participant_id to team name mapping for populating bracket
PARTICIPANTS: dict[int, str] = {}
# Maps "suggested_play_order" (game # effectively) to the participant IDs
MATCHES: dict[int, tuple[int | None, int | None]] = {}


def set_credentials(api_key: str, tournament_id: str):
    """Set Challonge API credentials."""
    global TOURNAMENT_ID, API_KEY
    API_KEY = api_key
    TOURNAMENT_ID = tournament_id
    print(f"[Challonge] Credentials set: {API_KEY} \n{TOURNAMENT_ID}")


# =============================================================================
# API HELPERS
# =============================================================================

def _api_request(endpoint: str, method: str = "GET", data: dict = None) -> dict | None:
    """
    Make a request to the Challonge API.
    
    Args:
        endpoint: API endpoint (e.g., "/tournaments/{id}.json")
        method: HTTP method
        data: Optional data for POST/PUT requests
        
    Returns:
        Parsed JSON response or None on error
    """
    if not API_KEY:
        print("[Challonge] API key not set")
        return None
    
    base_url = "https://api.challonge.com/v2.1"
    url = f"{base_url}{endpoint}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Content-Type": "application/vnd.api+json",
        "Authorization-Type": "v1",
        "Authorization": API_KEY,
    }
    try:
        if data:
            request_data = json.dumps(data).encode()
        else:
            request_data = None
            
        request = urllib.request.Request(url, data=request_data, headers=headers, method=method)
        
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode())
            
    except urllib.error.HTTPError as e:
        print(f"[Challonge] HTTP Error {e.code}: {e.reason}")
        try:
            error_body = e.read().decode()
            print(f"[Challonge] Error details: {error_body}")
        except:
            pass
        return None
    except urllib.error.URLError as e:
        print(f"[Challonge] URL Error: {e.reason}")
        return None
    except json.JSONDecodeError as e:
        print(f"[Challonge] JSON decode error: {e}")
        return None
    except Exception as e:
        print(f"[Challonge] Unexpected error: {e}")
        return None


# =============================================================================
# TOURNAMENT API
# =============================================================================

def get_participants():
    """Fetch all participants in the tournament and populate PARTICIPANTS dict."""
    global PARTICIPANTS
    
    if not TOURNAMENT_ID:
        print("[Challonge] Tournament ID not set")
        return
    
    result = _api_request(f"/tournaments/{TOURNAMENT_ID}/participants.json")
    
    if result and "data" in result:
        PARTICIPANTS = {
            int(p["id"]): p["attributes"]["name"] 
            for p in result["data"]
        }
        print(f"[Challonge] Loaded {len(PARTICIPANTS)} participants")


def get_matches():
    """Fetch matches from the tournament and populate MATCHES dict."""
    global MATCHES
    
    if not TOURNAMENT_ID:
        print("[Challonge] Tournament ID not set")
        return
    
    endpoint = f"/tournaments/{TOURNAMENT_ID}/matches.json"
    result = _api_request(endpoint)
    
    if result and "data" in result:
        MATCHES = {}
        for m in result["data"]:
            attrs = m["attributes"]
            play_order = attrs.get("suggested_play_order")
            
            if play_order is not None:
                points = attrs.get("points_by_participant", [])
                p1_id = points[0]["participant_id"] if len(points) > 0 else None
                p2_id = points[1]["participant_id"] if len(points) > 1 else None
                MATCHES[int(play_order)] = (PARTICIPANTS.get(p1_id, None), PARTICIPANTS.get(p2_id, None))
        
        print(f"[Challonge] Loaded {len(MATCHES)} matches")


def refresh_bracket():
    """Fetch both participants and matches from Challonge."""
    get_participants()
    get_matches()
    print(f"[Challonge] Participants: {PARTICIPANTS}")
    print(f"[Challonge] Matches: {MATCHES}")


def get_bracket_text_sources() -> dict[str, str]:
    """
    Generate mapping of OBS text source names to team names.
    
    Returns:
        Dict mapping source name (e.g., "G1_T1") to team name
    """
    sources = {}
    
    for game_num, (t1_name, t2_name) in MATCHES.items():
        # Team 1
        sources[f"G{game_num}_T1"] = t1_name
        
        # Team 2
        sources[f"G{game_num}_T2"] = t2_name
    
    return sources