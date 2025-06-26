import os
import csv
import argparse
import logging
from typing import List, Dict, Union, Any
from create_drill import FlowPokerDrillCreator
import config

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("batch_creator")


def get_tag_value(tag_name: str, prompt: str, options: List[str]) -> str:
    """
    Prompt user to select a tag value from options

    Args:
        tag_name: Name of the tag
        prompt: Prompt to display
        options: List of available options

    Returns:
        Selected tag value
    """
    print(f"\n{prompt}")
    for i, option in enumerate(options):
        print(f"{i+1}. {option}")

    while True:
        try:
            choice = int(input(f"Select {tag_name} (1-{len(options)}): "))
            if 1 <= choice <= len(options):
                return options[choice - 1]
            else:
                print(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print("Please enter a valid number")


def get_tags_from_user() -> Dict[str, str]:
    """
    Prompt user to input tags for drills

    Returns:
        Dictionary of tags
    """
    tags = {}

    # Get mode
    tags["mode"] = get_tag_value("mode", "Select a mode:", config.MODES)

    # Get depth
    tags["depth"] = get_tag_value("depth", "Select stack depth:", config.DEPTHS)

    # Get position
    tags["position"] = get_tag_value("position", "Select position:", config.POSITIONS)

    # Get field size
    tags["fieldsize"] = get_tag_value(
        "fieldsize", "Select field size:", config.FIELD_SIZES
    )

    # Get field left
    tags["fieldleft"] = get_tag_value(
        "fieldleft", "Select field left:", config.FIELD_LEFTS
    )

    return tags


def create_drill_from_image(
    creator: FlowPokerDrillCreator,
    image_path: str,
    name: str,
    description: str,
    answers: List[str],
    tags: Dict[str, str],
    answer_scores: List[Dict[str, Union[str, int]]],
) -> int:
    """
    Create a drill from an image file

    Args:
        creator: FlowPokerDrillCreator instance
        image_path: Path to the image file
        name: Name of the drill
        description: Description of the drill
        answers: List of possible answers
        tags: Dictionary of tags
        answer_scores: List of answer scores

    Returns:
        Drill ID
    """
    try:
        drill_id = creator.create_complete_drill(
            name=name,
            description=description,
            answers=answers,
            tags=tags,
            image_path=image_path,
            answers_scores=answer_scores,
        )
        return drill_id
    except Exception as e:
        print(f"Error creating drill from {image_path}: {str(e)}")
        return None


def process_csv_file(csv_path: str, image_dir: str = None) -> None:
    """
    Process a CSV file containing drill definitions

    CSV format:
    image_name,drill_name,description,answer1,answer2,answer3,score1,score2,score3

    Args:
        csv_path: Path to the CSV file
        image_dir: Directory containing images (optional)
    """
    creator = FlowPokerDrillCreator()

    # Get common tags from user
    tags = get_tags_from_user()

    with open(csv_path, "r") as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header row

        for row in reader:
            image_name = row[0]
            drill_name = row[1]
            description = row[2]

            # Get answers (may vary in number)
            answers = []
            scores = []
            for i in range(3, len(row)):
                if i < (len(row) + 3) // 2:
                    if row[i]:  # Check if not empty
                        answers.append(row[i])
                else:
                    if row[i]:  # Check if not empty
                        scores.append(row[i])

            # Construct image path
            if image_dir:
                image_path = os.path.join(image_dir, image_name)
            else:
                image_path = image_name

            if not os.path.exists(image_path):
                print(f"Image not found: {image_path}")
                continue

            # Prepare answer scores
            answer_scores = []
            for i, (answer, score) in enumerate(zip(answers, scores)):
                answer_scores.append({"points": score, "text": answer, "weight": 0})

            # Create the drill
            drill_id = create_drill_from_image(
                creator=creator,
                image_path=image_path,
                name=drill_name,
                description=description,
                answers=answers,
                tags=tags,
                answer_scores=answer_scores,
            )

            if drill_id:
                print(f"Successfully created drill '{drill_name}' with ID {drill_id}")
            else:
                print(f"Failed to create drill '{drill_name}'")


def process_image_folder(folder_path: str, base_name: str = "Poker Drill") -> None:
    """
    Process a folder of images to create drills

    Args:
        folder_path: Path to the folder containing images
        base_name: Base name for drills
    """
    creator = FlowPokerDrillCreator()

    # Get common tags from user
    tags = get_tags_from_user()

    # Get common answers and scores
    print("\nDefine possible answers:")
    answers = []
    i = 1
    while True:
        answer = input(f"Answer {i} (leave empty to finish): ")
        if not answer:
            break
        answers.append(answer)
        i += 1

    if not answers:
        print("No answers provided. Exiting.")
        return

    print("\nAssign scores to answers:")
    answer_scores = []
    for i, answer in enumerate(answers):
        while True:
            try:
                score = input(f"Score for '{answer}': ")
                answer_scores.append({"points": score, "text": answer, "weight": 0})
                break
            except ValueError:
                print("Please enter a valid score")

    # Process each image in the folder
    for filename in os.listdir(folder_path):
        if filename.lower().endswith((".png", ".jpg", ".jpeg")):
            image_path = os.path.join(folder_path, filename)

            # Use filename as part of drill name
            name_base = os.path.splitext(filename)[0]
            drill_name = f"{base_name} - {name_base}"
            description = f"Automatically created drill for {name_base}"

            # Create the drill
            drill_id = create_drill_from_image(
                creator=creator,
                image_path=image_path,
                name=drill_name,
                description=description,
                answers=answers,
                tags=tags,
                answer_scores=answer_scores,
            )

            if drill_id:
                print(f"Successfully created drill '{drill_name}' with ID {drill_id}")
            else:
                print(f"Failed to create drill '{drill_name}'")


def main():
    """Main function to parse arguments and process drills"""
    parser = argparse.ArgumentParser(
        description="Create poker drills from images or CSV file"
    )

    # Add arguments
    parser.add_argument("--csv", help="Path to CSV file with drill definitions")
    parser.add_argument("--image-dir", help="Path to directory containing images")
    parser.add_argument(
        "--base-name", default="Poker Drill", help="Base name for drills"
    )

    # Parse arguments
    args = parser.parse_args()

    if args.csv:
        # Process CSV file
        process_csv_file(args.csv, args.image_dir)
    elif args.image_dir:
        # Process folder of images
        process_image_folder(args.image_dir, args.base_name)
    else:
        print("Please provide either a CSV file or an image directory")
        parser.print_help()


if __name__ == "__main__":
    main()
