#!/usr/bin/env python
import os
import csv
import logging
import argparse
from typing import List, Dict, Union, Any, Optional, Tuple
import sys
import glob
import re
import time
from create_drill import FlowPokerDrillCreator

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("batch_visualizations_upload.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("batch_visualizations_upload")

# Set third-party loggers to a higher level to reduce noise
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("flow_auth").setLevel(logging.WARNING)
logging.getLogger("drill_creator").setLevel(logging.DEBUG)


def read_metadata(metadata_file: str) -> Dict[str, str]:
    """
    Read metadata.csv file and extract tags

    Args:
        metadata_file: Path to metadata.csv file

    Returns:
        Dictionary of tags from metadata
    """
    tags = {}
    try:
        with open(metadata_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                for key, value in row.items():
                    if value:  # Only add non-empty values
                        # Convert field_left format from "100%" to "100"
                        if key == "field_left" and "%" in value:
                            value = value.replace("%", "")
                        # Map CSV keys to Flow Poker tags
                        tag_key = {
                            "mode": "mode",
                            "field_size": "field_size",
                            "field_left": "field_left",
                            "position": "position",
                            "stack_depth": "stack_depth",
                            "action": "action",
                        }.get(key, key)
                        tags[tag_key] = value
                break  # Only read first row
    except Exception as e:
        logger.error(f"Error reading metadata file {metadata_file}: {str(e)}")

    return tags


def find_image_files(directory: str) -> List[str]:
    """
    Find image files in a directory

    Args:
        directory: Directory to search for images

    Returns:
        List of image file paths
    """
    image_files = []
    for file in os.listdir(directory):
        if file.lower().endswith(('.png', '.jpg', '.jpeg')) and "metadata" not in file.lower():
            image_files.append(os.path.join(directory, file))
    return sorted(image_files)


def read_actions_file(directory: str) -> Dict[str, Dict[str, int]]:
    """
    Read actions.csv file and extract hand-specific scores and actions

    Args:
        directory: Directory containing actions.csv file

    Returns:
        Dictionary mapping hand to action scores
    """
    actions_file = os.path.join(directory, "actions.csv")
    actions_data = {}

    if not os.path.exists(actions_file):
        logger.warning(f"No actions.csv file found in {directory}")
        return actions_data

    try:
        with open(actions_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                hand = row.get("hand", "")
                if not hand:
                    continue

                # Extract scores and round to nearest integer
                fold_score = round(float(row.get("F_score", 0)))
                raise_score = round(float(row.get("R2.6_score", 0)))
                allin_score = round(float(row.get("RAI_score", 0)))

                # Store the scores for this hand
                actions_data[hand] = {
                    "Fold": fold_score,
                    "Raise 2.6BBs": raise_score,
                    "All In": allin_score,
                    "best_action": row.get("best_action", "")
                }

        logger.info(f"Read actions data for {len(actions_data)} hands")
        return actions_data
    except Exception as e:
        logger.error(f"Error reading actions file {actions_file}: {str(e)}")
        return {}


def parse_hand_from_filename(filename: str) -> Optional[str]:
    """
    Extract hand information from filename

    Args:
        filename: Image filename

    Returns:
        Hand description or None if not found
    """
    # Extract hand from filename pattern like "76o_F_0.000000.png"
    match = re.search(r'([2-9TJQKA]{1}[2-9TJQKA]{1}[os]{1})', os.path.basename(filename))
    if match:
        hand = match.group(1)
        return hand  # Return just the hand code, not a description
    return None


def get_answer_scores_for_hand(hand: str, actions_data: Dict[str, Dict[str, int]]) -> List[Dict[str, Union[str, int]]]:
    """
    Get scores for a specific hand based on actions data

    Args:
        hand: Hand identifier (e.g., "52s", "K4o")
        actions_data: Actions data from actions.csv

    Returns:
        List of answer score objects
    """
    if not hand or not actions_data or hand not in actions_data:
        # Return default scores if hand not found
        return [
            {"points": "0", "text": "Fold", "weight": 0},
            {"points": "0", "text": "Raise 2.6BBs", "weight": 0},
            {"points": "0", "text": "All In", "weight": 0},
        ]

    # Get the specific scores for this hand
    hand_data = actions_data[hand]

    return [
        {"points": str(hand_data.get("Fold", 0)), "text": "Fold", "weight": 0},
        {"points": str(hand_data.get("Raise 2.6BBs", 0)), "text": "Raise 2.6BBs", "weight": 0},
        {"points": str(hand_data.get("All In", 0)), "text": "All In", "weight": 0},
    ]


def generate_drill_name(tags: Dict[str, str], hand_info: Optional[str] = None) -> str:
    """
    Generate a drill name based on tags and hand info

    Args:
        tags: Dictionary of tags
        hand_info: Optional hand information

    Returns:
        Generated drill name
    """
    components = []

    # Add mode (ICM/Cash)
    mode = tags.get("mode", "").upper()
    if mode:
        components.append(mode)

    # Add position
    position = tags.get("position", "").upper()
    if position:
        components.append(position)

    # Add action type
    action = tags.get("action", "").upper()
    if action:
        components.append(action)

    # Add hand info if available
    if hand_info:
        components.append(hand_info)

    # Add stack depth
    depth = tags.get("depth", "")
    if depth:
        components.append(f"{depth}")

    # Add field info
    field_size = tags.get("fieldsize", "")
    field_left = tags.get("fieldleft", "")
    if field_size and field_left:
        components.append(f"Field: {field_left}% of {field_size}")

    # Join all non-empty components
    name = " | ".join([c for c in components if c])

    # If name is too short, add a default prefix
    if len(name) < 5:
        name = f"Poker Drill: {name}"

    return name


def generate_drill_description(tags: Dict[str, str], hand_info: Optional[str] = None) -> str:
    """
    Generate a description for the drill based on tags

    Args:
        tags: Dictionary of tags
        hand_info: Optional hand information

    Returns:
        Generated description
    """
    description_parts = []

    # Start with a general instruction
    action_type = tags.get("action", "").lower()
    if action_type == "rfi":
        description_parts.append("Decide whether to open raise or fold this hand.")
    elif action_type == "vs3bet":
        description_parts.append("Decide how to respond to a 3-bet.")
    elif action_type == "vsrfi":
        description_parts.append("Decide how to respond to an open raise.")
    else:
        description_parts.append("Select the best play for this poker situation.")

    # Add position context
    position = tags.get("position", "").lower()
    if position:
        position_names = {
            "btn": "button",
            "sb": "small blind",
            "bb": "big blind",
            "utg": "under the gun",
            "mp": "middle position",
            "co": "cutoff",
            "hj": "hijack",
        }
        position_name = position_names.get(position, position)
        description_parts.append(f"You are in the {position_name} position.")

    # Add stack depth info
    depth = tags.get("depth", "")
    if depth:
        description_parts.append(f"Stack depth is {depth}.")

    # Add tournament context if ICM
    mode = tags.get("mode", "").lower()
    if mode == "icm":
        field_size = tags.get("fieldsize", "")
        field_left = tags.get("fieldleft", "")
        if field_size and field_left:
            description_parts.append(f"Tournament has {field_size} entrants with {field_left}% remaining.")

    # Add hand info if available
    if hand_info:
        description_parts.append(hand_info)

    # Join all parts with spaces
    return " ".join(description_parts)


def get_default_answers() -> Tuple[List[str], List[Dict[str, Union[str, int]]]]:
    """
    Get default answers for RFI scenarios

    Returns:
        Tuple of (answers, answer_scores)
    """
    # Standard RFI answers for poker drills based on actions.csv format
    answers = ["Fold", "Raise 2.6BBs", "All In"]
    answer_scores = [
        {"points": "0", "text": "Fold", "weight": 0},
        {"points": "0", "text": "Raise 2.6BBs", "weight": 0},
        {"points": "0", "text": "All In", "weight": 0},
    ]

    return answers, answer_scores


def process_scenario(metadata_file: str, creator: FlowPokerDrillCreator) -> None:
    """
    Process a scenario by reading metadata and creating a single drill with multiple questions

    Args:
        metadata_file: Path to metadata.csv file
        creator: FlowPokerDrillCreator instance
    """
    directory = os.path.dirname(metadata_file)
    logger.info(f"Processing scenario in directory: {directory}")

    # Read metadata
    tags = read_metadata(metadata_file)
    if not tags:
        logger.warning(f"No tags found in {metadata_file}, skipping")
        return

    # More concise tag logging - just show the most important ones
    important_tags = {k: tags[k] for k in ['mode', 'field_size', 'position', 'action', 'stack_depth'] if k in tags}
    logger.info(f"Processing with tags: {important_tags}")

    # Find image files
    image_files = find_image_files(directory)
    if not image_files:
        logger.warning(f"No image files found in {directory}, skipping")
        return

    num_images = len(image_files)
    logger.info(f"Found {num_images} image files")

    # Read actions.csv for hand-specific scores
    actions_data = read_actions_file(directory)

    # Get default answers (constant for all hands in this folder)
    answers, _ = get_default_answers()

    # Generate a general drill name and description for the whole scenario
    scenario_name = os.path.basename(os.path.dirname(directory))
    position = tags.get("position", "").upper()
    action_type = tags.get("action", "").upper()
    field_left = tags.get("field_left", "")
    mode = tags.get("mode", "").upper()
    stack_depth = tags.get("stack_depth", "")
    if stack_depth and '_' in stack_depth:
        stack_depth = stack_depth.split('_')[0]


    name = f"{mode} | {position} | {action_type} | {stack_depth} BBs | {field_left}% Field Left"
    description = f"Nesse treino você irá aprender o range de RFI para o {position} em uma profundidade de {stack_depth} BBs."
    try:
        # Step 1: Create the drill
        logger.info(f"Creating drill: {name}")
        drill_id = creator.create_drill(name, description, answers, tags)
        creator.drill_id = drill_id

        # Step 2: Upload ALL images first
        logger.info(f"Starting to upload all {num_images} images...")

        # Dictionary to store media_ids mapped to hands/image_files
        media_map = {}
        hand_map = {}

        # Upload each image and store its media_id
        for i, image_file in enumerate(image_files, start=1):
            try:
                logger.info(f"Uploading image {i}/{num_images}: {os.path.basename(image_file)}")
                media_id = creator.upload_image(image_file)

                # Get hand info from filename
                hand = parse_hand_from_filename(image_file)

                # Store mapping of image index to media_id and hand
                media_map[i] = media_id
                hand_map[i] = hand

                logger.info(f"Uploaded image {i}/{num_images}, media_id: {media_id}, hand: {hand}")

                # Small delay to avoid overwhelming the server
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Failed to upload image {image_file}: {str(e)}")
                # Continue with next image anyway

        # Step 3: Finish the uploading process to prepare for scoring
        logger.info("All images uploaded. Finishing upload phase...")
        creator.finish_uploading()        # Step 4: Get questions from the API - note that this might only return the first question
        logger.info("Getting questions list...")
        questions = creator.get_questions()

        if not questions:
            logger.error("Failed to retrieve questions list from API")
            return

        logger.info(f"Retrieved {len(questions)} questions")

        # Even if API only returns one question, we need to score all images
        # The API expects questions to be created for each image by scoring them with IDs 1, 2, 3, etc.
        # We'll create a list of question IDs based on the number of images
        question_ids = []

        # If we got at least one question, use its ID as a starting point
        if len(questions) > 0:
            first_question_id = questions[0].get("id")
            logger.info(f"First question ID: {first_question_id}")

            # We'll generate question IDs for all images
            question_ids = [first_question_id + i for i in range(num_images)]
        else:
            # Fallback if no questions returned
            logger.warning("No question IDs returned, will use sequential IDs starting from 1")
            question_ids = [i + 1 for i in range(num_images)]

        logger.info(f"Will score {num_images} questions with IDs: {question_ids[:5]}...")
        if len(question_ids) > 5:
            logger.info(f"... and {len(question_ids) - 5} more question IDs")

        # Step 5: Score ALL images as questions, one by one        logger.info("Starting to score all questions...")

        # Keep track of successful scores
        successful_scores = 0

        # Score each image as a question
        for i, image_index in enumerate(range(num_images), start=1):
            try:
                # Get the question ID from our generated list
                question_id = question_ids[i-1]

                # Get the media_id for this image
                media_id = media_map.get(i)
                if not media_id:
                    logger.warning(f"No media_id found for image {i}, skipping")
                    continue

                # Get the hand for this image
                hand = hand_map.get(i)

                # Get specific answer scores for this hand
                if hand and hand in actions_data:
                    answer_scores = get_answer_scores_for_hand(hand, actions_data)
                    logger.info(f"Scoring question {i}/{num_images}, ID: {question_id}, media_id: {media_id}, hand: {hand}")
                    logger.info(f"Using scores for {hand}: Fold={answer_scores[0]['points']}, Raise={answer_scores[1]['points']}, AllIn={answer_scores[2]['points']}")
                else:
                    # Default scores if hand not found
                    answer_scores = [
                        {"points": "0", "text": "Fold", "weight": 0},
                        {"points": "0", "text": "Raise 2.6BBs", "weight": 0},
                        {"points": "0", "text": "All In", "weight": 0},
                    ]
                    logger.warning(f"No score data found for {hand}, using defaults")

                # Score this question with retry logic
                max_retries = 3
                retry_delay = 2  # seconds
                success = False

                for retry in range(max_retries):
                    try:
                        if retry == 0:                            logger.info(f"Scoring question {i}/{num_images}, ID: {question_id}")
                        else:
                            logger.info(f"Retry {retry}/{max_retries-1} for question {i}/{num_images}, ID: {question_id}")

                        creator.score_answer(
                            question_id=question_id,
                            media_id=media_id,
                            answers_scores=answer_scores,
                            tags=tags,
                            current=i,
                            total=num_images  # Use the total number of images
                        )
                        success = True
                        successful_scores += 1
                        # Wait a bit to avoid overwhelming the server
                        time.sleep(1)
                        break
                    except Exception as e:
                        error_msg = str(e)
                        # Truncate very long error messages
                        if len(error_msg) > 100:
                            error_msg = error_msg[:100] + "..."

                        if retry < max_retries - 1:
                            logger.warning(f"Retry needed: {error_msg}")
                            logger.info(f"Waiting {retry_delay} seconds before retrying...")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                        else:
                            logger.error(f"Failed to score question: {error_msg}")

                if not success:
                    logger.error(f"Failed to score question after {max_retries} attempts")
                    # Continue with next question anyway
            except Exception as e:                logger.error(f"Failed to process question {i}: {str(e)}")

        # Log summary of scoring results
        logger.info(f"Completed scoring: {successful_scores}/{num_images} questions successfully scored")

        # If no questions were successfully scored, we might want to abort
        if successful_scores == 0:
            logger.error("No questions were successfully scored! The drill may not be usable.")

        # Step 6: Set wizard rules
        logger.info("Setting wizard rules...")
        max_retries = 3
        retry_delay = 2  # seconds

        # Try to set rules with retries
        for retry in range(max_retries):
            try:
                # Use the number of images for wizard rules (since we score one question per image)
                wizard_amount = num_images
                creator.set_wizard_rules(amount=wizard_amount)
                logger.info(f"Successfully set wizard rules for {wizard_amount} questions")
                break
            except Exception as e:
                error_msg = str(e)
                if len(error_msg) > 100:
                    error_msg = error_msg[:100] + "..."

                if retry < max_retries - 1:
                    logger.warning(f"Rule setting failed, will retry: {error_msg}")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"Failed to set wizard rules: {error_msg}")

        # Step 7: Promote the drill with retries
        logger.info("Promoting drill...")
        retry_delay = 2  # Reset delay
        max_promotion_retries = 5  # Increased from 3 to 5 due to common failures

        for retry in range(max_promotion_retries):
            try:
                creator.promote_drill()
                logger.info(f"Successfully created and promoted drill with ID: {drill_id}")
                break
            except Exception as e:
                error_msg = str(e)
                if len(error_msg) > 100:
                    error_msg = error_msg[:100] + "..."

                if retry < max_promotion_retries - 1:
                    logger.warning(f"Promotion failed (attempt {retry+1}/{max_promotion_retries}), will retry: {error_msg}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff with longer wait times
                elif retry == max_promotion_retries - 1:
                    logger.warning(f"Failed to promote drill after {max_promotion_retries} attempts, but drill was created")
                    logger.warning(f"Drill ID {drill_id} may need to be manually promoted in the Flow Poker interface")

    except Exception as e:
        logger.error(f"Failed to create drill for scenario: {str(e)}")


def find_metadata_files(base_dir: str) -> List[str]:
    """
    Find all metadata.csv files recursively

    Args:
        base_dir: Base directory to start searching from

    Returns:
        List of paths to metadata.csv files
    """
    metadata_files = []
    for root, dirs, files in os.walk(base_dir):
        if "metadata.csv" in files:
            metadata_files.append(os.path.join(root, "metadata.csv"))
    return metadata_files


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Create drills from visualization scenarios")
    parser.add_argument(
        "--visualizations-dir",
        default="../visualizations",
        help="Directory containing visualizations (default: ../visualizations)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit the number of drills to create (0 = no limit)",
    )
    parser.add_argument(
        "--solution",
        default=None,
        help="Process only a specific solution directory (e.g., MTTGeneral_ICM8m200PTSTART)",
    )
    parser.add_argument(
        "--resume-from",
        default=None,
        help="Resume processing from a specific directory path",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=3,
        help="Delay in seconds between processing each scenario (default: 3)",
    )
    args = parser.parse_args()

    # Resolve path
    visualizations_dir = os.path.abspath(args.visualizations_dir)
    if not os.path.isdir(visualizations_dir):
        logger.error(f"Visualizations directory not found: {visualizations_dir}")
        return

    logger.info(f"Starting batch creation from directory: {visualizations_dir}")

    # Create the drill creator
    creator = FlowPokerDrillCreator()

    # Find all metadata files
    if args.solution:
        solution_dir = os.path.join(visualizations_dir, args.solution)
        if not os.path.isdir(solution_dir):
            logger.error(f"Solution directory not found: {solution_dir}")
            return
        metadata_files = find_metadata_files(solution_dir)
    else:
        metadata_files = find_metadata_files(visualizations_dir)

    logger.info(f"Found {len(metadata_files)} metadata files")

    # Sort metadata files for consistent processing order
    metadata_files.sort()

    # Apply resume-from if specified
    if args.resume_from:
        resume_path = os.path.abspath(args.resume_from)
        logger.info(f"Resuming from: {resume_path}")

        # Find the index to resume from
        resume_index = -1
        for i, file_path in enumerate(metadata_files):
            if os.path.dirname(file_path).startswith(resume_path):
                resume_index = i
                break

        if resume_index >= 0:
            logger.info(f"Resuming from index {resume_index}, skipping {resume_index} earlier items")
            metadata_files = metadata_files[resume_index:]
        else:
            logger.warning(f"Resume path not found in metadata files: {resume_path}")

    # Apply limit if specified
    if args.limit > 0 and args.limit < len(metadata_files):
        logger.info(f"Limiting to {args.limit} metadata files")
        metadata_files = metadata_files[:args.limit]

    # Create a list to track processed directories for the session
    processed_dirs = []

    # Process each metadata file
    for i, metadata_file in enumerate(metadata_files):
        directory = os.path.dirname(metadata_file)

        # Skip if we've already processed this directory in this session
        if directory in processed_dirs:
            logger.info(f"Skipping already processed directory: {directory}")
            continue

        logger.info(f"Processing file {i+1}/{len(metadata_files)}: {metadata_file}")

        try:
            process_scenario(metadata_file, creator)
            processed_dirs.append(directory)

            # Add delay between scenario processing to avoid overwhelming the server
            if i < len(metadata_files) - 1 and args.delay > 0:
                logger.info(f"Waiting {args.delay} seconds before processing next scenario...")
                time.sleep(args.delay)
        except Exception as e:
            logger.error(f"Error processing scenario: {str(e)}")
            # Continue with next scenario

    logger.info("Batch creation completed")


if __name__ == "__main__":
    main()
