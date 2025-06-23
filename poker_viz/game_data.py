"""
Game data processing module for poker table visualization.
"""


class GameDataProcessor:
    """Process poker game data from JSON format."""

    def __init__(self, json_data):
        """
        Initialize the game data processor.

        Args:
            json_data: The JSON data containing poker game information
        """
        self.data = json_data
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

        # Replace UTG+2 with MP for consistency across the application
        for player in self.players:
            if player.get("position") == "UTG+2":
                player["position"] = "MP"

        # Find the hero
        self.hero = next((p for p in self.players if p.get("is_hero", False)), None)

        # Process chips on table for each player
        for player in self.players:
            # Convert chips_on_table to float or default to 0
            player["chips_on_table"] = float(player.get("chips_on_table", 0))

    def get_scenario_description(self):
        """Return a simple scenario description string."""
        if not self.players:
            return ""

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
            "MP": 6,  # Top left (UTG+2)
            "UTG+2": 6,  # Also map UTG+2 to same position as MP
            "UTG+1": 7,  # Left middle
            "UTG": 8,  # Bottom left
        }
