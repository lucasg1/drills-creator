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

        # Template images for static elements.
        # template_base contains everything except the player rectangles so
        # hero cards can be drawn underneath them. rectangles_overlay stores the
        # pre-rendered rectangles to overlay afterwards.
        if not hasattr(self, "template_base"):
            self.template_base = None
        if not hasattr(self, "rectangles_overlay"):
            self.rectangles_overlay = None
        if not hasattr(self, "template_image"):
            self.template_image = None

    def create_template(self):
        """Create a template image with static elements pre-rendered."""
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

        # Draw the table surface without dynamic text
        template, _ = template_table_drawer.draw_table(draw_text=False)

        # --------------------------------------------------------------
        # Pre-draw players so heavy shapes are rendered once
        # --------------------------------------------------------------
        template_player_drawer = PlayerDrawer(
            self.config, self.game_data, template, template_draw
        )
        template_player_drawer.set_fonts(
            self.title_font, self.player_font, self.card_font
        )
        template, template_draw = template_player_drawer.draw_player_circles()
        template_player_drawer.img = template
        template_player_drawer.draw = template_draw

        # --------------------------------------------------------------
        # Villain cards are drawn between the circle and the rectangle
        # --------------------------------------------------------------
        template_card_drawer = CardDrawer(
            self.config, self.game_data, template, template_draw, self.cards_folder
        )
        template_card_drawer.set_fonts(
            self.title_font, self.player_font, self.card_font
        )
        template, template_draw = template_card_drawer.draw_player_cards()

        # Save base template without rectangles for later reuse
        self.template_base = template.copy()

        # --------------------------------------------------------------
        # Pre-render player rectangles on a transparent overlay so we can
        # composite them after drawing hero cards
        # --------------------------------------------------------------
        rect_overlay = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
        )
        rect_draw = ImageDraw.Draw(rect_overlay, "RGBA")
        overlay_player_drawer = PlayerDrawer(
            self.config, self.game_data, rect_overlay, rect_draw
        )
        overlay_player_drawer.set_fonts(
            self.title_font, self.player_font, self.card_font
        )
        rect_overlay, rect_draw = overlay_player_drawer.draw_player_rectangles(
            draw_info=False
        )
        self.rectangles_overlay = rect_overlay

        # Compose a full template image for cases where no hero cards are drawn
        template = Image.alpha_composite(self.template_base, self.rectangles_overlay)
        template_draw = ImageDraw.Draw(template, "RGBA")
        self.template_image = template

        return self.template_image

    def refresh(self):
        """Refresh the visualizer's state when reusing it for different hands."""
        # If we have a base template, use it as the starting point
        if self.template_base is not None:
            self.img = self.template_base.copy()
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

    def create_visualization(self):
        """Create the poker table visualization."""
        # Refresh the visualizer's state when reusing it
        self.refresh()

        # If we don't have a template yet, create one
        if not self.template_image:
            self.create_template()
            self.refresh()  # Refresh again with the template as a base

        # Update drawer objects with the current image and draw objects
        self.player_drawer.img = self.img
        self.player_drawer.draw = self.draw
        self.card_drawer.img = self.img
        self.card_drawer.draw = self.draw
        self.chip_drawer.img = self.img
        self.chip_drawer.draw = self.draw

        # Draw hero cards if provided
        if self.card1 and self.card2:
            cards_img, cards_draw = self.card_drawer.draw_hero_cards()
            self.img = cards_img
            self.draw = cards_draw

        # After hero cards, overlay the pre-rendered rectangles so that
        # all cards appear behind them
        if self.rectangles_overlay is not None:
            self.img = Image.alpha_composite(self.img, self.rectangles_overlay)
            self.draw = ImageDraw.Draw(self.img, "RGBA")

        # Update player drawer with the current image after cards are drawn
        self.player_drawer.img = self.img
        self.player_drawer.draw = self.draw

        # Draw only the player information text
        player_text_img, player_text_draw = self.player_drawer.draw_player_text()
        self.img = player_text_img
        self.draw = player_text_draw

        # Update chip drawer with the current image
        self.chip_drawer.img = self.img
        self.chip_drawer.draw = self.draw

        # Draw player chips
        chips_img, chips_draw = self.chip_drawer.draw_player_chips()
        self.img = chips_img
        self.draw = chips_draw

        # Draw dynamic table text (scenario and pot)
        self.table_drawer.img = self.img
        self.table_drawer.draw = self.draw
        self.table_drawer.draw_table_text()
        self.img = self.table_drawer.img
        self.draw = self.table_drawer.draw

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
