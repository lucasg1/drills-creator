"""
Module for drawing chips on the poker table.
"""

from PIL import Image, ImageDraw, ImageFilter


class ChipDrawer:
    """Draws chips on the table representing player bets with realistic 3D effects."""

    def __init__(self, config, game_data, img, draw):
        """
        Initialize the chip drawer.

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

        A small blur is applied so the background fades out gently.
        """
        if fill is None:
            fill = self.config.text_color
        if bg is None:
            bg = self.config.text_bg_color
        text_width = self.draw.textlength(text, font=font)
        text_height = font.getbbox(text)[3]
        if radius is None:
            radius = (text_height + padding * 2) // 2
        bbox = [x - padding - 10, y - padding, x + text_width + padding + 10, y + text_height + padding]
        overlay = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
        )
        overlay_draw = ImageDraw.Draw(overlay, "RGBA")
        overlay_draw.rounded_rectangle(bbox, radius=radius, fill=bg)
        if blur:
            overlay = overlay.filter(ImageFilter.GaussianBlur(radius=blur))
        self.img = Image.alpha_composite(self.img, overlay)
        self.draw = ImageDraw.Draw(self.img, "RGBA")
        self.draw.text((x, y), text, fill=fill, font=font)

    def set_fonts(self, title_font, player_font, card_font):
        """Set the fonts for drawing text."""
        self.title_font = title_font
        self.player_font = player_font
        self.card_font = card_font

    def _draw_chip(self, chip_x, chip_y, chip_color):
        """Draw a single chip with edge markings and an inner circle."""
        scale_factor = self.config.scale_factor

        chip_radius = 15 * scale_factor
        rim_width = chip_radius * 0.2

        chip_border_color = tuple(max(0, c - 40) for c in chip_color)
        notch_color = (255, 255, 255, 255)

        # ------------------------------------------------------------------
        # Perspective setup - compress chip height so it looks flat on table
        # ------------------------------------------------------------------
        chip_height_ratio = 0.6
        ellipse_height = int(chip_radius * 2 * chip_height_ratio)

        # ------------------------------------------------------------------
        # Shadow drawing
        # ------------------------------------------------------------------
        shadow_size = int(chip_radius * 2)
        shadow_img = Image.new("RGBA", (shadow_size, shadow_size), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_img)
        shadow_draw.ellipse(
            [0, 0, shadow_size, shadow_size], fill=(0, 0, 0, 80)
        )
        shadow_img = shadow_img.resize(
            (shadow_size, ellipse_height), Image.LANCZOS
        )

        shadow_overlay = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
        )
        shadow_offset = int(scale_factor)
        shadow_top_left = (
            int(chip_x - chip_radius + shadow_offset),
            int(chip_y - ellipse_height / 2 + shadow_offset),
        )
        shadow_overlay.paste(shadow_img, shadow_top_left, shadow_img)
        shadow_overlay = shadow_overlay.filter(
            ImageFilter.GaussianBlur(radius=scale_factor)
        )
        self.img = Image.alpha_composite(self.img, shadow_overlay)

        # ------------------------------------------------------------------
        # Base chip drawing on a separate image then scaled to ellipse
        # ------------------------------------------------------------------
        chip_size = int(chip_radius * 2)
        chip_img = Image.new("RGBA", (chip_size, chip_size), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(chip_img, "RGBA")

        outer_bbox = [0, 0, chip_size, chip_size]
        overlay_draw.ellipse(
            outer_bbox,
            fill=chip_color,
            outline=chip_border_color,
            width=int(scale_factor),
        )

        # Edge marks around the rim
        num_notches = 8
        notch_angle = 20
        for i in range(num_notches):
            start = i * (360 / num_notches) - notch_angle / 2
            end = start + notch_angle
            overlay_draw.pieslice(outer_bbox, start, end, fill=notch_color)

        # Cover inner part of the notches to create rectangles on the rim
        inner_rim_radius = chip_radius - rim_width
        inner_rim_bbox = [
            chip_radius - inner_rim_radius,
            chip_radius - inner_rim_radius,
            chip_radius + inner_rim_radius,
            chip_radius + inner_rim_radius,
        ]
        overlay_draw.ellipse(inner_rim_bbox, fill=chip_color)

        # Inner circle for label area
        label_radius = inner_rim_radius * 0.6
        label_bbox = [
            chip_radius - label_radius,
            chip_radius - label_radius,
            chip_radius + label_radius,
            chip_radius + label_radius,
        ]
        overlay_draw.ellipse(
            label_bbox,
            fill=(255, 255, 255, 255),
            outline=chip_border_color,
            width=int(scale_factor * 0.8),
        )

        # Simple highlight arc for a touch of depth
        overlay_draw.arc(
            [
                chip_radius - label_radius,
                chip_radius - label_radius,
                chip_radius + label_radius,
                chip_radius + label_radius,
            ],
            start=20,
            end=160,
            fill=(220, 220, 220, 180),
            width=int(scale_factor),
        )

        chip_img = chip_img.resize((chip_size, ellipse_height), Image.LANCZOS)

        # ------------------------------------------------------------------
        # Chip thickness - draw a darker copy slightly offset downward
        # ------------------------------------------------------------------
        thickness = int(scale_factor * 4)
        edge_color = tuple(max(0, c - 30) for c in chip_color)
        edge_img = Image.new("RGBA", chip_img.size, edge_color)
        edge_img.putalpha(chip_img.split()[3])

        chip_overlay = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
        )
        top_left = (
            int(chip_x - chip_radius),
            int(chip_y - ellipse_height / 2),
        )
        chip_overlay.paste(edge_img, (top_left[0], top_left[1] + thickness), edge_img)
        chip_overlay.paste(chip_img, top_left, chip_img)

        self.img = Image.alpha_composite(self.img, chip_overlay)
        self.draw = ImageDraw.Draw(self.img, "RGBA")

    def draw_player_chips(self):
        """Draw chips on the table representing each player's bet with realistic 3D effects."""
        position_to_seat = self.game_data.get_position_mapping()

        # Chip colors mapped by denomination
        chip_colors = {
            0.1: (200, 200, 200),  # Grey
            0.5: (150, 75, 0),  # Brown
            1: (220, 40, 40),  # Red
            5: (30, 30, 180),  # Blue
            10: (0, 130, 0),  # Green
            50: (130, 0, 130),  # Purple
            100: (20, 20, 20),  # Black
        }
        text_color = self.config.text_color
        player_radius = self.config.player_radius
        scale_factor = self.config.scale_factor

        # Draw chips for each player who has chips on the table
        for player in self.game_data.players:
            chips = player.get("chips_on_table", 0)
            if chips <= 0:
                continue

            position = player.get("position")
            is_hero = player.get("is_hero", False)

            # Determine seat index based on position
            if is_hero:
                seat_index = 0  # Hero always at bottom middle
            elif position in position_to_seat:
                seat_index = position_to_seat[position]
            else:
                raise ValueError(
                    f"Position '{position}' not found in seat mapping. Cannot draw chips."
                )

            # Get the position coordinates
            x, y = self.config.seat_positions[seat_index]

            # Calculate chip position - between player and center of table
            table_center_x = self.config.table_center_x
            table_center_y = self.config.table_center_y

            # Vector from player to center
            dx = table_center_x - x
            dy = table_center_y - y

            # Normalize the vector
            length = (dx**2 + dy**2) ** 0.5
            if length > 0:
                dx /= length
                dy /= length

            # Custom distance factors depend on the number of seats so
            # they remain consistent when table size changes
            distance_maps = {
                2: {},
                3: {},
                4: {},
                5: {},
                6: {},
                7: {},
                8: {0: 0.6, 1: 0.3, 2: 0.2, 3: 0.3, 4: 0.3, 5: 0.5, 6: 0.3, 7: 0.5},
                9: {},
            }

            distance_factors = distance_maps.get(self.config.num_players, {})
            distance = distance_factors.get(seat_index, 0.6)

            chip_x = x + dx * (length * distance)
            chip_y = y + dy * (length * distance)

            # Break the chip value into known denominations
            denominations = [100, 50, 10, 5, 1, 0.5, 0.1]
            remaining = chips
            stack = []
            for denom in denominations:
                count = int(remaining // denom)
                if count:
                    stack.extend([denom] * count)
                    remaining -= count * denom
                    remaining = round(remaining, 2)

            stack_spacing = 8 * scale_factor
            for idx, denom in enumerate(stack):
                self._draw_chip(chip_x, chip_y - idx * stack_spacing, chip_colors[denom])

            chip_text = (
                f"{chips:.1f} BB" if chips < 10 else f"{chips:.0f} BB"
            )
            text_y = chip_y - (len(stack) - 1) * stack_spacing / 2 - self.player_font.getbbox(chip_text)[3] / 2
            text_x = chip_x + 15 * scale_factor + 5 * scale_factor + 15
            self._draw_text_with_background(
                chip_text,
                text_x,
                text_y,
                font=self.player_font,
                padding=4 * scale_factor,
                fill=text_color,
            )

        return self.img, self.draw
