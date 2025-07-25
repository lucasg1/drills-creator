"""
Module for drawing the poker table and its components.
"""

from PIL import Image, ImageDraw, ImageFilter
import os


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

    def _draw_text_with_background(
        self,
        text,
        x,
        y,
        font,
        padding=4,
        radius=None,
        fill=None,
        bg=None,
        blur=2,
    ):
        """Draw text with a rounded rectangle background.

        A bit of blur softens the rectangle so it blends with the table.

        Parameters
        ----------
        text: str
            Text to draw.
        x, y: int
            Top-left coordinates where the text should be drawn.
        font: ImageFont
            Font used for the text.
        padding: int
            Padding around the text inside the rectangle.
        radius: int
            Radius for the rounded rectangle corners.
        fill: tuple
            Text color.
        bg: tuple
            Background color (RGBA).
        blur: int
            Radius for the background blur to create soft edges.
        """
        if fill is None:
            fill = self.config.text_color
        if bg is None:
            bg = self.config.text_bg_color
        text_width = self.draw.textlength(text, font=font)
        text_height = font.getbbox(text)[3]
        if radius is None:
            radius = (text_height + padding * 2) // 2

        bbox = [
            x - padding - 10,
            y - padding,
            x + text_width + padding + 10,
            y + text_height + padding,
        ]

        overlay = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
        )
        overlay_draw = ImageDraw.Draw(overlay, "RGBA")
        overlay_draw.rounded_rectangle(
            [int(x) for x in bbox], radius=int(radius), fill=bg
        )
        if blur:
            overlay = overlay.filter(ImageFilter.GaussianBlur(radius=blur))

        self.img = Image.alpha_composite(self.img, overlay)
        self.draw = ImageDraw.Draw(self.img, "RGBA")
        self.draw.text((x, y), text, fill=fill, font=font)

    def draw_table(self, draw_text=True):
        """Draw the poker table with a simple 3D effect.

        Parameters
        ----------
        draw_text : bool, optional
            If ``True`` also render the scenario and pot text. When preparing a
            static template this can be disabled so text can be drawn later.
        """
        # Get dimensions from config
        table_center_x = self.config.table_center_x
        table_center_y = self.config.table_center_y
        table_width = self.config.table_width
        table_height = self.config.table_height
        scale_factor = self.config.scale_factor
        table_color = self.config.table_color
        text_color = self.config.text_color
        scenario_text_color = self.config.scenario_text_color

        # ------------------------------------------------------------------
        # Background
        # ------------------------------------------------------------------
        # Use a dark background with a subtle radial highlight
        base_color = (0, 0, 0, 255)
        highlight_color = (40, 40, 40, 255)
        bg = Image.new("RGBA", (self.config.width, self.config.height), base_color)

        highlight = Image.new(
            "RGBA", (self.config.width, self.config.height), highlight_color
        )
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
        border_thickness = int(min(table_width, table_height) * 0.08)

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
        side_bbox = [
            table_left - border_thickness,
            table_top,
            table_right + border_thickness,
            table_bottom + depth,
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
        shadow_overlay = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
        )
        shadow_draw = ImageDraw.Draw(shadow_overlay, "RGBA")
        shadow_offset = depth * 2
        shadow_bbox = [
            table_left - border_thickness + shadow_offset,
            table_top + depth - border_thickness + shadow_offset,
            table_right + border_thickness + shadow_offset,
            table_bottom + depth + border_thickness + shadow_offset,
        ]
        shadow_draw.rounded_rectangle(
            [int(x) for x in shadow_bbox],
            radius=int(radius + border_thickness),
            fill=(0, 0, 0, 120),
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

        # Draw the side of the table for the 3D effect
        overlay_draw.rounded_rectangle(
            [int(x) for x in side_bbox],
            radius=int(radius + border_thickness),
            fill=wood_color,
        )
        overlay_draw.rounded_rectangle(
            [int(x) for x in bottom_bbox], radius=int(radius), fill=darker_color
        )

        # Draw the flat wooden border on top
        overlay_draw.rounded_rectangle(
            [int(x) for x in outer_top_bbox],
            radius=int(radius + border_thickness),
            fill=wood_color,
        )
        overlay_draw.rounded_rectangle(
            [int(x) for x in top_bbox], radius=int(radius), fill=table_color
        )

        line_width = 2 * scale_factor

        # Create highlight on the outer edge for a subtle rounded effect
        highlight_overlay = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
        )
        highlight_draw = ImageDraw.Draw(highlight_overlay, "RGBA")
        highlight_width = max(1, border_thickness // 2)
        highlight_draw.rounded_rectangle(
            [int(x) for x in outer_top_bbox],
            radius=int(radius + border_thickness),
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
            [int(x) for x in top_bbox],
            radius=int(radius),
            outline=255,
            width=inner_width,
        )
        mask_draw.rectangle(
            [0, table_center_y, self.config.width, self.config.height], fill=0
        )
        shadow_mask = shadow_mask.filter(
            ImageFilter.GaussianBlur(radius=max(1, inner_width // 2))
        )
        inner_shadow = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 80)
        )
        inner_shadow.putalpha(shadow_mask)
        table_overlay = Image.alpha_composite(table_overlay, inner_shadow)

        # --------------------------------------------------------------
        # Accent line and center logo
        # --------------------------------------------------------------
        accent_inset = max(1, border_thickness // 3)
        accent_bbox = [
            top_bbox[0] + accent_inset,
            top_bbox[1] + accent_inset,
            top_bbox[2] - accent_inset,
            top_bbox[3] - accent_inset,
        ]
        overlay_draw.rounded_rectangle(
            [int(x) for x in accent_bbox],
            radius=int(radius - accent_inset),
            outline=(255, 255, 255, 80),
            width=int(max(1, line_width // 2)),
        )

        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "flow_logo.png",
        )
        logo_height = 0
        if os.path.exists(logo_path):
            logo = Image.open(logo_path).convert("RGBA")
            max_w = accent_bbox[2] - accent_bbox[0]
            max_h = accent_bbox[3] - accent_bbox[1]
            target_size = (int(max_w * 0.5), int(max_h * 0.5))
            logo.thumbnail(target_size, Image.LANCZOS)
            alpha = logo.split()[-1].point(lambda a: int(a * 0.2))
            logo.putalpha(alpha)
            logo_height = logo.height
            lx = int(table_center_x - logo.width / 2)
            ly = int(table_center_y - logo.height / 2)
            table_overlay.alpha_composite(logo, (lx, ly))

        overlay_draw.rounded_rectangle(
            [int(x) for x in outer_top_bbox],
            radius=int(radius + border_thickness),
            outline=(0, 0, 0, 255),
            width=int(line_width),
        )
        overlay_draw.rounded_rectangle(
            [int(x) for x in top_bbox],
            radius=int(radius),
            outline=(0, 0, 0, 255),
            width=int(line_width),
        )

        self.img = Image.alpha_composite(self.img, table_overlay)
        self.draw = ImageDraw.Draw(self.img, "RGBA")

        if draw_text:
            self.draw_table_text(table_center_x, table_center_y, logo_height)

        return self.img, self.draw

    def draw_table_text(self, table_center_x=None, table_center_y=None, logo_height=0):
        """Draw the scenario and pot text on the already rendered table."""

        if table_center_x is None:
            table_center_x = self.config.table_center_x
        if table_center_y is None:
            table_center_y = self.config.table_center_y

        scale_factor = self.config.scale_factor
        text_color = self.config.text_color
        scenario_text_color = self.config.scenario_text_color

        scenario_text = self.game_data.get_scenario_description()
        scenario_width = self.draw.textlength(scenario_text, font=self.player_font)
        scenario_height = self.title_font.getbbox(scenario_text)[3]
        scenario_y = table_center_y - logo_height / 4 - scenario_height - 25
        scenario_x = table_center_x - scenario_width / 2
        self._draw_text_with_background(
            scenario_text,
            scenario_x,
            scenario_y,
            font=self.player_font,
            padding=4 * scale_factor,
            fill=scenario_text_color,
        )

        pot_text = f"Total Pot: {self.game_data.pot:.2f} BB"
        pot_width = self.draw.textlength(pot_text, font=self.player_font)
        pot_y = table_center_y + logo_height / 4 + 30
        pot_x = table_center_x - pot_width / 2
        self._draw_text_with_background(
            pot_text,
            pot_x,
            pot_y,
            font=self.player_font,
            padding=4 * scale_factor,
            fill=text_color,
        )

        return self.img, self.draw

    def set_fonts(self, title_font, player_font, card_font):
        """Set the fonts for drawing text."""
        self.title_font = title_font
        self.player_font = player_font
        self.card_font = card_font
