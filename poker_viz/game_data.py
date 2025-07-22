"""
Game data processing module for poker table visualization.
"""


class GameDataProcessor:
    """Process poker game data from JSON format."""

    def __init__(self, json_data, solution_path=None):
        """
        Initialize the game data processor.

        Args:
            json_data: The JSON data containing poker game information
            solution_path (str, optional): Path to the original solution file.
                This is used to extract additional scenario information such as
                average stack and percentage of field left.
        """
        self.data = json_data
        self.solution_path = solution_path
        self.parsed_avg_stack = None
        self.parsed_field_left = None
        self.process_game_data()

    def update_data(self, json_data, solution_path=None):
        """Update the stored JSON data and reprocess it."""

        self.data = json_data
        if solution_path is not None:
            self.solution_path = solution_path

        # Clear cached info so it can be recalculated
        self.parsed_avg_stack = None
        self.parsed_field_left = None

        self.process_game_data()

    def process_game_data(self):
        """Extract relevant information from the JSON data."""
        self.game = self.data.get("game", {})
        self.players = self.game.get("players", [])
        self.num_players = len(self.players)
        self.pot = float(self.game.get("pot", 0))
        self.active_position = self.game.get("active_position", "")
        self.board = self.game.get("board", "")

        # Find which players are still in the hand
        self.active_players = [p for p in self.players if not p.get("is_folded", False)]

        # Find the hero
        self.hero = next((p for p in self.players if p.get("is_hero", False)), None)

        # Process chips on table for each player
        for player in self.players:
            # Convert chips_on_table to float or default to 0
            player["chips_on_table"] = float(player.get("chips_on_table", 0))

        # Parse additional scenario info from the solution path if provided
        if self.solution_path:
            self._parse_solution_path()

    def _parse_solution_path(self):
        """Extract average stack and field left information from the solution path."""
        import os
        import re

        try:
            path_parts = os.path.normpath(self.solution_path).split(os.sep)
            # Look for the directory starting with 'MTT'
            game_dir = next((p for p in path_parts if p.startswith("MTT")), "")

            # Extract field left information
            field_desc = None
            pct_match = re.search(r"PCT(\d+)", game_dir)
            if pct_match:
                field_desc = f"{pct_match.group(1)}% Field left"
            elif "START" in game_dir:
                field_desc = "100% Field left"
            elif "FT" in game_dir:
                field_desc = "Final table"
            elif "BUBBLEMID" in game_dir:
                field_desc = "Near bubble"

            self.parsed_field_left = field_desc

            # Extract average stack from depth directory
            depth_part = next((p for p in path_parts if p.startswith("depth_")), "")
            if depth_part:
                try:
                    self.parsed_avg_stack = int(depth_part.split("_")[1])
                except (IndexError, ValueError):
                    self.parsed_avg_stack = None
        except Exception:
            self.parsed_avg_stack = None
            self.parsed_field_left = None

    def get_scenario_description(self):
        """Return a simple scenario description string."""
        if not self.players:
            return ""
        # If we parsed information from the solution path, use that
        if self.parsed_avg_stack is not None and self.parsed_field_left:
            return f"Average: {self.parsed_avg_stack}BB, {self.parsed_field_left}"

        # Fallback to using data from the JSON itself
        avg_stack = sum(float(p.get("stack", 0)) for p in self.players) / len(
            self.players
        )
        players_left = len(self.players)

        avg_stack_bb = int(round(avg_stack))

        return f"{avg_stack_bb}bb, {players_left} players"

    def get_position_mapping(self):
        """
        Calculate position mapping based on hero position.

        Returns:
            dict: Mapping from poker positions to seat indices
        """
        # Define standard poker table positions based on player count
        standard_positions_by_count = {
            9: ["UTG", "UTG+1", "UTG+2", "LJ", "HJ", "CO", "BTN", "SB", "BB"],
            8: ["UTG", "UTG+1", "LJ", "HJ", "CO", "BTN", "SB", "BB"],
            7: ["UTG", "LJ", "HJ", "CO", "BTN", "SB", "BB"],
            6: ["LJ", "HJ", "CO", "BTN", "SB", "BB"],
            5: ["HJ", "CO", "BTN", "SB", "BB"],
            4: ["CO", "BTN", "SB", "BB"],
            3: ["BTN", "SB", "BB"],
            2: ["SB", "BB"],
        }

        # Get the standard positions for the current number of players
        standard_positions = standard_positions_by_count.get(self.num_players, [])

        # Find the hero player
        hero_player = self.hero
        hero_position = hero_player.get("position") if hero_player else None

        # Calculate position mapping based on hero position
        position_to_seat = {}
        if hero_position and standard_positions:
            try:
                # Get the index of hero position in standard_positions
                hero_index = standard_positions.index(hero_position)

                # Adjust seats based on hero position
                # Rearrange positions so hero is at seat 0 (bottom middle)
                for i in range(self.num_players):
                    # Calculate position index with wrapping (clockwise from hero)
                    pos_idx = (hero_index + i) % self.num_players
                    position = standard_positions[pos_idx]

                    # Assign to the appropriate seat
                    position_to_seat[position] = i
            except ValueError:
                # If hero position not found in standard_positions, use default mapping
                position_to_seat = self._get_default_mapping()
                # Ensure hero is at position 0
                position_to_seat[hero_position] = 0
        else:
            # Default mapping if no hero
            position_to_seat = self._get_default_mapping()

        return position_to_seat

    def _get_default_mapping(self):
        """Get the default position to seat mapping."""
        return {
            "BB": 8,  # Bottom left
            "SB": 1,  # Bottom right
            "BTN": 2,  # Right bottom
            "CO": 3,  # Right top
            "HJ": 4,  # Top right
            "LJ": 5,  # Top middle
            "UTG+2": 6,  # Top left
            "UTG+1": 7,  # Left middle
            "UTG": 8,  # Bottom left
        }
