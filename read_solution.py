import json
import pandas as pd
import numpy as np

def read_spot_solution(spot_solution_json):

    data = spot_solution_json

    # Get all available action codes
    action_solutions = data["action_solutions"]
    all_actions = [a["action"]["code"] for a in action_solutions]
    print(f"Available actions: {all_actions}")

    # Extract hand decision mappings
    hand_solutions = []
    actions_data = {}

    # Store both strategy (percentage) and EVs for each action
    for action_solution in action_solutions:
        action_code = action_solution["action"]["code"]
        actions_data[action_code] = {
            "strategy": action_solution["strategy"],
            "evs": action_solution["evs"],
        }

    # Get all hand names and index from simple_hand_counters
    hand_names = list(data["players_info"][0]["simple_hand_counters"].keys())
    hand_indices = {i: hand for i, hand in enumerate(hand_names)}

    # Create hand data with action percentages and EVs
    num_hands = len(hand_names)
    for i in range(num_hands):
        hand_data = {"hand": hand_indices[i]}

        # Add percentage and EV for each action
        for action_code in all_actions:
            if action_code in actions_data:
                # Add percentage for this action (0-100%)
                hand_data[f"{action_code}_strat"] = round(
                    actions_data[action_code]["strategy"][i] * 100, 2
                )

                # Add EV for this action
                hand_data[f"{action_code}_ev"] = round(
                    actions_data[action_code]["evs"][i], 5
                )

        # Also add the best action based on highest percentage
        best_action_strat = max(
            [(action_code, hand_data[f"{action_code}_strat"]) for action_code in all_actions],
            key=lambda x: x[1],
        )
        hand_data["best_action"] = best_action_strat[0]

        # Add highest EV action
        best_action_ev = max(
            [(action_code, hand_data[f"{action_code}_ev"]) for action_code in all_actions],
            key=lambda x: x[1],
        )
        hand_data["best_ev_action"] = best_action_ev[0]

        hand_solutions.append(hand_data)

    # Convert to DataFrame
    df_solutions = pd.DataFrame(hand_solutions)

    # Display the first few rows with all columns
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 120)
    print(df_solutions.head(40))

    # Save the results to a CSV file
    df_solutions.to_csv("hand_solutions.csv", index=False)
    print("\nResults saved to hand_solutions.csv")

    return df_solutions
