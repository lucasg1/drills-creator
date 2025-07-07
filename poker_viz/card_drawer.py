"""
Module for drawing cards in the poker visualization.
"""

import os
import math
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageFont


class CardDrawer:
    """Draws cards on the poker table."""

    def __init__(
        self, config, game_data, img, draw, cards_folder, card1=None, card2=None
    ):
        """
        Initialize the card drawer.

        Args:
            config: Configuration settings
            game_data: Processed game data
            img: PIL Image object
            draw: PIL ImageDraw object
            cards_folder: Path to card images folder
            card1: First hero card (e.g., "Ah")
            card2: Second hero card (e.g., "Kd")
        """
        self.config = config
        self.game_data = game_data
        self.img = img
        self.draw = draw
        self.cards_folder = cards_folder
        self.card1 = card1
        self.card2 = card2

        # Preload card back image
        self._preload_card_back()

    def set_fonts(self, title_font, player_font, card_font):
        """Set the fonts for drawing text."""
        self.title_font = title_font
        self.player_font = player_font
        self.card_font = card_font

    def _preload_card_back(self):
        """Preload the card back image."""
        card_back_path = os.path.join(self.cards_folder, "back.png")
        if os.path.exists(card_back_path):
            self.card_back_img = Image.open(card_back_path)
        else:
            self.card_back_img = None

    def draw_hero_cards(self):
        """Draw the hero's cards."""
        if not self.game_data.hero or not (self.card1 and self.card2):
            return self.img, self.draw

        # Hero is always at the bottom middle position
        hero_x, hero_y = (
            self.config.table_center_x + self.config.player_radius/1.5,
            self.config.table_center_y + self.config.table_height * 0.7 - self.config.player_radius / 4,
        )

        # Card dimensions - enlarged for better visibility
        card_width = 80 * self.config.scale_factor
        card_height = 120 * self.config.scale_factor
        card_overlap = (
            45 * self.config.scale_factor
        )  # Calculate rectangle dimensions (should match PlayerDrawer._draw_player_rectangle)
        player_radius = self.config.player_radius
        rect_width = player_radius * 1.8
        rect_height = player_radius * 1.2

        # Calculate circle parameters (matching PlayerDrawer._draw_player_elements)
        circle_diameter = max(rect_width, rect_height) * 1.1
        circle_radius = circle_diameter / 2
        circle_y_offset = rect_height * 0.4

        card_offset_x = 13

        # Position cards between the circle and rectangle
        # Cards should be visible above the rectangle but below the top of the circle
        card_offset_y = (
            -rect_height * 0.6
        )  # Position cards in the overlap area between circle and rectangle

        # First card (left card) - rotated counterclockwise
        card1_left = hero_x - card_width / 2 - card_overlap / 2 - card_offset_x
        card1_top = hero_y + card_offset_y
        self.draw_card(
            self.card1,
            card1_left,
            card1_top,
            card_width,
            card_height,
            rotation_angle=5,
        )

        # Second card (right card) - rotated clockwise
        card2_left = hero_x - card_width / 2 + card_overlap / 2 - card_offset_x
        card2_top = card1_top
        self.draw_card(
            self.card2,
            card2_left,
            card2_top,
            card_width,
            card_height,
            rotation_angle=-5,
        )

        return self.img, self.draw

    def draw_card(self, card, x, y, width, height, rotation_angle=0):
        """Draw a single card using the card image from cards-images folder."""
        if not card or len(card) < 2:
            return

        # Format the card name to match the image files
        # T for 10, then rank and suit
        rank = card[0].upper()
        suit = card[1].lower()

        # Convert 10 to T if needed
        if rank == "1" and len(card) > 2 and card[1] == "0":
            rank = "T"
            suit = card[2].lower()

        card_filename = f"{rank}{suit}.png"
        card_path = os.path.join(self.cards_folder, card_filename)

        # Check if the card image exists
        if os.path.exists(card_path):
            # Load the card image
            card_img = Image.open(card_path)

            # Resize the card image to the desired dimensions
            card_img = card_img.resize((width, height), Image.LANCZOS)

            # Rotate the card if needed
            if rotation_angle != 0:
                # Calculate the diagonal length to ensure rotated image is fully visible
                diagonal = int(math.sqrt(width**2 + height**2))
                # Create a square transparent image large enough to hold the rotated card
                rot_img = Image.new("RGBA", (diagonal, diagonal), (0, 0, 0, 0))
                # Paste the card in the center of this image
                paste_x = (diagonal - width) // 2
                paste_y = (diagonal - height) // 2
                rot_img.paste(card_img, (paste_x, paste_y))
                # Rotate around the center
                rot_img = rot_img.rotate(
                    rotation_angle, resample=Image.BICUBIC, expand=False
                )
                # Calculate new position to center the rotated image
                paste_x = int(x - diagonal / 2)
                paste_y = int(y - diagonal / 2)
                # Use alpha composite to properly overlay
                self.img.alpha_composite(rot_img, (paste_x, paste_y))
            else:
                # Paste the card directly for non-rotated cards
                paste_x = int(x)
                paste_y = int(y)
                self.img.alpha_composite(card_img, (paste_x, paste_y))

            # Update the draw object
            self.draw = ImageDraw.Draw(self.img, "RGBA")
        else:
            # Fallback to drawing a basic card
            self._draw_fallback_card(card, x, y, width, height, rotation_angle)

    def _draw_fallback_card(self, card, x, y, width, height, rotation_angle=0):
        """Draw a basic card as fallback if image loading fails."""
        if not card or len(card) < 2:
            return

        rank = card[0].upper()
        suit = card[1].lower()

        # Convert 10 to T if needed
        if rank == "1" and len(card) > 2 and card[1] == "0":
            rank = "T"
            suit = card[2].lower()

        # Map suit to symbol
        suit_symbol = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}.get(suit, suit)

        # Determine color
        if suit in ["h", "d"]:
            text_color = self.config.red_suits
        else:
            text_color = self.config.black_suits

        # For rotated cards, use a similar approach as in draw_card
        if rotation_angle != 0:
            # Create a card image
            card_img = Image.new("RGBA", (width, height), self.config.card_bg)
            card_draw = ImageDraw.Draw(card_img)

            # Draw card border
            card_draw.rectangle(
                [0, 0, width - 1, height - 1], outline=(0, 0, 0, 255), width=2
            )

            # Draw card text
            text = f"{rank}{suit_symbol}"
            text_width = card_draw.textlength(text, font=self.card_font)
            text_height = self.card_font.getbbox(text)[3]

            # Draw at top-left and bottom-right corners
            card_draw.text((5, 5), text, fill=text_color, font=self.card_font)
            card_draw.text(
                (width - text_width - 5, height - text_height - 5),
                text,
                fill=text_color,
                font=self.card_font,
            )

            # Draw big symbol in center
            big_font_size = int(min(width, height) * 0.4)
            try:
                big_font = ImageFont.truetype("arial.ttf", big_font_size)
            except IOError:
                big_font = self.card_font

            center_text = suit_symbol
            center_width = card_draw.textlength(center_text, font=big_font)
            center_height = big_font.getbbox(center_text)[3]

            card_draw.text(
                ((width - center_width) // 2, (height - center_height) // 2),
                center_text,
                fill=text_color,
                font=big_font,
            )

            # Calculate the diagonal length to ensure rotated image is fully visible
            diagonal = int(math.sqrt(width**2 + height**2))
            # Create a square transparent image large enough to hold the rotated card
            rot_img = Image.new("RGBA", (diagonal, diagonal), (0, 0, 0, 0))
            # Paste the card in the center of this image
            paste_x = (diagonal - width) // 2
            paste_y = (diagonal - height) // 2
            rot_img.paste(card_img, (paste_x, paste_y))
            # Rotate around the center
            rot_img = rot_img.rotate(
                rotation_angle, resample=Image.BICUBIC, expand=False
            )
            # Calculate new position to center the rotated image
            paste_x = int(x - diagonal / 2)
            paste_y = int(y - diagonal / 2)
            # Use alpha composite to properly overlay
            self.img.alpha_composite(rot_img, (paste_x, paste_y))
        else:
            # Draw a non-rotated card
            self.draw.rectangle(
                [x, y, x + width, y + height],
                fill=self.config.card_bg,
                outline=(0, 0, 0, 255),
                width=2,
            )

            # Draw card text
            text = f"{rank}{suit_symbol}"
            text_width = self.draw.textlength(text, font=self.card_font)
            text_height = self.card_font.getbbox(text)[3]

            # Draw at top-left and bottom-right corners
            self.draw.text((x + 5, y + 5), text, fill=text_color, font=self.card_font)
            self.draw.text(
                (x + width - text_width - 5, y + height - text_height - 5),
                text,
                fill=text_color,
                font=self.card_font,
            )

            # Draw big symbol in center
            big_font_size = int(min(width, height) * 0.4)
            try:
                big_font = ImageFont.truetype("arial.ttf", big_font_size)
            except IOError:
                big_font = self.card_font

            center_text = suit_symbol
            center_width = self.draw.textlength(center_text, font=big_font)
            center_height = big_font.getbbox(center_text)[3]

            self.draw.text(
                (x + (width - center_width) // 2, y + (height - center_height) // 2),
                center_text,
                fill=text_color,
                font=big_font,
            )

    def draw_card_back(self, x, y, width, height, rotation_angle=0):
        """Draw the back of a card using a card image."""
        # Use a preloaded card back image if possible
        if hasattr(self, "card_back_img") and self.card_back_img is not None:
            card_img = self.card_back_img.copy()

            # Resize the card image to the desired dimensions
            card_img = card_img.resize((width, height), Image.LANCZOS)

            # Rotate the card if needed
            if rotation_angle != 0:
                # Calculate the diagonal length to ensure rotated image is fully visible
                diagonal = int(math.sqrt(width**2 + height**2))
                # Create a square transparent image large enough to hold the rotated card
                rot_img = Image.new("RGBA", (diagonal, diagonal), (0, 0, 0, 0))
                # Paste the card in the center of this image
                paste_x = (diagonal - width) // 2
                paste_y = (diagonal - height) // 2
                rot_img.paste(card_img, (paste_x, paste_y))
                # Rotate around the center
                rot_img = rot_img.rotate(
                    rotation_angle, resample=Image.BICUBIC, expand=False
                )
                # Calculate new position to center the rotated image
                paste_x = int(x - diagonal / 2)
                paste_y = int(y - diagonal / 2)
                # Use alpha composite to properly overlay
                self.img.alpha_composite(rot_img, (paste_x, paste_y))
            else:
                # Paste the card directly for non-rotated cards
                paste_x = int(x)
                paste_y = int(y)
                self.img.alpha_composite(card_img, (paste_x, paste_y))

            # Update the draw object
            self.draw = ImageDraw.Draw(self.img, "RGBA")
        else:
            # Fallback implementation - Draw card back manually with rotation support
            self._draw_fallback_card_back(x, y, width, height, rotation_angle)

    def _draw_fallback_card_back(self, x, y, width, height, rotation_angle=0):
        """Draw a fallback card back if the image is not available."""
        # For rotated cards, use a similar approach as in draw_card
        if rotation_angle != 0:
            # Create a card image
            card_img = Image.new(
                "RGBA", (width, height), (30, 50, 150, 255)
            )  # Blue back
            card_draw = ImageDraw.Draw(card_img)

            # Draw card border
            card_draw.rectangle(
                [0, 0, width - 1, height - 1], outline=(0, 0, 0, 255), width=2
            )

            # Draw a simple pattern
            for i in range(0, width, 10):
                card_draw.line([(i, 0), (i, height)], fill=(40, 60, 160, 255), width=1)
            for i in range(0, height, 10):
                card_draw.line([(0, i), (width, i)], fill=(40, 60, 160, 255), width=1)

            # Calculate the diagonal length to ensure rotated image is fully visible
            diagonal = int(math.sqrt(width**2 + height**2))
            # Create a square transparent image large enough to hold the rotated card
            rot_img = Image.new("RGBA", (diagonal, diagonal), (0, 0, 0, 0))
            # Paste the card in the center of this image
            paste_x = (diagonal - width) // 2
            paste_y = (diagonal - height) // 2
            rot_img.paste(card_img, (paste_x, paste_y))
            # Rotate around the center
            rot_img = rot_img.rotate(
                rotation_angle, resample=Image.BICUBIC, expand=False
            )
            # Calculate new position to center the rotated image
            paste_x = int(x - diagonal / 2)
            paste_y = int(y - diagonal / 2)
            # Use alpha composite to properly overlay
            self.img.alpha_composite(rot_img, (paste_x, paste_y))
        else:
            # Draw a non-rotated card back
            self.draw.rectangle(
                [x, y, x + width, y + height],
                fill=(30, 50, 150, 255),  # Blue back
                outline=(0, 0, 0, 255),
                width=2,
            )

            # Draw a simple pattern
            for i in range(int(x), int(x + width), 10):
                self.draw.line(
                    [(i, y), (i, y + height)], fill=(40, 60, 160, 255), width=1
                )
            for i in range(int(y), int(y + height), 10):
                self.draw.line(
                    [(x, i), (x + width, i)], fill=(40, 60, 160, 255), width=1
                )

    def draw_player_cards(self):
        """Draw card backs for all active non-hero players."""
        # Get position mapping from game data
        position_to_seat = self.game_data.get_position_mapping()

        # For each active player (not folded), draw card backs
        for player in self.game_data.players:
            # Skip the hero (their cards are drawn separately)
            if player.get("is_hero", False):
                continue

            # Skip folded players
            if player.get("is_folded", False):
                continue

            position = player.get("position")

            # Determine seat index based on position
            if position in position_to_seat:
                seat_index = position_to_seat[position]
            else:
                # Skip unknown positions
                continue

            # Get the player position coordinates
            player_x, player_y = self.config.seat_positions[seat_index]

            # Card dimensions - slightly smaller than hero cards
            card_width = 70 * self.config.scale_factor
            card_height = 105 * self.config.scale_factor
            card_overlap = (
                30 * self.config.scale_factor
            )  # How much second card overlaps first card            # In the new design, cards should be between the circle and rectangle
            # The circle is positioned slightly above the rectangle
            # Calculate rectangle dimensions (should match PlayerDrawer._draw_player_rectangle)
            player_radius = self.config.player_radius
            rect_width = player_radius * 1.8
            rect_height = player_radius * 1.2

            # Calculate circle parameters (matching PlayerDrawer._draw_player_elements)
            circle_diameter = max(rect_width, rect_height) * 1.1
            circle_radius = circle_diameter / 2
            circle_y_offset = rect_height * 0.4

            # Position cards between the circle and rectangle
            # Cards should be visible above the rectangle but below the top of the circle
            card_offset_y = (
                -rect_height * 0.6
            )  # Position cards in the overlap area between circle and rectangle

            # Calculate card position based on player position and table center
            # We want cards to be on the side facing the center of the table
            table_center_x = self.config.table_center_x
            table_center_y = self.config.table_center_y

            # Vector from player to center
            dx = table_center_x - player_x
            dy = table_center_y - player_y

            # Normalize the vector
            length = (dx**2 + dy**2) ** 0.5
            if length > 0:
                dx /= length
                dy /= length

            # First card (left card) - rotated slightly counterclockwise
            card1_left = player_x - card_overlap / 2
            card1_top = player_y + card_offset_y
            self.draw_card_back(
                card1_left,
                card1_top,
                card_width,
                card_height,
                rotation_angle=5,
            )

            # Second card (right card) - rotated slightly clockwise
            card2_left = player_x + card_overlap / 2
            card2_top = card1_top
            self.draw_card_back(
                card2_left,
                card2_top,
                card_width,
                card_height,
                rotation_angle=-5,
            )

        return self.img, self.draw
