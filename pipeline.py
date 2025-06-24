from read_solution import read_spot_solution
from clear_spot_solution_json import clear_spot_solution_json
from poker_table_visualizer import PokerTableVisualizer
import json
import pandas as pd
import os
import shutil

# Path to the solution file
path = "solutions/icm/200 players/100% left/RFI/example.json"

# Clean and parse the JSON
clean_json = json.loads(clear_spot_solution_json(path))

# Read the spot solution
df_solutions = read_spot_solution(clean_json)

# Filter hands where the best strategy has EV between min_threshold and max_threshold
min_threshold = 0.009  # Minimum EV threshold
max_threshold = 0.05  # Maximum EV threshold
filtered_hands = []

for index, row in df_solutions.iterrows():
    best_action = row["best_action"]
    best_ev = row[f"{best_action}_ev"]

    if min_threshold < best_ev < max_threshold:
        filtered_hands.append(row)

# Convert the filtered hands to a DataFrame
if filtered_hands:
    filtered_df = pd.DataFrame(filtered_hands)

    # Create a result DataFrame with custom columns
    result_df = filtered_df[["hand", "best_action"]].copy()

    # Add a new column for the best action's EV
    result_df["best_ev"] = filtered_df.apply(
        lambda row: row[f"{row['best_action']}_ev"], axis=1
    )

    # Sort by best_ev in ascending order
    result_df = result_df.sort_values("best_ev")

    # Create visualization directory
    visualization_dir = "hand_visualizations"
    if os.path.exists(visualization_dir):
        shutil.rmtree(visualization_dir)
    os.makedirs(visualization_dir, exist_ok=True)

    # Create visualizations for each hand
    print("\nCreating visualizations for each filtered hand...")

    # Function to convert hand notation to card notation
    def hand_to_cards(hand):
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

        # Handle pairs (e.g., 22, AA)
        if len(hand) == 2 and hand[0] == hand[1]:
            rank = rank_map[hand[0]]
            # Use different suits for the pair
            return f"{rank}h", f"{rank}s"

        # Handle suited hands (e.g., AKs)
        elif len(hand) == 3 and hand[2] == "s":
            rank1 = rank_map[hand[0]]
            rank2 = rank_map[hand[1]]
            # Both cards have same suit (spades)
            return f"{rank1}s", f"{rank2}s"

        # Handle offsuit hands (e.g., AKo, or simply AK which is implied offsuit)
        else:
            rank1 = rank_map[hand[0]]
            rank2 = rank_map[hand[1]]
            # Use different suits (hearts and diamonds)
            return f"{rank1}h", f"{rank2}d"

    # Process each hand
    for i, row in result_df.iterrows():
        hand = row["hand"]
        action = row["best_action"]
        ev = row["best_ev"]

        # Convert hand notation to card notation
        card1, card2 = hand_to_cards(hand)

        # Create output path
        output_path = os.path.join(visualization_dir, f"{hand}_{action}_{ev:.6f}.png")

        # Create visualization
        visualizer = PokerTableVisualizer(
            clean_json,
            card1,
            card2,
            output_path,
            solution_path=path,
        )
        visualizer.create_visualization()

        print(
            f"  Created visualization for {hand} ({card1}, {card2}) - Best action: {action}, EV: {ev:.6f}"
        )

    # Save filtered results to CSV
    output_filename = f"filtered_hands_ev_{min_threshold}_to_{max_threshold}.csv"
    result_df.to_csv(output_filename, index=False)

    # Display results
    pd.set_option("display.max_rows", 20)  # Show more rows
    print(f"\nHands with best strategy EV between {min_threshold} and {max_threshold}:")
    print(result_df)
    print(f"\nTotal hands found: {len(result_df)}")
    print(f"Results saved to {output_filename}")
    print(f"Visualizations saved to {visualization_dir}/ directory")
else:
    print(
        f"\nNo hands found with best strategy EV between {min_threshold} and {max_threshold}"
    )
