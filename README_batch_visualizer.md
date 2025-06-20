# Poker Solution Batch Visualizer

This tool processes poker solution files from GTOWizard and creates visualizations for hands within a specified EV range.

## Features

- Processes all solution files in the organized folder structure
- Creates poker table visualizations for hands within a specified EV range
- Maintains the same folder structure for outputs
- Generates CSV files with filtered hand data
- Creates summary files with statistics for each scenario
- Supports filtering by game type, stack depth, and position

## Requirements

- Python 3.6+
- Pillow (PIL Fork)
- pandas
- numpy

## Usage

### Basic Usage

```bash
python batch_visualizer.py
```

This will process all solution files in the `poker_solutions` directory and save visualizations to the `visualizations` directory.

### Command-line Options

```bash
python batch_visualizer.py --input poker_solutions --output visualizations --min-ev 0.01 --max-ev 0.05
```

#### Available Options:

- `--input`: Directory containing solution JSON files (default: `poker_solutions`)
- `--output`: Directory to save visualizations (default: `visualizations`)
- `--min-ev`: Minimum EV threshold (default: 0.009)
- `--max-ev`: Maximum EV threshold (default: 0.05)
- `--game-type`: Filter by game type (e.g., `MTTGeneral_ICM8m200PTSTART`)
- `--depth`: Filter by stack depth (e.g., `200_125`)
- `--position`: Filter by position (e.g., `UTG`, `BTN`, `SB`)

### Examples

Process only solutions for the BTN position:

```bash
python batch_visualizer.py --position BTN
```

Process only solutions with 200.125 stack depth:

```bash
python batch_visualizer.py --depth 200_125
```

Adjust the EV range:

```bash
python batch_visualizer.py --min-ev 0.02 --max-ev 0.1
```

## Output Structure

The visualizer maintains the same folder structure as the input:

```
visualizations/
  ├── [game_type]/
  │    ├── [stack_depth]/
  │    │    ├── [street]/
  │    │    │    ├── [action_sequence]/
  │    │    │    │    ├── [position]/
  │    │    │    │    │    ├── [hand]_[action]_[ev].png
  │    │    │    │    │    ├── hands_ev_[min]_to_[max].csv
  │    │    │    │    │    └── summary.txt
```

Each scenario folder contains:

1. PNG files for each hand visualization
2. A CSV file with the filtered hands data
3. A summary.txt file with statistics for the scenario

## Logging

The tool logs all activity to both the console and a `batch_visualizer.log` file.
