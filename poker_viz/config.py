"""
Configuration settings for the poker table visualizer.
"""

import os
from PIL import ImageFont


class PokerTableConfig:
    def __init__(self, scale_factor=2, num_players=8):
        # Image dimensions - base dimensions
        self.base_width = 1432
        self.base_height = 849

        # Scale factor for high-res rendering
        self.scale_factor = scale_factor

        # Number of players
        self.num_players = num_players

        # Actual dimensions (higher resolution for better anti-aliasing)
        self.width = int(self.base_width * self.scale_factor)
        self.height = int(self.base_height * self.scale_factor)

        # Table dimensions
        self.table_center_x = self.width // 2
        self.table_center_y = int(
            self.height * 0.44
        )  # Shifted upwards to create more space at bottom
        self.table_width = int(self.width * 0.80)  # Wider table
        self.table_height = int(
            self.height * 0.5
        )  # Less tall to make it more elongated

        # Player dimensions - adjusted for higher resolution
        self.player_radius = 70 * self.scale_factor

        # Colors - with alpha channel for better blending
        self.table_color = (53, 101, 77, 255)  # Green table
        self.background_color = (30, 30, 30, 255)  # Dark background
        self.text_color = (255, 255, 255, 255)  # White text
        # Golden color for scenario text
        self.scenario_text_color = (255, 215, 0, 255)  # RGB for gold with full opacity
        # Default background for text labels (subtle black with some transparency)
        self.text_bg_color = (0, 0, 0, 50)
        self.player_color = (100, 100, 100, 255)  # Light gray player circles
        self.active_player_color = (80, 80, 160, 255)  # Blue for active player
        self.hero_player_color = (80, 160, 80, 255)  # Green for hero
        self.folded_player_color = (50, 50, 50, 255)  # Dark gray for folded
        self.dealer_button_color = (220, 220, 220, 255)  # Light gray dealer button
        # Card colors
        self.card_bg = (255, 255, 255, 255)
        self.red_suits = (220, 40, 40, 255)
        self.black_suits = (0, 0, 0, 255)

        # Define seat positions
        self._init_seat_positions(self.num_players)

    def _init_seat_positions(self, num_players=8):

        if num_players not in [2, 3, 4, 5, 6, 7, 8, 9]:
            print(
                f"Warning: Unsupported player count ({num_players}), defaulting to 8 players"
            )
            num_players = 8

        # Common positions used across different table sizes
        bottom_middle = (
            self.table_center_x,
            self.table_center_y + self.table_height * 0.75,
        )
        bottom_left = (
            self.table_center_x - self.table_width * 0.3,
            self.table_center_y + self.table_height * 0.65,
        )
        bottom_right = (
            self.table_center_x + self.table_width * 0.3,
            self.table_center_y + self.table_height * 0.65,
        )
        left_middle = (
            self.table_center_x - self.table_width * 0.5,
            self.table_center_y,
        )
        right_middle = (
            self.table_center_x + self.table_width * 0.5,
            self.table_center_y,
        )
        top_left = (
            self.table_center_x - self.table_width * 0.30,
            self.table_center_y - self.table_height * 0.50,
        )
        top_middle = (
            self.table_center_x,
            self.table_center_y - self.table_height * 0.57,
        )
        top_right = (
            self.table_center_x + self.table_width * 0.3,
            self.table_center_y - self.table_height * 0.50,
        )
        right_top = (
            self.table_center_x + self.table_width * 0.50,
            self.table_center_y - self.table_height * 0.3,
        )
        right_bottom = (
            self.table_center_x + self.table_width * 0.50,
            self.table_center_y + self.table_height * 0.30,
        )

        if num_players == 2:
            self.seat_positions = [
                bottom_middle,
                top_middle,
            ]
        elif num_players == 3:
            self.seat_positions = [
                bottom_middle,
                top_left,
                top_right,
            ]
        elif num_players == 4:
            self.seat_positions = [
                bottom_middle,
                left_middle,
                top_left,
                top_right,
            ]
        elif num_players == 5:
            self.seat_positions = [
                bottom_middle,
                left_middle,
                top_left,
                top_right,
                right_middle,
            ]
        elif num_players == 6:
            self.seat_positions = [
                bottom_middle,  # Hero
                bottom_left,
                left_middle,
                top_middle,
                right_middle,
                bottom_right,
            ]
        elif num_players == 7:
            self.seat_positions = [
                bottom_middle,  # Hero
                bottom_left,
                left_middle,
                top_middle,
                top_right,
                right_middle,
                bottom_right,
            ]
        elif num_players == 8:
            self.seat_positions = [
                bottom_middle,  # Hero
                bottom_left,
                left_middle,
                top_left,
                top_middle,
                top_right,
                right_middle,
                bottom_right,
            ]
        elif num_players == 9:
            self.seat_positions = [
                bottom_middle,  # Hero
                bottom_left,
                left_middle,
                top_left,
                top_middle,
                top_right,
                right_top,
                right_bottom,
                bottom_right,
            ]

    def load_fonts(self):
        # Use os.path.join for platform-independence
        font_dir = os.path.join("fonts", "static")

        """Load fonts with appropriate scaling."""
        try:
            title_font = ImageFont.truetype(
                os.path.join(font_dir, "Inter_24pt-Bold.ttf"),
                int(32 * self.scale_factor),
            )
            player_font = ImageFont.truetype(
                os.path.join(font_dir, "Inter_18pt-Regular.ttf"),
                int(20 * self.scale_factor),
            )
            card_font = ImageFont.truetype(
                os.path.join(font_dir, "Inter_24pt-SemiBold.ttf"),
                int(24 * self.scale_factor),
            )
        except IOError:
            # Fallback to Arial
            try:
                title_font = ImageFont.truetype(
                    "arial.ttf", int(32 * self.scale_factor)
                )
                player_font = ImageFont.truetype(
                    "arial.ttf", int(20 * self.scale_factor)
                )
                card_font = ImageFont.truetype("arial.ttf", int(24 * self.scale_factor))
            except IOError:
                # Final fallback to default bitmap font
                title_font = ImageFont.load_default()
                player_font = ImageFont.load_default()
                card_font = ImageFont.load_default()

        return title_font, player_font, card_font
