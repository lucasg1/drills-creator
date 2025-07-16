import json
import os
import pandas as pd
from pathlib import Path
import argparse
from read_solution import read_spot_solution
from clear_spot_solution_json import clear_spot_solution_json
import logging
import random
from concurrent.futures import ProcessPoolExecutor, as_completed

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("separate_solutions.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def process_single_hand(args):
    """Process a single hand and create a separate JSON file - for multiprocessing"""
    hand_data, clean_json, output_subdir, original_file_path, metadata = args
    hand, row = hand_data

    try:
        # Create a new JSON for this hand
        hand_json = {
            "metadata": {
                "original_file": str(original_file_path),
                "hand": hand,
                "best_action": row["best_action"],
                "best_ev": row["best_ev"],
                # Add scenario metadata
                "mode": metadata.get("mode", ""),
                "field_size": metadata.get("field_size", 0),
                "field_left": metadata.get("field_left", ""),
                "position": metadata.get("position", ""),
                "stack_depth": metadata.get("stack_depth", ""),
                "action": metadata.get("action", ""),
                "game_type": metadata.get("game_type", ""),
                "street": metadata.get("street", ""),
                "action_sequence": metadata.get("action_sequence", ""),
            },
            "spot_solution": clean_json.get("spot_solution", {}),
            "hand_data": {},
        }

        # Copy essential info from original JSON that applies to this hand
        if "game_info" in clean_json:
            hand_json["game_info"] = clean_json["game_info"]

        if "node_info" in clean_json:
            hand_json["node_info"] = clean_json["node_info"]

        # Extract hand-specific data
        action_codes = [col[:-6] for col in row.index if col.endswith("_strat")]

        # Add hand-specific data
        hand_json["hand_data"] = {
            "hand": hand,
            "best_action": row["best_action"],
            "best_ev": row["best_ev"],
        }

        # Add strategy and EV data for each action
        for code in action_codes:
            if f"{code}_strat" in row and f"{code}_ev" in row:
                hand_json["hand_data"][f"{code}_strat"] = row[f"{code}_strat"]
                hand_json["hand_data"][f"{code}_ev"] = row[f"{code}_ev"]

        # Create output file name
        output_path = output_subdir / f"{hand}.json"

        # Save to JSON file
        with open(output_path, "w") as f:
            json.dump(hand_json, f, indent=2)

        return f"Created separate JSON for hand {hand} - Best action: {row['best_action']}, EV: {row['best_ev']:.6f}"

    except Exception as e:
        logger.error(f"Error processing hand {hand}: {e}", exc_info=True)
        return f"Error processing hand {hand}: {str(e)}"


class SolutionSeparator:
    def __init__(
        self,
        solutions_dir="poker_solutions",
        output_dir="separated_solutions_by_hand",
        min_threshold=None,
        max_threshold=None,
        game_type=None,
        depth=None,
        position=None,
        exclude_poor_actions=False,
    ):
        """
        Initialize the solution separator

        Parameters:
        solutions_dir (str): Path to the directory with solution JSON files
        output_dir (str): Path to directory where individual hand JSONs will be saved
        min_threshold (float, optional): Minimum EV threshold for filtering hands
        max_threshold (float, optional): Maximum EV threshold for filtering hands
        game_type (str, optional): Filter by specific game type
        depth (str, optional): Filter by specific stack depth
        position (str, optional): Filter by specific position
        exclude_poor_actions (bool, optional): Exclude hands where all non-fold actions have EV < -0.05
        """
        self.solutions_dir = Path(solutions_dir)
        self.output_dir = Path(output_dir)
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.game_type = game_type
        self.depth = depth
        self.position = position
        self.exclude_poor_actions = exclude_poor_actions

        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)

        # Track stats
        self.stats = {
            "total_files": 0,
            "processed_files": 0,
            "skipped_files": 0,
            "total_hands": 0,
            "separated_hands": 0,
        }

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

    def create_metadata_json(
        self, game_type, depth, street, action_seq, position, output_dir
    ):
        """
        Create a JSON file with metadata information for the current folder

        Parameters:
        game_type (str): The game type (e.g., MTTGeneral_ICM8m200PT)
        depth (str): The stack depth
        street (str): The street
        action_seq (str): The action sequence
        position (str): The position
        output_dir (Path): The output directory
        """
        try:
            logger.info(
                f"Creating metadata JSON for: game_type={game_type}, depth={depth}, position={position}"
            )

            # Extract mode (icm or chipev)
            mode = "icm" if "ICM" in game_type.upper() else "chipev"

            # Extract field size (200 or 1000)
            field_size = 1000
            if "200" in game_type:
                field_size = 200

            # Extract field left
            field_left = "100%"  # Default
            if "START" in game_type:
                field_left = "100%"
            elif "PCT75" in game_type:
                field_left = "75%"
            elif "PCT50" in game_type:
                field_left = "50%"
            elif "PCT37" in game_type:
                field_left = "37%"
            elif "PCT25" in game_type:
                field_left = "25%"
            elif "BUBBLE" in game_type:
                field_left = "bubble"
            elif "3TL" in game_type:
                field_left = "3 tables left"
            elif "2TL" in game_type:
                field_left = "2 tables left"
            elif "FT" in game_type:
                field_left = "final table"

            # Process position (utg, utg+1, mp, hj, lj, co, btn, sb, bb)
            pos = position.lower()

            # Process action (default is "rfi")
            action = "rfi"
            if "pf_" in action_seq.lower():
                action = "rfi"
            # Add more action type detections as needed

            # Create metadata dict
            metadata = {
                "mode": mode,
                "field_size": field_size,
                "field_left": field_left,
                "position": pos,
                "stack_depth": depth,
                "action": action,
                "game_type": game_type,
                "street": street,
                "action_sequence": action_seq,
            }

            # Create JSON file
            json_path = output_dir / "metadata.json"
            logger.info(f"Writing metadata to: {json_path}")

            with open(json_path, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Created metadata JSON file at {json_path}")

            return metadata

        except Exception as e:
            logger.error(f"Error creating metadata JSON: {e}", exc_info=True)
            return {}

    def process_solution_file(self, file_path):
        """Process a single solution file and separate it into individual hand JSONs"""
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
            filtered_df = df_solutions
            if self.min_threshold is not None:
                filtered_df = filtered_df[filtered_df["best_ev"] >= self.min_threshold]
            if self.max_threshold is not None:
                filtered_df = filtered_df[filtered_df["best_ev"] <= self.max_threshold]

            # Filter out hands where all non-fold actions have EV < -0.05
            if self.exclude_poor_actions:

                def has_viable_non_fold_action(row):
                    non_fold_evs = [
                        row[f"{code}_ev"]
                        for code in action_codes
                        if code != "F" and f"{code}_ev" in row
                    ]

                    return (
                        any(ev >= -0.05 for ev in non_fold_evs)
                        if non_fold_evs
                        else True
                    )

                filtered_df = filtered_df[
                    filtered_df.apply(has_viable_non_fold_action, axis=1)
                ]

            filtered_df = filtered_df.copy()

            # Update stats
            self.stats["total_hands"] += len(df_solutions)
            self.stats["separated_hands"] += len(filtered_df)

            if filtered_df.empty:
                if self.min_threshold is not None or self.max_threshold is not None:
                    logger.info(
                        f"No hands found after applying EV thresholds {self.min_threshold} to {self.max_threshold}"
                    )
                else:
                    logger.info("No hands found in solution")
                self.stats["skipped_files"] += 1
                return

            # Create metadata JSON
            metadata = self.create_metadata_json(
                game_type, depth, street, action_seq, position, output_subdir
            )  # Process each hand in parallel
            with ProcessPoolExecutor() as executor:
                # Prepare arguments for each hand processing task
                hand_args = [
                    ((row["hand"], row), clean_json, output_subdir, file_path, metadata)
                    for _, row in filtered_df.iterrows()
                ]

                # Submit all hand processing tasks
                future_to_hand = {
                    executor.submit(process_single_hand, args): args[0][0]
                    for args in hand_args
                }

                # Process completed tasks as they finish
                for future in as_completed(future_to_hand):
                    try:
                        result_message = future.result()
                        logger.info(result_message)
                    except Exception as e:
                        hand = future_to_hand[future]
                        logger.error(
                            f"Error creating separate JSON for {hand}: {e}",
                            exc_info=True,
                        )

            # Update stats
            self.stats["processed_files"] += 1

            # Create a summary file
            scenario_name = f"{game_type}_{depth}_{street}_{action_seq}_{position}"
            with open(output_subdir / "summary.txt", "w") as f:
                f.write(f"Solution: {scenario_name}\n")
                f.write(f"Total hands in original solution: {len(df_solutions)}\n")
                f.write(f"Separated hands: {len(filtered_df)}\n")
                if self.min_threshold is not None or self.max_threshold is not None:
                    f.write(
                        f"EV range: {self.min_threshold} to {self.max_threshold}\n\n"
                    )

                f.write("Hands by action:\n")
                action_counts = filtered_df["best_action"].value_counts()
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
        logger.info(f"Separated hands: {self.stats['separated_hands']}")
        logger.info(f"Individual hand JSONs saved to: {self.output_dir}")


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description=(
            "Separate poker solution files into individual JSON files for each hand. "
            "Each hand will have its own JSON file with solution data."
        )
    )

    parser.add_argument(
        "--input",
        default="poker_solutions",
        help="Directory containing solution JSON files",
    )
    parser.add_argument(
        "--output",
        default="separated_solutions_by_hand",
        help="Directory to save individual hand JSON files",
    )
    parser.add_argument(
        "--min-ev", type=float, default=None, help="Minimum EV threshold"
    )
    parser.add_argument(
        "--max-ev", type=float, default=None, help="Maximum EV threshold"
    )
    parser.add_argument("--game-type", help="Filter by game type")
    parser.add_argument("--depth", help="Filter by stack depth")
    parser.add_argument("--position", help="Filter by position")
    parser.add_argument(
        "--exclude-poor-actions",
        action="store_true",
        help="Exclude hands where all non-fold actions have EV < -0.05",
    )

    args = parser.parse_args()

    # Create and run the solution separator
    separator = SolutionSeparator(
        solutions_dir=args.input,
        output_dir=args.output,
        min_threshold=args.min_ev,
        max_threshold=args.max_ev,
        game_type=args.game_type,
        depth=args.depth,
        position=args.position,
        exclude_poor_actions=args.exclude_poor_actions,
    )

    separator.run()


if __name__ == "__main__":
    main()
