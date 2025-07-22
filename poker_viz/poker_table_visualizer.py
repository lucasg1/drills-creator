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
        scale_factor=1,
    ):
        """
        Initialize the poker table visualizer.

        Args:
            json_data: JSON data containing poker game information
            card1: First hero card (e.g., "Ah")
            card2: Second hero card (e.g., "Kd")
            output_path: Path to save the output image
            solution_path: Path to the solution file (optional)
            scale_factor: Scale factor for rendering (default: 1)
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

        # Generate player layers on initialization
        self._create_player_layers()

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

        # Template image for static elements
        self.template_image = None

        # Cached layers for player graphics
        self.circle_layer = None
        self.rectangle_layer = None
        self.player_signature = None

    def create_template(self):
        """Create a template image with static elements (table, background, logo)"""
        # Reset the image and draw objects
        template = Image.new(
            "RGBA",
            (self.config.width, self.config.height),
            self.config.background_color,
        )
        template_draw = ImageDraw.Draw(template, "RGBA")

        # Create a temporary instance of TableDrawer for the template
        template_table_drawer = TableDrawer(
            self.config, self.game_data, template, template_draw
        )
        template_table_drawer.set_fonts(
            self.title_font, self.player_font, self.card_font
        )

        # Draw the table on the template
        template, _ = template_table_drawer.draw_table()

        # Store the template
        self.template_image = template

        return self.template_image

    def refresh(self):
        """Refresh the visualizer's state when reusing it for different hands."""
        # If we have a template, use it as the starting point
        if self.template_image:
            self.img = self.template_image.copy()
        else:
            # Otherwise create a new blank image
            self.img = Image.new(
                "RGBA",
                (self.config.width, self.config.height),
                self.config.background_color,
            )

        self.draw = ImageDraw.Draw(self.img, "RGBA")

        # Reset the game data if it's been changed
        if hasattr(self, "game_data") and hasattr(self.game_data, "process_data"):
            self.game_data.process_data()

        # Reinitialize all drawers with the current card values
        self._init_drawers()

        # Recompute player layers if the player layout changed
        current_sig = self._compute_player_signature()
        if (
            self.circle_layer is None
            or self.rectangle_layer is None
            or current_sig != self.player_signature
        ):
            self._create_player_layers()

    def _compute_player_signature(self):
        """Return a tuple uniquely identifying the current players."""
        return tuple(
            (
                p.get("position"),
                p.get("current_stack"),
                p.get("is_dealer"),
                p.get("is_active"),
                p.get("is_folded"),
                p.get("is_hero"),
            )
            for p in self.game_data.players
        )

    def _create_player_layers(self):
        """Pre-render player circles and rectangles for faster reuse."""
        base = Image.new("RGBA", (self.config.width, self.config.height), (0, 0, 0, 0))
        base_draw = ImageDraw.Draw(base, "RGBA")
        temp_drawer = PlayerDrawer(self.config, self.game_data, base, base_draw)
        temp_drawer.set_fonts(self.title_font, self.player_font, self.card_font)

        # Draw circles first and store the result
        temp_drawer.draw_player_circles()
        self.circle_layer = base.copy()

        # Draw rectangles on a new layer using stored positions
        rect_layer = Image.new("RGBA", (self.config.width, self.config.height), (0, 0, 0, 0))
        temp_drawer.img = rect_layer
        temp_drawer.draw = ImageDraw.Draw(rect_layer, "RGBA")
        temp_drawer.draw_player_rectangles()
        self.rectangle_layer = rect_layer

        # Record the current player signature
        self.player_signature = self._compute_player_signature()

    def create_visualization(self):
        """Create the poker table visualization."""
        # Refresh the visualizer's state when reusing it
        self.refresh()

        # If we don't have a template yet, create one
        if not self.template_image:
            self.create_template()
            self.refresh()  # Refresh again with the template as a base

        # Update drawer objects with the current image and draw objects
        self.card_drawer.img = self.img
        self.card_drawer.draw = self.draw
        self.chip_drawer.img = self.img
        self.chip_drawer.draw = self.draw

        # Composite background circles
        self.img = Image.alpha_composite(self.img, self.circle_layer)
        self.draw = ImageDraw.Draw(self.img, "RGBA")

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

        # Composite player rectangles on top of the cards
        self.img = Image.alpha_composite(self.img, self.rectangle_layer)
        self.draw = ImageDraw.Draw(self.img, "RGBA")

        # Update chip drawer with the current image
        self.chip_drawer.img = self.img
        self.chip_drawer.draw = self.draw

        # Draw player chips
        chips_img, chips_draw = self.chip_drawer.draw_player_chips()
        self.img = chips_img
        self.draw = chips_draw

        # Skip Gaussian blur for performance optimization
        # Directly downsample to the original base resolution with a faster filter
        if hasattr(self.config, "scale_factor") and self.config.scale_factor > 1:
            self.img = self.img.resize(
                (self.config.base_width, self.config.base_height), Image.BICUBIC
            )

        # Save the image
        self.img.save(self.output_path, optimize=True)
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
