# Poker Solutions Manager

This project helps manage and organize poker solution files from GTOWizard spot solutions.

## Scripts

### 1. Solution Extractor (`soluction_extractor.py`)

Extracts spot solutions from HAR network logs and organizes them in a structured directory format.

```
python soluction_extractor.py
```

The script organizes the solutions with this folder structure:

```
poker_solutions/
  ├── [game_type]/
  │    ├── depth_[stack_depth]/
  │    │    ├── [street]/
  │    │    │    ├── [action_sequence]/
  │    │    │    │    ├── [active_position]/
  │    │    │    │    │    └── hero_[position]_[details].json
```

### 2. Solution Manager (`solution_manager.py`)

Helps you navigate and analyze your poker solutions.

#### List all solutions:

```
python solution_manager.py list
```

#### List with details:

```
python solution_manager.py list --details
```

#### Search for specific solutions:

```
python solution_manager.py list --search "UTG"
```

#### Analyze a specific solution:

```
python solution_manager.py analyze poker_solutions/MTTGeneral_ICM8m200PTSTART/depth_200_125/preflop/no_actions/UTG/hero_UTG_0.json
```

## File Organization Logic

The files are organized based on:

1. **Game Type**: The poker game configuration (e.g., MTTGeneral_ICM8m200PTSTART)
2. **Stack Depth**: The size of player stacks (e.g., 200.125)
3. **Street**: preflop, flop, turn, or river
4. **Action Sequence**: The sequence of actions taken (e.g., pf_FF for two folds preflop)
5. **Active Position**: The position currently making the decision (e.g., UTG, BTN, BB)

Each file is named with the hero's position and additional details when available.

## Usage Workflow

1. Capture a HAR file from your browser while browsing GTOWizard solutions
2. Run `soluction_extractor.py` to extract and organize the solution files
3. Use `solution_manager.py` to explore and analyze your solutions

## Requirements

- Python 3.6+
- Standard library modules (no external dependencies)
