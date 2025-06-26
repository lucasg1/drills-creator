"""
Configuration file for drill tags and options
"""

# Available modes
MODES = ["icm", "chipev"]

# Available depths (stack sizes)
DEPTHS = ["200bbs", "100bbs", "50bbs", "40bbs", "30bbs", "20bbs", "15bbs", "10bbs"]

# Available positions
POSITIONS = ["utg", "utg+1", "mp", "hj", "lj", "co", "btn", "sb", "bb"]

# Available field sizes
FIELD_SIZES = ["200", "500", "1000"]

# Available field lefts
FIELD_LEFTS = [
    "100",
    "75",
    "50",
    "37",
    "25",
    "bubble",
    "3 tables",
    "2 tables",
    "final table",
]

# Academy level ID
DEFAULT_ACADEMY_LEVEL_ID = 15

# Default drill duration in minutes
DEFAULT_DURATION = "5"
