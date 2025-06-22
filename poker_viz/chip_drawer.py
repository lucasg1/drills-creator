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

    def set_fonts(self, title_font, player_font, card_font):
        """Set the fonts for drawing text."""
        self.title_font = title_font
        self.player_font = player_font
        self.card_font = card_font

    def _draw_chip(self, chip_x, chip_y, chip_color):
        """Draw a single chip at the specified position with a 3D look."""
        scale_factor = self.config.scale_factor

        chip_border_color = tuple(max(0, c - 40) for c in chip_color)
        highlight_color = tuple(min(255, c + 40) for c in chip_color)

        chip_radius = 15 * scale_factor
        chip_height_ratio = 0.4

        chip_mask = Image.new("L", (self.config.width, self.config.height), 0)
        chip_mask_draw = ImageDraw.Draw(chip_mask)
        chip_mask_draw.ellipse(
            [
                chip_x - chip_radius,
                chip_y - chip_radius * chip_height_ratio,
                chip_x + chip_radius,
                chip_y + chip_radius * chip_height_ratio,
            ],
            fill=255,
        )
        chip_mask = chip_mask.filter(
            ImageFilter.GaussianBlur(radius=scale_factor * 0.3)
        )

        chip_overlay = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
        )
        for py in range(
            max(0, int(chip_y - chip_radius - scale_factor * 2)),
            min(self.config.height, int(chip_y + chip_radius + scale_factor * 2)),
        ):
            for px in range(
                max(0, int(chip_x - chip_radius - scale_factor * 2)),
                min(self.config.width, int(chip_x + chip_radius + scale_factor * 2)),
            ):
                mask_value = chip_mask.getpixel((px, py))
                if mask_value > 0:
                    chip_overlay.putpixel((px, py), (*chip_color[:3], mask_value))

        self.img = Image.alpha_composite(self.img, chip_overlay)

        border_mask = Image.new("L", (self.config.width, self.config.height), 0)
        border_mask_draw = ImageDraw.Draw(border_mask)
        border_width = 2 * scale_factor
        border_mask_draw.ellipse(
            [
                chip_x - chip_radius,
                chip_y - chip_radius * chip_height_ratio,
                chip_x + chip_radius,
                chip_y + chip_radius * chip_height_ratio,
            ],
            fill=0,
            outline=255,
            width=border_width,
        )
        border_mask = border_mask.filter(
            ImageFilter.GaussianBlur(radius=scale_factor * 0.3)
        )
        border_overlay = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
        )
        for py in range(
            max(0, int(chip_y - chip_radius - scale_factor * 3)),
            min(self.config.height, int(chip_y + chip_radius + scale_factor * 3)),
        ):
            for px in range(
                max(0, int(chip_x - chip_radius - scale_factor * 3)),
                min(self.config.width, int(chip_x + chip_radius + scale_factor * 3)),
            ):
                mask_value = border_mask.getpixel((px, py))
                if mask_value > 0:
                    border_overlay.putpixel((px, py), (*chip_border_color[:3], mask_value))

        self.img = Image.alpha_composite(self.img, border_overlay)

        highlight_mask = Image.new("L", (self.config.width, self.config.height), 0)
        highlight_mask_draw = ImageDraw.Draw(highlight_mask)
        highlight_mask_draw.arc(
            [
                chip_x - chip_radius * 0.7,
                chip_y - chip_radius * chip_height_ratio * 0.7,
                chip_x + chip_radius * 0.7,
                chip_y + chip_radius * chip_height_ratio * 0.7,
            ],
            start=20,
            end=160,
            fill=255,
            width=2 * scale_factor,
        )
        highlight_mask = highlight_mask.filter(
            ImageFilter.GaussianBlur(radius=scale_factor * 0.2)
        )
        highlight_overlay = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
        )
        for py in range(
            max(0, int(chip_y - chip_radius - scale_factor * 2)),
            min(self.config.height, int(chip_y + chip_radius + scale_factor * 2)),
        ):
            for px in range(
                max(0, int(chip_x - chip_radius - scale_factor * 2)),
                min(self.config.width, int(chip_x + chip_radius + scale_factor * 2)),
            ):
                mask_value = highlight_mask.getpixel((px, py))
                if mask_value > 0:
                    highlight_overlay.putpixel(
                        (px, py), (*highlight_color[:3], mask_value)
                    )

        self.img = Image.alpha_composite(self.img, highlight_overlay)
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
                8: {0: 0.6, 1: 0.4, 2: 0.2, 3: 0.3, 4: 0.3, 5: 0.5, 6: 0.3, 7: 0.5},
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
            self.draw.text(
                (
                    chip_x + 15 * scale_factor + 5 * scale_factor,
                    text_y,
                ),
                chip_text,
                fill=text_color,
                font=self.player_font,
            )

        return self.img, self.draw
