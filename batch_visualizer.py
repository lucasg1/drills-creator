import json
import os
import pandas as pd
from pathlib import Path
import argparse
from read_solution import read_spot_solution
from clear_spot_solution_json import clear_spot_solution_json
from poker_table_visualizer import PokerTableVisualizer
import logging
import random

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("batch_visualizer.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class BatchVisualizer:
    def __init__(
        self,
        solutions_dir="poker_solutions",
        output_dir="visualizations",
        min_threshold=0.009,
        max_threshold=0.05,
        num_hands=20,
        game_type=None,
        depth=None,
        position=None,
    ):
        """
        Initialize the batch visualizer

        Parameters:
        solutions_dir (str): Path to the directory with solution JSON files
        output_dir (str): Path to directory where visualizations will be saved
        min_threshold (float): Minimum EV threshold for filtering hands
        max_threshold (float): Maximum EV threshold for filtering hands
        game_type (str, optional): Filter by specific game type
        depth (str, optional): Filter by specific stack depth
        position (str, optional): Filter by specific position
        num_hands (int, optional): Number of hardest hands to extract per file
        """
        self.solutions_dir = Path(solutions_dir)
        self.output_dir = Path(output_dir)
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.num_hands = num_hands
        self.game_type = game_type
        self.depth = depth
        self.position = position

        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)

        # Track stats
        self.stats = {
            "total_files": 0,
            "processed_files": 0,
            "skipped_files": 0,
            "total_hands": 0,
            "filtered_hands": 0,
        }

        # Function to convert hand notation to card notation
        self.hand_to_cards_map = {}

    def hand_to_cards(self, hand):
        """Convert hand notation (e.g., AKs, 22) to individual cards"""
        # Use cached conversion if available
        if hand in self.hand_to_cards_map:
            return self.hand_to_cards_map[hand]

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
        suits = ['h', 's', 'd', 'c']

        # Handle pairs (e.g., 22, AA)
        if len(hand) == 2 and hand[0] == hand[1]:
            rank = rank_map[hand[0]]
            # Use two different random suits for the pair
            suit1, suit2 = random.sample(suits, 2)
            result = (f"{rank}{suit1}", f"{rank}{suit2}")

        # Handle suited hands (e.g., AKs)
        elif len(hand) == 3 and hand[2] == "s":
            rank1 = rank_map[hand[0]]
            rank2 = rank_map[hand[1]]
            # Pick a random suit for both cards
            suit = random.choice(suits)
            result = (f"{rank1}{suit}", f"{rank2}{suit}")

        # Handle offsuit hands (e.g., AKo, or simply AK which is implied offsuit)
        else:
            rank1 = rank_map[hand[0]]
            rank2 = rank_map[hand[1]]
            # Use two different random suits
            suit1, suit2 = random.sample(suits, 2)
            result = (f"{rank1}{suit1}", f"{rank2}{suit2}")

        # Cache the result
        self.hand_to_cards_map[hand] = result
        return result

    def get_solution_files(self):
        """Get all solution JSON files, optionally filtered by criteria"""
        pattern = "**/*.json"
        all_files = list(self.solutions_dir.glob(pattern))

        # Apply filters if specified
        filtered_files = []
        for file_path in all_files:
            relative_path = file_path.relative_to(self.solutions_dir)
            parts = relative_path.parts

            # Apply game type filter
            if self.game_type and (len(parts) < 1 or parts[0] != self.game_type):
                continue

            # Apply depth filter
            if self.depth and (len(parts) < 2 or f"depth_{self.depth}" not in parts[1]):
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

            filtered_files.append(file_path)

        return filtered_files

    def process_solution_file(self, file_path):
        """Process a single solution file"""
        try:
            # Extract metadata from the file path
            relative_path = file_path.relative_to(self.solutions_dir)
            path_parts = relative_path.parts

            # Extract key information from path
            game_type = path_parts[0] if len(path_parts) > 0 else "unknown"
            depth = (
                path_parts[1].replace("depth_", "")
                if len(path_parts) > 1
                else "unknown"
            )
            street = path_parts[2] if len(path_parts) > 2 else "unknown"
            action_seq = path_parts[3] if len(path_parts) > 3 else "unknown"
            position = path_parts[4] if len(path_parts) > 4 else "unknown"

            # Create output directory that mirrors input structure
            output_subdir = (
                self.output_dir / game_type / depth / street / action_seq / position
            )
            os.makedirs(output_subdir, exist_ok=True)

            # Clean the JSON data
            logger.info(f"Processing {file_path}")
            json_text = clear_spot_solution_json(str(file_path))
            clean_json = json.loads(json_text)

            # Read the spot solution
            df_solutions = read_spot_solution(clean_json)

            # Dynamically gather all action codes from the dataframe columns
            action_codes = [
                col[:-6] for col in df_solutions.columns if col.endswith("_strat")
            ]

            # Compute best EV for each row
            df_solutions["best_ev"] = df_solutions.apply(
                lambda row: row[f"{row['best_action']}_ev"], axis=1
            )

            # Optional EV filtering if thresholds are specified
            filtered_df = df_solutions[
                (df_solutions["best_ev"] >= self.min_threshold)
                & (df_solutions["best_ev"] <= self.max_threshold)
            ].copy()

            # Update stats
            self.stats["total_hands"] += len(df_solutions)
            self.stats["filtered_hands"] += len(filtered_df)

            if filtered_df.empty:
                logger.info(
                    f"No hands found after applying EV thresholds {self.min_threshold} to {self.max_threshold}"
                )
                self.stats["skipped_files"] += 1
                return

            # Calculate difficulty score for each hand
            def calc_difficulty(row):
                best_action = row["best_action"]
                best_ev = row["best_ev"]
                alt_evs = [
                    row[f"{code}_ev"]
                    for code in action_codes
                    if code != best_action and f"{code}_ev" in row
                ]
                alt_max_ev = max(alt_evs) if alt_evs else None

                if best_action == "F":
                    return abs(alt_max_ev) if alt_max_ev is not None else 0
                elif best_action.startswith("R"):
                    return best_ev
                else:
                    if alt_max_ev is None:
                        return abs(best_ev)
                    return abs(best_ev - alt_max_ev)

            filtered_df["difficulty"] = filtered_df.apply(calc_difficulty, axis=1)

            # Sort by difficulty and take the hardest hands
            filtered_df = filtered_df.sort_values("difficulty").head(self.num_hands)

            # Prepare columns for the result dataframe
            result_columns = ["hand"]
            for code in action_codes:
                result_columns.append(f"{code}_strat")
                result_columns.append(f"{code}_ev")

            result_columns.extend(["best_action", "best_ev", "difficulty"])

            # Create the result dataframe with all strategies and EVs
            result_df = filtered_df[result_columns].copy()


            # Save filtered results to CSV
            csv_filename = output_subdir / f"hardest_{self.num_hands}_hands.csv"
            result_df.to_csv(csv_filename, index=False)

            # Create visualizations for each hand
            scenario_name = f"{game_type}_{depth}_{street}_{action_seq}_{position}"

            # Process each hand
            for i, row in result_df.iterrows():
                hand = row["hand"]
                action = row["best_action"]
                ev = row["best_ev"]

                # Convert hand notation to card notation
                card1, card2 = self.hand_to_cards(hand)

                # Create output path
                output_path = output_subdir / f"{hand}_{action}_{ev:.6f}.png"

                # Create visualization
                visualizer = PokerTableVisualizer(
                    clean_json,
                    card1,
                    card2,
                    str(output_path),
                    solution_path=str(file_path),
                )
                visualizer.create_visualization()

                logger.info(
                    f"Created visualization for {hand} ({card1}, {card2}) - Best action: {action}, EV: {ev:.6f}"
                )

            # Update stats
            self.stats["processed_files"] += 1

            # Create a summary file
            with open(output_subdir / "summary.txt", "w") as f:
                f.write(f"Solution: {scenario_name}\n")
                f.write(f"Total hands: {len(df_solutions)}\n")
                f.write(f"Filtered hands: {len(filtered_df)}\n")
                f.write(
                    f"EV range: {self.min_threshold} to {self.max_threshold}\n"
                )
                f.write(f"Top {self.num_hands} hardest hands\n\n")

                f.write("Hands by action:\n")
                action_counts = result_df["best_action"].value_counts()
                for action, count in action_counts.items():
                    f.write(f"  {action}: {count} hands\n")

            return len(filtered_df)

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}", exc_info=True)
            self.stats["skipped_files"] += 1
            return 0

    def run(self):
        """Process all solution files"""
        # Get solution files
        solution_files = self.get_solution_files()
        self.stats["total_files"] = len(solution_files)

        logger.info(f"Found {len(solution_files)} solution files to process")

        # Process each file
        for file_path in solution_files:
            self.process_solution_file(file_path)

        # Print final stats
        logger.info(f"\nProcessing complete!")
        logger.info(f"Total files: {self.stats['total_files']}")
        logger.info(f"Processed files: {self.stats['processed_files']}")
        logger.info(f"Skipped files: {self.stats['skipped_files']}")
        logger.info(f"Total hands: {self.stats['total_hands']}")
        logger.info(f"Filtered hands: {self.stats['filtered_hands']}")
        logger.info(f"Visualizations saved to: {self.output_dir}")


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Batch process poker solution files and create visualizations"
    )

    parser.add_argument(
        "--input",
        default="poker_solutions",
        help="Directory containing solution JSON files",
    )
    parser.add_argument(
        "--output", default="visualizations", help="Directory to save visualizations"
    )
    parser.add_argument(
        "--min-ev", type=float, default=0.009, help="Minimum EV threshold"
    )
    parser.add_argument(
        "--max-ev", type=float, default=0.05, help="Maximum EV threshold"
    )
    parser.add_argument(
        "--num-hands",
        type=int,
        default=20,
        help="Number of hardest hands to extract per solution file",
    )
    parser.add_argument("--game-type", help="Filter by game type")
    parser.add_argument("--depth", help="Filter by stack depth")
    parser.add_argument("--position", help="Filter by position")

    args = parser.parse_args()

    # Create and run the batch visualizer
    visualizer = BatchVisualizer(
        solutions_dir=args.input,
        output_dir=args.output,
        min_threshold=args.min_ev,
        max_threshold=args.max_ev,
        num_hands=args.num_hands,
        game_type=args.game_type,
        depth=args.depth,
        position=args.position,
    )

    visualizer.run()


if __name__ == "__main__":
    main()
