# Poker Table Visualizer - Refactored

This is a refactored version of the Poker Table Visualizer that breaks down the functionality into smaller, more manageable modules.

## Project Structure

The code has been reorganized into the following structure:

```
poker_viz/
├── __init__.py                 # Package initialization
├── config.py                   # Configuration settings
├── game_data.py                # Game data processing
├── table_drawer.py             # Table drawing functionality
├── player_drawer.py            # Player drawing functionality
├── card_drawer.py              # Card drawing functionality
└── poker_table_visualizer.py   # Main visualizer class
```

## How to Use

You can use the refactored code in two ways:

### 1. Backwards Compatibility

For backwards compatibility, you can use the `poker_table_visualizer_new.py` file which provides the same interface as the original file:

```python
from poker_table_visualizer_new import PokerTableVisualizer

# Load your JSON data
with open("your_poker_data.json", "r") as f:
    data = json.load(f)

# Create the visualization
visualizer = PokerTableVisualizer(data, "Ah", "Kd")
output_path = visualizer.create_visualization()
```

### 2. Using the New Modular Structure

Alternatively, you can directly use the new modular structure:

```python
from poker_viz.poker_table_visualizer import PokerTableVisualizer

# Load your JSON data
with open("your_poker_data.json", "r") as f:
    data = json.load(f)

# Create the visualization
visualizer = PokerTableVisualizer(data, "Ah", "Kd")
output_path = visualizer.create_visualization()
```

## Modules Description

### `config.py`

Contains configuration settings for the poker table visualization, including dimensions, colors, and seat positions.

### `game_data.py`

Processes poker game data from JSON format, handling players, positions, and other game state information.

### `table_drawer.py`

Handles drawing the poker table itself with smooth edges and borders.

### `player_drawer.py`

Manages drawing players around the table, including player circles, dealer buttons, and player information.

### `card_drawer.py`

Responsible for drawing cards, both hero cards and community cards, with support for loading card images or fallback drawing.

### `poker_table_visualizer.py`

The main class that coordinates all components to create the final visualization.

## Benefits of Refactoring

1. **Improved Maintainability**: Each module has a single responsibility, making it easier to understand and maintain.
2. **Better Organization**: Related functionality is grouped together in dedicated modules.
3. **Easier Testing**: Modules can be tested independently.
4. **Enhanced Readability**: Smaller files are easier to read and understand.
5. **Improved Extensibility**: New features can be added by extending or modifying specific modules without affecting others.

## Migration Notes

If you were using the original `poker_table_visualizer.py` directly, you can:

1. Keep using it as before (it still works)
2. Switch to using `poker_table_visualizer_new.py` (identical interface)
3. Migrate to the new modular structure for more flexibility
