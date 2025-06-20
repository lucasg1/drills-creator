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

    def draw_player_chips(self):
        """Draw chips on the table representing each player's bet with realistic 3D effects."""
        position_to_seat = self.game_data.get_position_mapping()

        # Chip colors
        chip_color = (220, 180, 0)  # Gold color for chips
        chip_border_color = (180, 140, 0)  # Darker gold for border
        highlight_color = (250, 240, 180)  # Light gold for highlights
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
                # Fallback for unknown positions
                seat_index = 8  # Default to bottom left

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

            # Position chips 75% of the way from player to center
            chip_x = x + dx * (player_radius + 75 * scale_factor)
            chip_y = y + dy * (player_radius + 75 * scale_factor)

            # Draw chip with 3D effect (ellipse with slight tilt)
            chip_radius = 15 * scale_factor
            chip_height_ratio = 0.4  # Height ratio for tilt effect (makes it appear 3D)

            # Create a mask for the chip
            chip_mask = Image.new("L", (self.config.width, self.config.height), 0)
            chip_mask_draw = ImageDraw.Draw(chip_mask)

            # Draw the chip shape on the mask (elliptical for 3D effect)
            chip_mask_draw.ellipse(
                [
                    chip_x - chip_radius,
                    chip_y - chip_radius * chip_height_ratio,
                    chip_x + chip_radius,
                    chip_y + chip_radius * chip_height_ratio,
                ],
                fill=255,
            )

            # Apply slight blur for smoother edges
            chip_mask = chip_mask.filter(
                ImageFilter.GaussianBlur(radius=scale_factor * 0.3)
            )

            # Create a chip overlay with the chip color
            chip_overlay = Image.new(
                "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
            )

            # Fill the chip with gold color
            for py in range(
                max(0, int(chip_y - chip_radius - scale_factor * 2)),
                min(self.config.height, int(chip_y + chip_radius + scale_factor * 2)),
            ):
                for px in range(
                    max(0, int(chip_x - chip_radius - scale_factor * 2)),
                    min(
                        self.config.width, int(chip_x + chip_radius + scale_factor * 2)
                    ),
                ):
                    mask_value = chip_mask.getpixel((px, py))
                    if mask_value > 0:
                        chip_overlay.putpixel((px, py), (*chip_color[:3], mask_value))

            # Overlay the chip on the main image
            self.img = Image.alpha_composite(self.img, chip_overlay)

            # Draw border with anti-aliasing
            border_mask = Image.new("L", (self.config.width, self.config.height), 0)
            border_mask_draw = ImageDraw.Draw(border_mask)

            # Draw just the outline on the border mask
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

            # Apply slight blur for smoother border
            border_mask = border_mask.filter(
                ImageFilter.GaussianBlur(radius=scale_factor * 0.3)
            )

            # Create a border overlay
            border_overlay = Image.new(
                "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
            )

            # Fill the border with darker gold
            for py in range(
                max(0, int(chip_y - chip_radius - scale_factor * 3)),
                min(self.config.height, int(chip_y + chip_radius + scale_factor * 3)),
            ):
                for px in range(
                    max(0, int(chip_x - chip_radius - scale_factor * 3)),
                    min(
                        self.config.width, int(chip_x + chip_radius + scale_factor * 3)
                    ),
                ):
                    mask_value = border_mask.getpixel((px, py))
                    if mask_value > 0:
                        border_overlay.putpixel(
                            (px, py), (*chip_border_color[:3], mask_value)
                        )

            # Overlay the border on the main image
            self.img = Image.alpha_composite(self.img, border_overlay)

            # Add a highlight to enhance 3D effect
            highlight_mask = Image.new("L", (self.config.width, self.config.height), 0)
            highlight_mask_draw = ImageDraw.Draw(highlight_mask)

            # Draw the highlight arc on the mask
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

            # Apply slight blur for smoother highlight
            highlight_mask = highlight_mask.filter(
                ImageFilter.GaussianBlur(radius=scale_factor * 0.2)
            )

            # Create a highlight overlay
            highlight_overlay = Image.new(
                "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
            )

            # Fill the highlight with light gold
            for py in range(
                max(0, int(chip_y - chip_radius - scale_factor * 2)),
                min(self.config.height, int(chip_y + chip_radius + scale_factor * 2)),
            ):
                for px in range(
                    max(0, int(chip_x - chip_radius - scale_factor * 2)),
                    min(
                        self.config.width, int(chip_x + chip_radius + scale_factor * 2)
                    ),
                ):
                    mask_value = highlight_mask.getpixel((px, py))
                    if mask_value > 0:
                        highlight_overlay.putpixel(
                            (px, py), (*highlight_color[:3], mask_value)
                        )

            # Overlay the highlight on the main image
            self.img = Image.alpha_composite(self.img, highlight_overlay)
            self.draw = ImageDraw.Draw(self.img, "RGBA")  # Recreate the draw object

            # Draw the chip value text
            chip_text = f"{chips:.1f}" if chips < 10 else f"{chips:.0f}"
            text_width = self.draw.textlength(chip_text, font=self.player_font)
            self.draw.text(
                (
                    chip_x
                    + chip_radius
                    + 5 * scale_factor,  # Position to the right of the chip
                    chip_y
                    - self.player_font.getbbox(chip_text)[3]
                    / 2,  # Vertically centered with the chip
                ),
                chip_text,
                fill=text_color,
                font=self.player_font,
            )

        return self.img, self.draw
