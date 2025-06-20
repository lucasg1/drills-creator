import json
import os
from datetime import datetime


def clear_spot_solution_json(input_file):
    """
    Clean a JSON file by removing specified keys from the players_info section.
    Formats 'strategy' and 'evs' arrays to have 13 elements per line in the JSON output.

    Args:
        input_file (str): Path to the input JSON file
        output_file (str, optional): Path to the output JSON file. If None, a default name will be created.

    Returns:
        str: Path to the created output file
    """

    # Keys to remove from each player in players_info
    keys_to_remove = [
        # "simple_hand_counters",
        "equity_buckets",
        "equity_buckets_advanced",
        "hand_categories",
        "draw_categories",
    ]

    # Player field to remove
    player_field_to_remove = "relative_postflop_position"

    try:
        # Load the JSON data
        with open(input_file, "r") as f:
            data = json.load(f)

        # Clean action_solutions
        if "action_solutions" in data:
            for action in data["action_solutions"]:
                if "equity_buckets" in action:
                    action["equity_buckets"] = []
                if "equity_buckets_advanced" in action:
                    action["equity_buckets_advanced"] = []
                if "hand_categories" in action:
                    action["hand_categories"] = []
                if "draw_categories" in action:
                    action["draw_categories"] = []

        # Clean players_info
        if "players_info" in data:
            for player_info in data["players_info"]:
                # Remove specified keys
                for key in keys_to_remove:
                    if key in player_info:
                        del player_info[key]

                # Remove the field from player object
                if (
                    "player" in player_info
                    and player_field_to_remove in player_info["player"]
                ):
                    del player_info["player"][player_field_to_remove]

        formatted_json = custom_json_format(data)
        return formatted_json

    except Exception as e:
        print(f"Error cleaning JSON: {str(e)}")
        return None


def custom_json_format(data, indent=2):
    """
    Custom JSON formatter that formats 'strategy' and 'evs' arrays with 13 elements per line.

    Args:
        data: The JSON data to format
        indent (int): The indentation level

    Returns:
        str: Formatted JSON string
    """
    if isinstance(data, dict):
        # Format dictionary
        result = "{\n"
        items = list(data.items())
        for i, (key, value) in enumerate(items):
            spaces = " " * indent
            result += f'{spaces}"{key}": {custom_json_format(value, indent + 2)}'
            if i < len(items) - 1:
                result += ","
            result += "\n"
        result += " " * (indent - 2) + "}"
        return result
    elif isinstance(data, list):
        # Check if this is a strategy or evs array (arrays of numbers)
        if data and all(isinstance(item, (int, float)) for item in data):
            # Format arrays of numbers with 13 elements per line
            result = "[\n"
            spaces = " " * indent
            for i in range(0, len(data), 13):
                chunk = data[i : i + 13]
                chunk_str = ", ".join(str(x) for x in chunk)
                result += f"{spaces}{chunk_str}"
                if i + 13 < len(data):
                    result += ","
                result += "\n"
            result += " " * (indent - 2) + "]"
            return result
        else:
            # Format regular arrays
            result = "[\n"
            for i, item in enumerate(data):
                spaces = " " * indent
                result += f"{spaces}{custom_json_format(item, indent + 2)}"
                if i < len(data) - 1:
                    result += ","
                result += "\n"
            result += " " * (indent - 2) + "]"
            return result
    elif isinstance(data, bool):
        return "true" if data else "false"
    elif isinstance(data, (int, float)):
        return str(data)
    elif data is None:
        return "null"
    else:
        # Format strings with proper escaping
        return json.dumps(data)


if __name__ == "__main__":
    # Use the current file's directory to find example.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, "example.json")

    # Call the clean_json function
    cleaned_file = clear_spot_solution_json(input_file)

    if cleaned_file:
        print(
            f"The JSON file has been cleaned. The following keys were removed from players_info:"
        )
        print("- simple_hand_counters")
        print("- equity_buckets")
        print("- equity_buckets_advanced")
        print("- hand_categories")
        print("- draw_categories")
        print("- relative_postflop_position (from player object)")
        print(
            "\nAdditionally, 'strategy' and 'evs' arrays were formatted with 13 elements per line for better readability."
        )
