#!/usr/bin/env python
"""
Batch Visualizations Upload Script

This script dynamically creates poker drills from visualization directories by:
1. Reading metadata.csv files to get drill parameters
2. Dynamically detecting available actions from actions.csv headers
   (supports both _score and _ev column formats)
3. Uploading images in parallel with retry logic
4. Creating drill questions with hand-specific scoring
5. Promoting completed drills

The script automatically adapts to different action sets like:
- Fold, Raise 2BBs, Raise 10BBs, Raise 15BBs
- Fold, Raise 2.6BBs, All In
- Any combination of F, R[amount], RAI actions

Column formats supported:
- F_score, R2_score, RAI_score, etc.
- F_ev, R2_ev, RAI_ev, etc.
"""
import os
import csv
import logging
import argparse
from typing import List, Dict, Union, Any, Optional, Tuple
import sys
import glob
import re
import time
import threading
import concurrent.futures
from dataclasses import dataclass
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


@dataclass
class UploadResult:
    """Class to track upload results"""

    index: int
    image_file: str
    hand: Optional[str]
    media_id: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    attempts: int = 0


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
                        elif key == "stack_depth" and "_" in value:
                            value = value.split("_")[
                                0
                            ]  # Handle stack depth format like "20_30" to just "20"
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
        if (
            file.lower().endswith((".png", ".jpg", ".jpeg"))
            and "metadata" not in file.lower()
        ):
            image_files.append(os.path.join(directory, file))
    return sorted(image_files)


def parse_action_name_from_column(column_name: str) -> Optional[str]:
    """
    Parse action name from CSV column header

    Args:
        column_name: Column name like "F_score", "R2_score", "RAI_score", "F_ev", "R2_ev", etc.

    Returns:
        Human-readable action name or None if not an action column
    """
    # Support both _score and _ev column formats
    if column_name.endswith("_score"):
        action_code = column_name.replace("_score", "")
    elif column_name.endswith("_ev"):
        action_code = column_name.replace("_ev", "")
    else:
        return None

    # Map action codes to display names
    if action_code == "F":
        return "Fold"
    elif action_code == "RAI":
        return "All In"
    elif action_code.startswith("R"):
        # Extract raise amount, handle various formats like R2, R2.6, R10, R15
        raise_amount = action_code[1:]  # Remove 'R' prefix
        if raise_amount.replace(".", "").isdigit():
            if "." in raise_amount:
                return f"Raise {raise_amount}BBs"
            else:
                return f"Raise {raise_amount}BBs"

    return None


def get_available_actions_from_file(
    actions_file: str,
) -> Tuple[List[str], Dict[str, str], str]:
    """
    Extract available actions from actions.csv file header

    Args:
        actions_file: Path to actions.csv file

    Returns:
        Tuple of (action_names, column_mapping, score_suffix) where:
        - action_names: List of human-readable action names
        - column_mapping: Maps action names to column prefixes
        - score_suffix: The suffix used for score columns ("_score" or "_ev")
    """
    if not os.path.exists(actions_file):
        # Return default if file doesn't exist
        return (
            ["Fold", "Raise 2.6BBs", "All In"],
            {"Fold": "F", "Raise 2.6BBs": "R2.6", "All In": "RAI"},
            "_score",
        )

    try:
        with open(actions_file, "r") as f:
            reader = csv.reader(f)
            header = next(reader)  # Read just the header

        action_names = []
        column_mapping = {}
        score_suffix = "_score"  # Default

        # First, determine what suffix is being used - prefer _score over _ev
        if any(col.endswith("_score") for col in header):
            score_suffix = "_score"
        elif any(col.endswith("_ev") for col in header):
            score_suffix = "_ev"

        # Only process columns with the chosen suffix to avoid duplicates
        for column in header:
            if column.endswith(score_suffix):
                action_name = parse_action_name_from_column(column)
                if action_name and action_name not in action_names:  # Avoid duplicates
                    action_names.append(action_name)
                    # Store the column prefix for later use
                    column_prefix = column.replace(score_suffix, "")
                    column_mapping[action_name] = column_prefix

        if not action_names:
            # Fallback to defaults if no actions found
            logger.warning(f"No action columns found in {actions_file}, using defaults")
            return (
                ["Fold", "Raise 2.6BBs", "All In"],
                {"Fold": "F", "Raise 2.6BBs": "R2.6", "All In": "RAI"},
                "_score",
            )

        logger.info(
            f"Found {len(action_names)} actions: {action_names} (using {score_suffix} columns)"
        )
        return action_names, column_mapping, score_suffix

    except Exception as e:
        logger.error(f"Error reading actions file header {actions_file}: {str(e)}")
        # Return defaults on error
        return (
            ["Fold", "Raise 2.6BBs", "All In"],
            {"Fold": "F", "Raise 2.6BBs": "R2.6", "All In": "RAI"},
            "_score",
        )


def read_actions_file(
    directory: str,
) -> Tuple[Dict[str, Dict[str, int]], List[str], Dict[str, str]]:
    """
    Read actions.csv file and extract hand-specific scores and available actions

    Args:
        directory: Directory containing actions.csv file

    Returns:
        Tuple of (actions_data, available_actions, column_mapping)
    """
    actions_file = os.path.join(directory, "actions.csv")
    actions_data = {}

    # First, get the available actions from the file header
    available_actions, column_mapping, score_suffix = get_available_actions_from_file(
        actions_file
    )

    if not os.path.exists(actions_file):
        logger.warning(f"No actions.csv file found in {directory}")
        return actions_data, available_actions, column_mapping

    try:
        with open(actions_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                hand = row.get("hand", "")
                if not hand:
                    continue

                # Dynamically extract scores based on available actions
                hand_scores = {}
                for action_name, column_prefix in column_mapping.items():
                    score_column = f"{column_prefix}{score_suffix}"
                    score_value = row.get(score_column, 0)

                    # Handle both numeric scores and strategy percentages
                    if score_suffix == "_ev":
                        # For _ev columns, use the EV value directly and scale it for scoring
                        # Convert EV to a score (multiply by 100 and round)
                        score = round(float(score_value) * 100) if score_value else 0
                    else:
                        # For _score columns, use as-is
                        score = round(float(score_value)) if score_value else 0

                    hand_scores[action_name] = score

                # Also store best action and other metadata
                hand_scores["best_action"] = row.get("best_action", "")
                actions_data[hand] = hand_scores

        logger.info(
            f"Read actions data for {len(actions_data)} hands with {len(available_actions)} actions"
        )
        return actions_data, available_actions, column_mapping
    except Exception as e:
        logger.error(f"Error reading actions file {actions_file}: {str(e)}")
        return {}, available_actions, column_mapping


def parse_hand_from_filename(filename: str) -> Optional[str]:
    """
    Extract hand information from filename

    Args:
        filename: Image filename

    Returns:
        Hand description or None if not found
    """
    # Extract hand from filename pattern like "76o_F_0.000000.png" or "22_R15_0.108670.png"
    # Match either:
    # 1. Pocket pairs: two identical cards (22, 33, AA, etc.)
    # 2. Non-pairs: two different cards followed by 'o' or 's' (76o, AKs, etc.)
    match = re.search(
        r"(([2-9TJQKA])\2|[2-9TJQKA]{2}[os])_", os.path.basename(filename)
    )
    if match:
        hand = match.group(1)
        return hand  # Return just the hand code, not a description
    return None


def upload_single_image_with_retry(
    creator: FlowPokerDrillCreator,
    image_file: str,
    index: int,
    max_retries: int = 3,
    lock: threading.Lock = None,
) -> UploadResult:
    """
    Upload a single image with retry logic

    Args:
        creator: FlowPokerDrillCreator instance
        image_file: Path to the image file
        index: Image index for tracking
        max_retries: Maximum number of retry attempts
        lock: Threading lock for thread-safe logging

    Returns:
        UploadResult object with upload status
    """
    result = UploadResult(
        index=index, image_file=image_file, hand=parse_hand_from_filename(image_file)
    )

    for attempt in range(max_retries):
        result.attempts = attempt + 1
        try:
            if lock:
                with lock:
                    if attempt == 0:
                        logger.info(
                            f"Uploading image {index}: {os.path.basename(image_file)}"
                        )
                    else:
                        logger.info(
                            f"Retry {attempt}/{max_retries-1} for image {index}: {os.path.basename(image_file)}"
                        )

            media_id = creator.upload_image(image_file)
            result.media_id = media_id
            result.success = True

            if lock:
                with lock:
                    logger.info(
                        f"Successfully uploaded image {index}, media_id: {media_id}, hand: {result.hand}"
                    )

            return result

        except Exception as e:
            result.error = str(e)
            if attempt < max_retries - 1:
                # Wait before retry with exponential backoff
                wait_time = (attempt + 1) * 2
                if lock:
                    with lock:
                        logger.warning(
                            f"Upload failed for image {index}, retrying in {wait_time}s: {str(e)[:100]}"
                        )
                time.sleep(wait_time)
            else:
                if lock:
                    with lock:
                        logger.error(
                            f"Failed to upload image {index} after {max_retries} attempts: {str(e)[:100]}"
                        )

    return result


def upload_images_parallel(
    creator: FlowPokerDrillCreator,
    image_files: List[str],
    max_workers: int = 5,
    max_retries: int = 3,
) -> Tuple[Dict[int, str], Dict[int, str], bool]:
    """
    Upload images in parallel with retry logic

    Args:
        creator: FlowPokerDrillCreator instance
        image_files: List of image file paths
        max_workers: Maximum number of parallel workers
        max_retries: Maximum retry attempts per image

    Returns:
        Tuple of (media_map, hand_map, success_flag)
    """
    num_images = len(image_files)
    logger.info(
        f"Starting parallel upload of {num_images} images with {max_workers} workers (max {max_retries} retries per image)"
    )

    media_map = {}
    hand_map = {}
    lock = threading.Lock()
    failed_uploads = []

    # Create a thread pool executor
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all upload tasks
        future_to_index = {}
        for i, image_file in enumerate(image_files, start=1):
            future = executor.submit(
                upload_single_image_with_retry,
                creator,
                image_file,
                i,
                max_retries,
                lock,
            )
            future_to_index[future] = i

        # Collect results as they complete
        completed = 0
        for future in concurrent.futures.as_completed(future_to_index):
            completed += 1
            try:
                result = future.result()

                if result.success:
                    media_map[result.index] = result.media_id
                    hand_map[result.index] = result.hand
                    with lock:
                        logger.info(
                            f"Progress: {completed}/{num_images} uploads completed"
                        )
                else:
                    failed_uploads.append(result)
                    with lock:
                        logger.error(
                            f"Upload failed permanently for image {result.index}: {result.image_file}"
                        )

            except Exception as e:
                index = future_to_index[future]
                with lock:
                    logger.error(f"Unexpected error processing image {index}: {str(e)}")
                failed_uploads.append(
                    UploadResult(
                        index=index,
                        image_file=(
                            image_files[index - 1]
                            if index <= len(image_files)
                            else "unknown"
                        ),
                        hand=None,
                        error=str(e),
                    )
                )

    # Report final results
    successful_uploads = len(media_map)
    logger.info(
        f"Upload completed: {successful_uploads}/{num_images} images successfully uploaded"
    )

    if failed_uploads:
        logger.error(f"Failed uploads: {len(failed_uploads)} images")
        for failed in failed_uploads:
            logger.error(
                f"  - Image {failed.index}: {os.path.basename(failed.image_file)} (attempts: {failed.attempts})"
            )

    # Return success flag - True if all images uploaded successfully
    all_successful = len(failed_uploads) == 0

    return media_map, hand_map, all_successful


def get_answer_scores_for_hand(
    hand: str, actions_data: Dict[str, Dict[str, int]], available_actions: List[str]
) -> List[Dict[str, Union[str, int]]]:
    """
    Get scores for a specific hand based on actions data

    Args:
        hand: Hand identifier (e.g., "52s", "K4o")
        actions_data: Actions data from actions.csv
        available_actions: List of available action names

    Returns:
        List of answer score objects
    """
    answer_scores = []

    for action_name in available_actions:
        if hand and actions_data and hand in actions_data:
            # Get the score for this hand and action
            score = actions_data[hand].get(action_name, 0)
        else:
            # Default score if hand not found
            score = 0

        answer_scores.append({"points": str(score), "text": action_name, "weight": 0})

    return answer_scores


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


def generate_drill_description(
    tags: Dict[str, str], hand_info: Optional[str] = None
) -> str:
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
            description_parts.append(
                f"Tournament has {field_size} entrants with {field_left}% remaining."
            )

    # Add hand info if available
    if hand_info:
        description_parts.append(hand_info)

    # Join all parts with spaces
    return " ".join(description_parts)


def get_answers_from_actions(
    available_actions: List[str],
) -> Tuple[List[str], List[Dict[str, Union[str, int]]]]:
    """
    Get answers for drill creation based on available actions

    Args:
        available_actions: List of available action names from actions.csv

    Returns:
        Tuple of (answers, answer_scores_template)
    """
    answers = available_actions.copy()
    answer_scores_template = []

    for action_name in available_actions:
        answer_scores_template.append(
            {
                "points": "0",  # Will be overridden per hand
                "text": action_name,
                "weight": 0,
            }
        )

    return answers, answer_scores_template


def process_scenario(
    metadata_file: str,
    creator: FlowPokerDrillCreator,
    max_workers: int = 5,
    upload_retries: int = 3,
) -> None:
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
    important_tags = {
        k: tags[k]
        for k in ["mode", "field_size", "position", "action", "stack_depth"]
        if k in tags
    }
    logger.info(f"Processing with tags: {important_tags}")

    # Find image files
    image_files = find_image_files(directory)
    if not image_files:
        logger.warning(f"No image files found in {directory}, skipping")
        return

    num_images = len(image_files)
    logger.info(f"Found {num_images} image files")

    # Read actions.csv for hand-specific scores and available actions
    actions_data, available_actions, column_mapping = read_actions_file(directory)

    # Get dynamic answers based on available actions from this folder
    answers, _ = get_answers_from_actions(available_actions)

    # Generate a general drill name and description for the whole scenario
    scenario_name = os.path.basename(os.path.dirname(directory))
    position = tags.get("position", "").upper()
    action_type = tags.get("action", "").upper()
    field_left = tags.get("field_left", "")
    mode = tags.get("mode", "").upper()
    stack_depth = tags.get("stack_depth", "")
    if stack_depth and "_" in stack_depth:
        stack_depth = stack_depth.split("_")[0]

    # Generate dynamic drill name based on field_left value
    if field_left and field_left.lower() == "final table":
        field_info = "Final Table"
    elif field_left and field_left.lower() == "3 tables":
        field_info = "3 Tables Left"
    elif field_left and field_left.lower() == "2 tables":
        field_info = "2 Tables Left"
    elif field_left and field_left.lower() == "bubble":
        field_info = "Bolha do ITM"
    else:
        # For numeric values, maintain the percentage format
        field_info = f"{field_left}% Field Left"

    name = f"{mode} | {position} | {action_type} | {stack_depth} BBs | {field_info}"
    description = f"Nesse treino, você irá aprender o range de RFI para o {position}, com {stack_depth} BBs de profundidade, no cenário de {field_info}."

    try:
        # Step 1: Create the drill
        logger.info(f"Creating drill: {name}")
        drill_id = creator.create_drill(name, description, answers, tags)
        creator.drill_id = drill_id

        # Step 2: Upload ALL images in parallel
        logger.info(f"Starting parallel upload of all {num_images} images...")

        # Upload images in parallel with retry logic
        media_map, hand_map, upload_success = upload_images_parallel(
            creator=creator,
            image_files=image_files,
            max_workers=max_workers,
            max_retries=upload_retries,
        )

        # Check if all uploads were successful
        if not upload_success:
            logger.error(
                "Not all images were uploaded successfully after retries. Cancelling drill creation."
            )
            return

        logger.info(f"All {len(media_map)} images uploaded successfully!")

        # Create a mapping from hands to media_ids for proper scoring
        hand_to_media_map = {}
        for index, media_id in media_map.items():
            hand = hand_map.get(index)
            if hand:
                hand_to_media_map[hand] = media_id
                logger.debug(f"Mapped hand {hand} to media_id {media_id}")

        logger.info(f"Created hand-to-media mapping for {len(hand_to_media_map)} hands")

        # Step 3: Finish the uploading process to prepare for scoring
        logger.info("All images uploaded. Finishing upload phase...")
        creator.finish_uploading()

        # Step 4: Get questions from the API - note that this might only return the first question
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
            logger.warning(
                "No question IDs returned, will use sequential IDs starting from 1"
            )
            question_ids = [i + 1 for i in range(num_images)]

        logger.info(
            f"Will score {num_images} questions with IDs: {question_ids[:5]}..."
        )
        if len(question_ids) > 5:
            logger.info(f"... and {len(question_ids) - 5} more question IDs")

        # Step 5: Score ALL images as questions, based on hand mapping
        logger.info("Starting to score all questions...")

        # Keep track of successful scores
        successful_scores = 0

        # Get all hands that have actions data, in sorted order for consistent processing
        hands_with_data = sorted(
            [hand for hand in hand_to_media_map.keys() if hand in actions_data]
        )
        hands_without_data = sorted(
            [hand for hand in hand_to_media_map.keys() if hand not in actions_data]
        )

        # Process hands with data first, then hands without data
        all_hands_to_process = hands_with_data + hands_without_data

        logger.info(
            f"Processing {len(hands_with_data)} hands with score data and {len(hands_without_data)} hands with default scores"
        )

        # Score each hand as a question
        for i, hand in enumerate(all_hands_to_process, start=1):
            try:
                # Get the question ID from our generated list
                question_id = question_ids[i - 1]

                # Get the media_id for this hand
                media_id = hand_to_media_map.get(hand)
                if not media_id:
                    logger.warning(f"No media_id found for hand {hand}, skipping")
                    continue

                # Get specific answer scores for this hand
                if hand in actions_data:
                    answer_scores = get_answer_scores_for_hand(
                        hand, actions_data, available_actions
                    )
                    logger.info(
                        f"Scoring question {i}/{num_images}, ID: {question_id}, media_id: {media_id}, hand: {hand}"
                    )
                    # Create dynamic score logging
                    score_info = ", ".join(
                        [
                            f"{score['text']}={score['points']}"
                            for score in answer_scores
                        ]
                    )
                    logger.info(f"Using scores for {hand}: {score_info}")
                else:
                    # Default scores if hand not found - use available actions
                    answer_scores = get_answer_scores_for_hand(
                        hand, {}, available_actions
                    )
                    logger.warning(
                        f"No score data found for {hand}, using default scores"
                    )

                # Score this question with retry logic
                max_retries = 3
                retry_delay = 30  # seconds
                success = False

                for retry in range(max_retries):
                    try:
                        if retry == 0:
                            logger.info(
                                f"Scoring question {i}/{num_images}, ID: {question_id}"
                            )
                        else:
                            logger.info(
                                f"Retry {retry}/{max_retries-1} for question {i}/{num_images}, ID: {question_id}"
                            )

                        creator.score_answer(
                            question_id=question_id,
                            media_id=media_id,
                            answers_scores=answer_scores,
                            tags=tags,
                            current=i,
                            total=num_images,  # Use the total number of images
                        )
                        success = True
                        successful_scores += 1
                        # Wait a bit to avoid overwhelming the server
                        time.sleep(5)
                        break
                    except Exception as e:
                        error_msg = str(e)
                        # Truncate very long error messages
                        if len(error_msg) > 100:
                            error_msg = error_msg[:100] + "..."

                        if retry < max_retries - 1:
                            logger.warning(f"Retry needed: {error_msg}")
                            logger.info(
                                f"Waiting {retry_delay} seconds before retrying..."
                            )
                            time.sleep(retry_delay)
                            from flow_auth import refresh_session

                            refresh_session()
                            retry_delay *= 2  # Exponential backoff
                        else:
                            logger.error(f"Failed to score question: {error_msg}")

                if not success:
                    logger.error(
                        f"Failed to score question after {max_retries} attempts"
                    )
                    logger.error(
                        "Fatal error during question scoring. Stopping drill creation."
                    )
                    return
            except Exception as e:
                logger.error(
                    f"Failed to process question {i} for hand {hand}: {str(e)}"
                )

        # Log summary of scoring results
        logger.info(
            f"Completed scoring: {successful_scores}/{num_images} questions successfully scored"
        )

        # If no questions were successfully scored, we might want to abort
        if successful_scores == 0:
            logger.error(
                "No questions were successfully scored! The drill may not be usable."
            )

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
                logger.info(
                    f"Successfully set wizard rules for {wizard_amount} questions"
                )
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
                logger.info(
                    f"Successfully created and promoted drill with ID: {drill_id}"
                )
                break
            except Exception as e:
                error_msg = str(e)
                if len(error_msg) > 100:
                    error_msg = error_msg[:100] + "..."

                if retry < max_promotion_retries - 1:
                    logger.warning(
                        f"Promotion failed (attempt {retry+1}/{max_promotion_retries}), will retry: {error_msg}"
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff with longer wait times
                elif retry == max_promotion_retries - 1:
                    logger.warning(
                        f"Failed to promote drill after {max_promotion_retries} attempts, but drill was created"
                    )
                    logger.warning(
                        f"Drill ID {drill_id} may need to be manually promoted in the Flow Poker interface"
                    )

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
    parser = argparse.ArgumentParser(
        description="Create drills from visualization scenarios"
    )
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
    parser.add_argument(
        "--max-workers",
        type=int,
        default=5,
        help="Maximum number of parallel workers for image uploads (default: 5)",
    )
    parser.add_argument(
        "--upload-retries",
        type=int,
        default=3,
        help="Maximum number of retry attempts per image upload (default: 3)",
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
            logger.info(
                f"Resuming from index {resume_index}, skipping {resume_index} earlier items"
            )
            metadata_files = metadata_files[resume_index:]
        else:
            logger.warning(f"Resume path not found in metadata files: {resume_path}")

    # Apply limit if specified
    if args.limit > 0 and args.limit < len(metadata_files):
        logger.info(f"Limiting to {args.limit} metadata files")
        metadata_files = metadata_files[: args.limit]

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
            process_scenario(
                metadata_file,
                creator,
                max_workers=args.max_workers,
                upload_retries=args.upload_retries,
            )
            processed_dirs.append(directory)

            # Add delay between scenario processing to avoid overwhelming the server
            if i < len(metadata_files) - 1 and args.delay > 0:
                logger.info(
                    f"Waiting {args.delay} seconds before processing next scenario..."
                )
                time.sleep(args.delay)
        except Exception as e:
            logger.error(f"Error processing scenario: {str(e)}")
            # Continue with next scenario

    logger.info("Batch creation completed")


if __name__ == "__main__":
    main()
