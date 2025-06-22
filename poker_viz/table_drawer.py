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
        # Draw the table using rounded rectangles to simulate perspective
        table_left = table_center_x - table_width // 2
        table_top = table_center_y - table_height // 2
        table_right = table_left + table_width
        table_bottom = table_top + table_height

        # Thickness of the wooden border around the table
        border_thickness = int(min(table_width, table_height) * 0.05)

        # Thickness of the table for the 3D look
        depth = max(6, table_height // 12)

        # Radius for the rounded edges (half the height makes the sides straight)
        radius = table_height // 2

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

        darker_color = tuple(max(0, c - 25) for c in table_color[:3]) + (
            table_color[3],
        )

        # Color for the wooden border
        wood_color = (133, 94, 66, 255)

        # Slightly lighter and darker shades used only for lighting effects
        wood_light = tuple(min(255, c + 20) for c in wood_color[:3]) + (120,)
        wood_dark = tuple(max(0, c - 20) for c in wood_color[:3]) + (120,)

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
        shadow_draw.rounded_rectangle(
            shadow_bbox, radius=radius + border_thickness, fill=(0, 0, 0, 120)
        )
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

        # Draw the bottom portion for the 3D effect
        overlay_draw.rounded_rectangle(
            outer_bottom_bbox,
            radius=radius + border_thickness,
            fill=wood_color,
        )
        overlay_draw.rounded_rectangle(
            bottom_bbox, radius=radius, fill=darker_color
        )

        # Draw the flat wooden border on top
        overlay_draw.rounded_rectangle(
            outer_top_bbox, radius=radius + border_thickness, fill=wood_color
        )
        overlay_draw.rounded_rectangle(top_bbox, radius=radius, fill=table_color)

        line_width = 2 * scale_factor

        # Create highlight on the outer edge for a subtle rounded effect
        highlight_overlay = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
        )
        highlight_draw = ImageDraw.Draw(highlight_overlay, "RGBA")
        highlight_width = max(1, border_thickness // 2)
        highlight_draw.rounded_rectangle(
            outer_top_bbox,
            radius=radius + border_thickness,
            outline=wood_light,
            width=highlight_width,
        )
        highlight_overlay = highlight_overlay.filter(
            ImageFilter.GaussianBlur(radius=max(1, highlight_width // 2))
        )
        table_overlay = Image.alpha_composite(table_overlay, highlight_overlay)

        # Dark shadow along the inner edge near the top side
        shadow_mask = Image.new("L", (self.config.width, self.config.height), 0)
        mask_draw = ImageDraw.Draw(shadow_mask)
        inner_width = max(1, border_thickness // 2)
        mask_draw.rounded_rectangle(
            top_bbox,
            radius=radius,
            outline=255,
            width=inner_width,
        )
        mask_draw.rectangle(
            [0, table_center_y, self.config.width, self.config.height], fill=0
        )
        shadow_mask = shadow_mask.filter(
            ImageFilter.GaussianBlur(radius=max(1, inner_width // 2))
        )
        inner_shadow = Image.new("RGBA", (self.config.width, self.config.height), (0, 0, 0, 80))
        inner_shadow.putalpha(shadow_mask)
        table_overlay = Image.alpha_composite(table_overlay, inner_shadow)

        overlay_draw.rounded_rectangle(
            outer_top_bbox,
            radius=radius + border_thickness,
            outline=(0, 0, 0, 255),
            width=line_width,
        )
        overlay_draw.rounded_rectangle(
            top_bbox, radius=radius, outline=(0, 0, 0, 255), width=line_width
        )

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
