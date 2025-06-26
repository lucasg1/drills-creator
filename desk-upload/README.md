# Flow Poker Drill Creator

This tool automates the creation of poker drills on the Flow Poker website.

## Features

- Create single or multiple drills with consistent tagging
- Upload images for each drill
- Assign scores to possible actions
- Batch processing from CSV files or image folders
- Configurable tags for mode, depth, position, field size, etc.
- Automatic authentication with Flow Poker website

## Files

- `create_drill.py`: Core functionality for API interactions
- `flow_auth.py`: Authentication module for Flow Poker API
- `config.py`: Configuration settings for drill tags
- `batch_create_drills.py`: Process multiple drills from CSV or folder
- `generate_csv_template.py`: Create CSV templates for batch processing

## Tag Options

All drills must include the following tags:

- **Mode**: icm, chipev
- **Depth**: 200bbs, 100bbs, 50bbs, etc.
- **Position**: utg+1, utg, mp, hj, lj, co, btn, sb, or bb
- **Field Size**: 200, 500, 1000, etc.
- **Field Left**: 100, 75, 50, 37, 25, bubble, 3 tables, 2 tables, final table

## Usage

### Single Drill Creation

To use the core functionality directly:

```python
from create_drill import FlowPokerDrillCreator

# Create a new drill creator
creator = FlowPokerDrillCreator()

# Example tags
tags = {
    "mode": "icm",
    "depth": "200bbs",
    "position": "btn",
    "fieldsize": "200",
    "fieldleft": "100"
}

# Example answers
answers = ["Raise 2 BBs", "All in", "Fold"]

# Example scores for each answer
answer_scores = [
    {"points": "10", "text": "Raise 2 BBs", "weight": 0},
    {"points": "0", "text": "All in", "weight": 0},
    {"points": "2", "text": "Fold", "weight": 0}
]

# Example image path
image_path = "../visualizations/MTTGeneral_ICM8m200PTSTART/sample_image.png"

# Create a complete drill
drill_id = creator.create_complete_drill(
    name="Example Drill",
    description="This is an example drill created using automation",
    answers=answers,
    tags=tags,
    image_path=image_path,
    answers_scores=answer_scores
)
```

### Batch Processing from CSV

1. First, generate a CSV template:

```
python generate_csv_template.py --template --output drills.csv
```

2. Fill in the CSV with your drill information

3. Create the drills from the CSV:

```
python batch_create_drills.py --csv drills.csv --image-dir ../visualizations/MTTGeneral_ICM8m200PTSTART
```

### Batch Processing from Image Folder

Process all images in a folder:

```
python batch_create_drills.py --image-dir ../visualizations/MTTGeneral_ICM8m200PTSTART
```

### Generate CSV from Images

Generate a CSV template based on images in a folder:

```
python generate_csv_template.py --from-images ../visualizations/MTTGeneral_ICM8m200PTSTART --output drills.csv
```

## CSV Format

The CSV format for batch processing includes:

- `image_name`: Filename of the image (with extension)
- `drill_name`: Name of the drill
- `description`: Description of the drill
- `answer1`, `answer2`, `answer3`, etc.: Possible answers
- `score1`, `score2`, `score3`, etc.: Scores for each answer

Example:

```
image_name,drill_name,description,answer1,answer2,answer3,score1,score2,score3
example.png,Sample Drill,This is a sample drill,Raise 2 BBs,All in,Fold,10,0,2
```

## Requirements

- Python 3.6+
- Required packages (install via `pip install -r requirements.txt`):
  - requests
  - urllib3
  - python-dotenv

## Authentication

The tool automatically handles authentication with the Flow Poker website using session cookies. It will:

1. Attempt to log in and obtain a JSESSIONID cookie
2. Use this cookie for all subsequent requests
3. Automatically refresh the session if it expires
4. Handle SSL verification issues
