import os
import json
import argparse
from pathlib import Path


def list_solutions(base_dir, search_term=None, list_details=False):
    """List all solution files with optional search and details."""
    base_path = Path(base_dir)

    if not base_path.exists():
        print(f"Error: Directory '{base_dir}' does not exist.")
        return

    print(f"\n=== Poker Solutions ===")

    # Collect all solution files
    solution_files = list(base_path.glob("**/*.json"))

    if not solution_files:
        print(f"No solution files found in {base_dir}")
        return

    # Group by game type
    game_types = {}
    for file_path in solution_files:
        # Extract game type from path
        rel_path = file_path.relative_to(base_path)
        parts = rel_path.parts

        if len(parts) > 0:
            game_type = parts[0]
            if game_type not in game_types:
                game_types[game_type] = []

            # If search term provided, filter files
            if search_term:
                # Check path
                if search_term.lower() in str(rel_path).lower():
                    game_types[game_type].append((rel_path, file_path))
                    continue

                # Check file content if detailed search requested
                if list_details:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = json.load(f)
                            content_str = json.dumps(content)
                            if search_term.lower() in content_str.lower():
                                game_types[game_type].append((rel_path, file_path))
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
            else:
                game_types[game_type].append((rel_path, file_path))

    # Print results
    total_count = 0
    for game_type, files in sorted(game_types.items()):
        if not files:  # Skip empty game types after filtering
            continue

        print(f"\n[{game_type}] - {len(files)} solutions")

        for rel_path, full_path in sorted(files):
            print(f"  {rel_path}")

            # Print additional details if requested
            if list_details:
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                        # Extract key information
                        active_pos = data.get("game", {}).get(
                            "active_position", "Unknown"
                        )
                        pot = data.get("game", {}).get("pot", "Unknown")
                        street = (
                            data.get("game", {})
                            .get("current_street", {})
                            .get("type", "Unknown")
                        )
                        board = data.get("game", {}).get("board", "")

                        # Get hero position
                        hero_pos = "Unknown"
                        for player in data.get("game", {}).get("players", []):
                            if player.get("is_hero", False):
                                hero_pos = player.get("position", "Unknown")
                                break

                        print(f"    • Street: {street}")
                        print(f"    • Active Position: {active_pos}")
                        print(f"    • Hero Position: {hero_pos}")
                        print(f"    • Pot: {pot}")
                        if board:
                            print(f"    • Board: {board}")
                        print("")

                except Exception as e:
                    print(f"    • Error reading file details: {e}\n")

            total_count += 1

    print(f"\nTotal solutions found: {total_count}")


def analyze_solution(file_path):
    """Display a summary of a specific solution file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        print(f"\n=== Solution Analysis: {file_path} ===\n")

        # Game info
        game = data.get("game", {})
        print(f"Street: {game.get('current_street', {}).get('type', 'Unknown')}")
        print(f"Active Position: {game.get('active_position', 'Unknown')}")
        print(f"Pot: {game.get('pot', 'Unknown')}")
        if game.get("board"):
            print(f"Board: {game.get('board')}")
        print()

        # Player info
        print("Players:")
        for player in game.get("players", []):
            hero_mark = " (HERO)" if player.get("is_hero", False) else ""
            active_mark = " (ACTIVE)" if player.get("is_active", False) else ""
            stack = player.get("stack", "Unknown")
            position = player.get("position", "Unknown")

            print(f"  {position}: Stack {stack}{hero_mark}{active_mark}")

        print()

        # Action solutions
        print("Actions:")
        for action_sol in data.get("action_solutions", []):
            action = action_sol.get("action", {})
            freq = action_sol.get("total_frequency", 0)
            print(f"  {action.get('display_name', 'Unknown')}: {freq*100:.2f}%")

    except Exception as e:
        print(f"Error analyzing file: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Manage and search poker solution files"
    )
    parser.add_argument(
        "--dir", default="poker_solutions", help="Base directory for solution files"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List command
    list_parser = subparsers.add_parser("list", help="List solution files")
    list_parser.add_argument("--search", help="Search term to filter solutions")
    list_parser.add_argument(
        "--details", action="store_true", help="Show detailed information"
    )

    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze a specific solution file"
    )
    analyze_parser.add_argument("file", help="Path to the solution file")

    args = parser.parse_args()

    if args.command == "list" or args.command is None:
        list_solutions(args.dir, args.search, args.details)
    elif args.command == "analyze":
        analyze_solution(args.file)


if __name__ == "__main__":
    main()
