import json
import os
import re
import urllib.parse
from pathlib import Path

# === CONFIGURATION ===
HAR_FILE = "rest_symmetric.har"  # Path to your HAR file
BASE_OUTPUT_DIR = "poker_solutions"  # Base directory to save the extracted JSONs

# === CREATE BASE OUTPUT DIRECTORY ===
os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)

# === LOAD HAR DATA ===
with open(HAR_FILE, "r", encoding="utf-8") as f:
    har_data = json.load(f)


def parse_url_parameters(url):
    """Extract parameters from the URL."""
    parsed_url = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed_url.query)

    # Convert lists to single values for our parameters
    params = {}
    for key, value in query_params.items():
        params[key] = value[0] if value and len(value) == 1 else value

    return params


def extract_position_info(json_data):
    """Extract position information from the JSON data."""
    try:
        # Get active position
        active_position = json_data.get("game", {}).get("active_position", "Unknown")

        # Get hero position
        hero_position = "Unknown"
        players = json_data.get("game", {}).get("players", [])
        for player in players:
            if player.get("is_hero", False):
                hero_position = player.get("position", "Unknown")
                break

        return {"active_position": active_position, "hero_position": hero_position}
    except Exception as e:
        print(f"Error extracting position info: {e}")
        return {"active_position": "Unknown", "hero_position": "Unknown"}


def get_folder_path(url_params, json_data):
    """Generate a folder path based on the parameters."""
    # Extract key parameters
    gametype = url_params.get("gametype", "unknown_game")
    depth = url_params.get("depth", "unknown_depth")
    stacks = url_params.get("stacks", "unknown_stacks")
    preflop_actions = url_params.get("preflop_actions", "")
    flop_actions = url_params.get("flop_actions", "")
    turn_actions = url_params.get("turn_actions", "")
    river_actions = url_params.get("river_actions", "")
    board = url_params.get("board", "")

    # Get position information
    position_info = extract_position_info(json_data)
    active_position = position_info["active_position"]
    hero_position = position_info["hero_position"]

    # Create street-based path
    street_path = "preflop"
    if board:
        if river_actions:
            street_path = "river"
        elif turn_actions:
            street_path = "turn"
        elif flop_actions:
            street_path = "flop"

    # Format action sequence for folder name
    action_sequence = "_".join(
        filter(
            None,
            [
                f"pf_{preflop_actions.replace('-', '')}" if preflop_actions else "",
                f"f_{flop_actions.replace('-', '')}" if flop_actions else "",
                f"t_{turn_actions.replace('-', '')}" if turn_actions else "",
                f"r_{river_actions.replace('-', '')}" if river_actions else "",
            ],
        )
    )

    if not action_sequence:
        action_sequence = "no_actions"

    # Create a clean depth value for the folder name
    clean_depth = depth.replace(".", "_")

    # Base path
    folder_path = os.path.join(
        BASE_OUTPUT_DIR,
        gametype,
        f"depth_{clean_depth}",
        street_path,
        action_sequence,
        active_position,
    )

    return folder_path


def generate_filename(url_params, json_data, count):
    """Generate a descriptive filename for the solution."""
    # Extract key parameters
    board = url_params.get("board", "")
    position_info = extract_position_info(json_data)
    hero_position = position_info["hero_position"]

    # Clean the board for filename
    board_str = board.replace(",", "") if board else "no_board"

    # Use the hero position in the filename
    filename = f"hero_{hero_position}"

    # Add board if present
    if board:
        filename += f"_board_{board_str}"

    # Add a unique counter to avoid overwriting
    filename += f"_{count}"

    return f"{filename}.json"


# === EXTRACT JSON RESPONSES ===
count = 0
for entry in har_data["log"]["entries"]:
    url = entry["request"]["url"]
    if "spot-solution" in url:
        response = entry.get("response", {})
        content = response.get("content", {})
        mime_type = content.get("mimeType", "")
        text = content.get("text", "")

        if not text:
            continue

        # Try to parse JSON (some may be base64-encoded or invalid)
        try:
            if content.get("encoding") == "base64":
                import base64

                decoded = base64.b64decode(text).decode("utf-8")
                json_data = json.loads(decoded)
            else:
                json_data = json.loads(text)

            # Parse URL parameters
            url_params = parse_url_parameters(url)

            # Generate folder path
            folder_path = get_folder_path(url_params, json_data)
            os.makedirs(folder_path, exist_ok=True)

            # Generate filename
            filename = generate_filename(url_params, json_data, count)
            filepath = os.path.join(folder_path, filename)

            # Save the JSON file
            with open(filepath, "w", encoding="utf-8") as out_f:
                json.dump(json_data, out_f, indent=2)

            print(f"✅ Saved: {filepath}")
            count += 1

        except Exception as e:
            print(f"⚠️  Skipped (error parsing): {url}\nReason: {e}")

print(f"\nTotal saved: {count}")
