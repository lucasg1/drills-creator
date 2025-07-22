import json
import os
import tempfile
import random
import logging
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from poker_table_visualizer import PokerTableVisualizer, load_json_data
from clear_spot_solution_json import clear_spot_solution_json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global cache for visualizer instances
# Keys will be (num_players, hero_position)
visualizer_cache = {}


def init_visualizer_cache():
    """Preload visualizers for every hero position for 8 and 9 players."""
    global visualizer_cache

    logger.info("Initializing PokerTableVisualizer cache...")
    solutions_dir = Path("poker_solutions")

    # Skip if the directory doesn't exist
    if not solutions_dir.exists():
        logger.warning(
            "No poker_solutions directory found. Cache initialization skipped."
        )
        return

    # Positions we want to cover for each player count
    required_positions = {
        8: ["UTG", "UTG+1", "LJ", "HJ", "CO", "BTN", "SB", "BB"],
        9: ["UTG", "UTG+1", "UTG+2", "LJ", "HJ", "CO", "BTN", "SB", "BB"],
    }

    found_positions = {8: set(), 9: set()}
    sample_json = {8: None, 9: None}

    # Walk through all JSON files once
    for root, _, files in os.walk(solutions_dir):
        for file in files:
            if not file.endswith(".json"):
                continue
            json_path = os.path.join(root, file)
            try:
                json_text = clear_spot_solution_json(json_path)
                json_data = json.loads(json_text)
            except Exception:
                continue

            num_players = len(json_data.get("game", {}).get("players", []))
            if num_players not in required_positions:
                continue

            # Remember a sample for this player count in case some positions are missing
            if sample_json[num_players] is None:
                sample_json[num_players] = (json_data, json_path)

            hero_position = next(
                (
                    p.get("position")
                    for p in json_data["game"]["players"]
                    if p.get("is_hero")
                ),
                None,
            )

            if hero_position not in required_positions[num_players]:
                continue

            cache_key = (num_players, hero_position)
            if cache_key in visualizer_cache:
                continue

            temp_output = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name

            visualizer = PokerTableVisualizer(
                json_data,
                "Ah",  # Placeholder cards
                "Kh",
                temp_output,
                solution_path=json_path,
                scale_factor=1,
            )
            visualizer.create_template()

            visualizer_cache[cache_key] = visualizer
            found_positions[num_players].add(hero_position)

            # Stop early if we covered everything
            if all(
                len(found_positions[n]) == len(required_positions[n])
                for n in required_positions
            ):
                break
        else:
            continue
        break

    # Create missing hero positions by modifying a sample JSON
    for num_players, positions in required_positions.items():
        missing = set(positions) - found_positions[num_players]
        if not missing:
            continue

        sample = sample_json[num_players]
        if sample is None:
            logger.warning(
                f"No sample JSON found for {num_players} players; cannot create templates"
            )
            continue

        base_data, base_path = sample
        for hero_position in missing:
            data_copy = json.loads(json.dumps(base_data))

            # Remove existing hero flag
            for p in data_copy["game"]["players"]:
                p["is_hero"] = False
            # Set hero on the requested position
            bb_player = next(
                (p for p in data_copy["game"]["players"] if p.get("position") == hero_position),
                None,
            )
            if bb_player is None:
                continue
            bb_player["is_hero"] = True

            temp_output = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
            visualizer = PokerTableVisualizer(
                data_copy,
                "Ah",
                "Kh",
                temp_output,
                solution_path=base_path,
                scale_factor=1,
            )
            visualizer.create_template()
            cache_key = (num_players, hero_position)
            visualizer_cache[cache_key] = visualizer
            found_positions[num_players].add(hero_position)

    logger.info(
        f"Visualizer cache initialized with {len(visualizer_cache)} configurations"
    )


def convert_hand_to_cards(hand):
    """Convert hand notation (e.g., AKs, 22) to individual cards"""
    # Dictionary to map ranks
    rank_map = {
        "A": "A",
        "K": "K",
        "Q": "Q",
        "J": "J",
        "T": "T",
        "9": "9",
        "8": "8",
        "7": "7",
        "6": "6",
        "5": "5",
        "4": "4",
        "3": "3",
        "2": "2",
    }

    # Define the suits we can use
    suits = ["h", "s", "d", "c"]

    # Handle pairs (e.g., 22, AA)
    if len(hand) == 2 and hand[0] == hand[1]:
        rank = rank_map[hand[0]]
        # Use two different random suits for the pair
        suit1, suit2 = random.sample(suits, 2)
        return f"{rank}{suit1}", f"{rank}{suit2}"

    # Handle suited hands (e.g., AKs)
    elif len(hand) == 3 and hand[2] == "s":
        rank1 = rank_map[hand[0]]
        rank2 = rank_map[hand[1]]
        # Pick a random suit for both cards
        suit = random.choice(suits)
        return f"{rank1}{suit}", f"{rank2}{suit}"

    # Handle offsuit hands (e.g., AKo, or simply AK which is implied offsuit)
    else:
        rank1 = rank_map[hand[0]]
        rank2 = rank_map[hand[1]]
        # Use two different random suits
        suit1, suit2 = random.sample(suits, 2)
        return f"{rank1}{suit1}", f"{rank2}{suit2}"


def create_visualization_from_json(hand_json):
    """Create a visualization from JSON data and return the image path"""
    try:
        # Extract necessary information
        hand = hand_json["metadata"]["hand"]
        best_action = hand_json["metadata"]["best_action"]
        best_ev = hand_json["metadata"]["best_ev"]

        # Extract folder structure information
        game_type = hand_json["metadata"].get("game_type")
        position = hand_json["metadata"].get("position")
        action_sequence = hand_json["metadata"].get("action_sequence", "no_actions")
        stack_depth = hand_json["metadata"].get("stack_depth", "unknown")
        street = hand_json["metadata"].get("street", "preflop")

        # Capitalize position as needed (e.g., "utg" to "UTG")
        if position:
            position = position.upper()

        # Convert hand notation to card notation
        card1, card2 = convert_hand_to_cards(hand)

        # Create temporary output file
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        output_path = temp_file.name
        temp_file.close()

        # Find the original solution file in the poker_solutions directory
        solutions_dir = Path("poker_solutions")
        original_file = None
        original_json = None

        if game_type and position:
            # Normalize stack_depth to match folder structure format
            depth_folder = f"depth_{stack_depth}"

            # Try to find the correct solution file
            try:
                # Log the path we're looking for
                potential_path = (
                    solutions_dir
                    / game_type
                    / depth_folder
                    / street
                    / action_sequence
                    / position
                )

                # Check if the directory exists
                if potential_path.exists() and potential_path.is_dir():
                    # Find any JSON file in this directory
                    json_files = list(potential_path.glob("*.json"))
                    if json_files:
                        original_file = str(json_files[0])
                        logger.info(f"Found solution file: {original_file}")
            except Exception as e:
                logger.warning(f"Error finding solution file: {e}")

        try:
            if original_file:
                # Load the original solution to get the game structure
                json_text = clear_spot_solution_json(original_file)
                original_json = json.loads(json_text)

                # Get the number of players and hero position
                num_players = len(original_json["game"]["players"])
                hero_position = next(
                    (p.get("position") for p in original_json["game"]["players"] if p.get("is_hero")),
                    None,
                )

                # Try to get a cached visualizer for this configuration
                cache_key = (num_players, hero_position)

                if cache_key in visualizer_cache:
                    # Use the cached visualizer
                    logger.info(
                        f"Using cached visualizer for {num_players} players and hero {hero_position}"
                    )
                    visualizer = visualizer_cache[cache_key]

                    # Update with the new data and output path
                    visualizer.card1 = card1
                    visualizer.card2 = card2
                    visualizer.output_path = output_path
                    visualizer.game_data.update_data(original_json, original_file)
                else:
                    # Create a new visualizer and add it to the cache
                    logger.info(
                        f"Creating new visualizer for {num_players} players and hero {hero_position}"
                    )
                    visualizer = PokerTableVisualizer(
                        original_json,
                        card1,
                        card2,
                        output_path,
                        solution_path=original_file,
                        scale_factor=1,
                    )
                    visualizer.create_template()
                    visualizer_cache[cache_key] = visualizer

                # Generate the visualization
                visualizer.create_visualization()
                logger.info(
                    f"Created visualization using solution from {original_file}"
                )
            else:
                # If no original file is found, log a warning
                logger.warning(
                    f"Couldn't find original solution file for game_type={game_type}, "
                    f"position={position}, stack_depth={stack_depth}, action_sequence={action_sequence}"
                )
                # Fall back to minimal structure (would need to be implemented)

        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            logger.warning(
                f"Couldn't load original file: {original_file}. Creating minimal structure: {e}"
            )
            # Fall back to minimal structure (would need to be implemented)

        return output_path

    except Exception as e:
        logger.error(f"Error creating visualization: {e}", exc_info=True)
        raise


@app.route("/generate_image", methods=["POST"])
def generate_image():
    """API endpoint to generate hand image from JSON"""
    try:
        # Check if request contains JSON
        if not request.is_json:
            return jsonify({"error": "Request must contain JSON data"}), 400

        # Get raw request data for debugging
        raw_data = request.get_data(as_text=True)
        logger.info(f"Received raw data (first 500 chars): {raw_data[:500]}")

        # Try to parse JSON with better error handling
        try:
            hand_json = request.get_json(force=True)
        except Exception as json_error:
            logger.error(f"JSON parsing error: {json_error}")
            logger.error(f"Raw data causing error: {raw_data}")
            return (
                jsonify(
                    {
                        "error": f"Invalid JSON format: {str(json_error)}",
                        "raw_data_preview": (
                            raw_data[:200]
                            if len(raw_data) <= 200
                            else raw_data[:200] + "..."
                        ),
                    }
                ),
                400,
            )

        # Validate required fields
        if not hand_json or "metadata" not in hand_json:
            return (
                jsonify(
                    {"error": "Invalid JSON structure. 'metadata' field is required"}
                ),
                400,
            )

        metadata = hand_json["metadata"]
        required_fields = ["hand", "best_action", "best_ev", "game_type", "position"]
        for field in required_fields:
            if field not in metadata:
                return (
                    jsonify({"error": f"Missing required field in metadata: {field}"}),
                    400,
                )

        # Generate the visualization
        image_path = create_visualization_from_json(hand_json)

        # Return the image file
        def cleanup_file():
            try:
                os.unlink(image_path)
            except:
                pass

        return send_file(
            image_path,
            mimetype="image/png",
            as_attachment=False,
            download_name=f"{metadata['hand']}_{metadata['best_action']}_{metadata['best_ev']:.6f}.png",
        )

    except Exception as e:
        logger.error(f"Error in generate_image endpoint: {e}", exc_info=True)
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "Hand image server is running"})


@app.route("/", methods=["GET"])
def home():
    """Home endpoint with usage instructions"""
    return jsonify(
        {
            "message": "Hand Image Generator Server",
            "usage": {
                "endpoint": "/generate_image",
                "method": "POST",
                "content_type": "application/json",
                "description": "Send hand JSON data to generate visualization image",
            },
            "example_request": {
                "metadata": {
                    "hand": "22",
                    "best_action": "F",
                    "best_ev": 0.0,
                    "mode": "icm",
                    "field_size": 200,
                    "field_left": "bubble",
                    "position": "UTG",  # Note: position should be uppercase
                    "stack_depth": "20_125",
                    "action_sequence": "no_actions",
                    "game_type": "MTTGeneral_ICM8m200PTBUBBLEMID",
                    "street": "preflop",
                },
                "spot_solution": {},
                "hand_data": {
                    "hand": "22",
                    "best_action": "F",
                    "best_ev": 0.0,
                    "F_strat": 100.0,
                    "F_ev": 0.0,
                    "R2_strat": 0.0,
                    "R2_ev": -0.06933,
                    "RAI_strat": 0.0,
                    "RAI_ev": -1.04083,
                },
            },
        }
    )


if __name__ == "__main__":
    # Initialize visualizer cache before starting the server
    init_visualizer_cache()

    logger.info("Starting Hand Image Generator Server on port 8777")
    app.run(host="0.0.0.0", port=8777, debug=False)
