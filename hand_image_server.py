import json
import os
import tempfile
import random
import logging
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from poker_table_visualizer import PokerTableVisualizer

# Cache for already loaded and cleaned solution JSON files
json_cache = {}


def load_clean_json(file_path):
    """Load and clean a solution JSON file with caching."""
    if file_path in json_cache:
        return json_cache[file_path]

    try:
        with open(file_path, "r") as f:
            data = json.load(f)

        # Keys that should be removed from each player info block
        keys_to_remove = [
            "equity_buckets",
            "equity_buckets_advanced",
            "hand_categories",
            "draw_categories",
        ]

        # Remove heavy fields from players_info
        if "players_info" in data:
            for player_info in data["players_info"]:
                for key in keys_to_remove:
                    player_info.pop(key, None)
                if (
                    "player" in player_info
                    and "relative_postflop_position" in player_info["player"]
                ):
                    del player_info["player"]["relative_postflop_position"]

        # Clean action_solutions blocks
        if "action_solutions" in data:
            for action in data["action_solutions"]:
                for key in keys_to_remove:
                    action.pop(key, None)

        json_cache[file_path] = data
        return data
    except Exception as e:
        logger.warning(f"Failed to load solution file {file_path}: {e}")
        return None

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global cache for visualizer instances
# Keys will be (game_type, num_players)
visualizer_cache = {}


def init_visualizer_cache():
    """Initialize the visualizer cache with common configurations."""
    global visualizer_cache

    logger.info("Initializing PokerTableVisualizer cache...")
    solutions_dir = Path("poker_solutions")

    # Skip if the directory doesn't exist
    if not solutions_dir.exists():
        logger.warning(
            "No poker_solutions directory found. Cache initialization skipped."
        )
        return

    # Find all available game types
    game_types = [d for d in solutions_dir.iterdir() if d.is_dir()]

    for game_type_dir in game_types:
        game_type = game_type_dir.name
        logger.info(f"Processing game type: {game_type}")

        # Find one JSON file to use as a template for this game type
        json_files = []
        for root, _, files in os.walk(game_type_dir):
            for file in files:
                if file.endswith(".json"):
                    json_files.append(os.path.join(root, file))
                    break
            if json_files:
                break

        if not json_files:
            logger.warning(f"No JSON files found for game type: {game_type}")
            continue

        json_path = json_files[0]
        logger.info(f"Using template file: {json_path}")

        try:
            # Load the JSON data using the caching helper
            json_data = load_clean_json(json_path)

            # Get the number of players
            num_players = len(json_data["game"]["players"])

            # Create a visualizer instance for this configuration if it doesn't exist
            cache_key = (game_type, num_players)
            if cache_key not in visualizer_cache:
                logger.info(
                    f"Creating visualizer for game type {game_type} with {num_players} players"
                )
                # Create a temporary file that won't be used
                temp_output = tempfile.NamedTemporaryFile(
                    suffix=".png", delete=False
                ).name

                # Initialize the visualizer with placeholder cards
                visualizer = PokerTableVisualizer(
                    json_data,
                    "Ah",  # Placeholder cards
                    "Kh",
                    temp_output,
                    solution_path=json_path,
                    scale_factor=1,
                )

                # Create the template for static elements
                logger.info(
                    f"Creating template for {game_type} with {num_players} players"
                )
                visualizer.create_template()

                # Store in cache
                visualizer_cache[cache_key] = visualizer

        except Exception as e:
            logger.error(f"Error initializing visualizer for {game_type}: {e}")

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

        # Temporary output path for compatibility when saving to disk
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        output_path = temp_file.name
        temp_file.close()

        # Find the original solution file in the poker_solutions directory
        solutions_dir = Path("poker_solutions")
        original_file = None
        original_json = None
        image_bytes = None

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
                original_json = load_clean_json(original_file)

                # Get the number of players
                num_players = len(original_json["game"]["players"])

                # Try to get a cached visualizer for this game type and player count
                cache_key = (game_type, num_players)

                if cache_key in visualizer_cache:
                    # Use the cached visualizer
                    logger.info(
                        f"Using cached visualizer for {game_type} with {num_players} players"
                    )
                    visualizer = visualizer_cache[cache_key]

                    # Update the visualizer with the new cards and output path
                    visualizer.card1 = card1
                    visualizer.card2 = card2
                    visualizer.output_path = output_path

                    # If we have a different solution file, update that too
                    if visualizer.solution_path != original_file:
                        visualizer.solution_path = original_file
                        visualizer.data = original_json
                        # Reinitialize game data with the new solution
                        visualizer.game_data.json_data = original_json
                        visualizer.game_data.solution_path = original_file
                else:
                    # Create a new visualizer and add it to the cache
                    logger.info(
                        f"Creating new visualizer for {game_type} with {num_players} players"
                    )
                    visualizer = PokerTableVisualizer(
                        original_json,
                        card1,
                        card2,
                        output_path,
                        solution_path=original_file,
                        scale_factor=1,
                    )
                    # Create the template for static elements
                    visualizer.create_template()
                    visualizer_cache[cache_key] = visualizer

                # Generate the visualization and get bytes
                image_bytes = visualizer.create_visualization_bytes()
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
                image_bytes = None

        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            logger.warning(
                f"Couldn't load original file: {original_file}. Creating minimal structure: {e}"
            )
            # Fall back to minimal structure (would need to be implemented)
            image_bytes = None

        return image_bytes

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

        # Generate the visualization and receive bytes
        image_bytes = create_visualization_from_json(hand_json)
        if image_bytes is None:
            return jsonify({"error": "Failed to create visualization"}), 500

        return send_file(
            image_bytes,
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
