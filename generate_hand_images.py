import json
import os
import argparse
from pathlib import Path
import logging
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
from poker_table_visualizer import PokerTableVisualizer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("generate_hand_images.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def create_visualization_for_hand(args):
    """Create a visualization for a single hand JSON file"""
    hand_json_path, output_dir, hand_to_cards_map = args

    try:
        # Load the hand JSON file
        with open(hand_json_path, "r") as f:
            hand_json = json.load(f)

        # Extract necessary information
        hand = hand_json["metadata"]["hand"]
        best_action = hand_json["metadata"]["best_action"]
        best_ev = hand_json["metadata"]["best_ev"]

        # Convert hand notation to card notation
        if hand in hand_to_cards_map:
            card1, card2 = hand_to_cards_map[hand]
        else:
            # Fallback conversion if not in cache
            card1, card2 = convert_hand_to_cards(hand)
            hand_to_cards_map[hand] = (card1, card2)

        # Create output filename
        output_filename = f"{hand}_{best_action}_{best_ev:.6f}.png"
        output_path = output_dir / output_filename

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Load the original solution file to get the full game structure
        original_file = hand_json["metadata"]["original_file"]
        try:
            # Try to load the original solution to get the game structure
            from clear_spot_solution_json import clear_spot_solution_json

            json_text = clear_spot_solution_json(original_file)
            original_json = json.loads(json_text)

            # Create visualization
            visualizer = PokerTableVisualizer(
                original_json,
                card1,
                card2,
                str(output_path),
                solution_path=str(hand_json_path),
            )
            visualizer.create_visualization()

        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            # If we can't load the original, create a minimal structure for visualization
            logger.warning(
                f"Couldn't load original file: {original_file}. Creating minimal structure: {e}"
            )

            # Create a minimal structure required by PokerTableVisualizer
            minimal_json = {
                "game": {
                    "players": [
                        {"position": "UTG", "stack": 100},
                        {"position": "MP", "stack": 100},
                        {"position": "CO", "stack": 100},
                        {"position": "BTN", "stack": 100},
                        {"position": "SB", "stack": 100, "is_hero": True},
                        {"position": "BB", "stack": 100},
                    ],
                    "blinds": {"sb": 0.5, "bb": 1.0},
                    "pot": 1.5,
                },
                "spot_solution": hand_json["spot_solution"],
                "hand_data": hand_json["hand_data"],
                "metadata": {
                    "mode": hand_json["metadata"].get("mode", ""),
                    "field_size": hand_json["metadata"].get("field_size", 0),
                    "field_left": hand_json["metadata"].get("field_left", ""),
                    "position": hand_json["metadata"].get("position", ""),
                    "stack_depth": hand_json["metadata"].get("stack_depth", ""),
                    "action": hand_json["metadata"].get("action", ""),
                    "game_type": hand_json["metadata"].get("game_type", ""),
                    "street": hand_json["metadata"].get("street", ""),
                    "action_sequence": hand_json["metadata"].get("action_sequence", ""),
                },
            }

            # Create visualization with minimal structure
            visualizer = PokerTableVisualizer(
                minimal_json,
                card1,
                card2,
                str(output_path),
                solution_path=str(hand_json_path),
            )
            visualizer.create_visualization()

        return f"Created visualization for {hand} ({card1}, {card2}) - Best action: {best_action}, EV: {best_ev:.6f}"

    except Exception as e:
        logger.error(
            f"Error creating visualization for {hand_json_path}: {e}", exc_info=True
        )
        return f"Error processing {hand_json_path}: {str(e)}"


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


class HandImageGenerator:
    def __init__(
        self,
        input_dir="separated_solutions_by_hand",
        output_dir="hand_images",
        game_type=None,
        depth=None,
        position=None,
        max_workers=None,
        specific_hand=None,
    ):
        """
        Initialize the hand image generator

        Parameters:
        input_dir (str): Path to the directory containing hand JSON files
        output_dir (str): Path to directory where images will be saved
        game_type (str, optional): Filter by game type
        depth (str, optional): Filter by stack depth
        position (str, optional): Filter by position
        max_workers (int, optional): Maximum number of worker processes to use
        specific_hand (str, optional): Generate image for a specific hand only (e.g., 'AKs', 'TT')
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.game_type = game_type
        self.depth = depth
        self.position = position
        self.max_workers = max_workers
        self.specific_hand = specific_hand

        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)

        # Cache for hand to cards mapping
        self.hand_to_cards_map = {}

        # Stats tracking
        self.stats = {
            "total_files": 0,
            "processed_files": 0,
            "skipped_files": 0,
            "error_files": 0,
        }

    def get_hand_json_files(self):
        """Get all hand JSON files, optionally filtered by criteria"""
        pattern = "**/*.json"
        all_files = list(self.input_dir.glob(pattern))

        # Skip metadata.json files
        all_files = [f for f in all_files if f.name != "metadata.json"]

        # Apply filters if specified
        filtered_files = []
        for file_path in all_files:
            relative_path = file_path.relative_to(self.input_dir)
            parts = relative_path.parts

            # Apply game type filter
            if self.game_type and (len(parts) < 1 or parts[0] != self.game_type):
                continue

            # Apply depth filter
            if self.depth and (len(parts) < 2 or parts[1] != self.depth):
                continue

            # Apply position filter
            if self.position:
                position_found = False
                for part in parts:
                    if part == self.position:
                        position_found = True
                        break
                if not position_found:
                    continue

            # Apply specific hand filter if provided
            if self.specific_hand:
                # Check if the file is for the specific hand
                # The filename pattern is typically [hand].json
                if not file_path.stem == self.specific_hand:
                    continue

            filtered_files.append(file_path)

        return filtered_files

    def run(self):
        """Process all hand JSON files and generate images"""
        # Get hand JSON files
        hand_json_files = self.get_hand_json_files()
        self.stats["total_files"] = len(hand_json_files)

        if self.specific_hand:
            logger.info(f"Looking for files with hand: {self.specific_hand}")
        logger.info(f"Found {len(hand_json_files)} hand JSON files to process")

        if not hand_json_files:
            logger.warning(
                "No hand JSON files found. Make sure the input directory is correct."
            )
            return

        # If we're processing a specific hand, just print the files we found
        if self.specific_hand and len(hand_json_files) > 0:
            logger.info(
                f"Found {len(hand_json_files)} files for hand {self.specific_hand}:"
            )
            for file in hand_json_files:
                logger.info(f"  - {file}")

        # Process files in parallel (or just one file if specific_hand is set)
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Prepare arguments for visualization tasks
            visualization_args = []

            for hand_json_path in hand_json_files:
                # Create matching output directory structure
                relative_path = hand_json_path.relative_to(self.input_dir)
                output_subdir = self.output_dir / relative_path.parent

                # Append task arguments
                visualization_args.append(
                    (hand_json_path, output_subdir, self.hand_to_cards_map)
                )

            # Submit visualization tasks
            future_to_path = {
                executor.submit(create_visualization_for_hand, args): args[0]
                for args in visualization_args
            }

            # Process results as they complete
            for i, future in enumerate(as_completed(future_to_path)):
                try:
                    result = future.result()
                    logger.info(f"[{i+1}/{len(hand_json_files)}] {result}")
                    self.stats["processed_files"] += 1
                except Exception as e:
                    hand_json_path = future_to_path[future]
                    logger.error(
                        f"Error processing {hand_json_path}: {e}", exc_info=True
                    )
                    self.stats["error_files"] += 1

                # Log progress every 50 files
                if (i + 1) % 50 == 0:
                    logger.info(
                        f"Progress: {i+1}/{len(hand_json_files)} files processed"
                    )

        # Print final stats
        logger.info("\nProcessing complete!")
        logger.info(f"Total files: {self.stats['total_files']}")
        logger.info(f"Processed files: {self.stats['processed_files']}")
        logger.info(f"Error files: {self.stats['error_files']}")
        logger.info(f"Images saved to: {self.output_dir}")


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Generate images from hand JSON files")

    parser.add_argument(
        "--input",
        default="separated_solutions_by_hand",
        help="Directory containing hand JSON files",
    )
    parser.add_argument(
        "--output", default="hand_images", help="Directory to save hand images"
    )
    parser.add_argument("--game-type", help="Filter by game type")
    parser.add_argument("--depth", help="Filter by stack depth")
    parser.add_argument("--position", help="Filter by position")
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Maximum number of worker processes to use",
    )
    parser.add_argument(
        "--hand", help="Generate image for a specific hand only (e.g., 'AKs', 'TT')"
    )
    parser.add_argument(
        "--file", help="Generate image for a specific hand JSON file (absolute path)"
    )

    args = parser.parse_args()

    # Process a single specific file if provided
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return

        output_dir = Path(args.output)
        os.makedirs(output_dir, exist_ok=True)

        hand_to_cards_map = {}
        result = create_visualization_for_hand(
            (file_path, output_dir, hand_to_cards_map)
        )
        logger.info(result)
        return

    # Create and run image generator
    generator = HandImageGenerator(
        input_dir=args.input,
        output_dir=args.output,
        game_type=args.game_type,
        depth=args.depth,
        position=args.position,
        max_workers=args.max_workers,
        specific_hand=args.hand,
    )

    generator.run()


if __name__ == "__main__":
    main()
