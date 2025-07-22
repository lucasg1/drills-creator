"""
Main module for poker table visualization.
"""

import os
from PIL import Image, ImageDraw, ImageFilter

from .config import PokerTableConfig
from .game_data import GameDataProcessor
from .table_drawer import TableDrawer
from .player_drawer import PlayerDrawer
from .card_drawer import CardDrawer
from .chip_drawer import ChipDrawer


class PokerTableVisualizer:
    """Main class for creating poker table visualizations."""

    def __init__(
        self,
        json_data,
        card1=None,
        card2=None,
        output_path="poker_table.png",
        solution_path=None,
        scale_factor=2,
    ):
        """
        Initialize the poker table visualizer.

        Args:
            json_data: JSON data containing poker game information
            card1: First hero card (e.g., "Ah")
            card2: Second hero card (e.g., "Kd")
            output_path: Path to save the output image
            solution_path: Path to the solution file (optional)
            scale_factor: Scale factor for rendering (default: 2)
        """
        self.data = json_data
        self.card1 = card1
        self.card2 = card2
        self.output_path = output_path
        self.solution_path = solution_path

        # Path to card images
        self.cards_folder = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cards-images"
        )

        num_players = len(self.data["game"]["players"])

        # Initialize configuration
        self.config = PokerTableConfig(
            scale_factor=scale_factor, num_players=num_players
        )

        # Setup the image and draw objects
        self.img = Image.new(
            "RGBA",
            (self.config.width, self.config.height),
            self.config.background_color,
        )
        self.draw = ImageDraw.Draw(
            self.img, "RGBA"
        )  # RGBA mode for better anti-aliasing

        # Load fonts
        self.title_font, self.player_font, self.card_font = self.config.load_fonts()

        # Process game data
        self.game_data = GameDataProcessor(json_data, solution_path=solution_path)

        # Initialize drawers
        self._init_drawers()

    def _init_drawers(self):
        """Initialize all drawing components."""
        # Table drawer
        self.table_drawer = TableDrawer(
            self.config, self.game_data, self.img, self.draw
        )
        self.table_drawer.set_fonts(self.title_font, self.player_font, self.card_font)

        # Player drawer
        self.player_drawer = PlayerDrawer(
            self.config, self.game_data, self.img, self.draw
        )
        self.player_drawer.set_fonts(self.title_font, self.player_font, self.card_font)

        # Card drawer
        self.card_drawer = CardDrawer(
            self.config,
            self.game_data,
            self.img,
            self.draw,
            self.cards_folder,
            self.card1,
            self.card2,
        )
        self.card_drawer.set_fonts(
            self.title_font, self.player_font, self.card_font
        )  # Chip drawer
        self.chip_drawer = ChipDrawer(self.config, self.game_data, self.img, self.draw)
        self.chip_drawer.set_fonts(self.title_font, self.player_font, self.card_font)

    def create_visualization(self):
        """Create the poker table visualization."""
        # Draw the table
        table_img, table_draw = self.table_drawer.draw_table()
        self.img = table_img
        self.draw = table_draw

        # Update drawer objects with the current image and draw objects
        self.player_drawer.img = self.img
        self.player_drawer.draw = self.draw
        self.card_drawer.img = self.img
        self.card_drawer.draw = self.draw
        self.chip_drawer.img = self.img
        self.chip_drawer.draw = self.draw

        # Draw players - this now draws only the background circles
        player_circles_img, player_circles_draw = (
            self.player_drawer.draw_player_circles()
        )
        self.img = player_circles_img
        self.draw = player_circles_draw

        # Update card drawer with the current image
        self.card_drawer.img = self.img
        self.card_drawer.draw = self.draw

        # Draw cards for non-hero players still in the hand
        other_cards_img, other_cards_draw = self.card_drawer.draw_player_cards()
        self.img = other_cards_img
        self.draw = other_cards_draw

        # Draw hero cards if provided
        if self.card1 and self.card2:
            cards_img, cards_draw = self.card_drawer.draw_hero_cards()
            self.img = cards_img
            self.draw = cards_draw

        # Update player drawer with the current image after cards are drawn
        self.player_drawer.img = self.img
        self.player_drawer.draw = self.draw

        # Draw player info rectangles on top of the circles and cards
        player_rectangles_img, player_rectangles_draw = (
            self.player_drawer.draw_player_rectangles()
        )
        self.img = player_rectangles_img
        self.draw = player_rectangles_draw

        # Update chip drawer with the current image
        self.chip_drawer.img = self.img
        self.chip_drawer.draw = self.draw

        # Draw player chips
        chips_img, chips_draw = self.chip_drawer.draw_player_chips()
        self.img = chips_img
        self.draw = chips_draw

        # Apply a final subtle smoothing filter
        self.img = self.img.filter(ImageFilter.GaussianBlur(radius=0.5))

        # Downsample to the original base resolution for super-smooth edges
        # This creates an anti-aliasing effect by averaging neighboring pixels
        if hasattr(self.config, "scale_factor") and self.config.scale_factor > 1:
            self.img = self.img.resize(
                (self.config.base_width, self.config.base_height), Image.LANCZOS
            )

        # Save the image
        self.img.save(self.output_path)
        print(f"Poker table visualization saved to {self.output_path}")

        return self.output_path


def load_json_data(json_file):
    """Load JSON data from file."""
    import json

    with open(json_file, "r") as f:
        return json.load(f)


def main():
    """Main function to run the poker table visualizer."""
    import json

    # Path to the JSON file
    json_file = "poker_solutions/MTTGeneral_ICM8m200PTSTART/depth_100_125/preflop/no_actions/UTG/hero_UTG_22.json"

    # Load the JSON data
    data = load_json_data(json_file)

    # Define hero cards (these would be provided by the user)
    # Examples: "As" (Ace of spades), "Kh" (King of hearts)
    card1 = "Ah"  # Ace of hearts - change this as needed
    card2 = "Kd"  # King of diamonds - change this as needed

    # Create the visualization
    visualizer = PokerTableVisualizer(data, card1, card2, solution_path=json_file)
    output_path = visualizer.create_visualization()

    print(f"Open {output_path} to see the poker table visualization")


if __name__ == "__main__":
    main()
