"""
Module for drawing players and player-related elements.
"""

import os
from PIL import Image, ImageDraw, ImageFilter


class PlayerDrawer:
    """Draws players, dealer buttons, and player information."""

    def __init__(self, config, game_data, img, draw):
        """
        Initialize the player drawer.

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
        self._avatar_cache = None  # Cache for the avatar image

    def set_fonts(self, title_font, player_font, card_font):
        """Set the fonts for drawing text."""
        self.title_font = title_font
        self.player_font = player_font
        self.card_font = card_font

    def draw_players(self):
        """Draw all players around the table (DEPRECATED - use draw_player_circles and draw_player_rectangles instead)."""
        # Get position mapping
        position_to_seat = self.game_data.get_position_mapping()

        # Draw each player
        for player in self.game_data.players:
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

            # Get the position coordinates safely
            x, y = self._get_safe_seat_position(seat_index)

            # Determine player color
            is_active = (
                player.get("is_active", False)
                or player.get("position") == self.game_data.active_position
            )
            is_folded = player.get("is_folded", False)

            if is_folded:
                player_color = self.config.folded_player_color
            elif is_hero:
                player_color = self.config.hero_player_color
            elif is_active:
                player_color = self.config.active_player_color
            else:
                player_color = (
                    self.config.player_color
                )  # Draw player background circle and foreground rectangle
            self._draw_player_elements(x, y, player_color, player)

            # Draw dealer button if this player is the dealer
            if player.get("is_dealer", False):
                self._draw_dealer_button(x, y, seat_index)

        return self.img, self.draw

    def draw_player_circles(self):
        """Draw all player background circles around the table."""
        # Get position mapping
        position_to_seat = self.game_data.get_position_mapping()

        # Store player info for later use in draw_player_rectangles
        self.player_positions = []

        # Draw each player's background circle
        for player in self.game_data.players:
            position = player.get("position")
            is_hero = player.get("is_hero", False)

            # Determine seat index based on position
            if is_hero:
                seat_index = 0  # Hero always at bottom middle
            elif position in position_to_seat:
                seat_index = position_to_seat[position]
            else:
                # Fallback for unknown positions
                seat_index = min(
                    8, len(self.config.seat_positions) - 1
                )  # Default to bottom left or last available

            # Get the position coordinates safely
            x, y = self._get_safe_seat_position(seat_index)

            # Determine player color
            is_active = (
                player.get("is_active", False)
                or player.get("position") == self.game_data.active_position
            )
            is_folded = player.get("is_folded", False)

            if is_folded:
                player_color = self.config.folded_player_color
            elif is_hero:
                player_color = self.config.hero_player_color
            elif is_active:
                player_color = self.config.active_player_color
            else:
                player_color = self.config.player_color

            # Store player info for later use in draw_player_rectangles
            self.player_positions.append(
                {
                    "x": x,
                    "y": y,
                    "color": player_color,
                    "player": player,
                    "is_dealer": player.get("is_dealer", False),
                    "seat_index": seat_index,
                }
            )

            # Draw just the background circle
            self._draw_background_circle(
                x,
                y - 0.8 * self.config.player_radius,
                self.config.player_radius,
                player_color,
            )

        return self.img, self.draw

    def draw_player_rectangles(self):
        """Draw all player info rectangles on top of the background circles."""
        # Draw each player's rectangle using stored positions
        if not hasattr(self, "player_positions"):
            # If draw_player_circles wasn't called first, get the positions now
            return self.draw_players()

        for pos_info in self.player_positions:
            x = pos_info["x"]
            y = pos_info["y"]
            player_color = pos_info["color"]
            player = pos_info["player"]

            # Calculate rectangle dimensions
            player_radius = self.config.player_radius
            rect_width = player_radius * 1.8
            rect_height = player_radius * 1.2  # Draw the rectangle with player info
            self._draw_player_rectangle(
                x, y, rect_width, rect_height, player_color, player
            )

            # Draw dealer button if this player is the dealer
            if pos_info["is_dealer"]:
                self._draw_dealer_button(x, y, pos_info.get("seat_index", 0))

        return self.img, self.draw

    def _draw_player_elements(self, x, y, player_color, player):
        """Draw a player with background circle and foreground rectangle."""
        scale_factor = self.config.scale_factor
        player_radius = self.config.player_radius

        # Calculate rectangle dimensions
        rect_width = player_radius * 1.8
        rect_height = player_radius * 1.2

        # Calculate circle diameter based on the larger side of the rectangle
        circle_diameter = (
            max(rect_width, rect_height) * 1.1
        )  # Make circle slightly larger
        circle_radius = circle_diameter / 2

        # Adjust circle position to be 20% hidden behind the rectangle
        # The circle center is slightly higher than the rectangle center
        circle_y = (
            y - rect_height * 0.4
        )  # Increased offset to position circle more above the rectangle

        # Step 1: Draw the background circle with anti-aliasing
        self._draw_background_circle(x, circle_y, circle_radius, player_color)

        # Step 2: Here is where player cards would be drawn (between circle and rectangle)
        # Note: This is done in a separate method (typically called from card_drawer.py)

        # Step 3: Draw the foreground rounded rectangle with player info
        self._draw_player_rectangle(x, y, rect_width, rect_height, player_color, player)

    def _draw_background_circle(self, x, y, radius, player_color):
        """Draw a background circle with anti-aliasing."""
        scale_factor = self.config.scale_factor

        # Create a circular mask for the player
        circle_mask = Image.new("L", (self.config.width, self.config.height), 0)
        circle_mask_draw = ImageDraw.Draw(circle_mask)

        # Draw the circle on the mask
        circle_mask_draw.ellipse(
            [
                x - radius,
                y - radius,
                x + radius,
                y + radius,
            ],
            fill=255,
        )

        # Apply slight blur for smoother edges
        circle_mask = circle_mask.filter(
            ImageFilter.GaussianBlur(radius=scale_factor * 0.5)
        )

        # Create a player circle overlay
        circle_overlay = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
        )

        # Fill the player circle with the appropriate color
        for py in range(
            max(0, int(y - radius - scale_factor * 2)),
            min(self.config.height, int(y + radius + scale_factor * 2)),
        ):
            for px in range(
                max(0, int(x - radius - scale_factor * 2)),
                min(self.config.width, int(x + radius + scale_factor * 2)),
            ):
                mask_value = circle_mask.getpixel((px, py))
                if mask_value > 0:
                    circle_overlay.putpixel((px, py), (*player_color[:3], mask_value))

        # Overlay the player circle on the main image
        self.img = Image.alpha_composite(self.img, circle_overlay)
        self.draw = ImageDraw.Draw(self.img, "RGBA")  # Recreate the draw object

        # Draw avatar inside the circle
        self._draw_avatar_in_circle(x, y, radius)

        # Draw border with anti-aliasing
        border_mask = Image.new("L", (self.config.width, self.config.height), 0)
        border_mask_draw = ImageDraw.Draw(border_mask)

        # Draw just the outline on the border mask
        border_width = 2 * scale_factor
        border_mask_draw.ellipse(
            [
                x - radius,
                y - radius,
                x + radius,
                y + radius,
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

        # Fill the border with black
        for py in range(
            max(0, int(y - radius - scale_factor * 3)),
            min(self.config.height, int(y + radius + scale_factor * 3)),
        ):
            for px in range(
                max(0, int(x - radius - scale_factor * 3)),
                min(self.config.width, int(x + radius + scale_factor * 3)),
            ):
                mask_value = border_mask.getpixel((px, py))
                if mask_value > 0:
                    border_overlay.putpixel((px, py), (0, 0, 0, mask_value))

        # Overlay the border on the main image
        self.img = Image.alpha_composite(self.img, border_overlay)
        self.draw = ImageDraw.Draw(self.img, "RGBA")  # Recreate the draw object

    def _draw_player_rectangle(self, x, y, width, height, player_color, player):
        """Draw a rounded rectangle with player position and stack information."""
        scale_factor = self.config.scale_factor
        text_color = self.config.text_color
        corner_radius = height * 0.3  # Rounded corners

        # Create a mask for the rounded rectangle
        rect_mask = Image.new("L", (self.config.width, self.config.height), 0)
        rect_mask_draw = ImageDraw.Draw(rect_mask)

        # Draw rounded rectangle on the mask
        left = x - width / 2
        top = y - height / 2
        right = x + width / 2
        bottom = y + height / 2

        # Draw the rectangle with rounded corners
        rect_mask_draw.rounded_rectangle(
            [left, top, right, bottom],
            radius=corner_radius,
            fill=255,
        )

        # Apply slight blur for smoother edges
        rect_mask = rect_mask.filter(
            ImageFilter.GaussianBlur(radius=scale_factor * 0.3)
        )

        # Create a rectangle overlay
        rect_overlay = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
        )

        # Fill the rectangle with the player color
        for py in range(
            max(0, int(top - scale_factor * 2)),
            min(self.config.height, int(bottom + scale_factor * 2)),
        ):
            for px in range(
                max(0, int(left - scale_factor * 2)),
                min(self.config.width, int(right + scale_factor * 2)),
            ):
                mask_value = rect_mask.getpixel((px, py))
                if mask_value > 0:
                    # Make rectangle slightly darker than the circle
                    color_r = max(0, int(player_color[0] * 0.9))
                    color_g = max(0, int(player_color[1] * 0.9))
                    color_b = max(0, int(player_color[2] * 0.9))
                    rect_overlay.putpixel(
                        (px, py), (color_r, color_g, color_b, mask_value)
                    )

        # Overlay the rectangle on the main image
        self.img = Image.alpha_composite(self.img, rect_overlay)
        self.draw = ImageDraw.Draw(self.img, "RGBA")  # Recreate the draw object

        # Draw rectangle border
        border_mask = Image.new("L", (self.config.width, self.config.height), 0)
        border_mask_draw = ImageDraw.Draw(border_mask)

        # Draw just the outline on the border mask
        border_width = 2 * scale_factor
        border_mask_draw.rounded_rectangle(
            [left, top, right, bottom],
            radius=corner_radius,
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
        )  # Fill the border with black
        for py in range(
            max(0, int(top - scale_factor * 3)),
            min(self.config.height, int(bottom + scale_factor * 3)),
        ):
            for px in range(
                max(0, int(left - scale_factor * 3)),
                min(self.config.width, int(right + scale_factor * 3)),
            ):
                mask_value = border_mask.getpixel((px, py))
                if mask_value > 0:
                    border_overlay.putpixel((px, py), (0, 0, 0, mask_value))

        # Overlay the border on the main image
        self.img = Image.alpha_composite(self.img, border_overlay)
        self.draw = ImageDraw.Draw(self.img, "RGBA")  # Recreate the draw object

        # Draw player information inside the rectangle
        self._draw_player_info(x, y, player, height)

    def _draw_player_info(self, x, y, player, rect_height):
        """Draw player position and stack information inside the rectangle."""
        scale_factor = self.config.scale_factor
        text_color = self.config.text_color

        # Draw player position
        position_text = player.get("position", "")
        pos_width = self.draw.textlength(position_text, font=self.player_font)

        # Position the text at the top part of the rectangle
        pos_y = y - rect_height * 0.25
        self.draw.text(
            (
                x - pos_width / 2,
                pos_y - self.player_font.getbbox(position_text)[3] / 2,
            ),
            position_text,
            fill=text_color,
            font=self.player_font,
        )

        # Draw player stack
        stack = float(player.get("current_stack", 0))
        stack_text = f"{stack:.1f} BB"
        stack_width = self.draw.textlength(stack_text, font=self.player_font)

        # Position the stack text at the bottom part of the rectangle
        stack_y = y + rect_height * 0.25
        self.draw.text(
            (
                x - stack_width / 2,
                stack_y - self.player_font.getbbox(stack_text)[3] / 2,
            ),
            stack_text,
            fill=text_color,
            font=self.player_font,
        )

    def _draw_dealer_button(self, x, y, seat_index):
        """Draw the dealer button next to a player with a simple 3D effect."""
        dealer_radius = 12 * self.config.scale_factor
        player_radius = self.config.player_radius
        scale_factor = self.config.scale_factor
        dealer_button_color = self.config.dealer_button_color

        # --------------------------------------------------------------
        # Custom offsets so the button does not overlap with chips
        # --------------------------------------------------------------
        offset_maps = {
            8: {
                0: (1.4, -1.8),
                1: (1.1, -1.4),
                2: (0.8, 0.7),
                3: (0.8, 0.7),
                4: (0.8, 0.9),
                5: (0.8, 0.7),
                6: (-0.8, 0.7),
                7: (-1.3, -1.4),
            }
        }
        offsets = offset_maps.get(self.config.num_players, {})
        dx_factor, dy_factor = offsets.get(seat_index, (0.7, -0.7))
        button_x = x + player_radius * dx_factor
        button_y = y + player_radius * dy_factor

        # Height of the button for the 3D look
        thickness = int(scale_factor * 3)

        # --------------------------------------------------------------
        # Shadow under the button
        # --------------------------------------------------------------
        shadow_size = int(dealer_radius * 2)
        shadow_img = Image.new("RGBA", (shadow_size, shadow_size), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_img)
        shadow_draw.ellipse([0, 0, shadow_size, shadow_size], fill=(0, 0, 0, 80))
        shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=scale_factor))
        shadow_overlay = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
        )
        shadow_overlay.paste(
            shadow_img,
            (
                int(button_x - dealer_radius + thickness),
                int(button_y - dealer_radius + thickness),
            ),
            shadow_img,
        )
        self.img = Image.alpha_composite(self.img, shadow_overlay)
        self.draw = ImageDraw.Draw(self.img, "RGBA")

        # --------------------------------------------------------------
        # Button thickness - darker ellipse slightly below the top face
        # --------------------------------------------------------------
        edge_color = tuple(max(0, c - 40) for c in dealer_button_color[:3]) + (255,)
        edge_overlay = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
        )
        edge_draw = ImageDraw.Draw(edge_overlay)
        edge_draw.ellipse(
            [
                button_x - dealer_radius,
                button_y - dealer_radius + thickness,
                button_x + dealer_radius,
                button_y + dealer_radius + thickness,
            ],
            fill=edge_color,
        )
        self.img = Image.alpha_composite(self.img, edge_overlay)
        self.draw = ImageDraw.Draw(self.img, "RGBA")

        # --------------------------------------------------------------
        # Top face of the button
        # --------------------------------------------------------------
        button_img = Image.new("RGBA", (shadow_size, shadow_size), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(button_img, "RGBA")
        overlay_draw.ellipse(
            [0, 0, shadow_size, shadow_size],
            fill=dealer_button_color,
            outline=(0, 0, 0, 255),
            width=max(1, scale_factor),
        )
        top_overlay = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
        )
        top_overlay.paste(
            button_img,
            (int(button_x - dealer_radius), int(button_y - dealer_radius)),
            button_img,
        )
        self.img = Image.alpha_composite(self.img, top_overlay)
        self.draw = ImageDraw.Draw(self.img, "RGBA")

        # --------------------------------------------------------------
        # Draw "D" label in the centre
        # --------------------------------------------------------------
        d_text = "D"
        d_width = self.draw.textlength(d_text, font=self.player_font)
        d_height = self.player_font.getbbox(d_text)[3]
        self.draw.text(
            (button_x - d_width / 2, button_y - d_height / 2),
            d_text,
            fill=(0, 0, 0, 255),
            font=self.player_font,
        )

    def _get_safe_seat_position(self, seat_index):
        """Safely get the seat position even if the index is out of range.

        Args:
            seat_index: The seat index to get the position for

        Returns:
            tuple: The (x, y) coordinates for the seat position
        """
        # Check if the seat_index is out of range
        if seat_index >= len(self.config.seat_positions):
            print(
                f"Warning: Seat index {seat_index} is out of range (max: {len(self.config.seat_positions)-1})"
            )
            # Use the first seat position (hero) as a fallback
            seat_index = 0

        return self.config.seat_positions[seat_index]

    def _load_avatar_image(self):
        """Load and cache the avatar image."""
        if self._avatar_cache is None:
            avatar_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "avatar.png"
            )
            if os.path.exists(avatar_path):
                try:
                    self._avatar_cache = Image.open(avatar_path).convert("RGBA")
                except Exception as e:
                    print(f"Warning: Could not load avatar image: {e}")
                    self._avatar_cache = (
                        False  # Mark as failed to avoid repeated attempts
                    )
            else:
                print(f"Warning: Avatar image not found at {avatar_path}")
                self._avatar_cache = False
        return self._avatar_cache if self._avatar_cache else None

    def _draw_avatar_in_circle(self, x, y, radius):
        """Draw the avatar image inside the circle with proper masking."""
        avatar_img = self._load_avatar_image()
        if not avatar_img:
            return

        scale_factor = self.config.scale_factor

        # Calculate avatar size (slightly smaller than circle to leave some padding)
        avatar_radius = radius * 0.85
        avatar_size = int(avatar_radius * 2)

        # Resize avatar to fit the circle
        avatar_resized = avatar_img.resize(
            (avatar_size, avatar_size), Image.Resampling.LANCZOS
        )

        # Create a circular mask for the avatar
        avatar_mask = Image.new("L", (avatar_size, avatar_size), 0)
        avatar_mask_draw = ImageDraw.Draw(avatar_mask)
        avatar_mask_draw.ellipse([0, 0, avatar_size, avatar_size], fill=255)

        # Apply slight blur for smoother edges
        avatar_mask = avatar_mask.filter(
            ImageFilter.GaussianBlur(radius=scale_factor * 0.3)
        )

        # Create avatar overlay
        avatar_overlay = Image.new(
            "RGBA", (self.config.width, self.config.height), (0, 0, 0, 0)
        )

        # Calculate position to center the avatar
        avatar_x = int(x - avatar_radius)
        avatar_y = int(y - avatar_radius - 35)

        # Apply the circular mask to the avatar
        avatar_masked = Image.new("RGBA", (avatar_size, avatar_size), (0, 0, 0, 0))
        for py in range(avatar_size):
            for px in range(avatar_size):
                mask_value = avatar_mask.getpixel((px, py))
                if mask_value > 0:
                    avatar_pixel = avatar_resized.getpixel((px, py))
                    # Apply mask to alpha channel
                    alpha = int(
                        (avatar_pixel[3] if len(avatar_pixel) == 4 else 255)
                        * mask_value
                        / 255
                    )
                    avatar_masked.putpixel((px, py), (*avatar_pixel[:3], alpha))

        # Paste the masked avatar onto the overlay
        avatar_overlay.paste(avatar_masked, (avatar_x, avatar_y), avatar_masked)

        # Composite the avatar overlay onto the main image
        self.img = Image.alpha_composite(self.img, avatar_overlay)
        self.draw = ImageDraw.Draw(self.img, "RGBA")  # Recreate the draw object
