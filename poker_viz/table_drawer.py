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
        """Draw the poker table with a simple 3D effect."""
        # Get dimensions from config
        table_center_x = self.config.table_center_x
        table_center_y = self.config.table_center_y
        table_width = self.config.table_width
        table_height = self.config.table_height
        scale_factor = self.config.scale_factor
        table_color = self.config.table_color
        text_color = self.config.text_color

        # ------------------------------------------------------------------
        # Background
        # ------------------------------------------------------------------
        # Use a dark background with a subtle radial highlight
        base_color = (0, 0, 0, 255)
        highlight_color = (40, 40, 40, 255)
        bg = Image.new("RGBA", (self.config.width, self.config.height), base_color)

        highlight = Image.new("RGBA", (self.config.width, self.config.height), highlight_color)
        mask = Image.new("L", (self.config.width, self.config.height), 0)
        mask_draw = ImageDraw.Draw(mask)

        # Use a large ellipse mask for a soft radial effect
        extra = max(table_width, table_height)
        mask_draw.ellipse(
            [
                table_center_x - extra,
                table_center_y - extra,
                table_center_x + extra,
                table_center_y + extra,
            ],
            fill=255,
        )
        mask = mask.filter(ImageFilter.GaussianBlur(radius=extra // 2))
        bg = Image.composite(highlight, bg, mask)

        self.img = bg
        self.draw = ImageDraw.Draw(self.img, "RGBA")

        # ------------------------------------------------------------------
        # Draw the table using two ellipses to simulate perspective
        table_left = table_center_x - table_width // 2
        table_top = table_center_y - table_height // 2
        table_right = table_left + table_width
        table_bottom = table_top + table_height

        # Thickness of the wooden border around the table
        border_thickness = int(min(table_width, table_height) * 0.05)

        # Thickness of the table for the 3D look
        depth = max(6, table_height // 12)

        top_bbox = [table_left, table_top, table_right, table_bottom]
        bottom_bbox = [table_left, table_top + depth, table_right, table_bottom + depth]

        # Bounding boxes including the wooden border
        outer_top_bbox = [
            table_left - border_thickness,
            table_top - border_thickness,
            table_right + border_thickness,
            table_bottom + border_thickness,
        ]
        outer_bottom_bbox = [
            table_left - border_thickness,
            table_top + depth - border_thickness,
            table_right + border_thickness,
            table_bottom + depth + border_thickness,
        ]

        darker_color = tuple(max(0, c - 40) for c in table_color[:3]) + (
            table_color[3],
        )

        # Colors for the wooden border
        wood_color = (133, 94, 66, 255)
        wood_darker = tuple(max(0, c - 40) for c in wood_color[:3]) + (wood_color[3],)

        # ------------------------------------------------------------------
        # Background shadow of the table
        # ------------------------------------------------------------------
        shadow_overlay = Image.new("RGBA", (self.config.width, self.config.height), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_overlay, "RGBA")
        shadow_offset = depth * 2
        shadow_bbox = [
            table_left - border_thickness + shadow_offset,
            table_top + depth - border_thickness + shadow_offset,
            table_right + border_thickness + shadow_offset,
            table_bottom + depth + border_thickness + shadow_offset,
        ]
        shadow_draw.ellipse(shadow_bbox, fill=(0, 0, 0, 120))
        shadow_overlay = shadow_overlay.filter(ImageFilter.GaussianBlur(radius=depth))
        self.img = Image.alpha_composite(self.img, shadow_overlay)
        self.draw = ImageDraw.Draw(self.img, "RGBA")

        # ------------------------------------------------------------------
        # Table surface
        # ------------------------------------------------------------------
        table_overlay = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
        )
        overlay_draw = ImageDraw.Draw(table_overlay, "RGBA")

        # Draw wooden border with simple 3D look
        overlay_draw.ellipse(outer_bottom_bbox, fill=wood_darker)
        overlay_draw.ellipse(bottom_bbox, fill=darker_color)
        overlay_draw.ellipse(outer_top_bbox, fill=wood_color)
        overlay_draw.ellipse(top_bbox, fill=table_color)

        line_width = 3 * scale_factor
        overlay_draw.ellipse(outer_top_bbox, outline=(0, 0, 0, 255), width=line_width)
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
