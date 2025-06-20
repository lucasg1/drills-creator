"""
Configuration settings for the poker table visualizer.
"""

import os
from PIL import ImageFont


class PokerTableConfig:
    def __init__(self, scale_factor=2):
        # Image dimensions - base dimensions
        self.base_width = 1200
        self.base_height = 800

        # Scale factor for high-res rendering
        self.scale_factor = scale_factor

        # Actual dimensions (higher resolution for better anti-aliasing)
        self.width = self.base_width * self.scale_factor
        self.height = self.base_height * self.scale_factor

        # Table dimensions
        self.table_center_x = self.width // 2
        self.table_center_y = self.height // 2
        self.table_width = int(self.width * 0.85)  # Wider table
        self.table_height = int(
            self.height * 0.5
        )  # Less tall to make it more elongated

        # Player dimensions - adjusted for higher resolution
        self.player_radius = 70 * self.scale_factor

        # Colors - with alpha channel for better blending
        self.table_color = (53, 101, 77, 255)  # Green table
        self.background_color = (30, 30, 30, 255)  # Dark background
        self.text_color = (255, 255, 255, 255)  # White text
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
        self._init_seat_positions()

    def _init_seat_positions(self):
        """Initialize seat positions around the table for 9 players."""
        # Fixed positions around the table (9 seats)
        # Indices: 0=bottom-middle (hero), 1=bottom-left, 2=left-middle, 3=top-left,
        #          4=top-middle, 5=top-right, 6=right-top, 7=right-bottom, 8=bottom-right
        self.seat_positions = [
            (
                self.table_center_x,
                self.table_center_y + self.table_height * 0.7,
            ),  # Bottom middle (hero)
            (
                self.table_center_x - self.table_width * 0.25,
                self.table_center_y + self.table_height * 0.7,
            ),  # Bottom left
            (
                self.table_center_x - self.table_width * 0.5,
                self.table_center_y,
            ),  # Left middle
            (
                self.table_center_x - self.table_width * 0.25,
                self.table_center_y - self.table_height * 0.55,
            ),  # Top left
            (
                self.table_center_x,
                self.table_center_y - self.table_height * 0.55,
            ),  # Top middle
            (
                self.table_center_x + self.table_width * 0.25,
                self.table_center_y - self.table_height * 0.55,
            ),  # Top right
            (
                self.table_center_x + self.table_width * 0.50,
                self.table_center_y - self.table_height * 0.3,
            ),  # Right top
            (
                self.table_center_x + self.table_width * 0.50,
                self.table_center_y + self.table_height * 0.30,
            ),  # Right bottom
            (
                self.table_center_x + self.table_width * 0.25,
                self.table_center_y + self.table_height * 0.7,
            ),  # Bottom right
        ]

    def load_fonts(self):
        """Load fonts with appropriate scaling."""
        try:
            title_font = ImageFont.truetype("arial.ttf", 32 * self.scale_factor)
            player_font = ImageFont.truetype("arial.ttf", 16 * self.scale_factor)
            card_font = ImageFont.truetype("arial.ttf", 24 * self.scale_factor)
        except IOError:
            # Fallback to default font
            title_font = ImageFont.load_default()
            player_font = ImageFont.load_default()
            card_font = ImageFont.load_default()

        return title_font, player_font, card_font
