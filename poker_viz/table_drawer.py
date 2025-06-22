"""
Module for drawing the poker table and its components.
"""

from PIL import Image, ImageDraw


class TableDrawer:
    """Draws the poker table and related elements."""

    def __init__(self, config, game_data, img, draw):
        """
        Initialize the table drawer.

        Args:
            config: Configuration settings
            game_data: Processed game data
            img: PIL Image object
            draw: PIL ImageDraw object
        """
        self.config = config
        self.game_data = game_data
        self.img = img
        self.draw = draw

    def draw_table(self):
        """Draw the poker table with a simple 3D effect."""
        # Get dimensions from config
        table_center_x = self.config.table_center_x
        table_center_y = self.config.table_center_y
        table_width = self.config.table_width
        table_height = self.config.table_height
        scale_factor = self.config.scale_factor
        table_color = self.config.table_color
        text_color = self.config.text_color

        # Draw the table using two ellipses to simulate perspective
        table_left = table_center_x - table_width // 2
        table_top = table_center_y - table_height // 2
        table_right = table_left + table_width
        table_bottom = table_top + table_height

        # Thickness of the table for the 3D look
        depth = max(6, table_height // 12)

        top_bbox = [table_left, table_top, table_right, table_bottom]
        bottom_bbox = [table_left, table_top + depth, table_right, table_bottom + depth]

        darker_color = tuple(max(0, c - 40) for c in table_color[:3]) + (table_color[3],)

        table_overlay = Image.new("RGBA", (self.config.width, self.config.height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(table_overlay, "RGBA")
        overlay_draw.ellipse(bottom_bbox, fill=darker_color)
        overlay_draw.ellipse(top_bbox, fill=table_color)

        line_width = 3 * scale_factor
        overlay_draw.ellipse(top_bbox, outline=(0, 0, 0, 255), width=line_width)

        self.img = Image.alpha_composite(self.img, table_overlay)
        self.draw = ImageDraw.Draw(self.img, "RGBA")

        # Draw the pot
        pot_text = f"Pot: {self.game_data.pot} BB"
        text_width = self.draw.textlength(pot_text, font=self.title_font)
        self.draw.text(
            (table_center_x - text_width / 2, table_center_y - 20),
            pot_text,
            fill=text_color,
            font=self.title_font,
        )

        return self.img, self.draw

    def set_fonts(self, title_font, player_font, card_font):
        """Set the fonts for drawing text."""
        self.title_font = title_font
        self.player_font = player_font
        self.card_font = card_font
