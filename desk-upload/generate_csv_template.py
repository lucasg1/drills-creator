import os
import csv
import argparse
from typing import List, Dict


def create_template_csv(output_path: str, num_answers: int = 3) -> None:
    """
    Create a template CSV file for batch drill creation

    Args:
        output_path: Path to save the CSV file
        num_answers: Number of possible answers per drill
    """
    header = ["image_name", "drill_name", "description"]

    # Add answer columns
    for i in range(1, num_answers + 1):
        header.append(f"answer{i}")

    # Add score columns
    for i in range(1, num_answers + 1):
        header.append(f"score{i}")

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        # Add a sample row
        sample_row = ["example.png", "Sample Drill", "This is a sample drill"]

        # Add sample answers
        sample_answers = ["Raise 2 BBs", "All in", "Fold"]
        for i in range(num_answers):
            if i < len(sample_answers):
                sample_row.append(sample_answers[i])
            else:
                sample_row.append("")

        # Add sample scores
        sample_scores = ["10", "0", "2"]
        for i in range(num_answers):
            if i < len(sample_scores):
                sample_row.append(sample_scores[i])
            else:
                sample_row.append("")

        writer.writerow(sample_row)

    print(f"Template CSV created at {output_path}")


def generate_csv_from_images(
    folder_path: str, output_path: str, num_answers: int = 3
) -> None:
    """
    Generate a CSV file from a folder of images

    Args:
        folder_path: Path to the folder containing images
        output_path: Path to save the CSV file
        num_answers: Number of possible answers per drill
    """
    header = ["image_name", "drill_name", "description"]

    # Add answer columns
    for i in range(1, num_answers + 1):
        header.append(f"answer{i}")

    # Add score columns
    for i in range(1, num_answers + 1):
        header.append(f"score{i}")

    rows = []

    # Process each image in the folder
    for filename in os.listdir(folder_path):
        if filename.lower().endswith((".png", ".jpg", ".jpeg")):
            # Use filename as part of drill name
            name_base = os.path.splitext(filename)[0]
            drill_name = f"Poker Drill - {name_base}"
            description = f"Drill for {name_base}"

            row = [filename, drill_name, description]

            # Add empty answer placeholders
            for _ in range(num_answers):
                row.append("")

            # Add empty score placeholders
            for _ in range(num_answers):
                row.append("")

            rows.append(row)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"CSV file generated at {output_path}")
    print(f"Found {len(rows)} images. Please fill in the answers and scores.")


def main():
    """Main function to parse arguments and generate CSV files"""
    parser = argparse.ArgumentParser(
        description="Generate CSV templates for batch drill creation"
    )

    # Add arguments
    parser.add_argument(
        "--template", action="store_true", help="Create a template CSV file"
    )
    parser.add_argument("--from-images", help="Generate CSV from a folder of images")
    parser.add_argument("--output", default="drills.csv", help="Output CSV file path")
    parser.add_argument(
        "--answers", type=int, default=3, help="Number of possible answers per drill"
    )

    # Parse arguments
    args = parser.parse_args()

    if args.template:
        # Create template CSV
        create_template_csv(args.output, args.answers)
    elif args.from_images:
        # Generate CSV from folder of images
        generate_csv_from_images(args.from_images, args.output, args.answers)
    else:
        print("Please specify either --template or --from-images")
        parser.print_help()


if __name__ == "__main__":
    main()
