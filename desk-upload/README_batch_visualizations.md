# Batch Visualizations Upload

This script automates the process of creating poker drills from visualization scenarios. It reads metadata files and images from the visualizations directory and uploads them to Flow Poker using the `create_drill.py` module.

## Features

- Recursively scans the visualizations directory for metadata.csv files
- Creates a single drill with multiple questions for each scenario folder
- Reads tags from metadata to configure drill settings
- Processes all images in a scenario folder as separate questions in the same drill
- Configures appropriate answers based on action type (rfi, vs3bet, etc.)
- Logs all operations for easy troubleshooting

## Usage

```bash
# Basic usage (scans all visualizations)
python batch_visualizations_upload.py

# Specify a different visualizations directory
python batch_visualizations_upload.py --visualizations-dir C:\path\to\visualizations

# Limit the number of drills to create
python batch_visualizations_upload.py --limit 10

# Process only a specific solution directory
python batch_visualizations_upload.py --solution MTTGeneral_ICM8m200PTSTART

# Resume processing from a specific directory (after a failure)
python batch_visualizations_upload.py --resume-from "C:\path\to\last\processed\folder"

# Set a custom delay between processing scenarios (in seconds)
python batch_visualizations_upload.py --delay 5
```

## Metadata Format

The script expects metadata.csv files with the following format:

```csv
mode,field_size,field_left,position,stack_depth,action
icm,200,100%,btn,200_125,rfi
```

These fields are mapped to Flow Poker tags as follows:
- mode → mode (e.g., "icm")
- field_size → fieldsize (e.g., "200")
- field_left → fieldleft (e.g., "100")
- position → position (e.g., "btn")
- stack_depth → depth (e.g., "200_125")
- action → action (e.g., "rfi")

## Score Configuration

The script reads the `actions.csv` file in each scenario directory to determine the correct scoring for each hand. The format should be:

```csv
hand,F_strat,F_ev,F_score,R2.6_strat,R2.6_ev,R2.6_score,RAI_strat,RAI_ev,RAI_score,best_action,best_ev,difficulty
52s,25.8,0.0,8.6,74.2,6e-05,10.0,0.0,-0.66918,0.0,R2.6,6e-05,6e-05
```

For each hand, the script will:
1. Extract the hand code (e.g., "52s") from the image filename
2. Look up the appropriate scores in the actions.csv file
3. Round the scores to the nearest integer (e.g., 8.6 becomes 9)
4. Use these scores for the answer options (Fold, Raise 2.6BBs, All In)

If no actions.csv file is found or a hand is not listed, default scores of 0 will be used.

## Image Files

The script will process all PNG, JPG, and JPEG files in the same directory as the metadata.csv file. All images in a single scenario folder will be uploaded as separate questions within the same drill. For example, if a folder contains 20 hand images, the script will create a single drill with 20 questions.

The script will attempt to extract hand information from filenames matching patterns like "76o_F_0.000000.png".

## Logging

All operations are logged to both the console and a file named `batch_visualizations_upload.log`.

## Error Handling and Reliability

The script includes several features to handle errors and ensure reliability:

- Automatic retries for API calls that fail (up to 3 attempts with exponential backoff)
- Delay between processing scenarios to avoid overwhelming the server
- Resume capability to continue from where processing stopped after a failure
- Tracking of processed directories to avoid duplicates within a session

If the script encounters errors while processing a scenario, it will log the error and continue with the next scenario rather than failing completely.

## Requirements

- Python 3.6+
- The `create_drill.py` module and its dependencies

## Examples

Process all scenarios from a specific solution:
```bash
python batch_visualizations_upload.py --solution MTTGeneral_ICM8m200PTSTART
```

Process only 5 scenarios to test the script:
```bash
python batch_visualizations_upload.py --limit 5
```

Resume processing after a failure:
```bash
python batch_visualizations_upload.py --resume-from "C:\Users\lucas\Documents\Poker\drills-creator\visualizations\MTTGeneral_ICM8m200PTSTART\200_125\preflop\pf_FFFFF\BTN"
```

Increase delay between scenarios to reduce server load:
```bash
python batch_visualizations_upload.py --delay 10
```
