"""
Backwards compatibility module for the poker table visualizer.
This file provides the same interface as the original poker_table_visualizer.py
but imports the functionality from the modular implementation.
"""

import json
import os
from poker_viz.poker_table_visualizer import PokerTableVisualizer, load_json_data


def main():
    """Main function to run the poker table visualizer."""
    # Path to the JSON file
    json_file = "poker_solutions/MTTGeneral_ICM8m200PTSTART/depth_100_125/preflop/no_actions/UTG/hero_UTG_22.json"

    # Load the JSON data
    data = load_json_data(json_file)

    # Define hero cards (these would be provided by the user)
    # Examples: "As" (Ace of spades), "Kh" (King of hearts)
    card1 = "Ah"  # Ace of hearts - change this as needed
    card2 = "Kd"  # King of diamonds - change this as needed

    # Create the visualization
    visualizer = PokerTableVisualizer(data, card1, card2)
    output_path = visualizer.create_visualization()

    print(f"Open {output_path} to see the poker table visualization")


if __name__ == "__main__":
    main()
