"""
Module for drawing the poker table and its components.
"""

from PIL import Image, ImageDraw, ImageFilter


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
        """Draw the poker table with smooth edges."""
        # Get dimensions from config
        table_center_x = self.config.table_center_x
        table_center_y = self.config.table_center_y
        table_width = self.config.table_width
        table_height = self.config.table_height
        scale_factor = self.config.scale_factor
        table_color = self.config.table_color
        text_color = self.config.text_color

        # Draw the table
        table_left = table_center_x - table_width // 2
        table_top = table_center_y - table_height // 2
        table_right = table_left + table_width
        table_bottom = table_top + table_height

        # Create a stadium-like shape (rectangle with rounded ends)
        # Define the rectangle and the two semicircles on the sides
        rect_width = table_width - table_height
        rect_left = table_left + table_height // 2
        rect_right = rect_left + rect_width

        # Create an alpha mask for the entire table for better anti-aliasing
        mask = Image.new("L", (self.config.width, self.config.height), 0)
        mask_draw = ImageDraw.Draw(mask)

        # Draw the table shape on the mask
        # Middle rectangle
        mask_draw.rectangle(
            [rect_left, table_top, rect_right, table_bottom],
            fill=255,
        )

        # Left semicircle
        mask_draw.ellipse(
            [table_left, table_top, table_left + table_height, table_bottom],
            fill=255,
        )

        # Right semicircle
        mask_draw.ellipse(
            [table_right - table_height, table_top, table_right, table_bottom],
            fill=255,
        )

        # Apply slight gaussian blur to the mask for smoother edges
        mask = mask.filter(ImageFilter.GaussianBlur(radius=scale_factor))

        # Create a table overlay image with the table color
        table_overlay = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
        )
        table_overlay_draw = ImageDraw.Draw(table_overlay)

        # Fill the table area with the table color
        for y in range(self.config.height):
            for x in range(self.config.width):
                mask_value = mask.getpixel((x, y))
                if mask_value > 0:
                    alpha = mask_value  # Use mask value as alpha
                    table_overlay.putpixel((x, y), (*table_color[:3], alpha))

        # Paste the table overlay onto the main image using the mask
        self.img = Image.alpha_composite(self.img, table_overlay)
        self.draw = ImageDraw.Draw(self.img, "RGBA")  # Recreate the draw object

        # Draw the border with anti-aliasing
        # Calculate the line width based on scale factor
        line_width = 3 * scale_factor

        # Create a border mask with larger blur for softer edges
        border_mask = Image.new("L", (self.config.width, self.config.height), 0)
        border_draw = ImageDraw.Draw(border_mask)

        # Draw only the border lines on the mask
        # Top line
        border_draw.line(
            [rect_left, table_top, rect_right, table_top],
            fill=255,
            width=line_width,
        )

        # Bottom line
        border_draw.line(
            [rect_left, table_bottom, rect_right, table_bottom],
            fill=255,
            width=line_width,
        )

        # Left semicircle arc
        border_draw.arc(
            [table_left, table_top, table_left + table_height, table_bottom],
            start=90,
            end=270,
            fill=255,
            width=line_width,
        )

        # Right semicircle arc
        border_draw.arc(
            [table_right - table_height, table_top, table_right, table_bottom],
            start=270,
            end=90,
            fill=255,
            width=line_width,
        )

        # Apply slight blur to the border mask
        border_mask = border_mask.filter(
            ImageFilter.GaussianBlur(radius=scale_factor * 0.5)
        )

        # Create a border overlay with black color
        border_overlay = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
        )
        for y in range(self.config.height):
            for x in range(self.config.width):
                mask_value = border_mask.getpixel((x, y))
                if mask_value > 0:
                    border_overlay.putpixel((x, y), (0, 0, 0, mask_value))

        # Apply the border overlay
        self.img = Image.alpha_composite(self.img, border_overlay)
        self.draw = ImageDraw.Draw(self.img, "RGBA")  # Recreate the draw object

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
