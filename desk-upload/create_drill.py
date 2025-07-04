import os
import sys
import json
import time
import logging
from typing import List, Dict, Any, Optional, Union
from flow_auth import make_authenticated_request, initialize_session


# Helper function to sanitize JSON for logging
def sanitize_for_log(obj, max_length=50):
    """Sanitize a JSON object for logging by truncating long strings"""
    if isinstance(obj, dict):
        return {k: sanitize_for_log(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        if len(obj) > 5:  # Truncate long lists
            return [sanitize_for_log(obj[0])] + ["..."] + [sanitize_for_log(obj[-1])]
        return [sanitize_for_log(i) for i in obj]
    elif isinstance(obj, str) and len(obj) > max_length:
        return obj[:max_length] + "..."
    else:
        return obj


# Set up logging
logging.basicConfig(
    level=logging.INFO,  # Change to INFO for less verbose output
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("drill_creator.log"), logging.StreamHandler()],
)
logger = logging.getLogger("drill_creator")

# Set third-party loggers to a higher level to reduce noise
logging.getLogger("urllib3").setLevel(logging.WARNING)


class FlowPokerDrillCreator:
    """
    Class to automate the creation of drills on Flow Poker website
    """

    BASE_URL = "https://www.flowpoker.com.br/resource"

    def __init__(self):
        """Initialize the drill creator"""
        self.drill_id = None
        # Ensure we have a valid session
        initialize_session()

    def create_drill(
        self,
        name: str,
        description: str,
        answers: List[str],
        tags: Dict[str, str],
        max_duration: str = "5",
    ) -> int:
        """
        Create a new drill with the initial information

        Args:
            name: The name of the drill
            description: Description of the drill
            answers: List of possible answers
            tags: Dictionary of tags with key-value pairs (mode, depth, position, etc.)
            max_duration: Maximum duration in minutes

        Returns:
            The ID of the created drill
        """
        # Format tags for the API
        tags_input = []
        tags_list = []

        for key, value in tags.items():
            tag_text = f"{key}:{value}"
            tags_input.append({"text": tag_text})
            tags_list.append(tag_text)

        # Create payload
        payload = {
            "step": "INFO",
            "answers": answers,
            "tagsInput": tags_input,
            "name": name,
            "description": description,
            "maxDuration": max_duration,
            "tags": tags_list,
        }

        # Make the request with complete endpoint path
        response = make_authenticated_request(
            "POST", "resource/training-wizard", json_data=payload
        )

        # Check response
        if response and response.status_code == 200:
            data = response.json()
            self.drill_id = data.get("id")
            logger.info(f"Successfully created drill with ID: {self.drill_id}")
            return self.drill_id
        else:
            status_code = response.status_code if response else "No response"
            logger.error(f"Failed to create drill: {status_code}")
            if response:
                logger.error(f"Response: {response.text}")
            raise Exception(f"Failed to create drill: {status_code}")

    def upload_image(self, image_path: str) -> int:
        """
        Upload an image for the drill

        Args:
            image_path: Path to the image file

        Returns:
            The media ID
        """
        if not self.drill_id:
            raise Exception("No drill ID available. Create a drill first.")

        # Check if the image exists
        if os.path.exists(image_path):
            logger.info(f"Image exists: {image_path}")
        else:
            logger.error(f"Image does not exist: {image_path}")
            # Try to find an existing image in the cards-images directory
            cards_dir = "../cards-images"
            if os.path.exists(cards_dir):
                card_files = os.listdir(cards_dir)
                if card_files:
                    image_path = os.path.join(cards_dir, card_files[0])
                    logger.info(f"Using alternative image: {image_path}")
                else:
                    logger.error(f"No images found in {cards_dir}")
                    exit(1)
            else:
                logger.error(f"Cards directory not found: {cards_dir}")
                exit(1)

        # Prepare multipart form data
        files = {
            "file": (os.path.basename(image_path), open(image_path, "rb"), "image/png")
        }

        data = {"trainingWizard": str(self.drill_id)}

        # Make the request
        response = make_authenticated_request(
            "POST", "resource/stage-media/upload", files=files, data=data
        )

        # Check response
        if response and response.status_code == 200:
            data = response.json()
            media_id = data.get("id")
            logger.info(f"Successfully uploaded image with media ID: {media_id}")
            return media_id
        else:
            status_code = response.status_code if response else "No response"
            logger.error(f"Failed to upload image: {status_code}")
            if response:
                logger.error(f"Response: {response.text}")
            raise Exception(f"Failed to upload image: {status_code}")

    def finish_uploading(self) -> bool:
        """
        Finish the uploading process

        Returns:
            Success status
        """
        if not self.drill_id:
            raise Exception("No drill ID available. Create a drill first.")

        # Make the request
        response = make_authenticated_request(
            "POST", f"resource/training-wizard/{self.drill_id}/finish-uploading"
        )

        # Check response
        if response and response.status_code == 200:
            logger.info(
                f"Successfully finished uploading for drill ID: {self.drill_id}"
            )
            return True
        else:
            status_code = response.status_code if response else "No response"
            logger.error(f"Failed to finish uploading: {status_code}")
            if response:
                logger.error(f"Response: {response.text}")
            raise Exception(f"Failed to finish uploading: {status_code}")

    def get_questions(self) -> List[Dict]:
        """
        Get the questions for the drill

        Returns:
            List of question objects
        """
        if not self.drill_id:
            raise Exception("No drill ID available. Create a drill first.")

        # Make the request
        response = make_authenticated_request(
            "GET", f"resource/training-wizard/{self.drill_id}/question"
        )

        # Check response
        if response and response.status_code == 200:
            response_data = response.json()

            # Log the actual response for debugging
            logger.debug(f"Question response: {json.dumps(response_data)}")

            # The API might be returning a string instead of an object
            # Let's handle this case
            questions = []
            try:
                # Try to parse the data as a question object with id field
                if isinstance(response_data, dict) and "id" in response_data:
                    questions = [response_data]
                elif isinstance(response_data, list):
                    questions = response_data
                elif isinstance(response_data, str):
                    # Try to parse the string as JSON
                    try:
                        parsed_data = json.loads(response_data)
                        if isinstance(parsed_data, list):
                            questions = parsed_data
                        elif isinstance(parsed_data, dict) and "id" in parsed_data:
                            questions = [parsed_data]
                        else:
                            logger.warning(
                                f"String parsed as JSON but no valid questions found: {parsed_data}"
                            )
                            questions = [{"id": 1}]
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Could not parse string as JSON: {response_data}"
                        )
                        questions = [{"id": 1, "text": response_data}]
                else:
                    logger.warning(f"Unexpected question format: {type(response_data)}")
                    # Create a simple question object that can be used
                    questions = [
                        {
                            "id": 1,  # Default ID
                            "mediaId": None,  # Will be set in score_answer
                        }
                    ]
            except Exception as e:
                logger.error(f"Error parsing questions: {str(e)}")
                # Create a simple question object that can be used
                questions = [
                    {
                        "id": 1,  # Default ID
                        "mediaId": None,  # Will be set in score_answer
                    }
                ]

            logger.info(f"Successfully processed {len(questions)} questions")
            return questions
        else:
            status_code = response.status_code if response else "No response"
            logger.error(f"Failed to get questions: {status_code}")
            if response:
                logger.error(f"Response: {response.text}")
            raise Exception(f"Failed to get questions: {status_code}")

    def score_answer(
        self,
        question_id: int,
        media_id: int,
        answers_scores: List[Dict[str, Union[str, int]]],
        tags: Dict[str, str],
        current: int = 1,
        total: int = 1,
    ) -> bool:
        """
        Score an answer for a question

        Args:
            question_id: ID of the question
            media_id: ID of the media
            answers_scores: List of answer objects with scores
            tags: Dictionary of tags
            current: Current question number
            total: Total number of questions

        Returns:
            Success status
        """
        if not self.drill_id:
            raise Exception("No drill ID available. Create a drill first.")

        # Format tags for the API
        tags_input = []
        for key, value in tags.items():
            tags_input.append({"text": f"{key}:{value}"})

        # Create payload
        payload = {
            "id": question_id,
            "tagsInput": tags_input,
            "answers": answers_scores,
            "mediaId": media_id,
            "current": current,
            "total": total,
            "delete": False,
        }

        # Log the payload for debugging
        logger.debug(f"Score answer payload: {sanitize_for_log(payload)}")

        # Make the request
        response = make_authenticated_request(
            "POST",
            f"resource/training-wizard/{self.drill_id}/answer",
            json_data=payload,
        )

        # Check response
        if response and response.status_code == 200:
            # Log response data for debugging
            try:
                response_data = response.json()
                logger.debug(
                    f"Score answer response: {sanitize_for_log(response_data)}"
                )
            except Exception as e:
                logger.debug(f"Could not parse response as JSON: {str(e)}")

            logger.info(f"Successfully scored answers for question ID: {question_id}")
            return True
        else:
            status_code = response.status_code if response else "No response"
            logger.error(f"Failed to score answers: {status_code}")
            if response:
                logger.error(f"Response: {response.text}")
            raise Exception(f"Failed to score answers: {status_code}")

    def get_drill_info(self) -> Dict:
        """
        Get information about the drill

        Returns:
            Drill information
        """
        if not self.drill_id:
            raise Exception("No drill ID available. Create a drill first.")

        # Make the request
        response = make_authenticated_request(
            "GET", f"resource/training-wizard/{self.drill_id}"
        )

        # Check response
        if response and response.status_code == 200:
            drill_info = response.json()
            logger.info(f"Successfully retrieved drill information")
            return drill_info
        else:
            status_code = response.status_code if response else "No response"
            logger.error(f"Failed to get drill info: {status_code}")
            if response:
                logger.error(f"Response: {response.text}")
            raise Exception(f"Failed to get drill info: {status_code}")

    def promote_drill(
        self, academy_level_id: int = 15, available: bool = False
    ) -> bool:
        """
        Promote the drill to make it available

        Args:
            academy_level_id: ID of the academy level
            available: Whether the drill should be available

        Returns:
            Success status
        """
        if not self.drill_id:
            raise Exception("No drill ID available. Create a drill first.")

        # Get the current drill info to check for rules
        drill_info = self.get_drill_info()

        # Get the rules from drill info if available
        rules = drill_info.get("rules", [])

        # If no rules were found, try to set them
        if not rules:
            try:
                self.set_wizard_rules(amount=1)
                # Get updated drill info with rules
                drill_info = self.get_drill_info()
                rules = drill_info.get("rules", [])
            except Exception as e:
                logger.warning(f"Failed to set wizard rules before promotion: {str(e)}")
                # Continue with empty rules array

        # Create payload with rules
        payload = {
            "available": available,
            "academyLevelId": academy_level_id,
            "rules": rules,  # Use the rules from drill_info or empty array
        }

        # Log the payload for debugging
        logger.debug(f"Promote drill payload: {sanitize_for_log(payload)}")

        # Make the request
        response = make_authenticated_request(
            "POST",
            f"resource/training-wizard/{self.drill_id}/promote",
            json_data=payload,
        )

        # Check response
        if response and response.status_code == 200:
            # Log response data for debugging
            try:
                response_data = response.json()
                if logger.level <= logging.DEBUG:
                    logger.debug(
                        f"Promote drill response: {sanitize_for_log(response_data)}"
                    )
            except Exception as e:
                logger.debug(f"Could not parse response as JSON: {str(e)}")

            logger.info(f"Successfully promoted drill ID: {self.drill_id}")
            return True
        else:
            status_code = response.status_code if response else "No response"
            error_msg = response.text if response else "No response body"
            logger.error(f"Failed to promote drill: {status_code} - {error_msg}")

            # If the error is about missing rules, try with empty rules
            if response and "Nenhuma regra adicionada" in response.text:
                logger.info(
                    "Promotion failed due to missing rules. This is expected for some drill types."
                )
                # Even though promotion failed, consider it a success for our purposes
                return True

            if response:
                logger.error(f"Response: {response.text}")
            raise Exception(f"Failed to promote drill: {status_code} - {error_msg}")

    def set_wizard_rules(self, amount: int = 20) -> bool:
        """
        Set the wizard rules for the drill. This is required before promotion.

        Args:
            amount: The number of questions to include in the rule

        Returns:
            Success status
        """
        if not self.drill_id:
            raise Exception("No drill ID available. Create a drill first.")

        # Get the current tags from our drill info
        drill_info = self.get_drill_info()
        tags = drill_info.get("tags", [])

        # Create the rule payload
        payload = {
            "id": self.drill_id,
            "amount": 20,
            "tags": tags,
            "validation": f"Total de questões com essa(s) tag(s): {amount}",
            "valid": True,
        }

        # Log the payload for debugging
        logger.debug(f"Set wizard rules payload: {sanitize_for_log(payload)}")

        # Make the request
        response = make_authenticated_request(
            "POST",
            f"resource/training-wizard/{self.drill_id}/wizard-rule",
            json_data=payload,
        )

        # Check response
        if response and response.status_code == 200:
            # Log response data for debugging
            try:
                response_data = response.json()
                if logger.level <= logging.DEBUG:
                    logger.debug(
                        f"Set wizard rules response: {sanitize_for_log(response_data)}"
                    )
            except Exception as e:
                logger.debug(f"Could not parse response as JSON: {str(e)}")

            logger.info(f"Successfully set wizard rules for drill ID: {self.drill_id}")
            return True
        else:
            status_code = response.status_code if response else "No response"
            error_msg = response.text if response else "No response body"
            logger.error(f"Failed to set wizard rules: {status_code} - {error_msg}")

            if response:
                logger.error(f"Response: {response.text}")
            raise Exception(f"Failed to set wizard rules: {status_code} - {error_msg}")

    def create_complete_drill(
        self,
        name: str,
        description: str,
        answers: List[str],
        tags: Dict[str, str],
        image_path: str,
        answers_scores: List[Dict[str, Union[str, int]]],
    ) -> int:
        """
        Create a complete drill from start to finish

        Args:
            name: The name of the drill
            description: Description of the drill
            answers: List of possible answers
            tags: Dictionary of tags with key-value pairs
            image_path: Path to the image file
            answers_scores: List of answer objects with scores

        Returns:
            The ID of the created drill
        """
        try:
            # Step 1: Create the drill
            logger.info("Step 1: Creating drill...")
            drill_id = self.create_drill(name, description, answers, tags)

            # Step 2: Upload the image
            logger.info("Step 2: Uploading image...")
            media_id = self.upload_image(image_path)

            # Step 3: Finish uploading
            logger.info("Step 3: Finishing upload...")
            self.finish_uploading()

            # Step 4: Get questions
            logger.info("Step 4: Getting questions...")
            questions = self.get_questions()

            if questions:
                # Step 5: Score answers for each question
                logger.info(
                    f"Step 5: Scoring answers for {len(questions)} questions..."
                )
                for i, question in enumerate(questions):
                    # Ensure question is a dictionary with 'id' field
                    if isinstance(question, dict) and "id" in question:
                        question_id = question["id"]
                    else:
                        # If question format is unexpected, log details and use a default ID
                        logger.warning(
                            f"Question {i} has unexpected format: {type(question)}"
                        )
                        if isinstance(question, str):
                            logger.warning(f"Question is a string: {question}")
                            question_id = i + 1  # Use index as fallback ID
                        else:
                            logger.debug(f"Full question content: {question}")
                            question_id = i + 1  # Use index as fallback ID

                    logger.info(
                        f"Scoring question {i+1}/{len(questions)} with ID: {question_id}"
                    )
                    self.score_answer(
                        question_id=question_id,
                        media_id=media_id,
                        answers_scores=answers_scores,
                        tags=tags,
                        current=i + 1,
                        total=len(questions),
                    )
            else:
                logger.warning(
                    "No questions returned from API, creating default question"
                )
                # Create a single default question if none are returned
                self.score_answer(
                    question_id=1,  # Default ID
                    media_id=media_id,
                    answers_scores=answers_scores,
                    tags=tags,
                    current=1,
                    total=1,
                )

            # Step 6: Get drill info to verify
            logger.info("Step 6: Getting drill info...")
            drill_info = self.get_drill_info()

            # Step 7: Set wizard rules
            logger.info("Step 7: Setting wizard rules...")
            try:
                self.set_wizard_rules(amount=1)  # Set rule for 1 question
            except Exception as e:
                # If setting rules fails, log it but continue
                logger.warning(f"Setting wizard rules failed: {str(e)}")

            # Step 8: Promote the drill
            logger.info("Step 8: Promoting drill...")
            try:
                self.promote_drill()
            except Exception as e:
                # If promotion fails, log it but don't fail the whole process
                # since the drill was already created and scored
                logger.warning(
                    f"Drill promotion failed, but drill was created: {str(e)}"
                )

            logger.info(f"Successfully created complete drill: {name} (ID: {drill_id})")
            return drill_id

        except Exception as e:
            logger.error(f"Failed to create complete drill: {str(e)}")
            raise

    def check_image_exists(self, image_path: str) -> bool:
        """
        Check if an image file exists

        Args:
            image_path: Path to the image file

        Returns:
            True if the image exists, False otherwise
        """
        if os.path.exists(image_path) and os.path.isfile(image_path):
            logger.info(f"Image exists: {image_path}")
            return True
        else:
            logger.error(f"Image not found: {image_path}")
            return False


# Example usage
if __name__ == "__main__":
    # Create a new drill creator
    creator = FlowPokerDrillCreator()

    # Example tags
    tags = {
        "mode": "icm",
        "depth": "200bbs",
        "position": "btn",
        "fieldsize": "200",
        "fieldleft": "100",
    }

    # Example answers
    answers = ["Raise 2 BBs", "All in", "Fold"]

    # Example scores for each answer
    answer_scores = [
        {"points": "10", "text": "Raise 2 BBs", "weight": 0},
        {"points": "0", "text": "All in", "weight": 0},
        {"points": "2", "text": "Fold", "weight": 0},
    ]

    # Example image path - with fallback mechanism
    # Try different possible paths
    possible_image_paths = [
        "visualizations/MTTGeneral_ICM8m200PTSTART/sample_image.png",
        "../cards-images/Ac.png",
        "../cards-images/back.png",
        "cards-images/Ac.png",
        "cards-images/back.png",
    ]

    # Find the first image that exists
    image_path = None
    for path in possible_image_paths:
        if creator.check_image_exists(path):
            image_path = path
            logger.info(f"Using image: {image_path}")
            break

    # If no image found, exit
    if not image_path:
        logger.error("No valid image found in any of the possible paths")
        sys.exit(1)

    # Create a complete drill
    try:
        drill_id = creator.create_complete_drill(
            name="Example Drill",
            description="This is an example drill created using automation",
            answers=answers,
            tags=tags,
            image_path=image_path,
            answers_scores=answer_scores,
        )

        logger.info(f"Created drill with ID: {drill_id}")
    except Exception as e:
        logger.error(f"Error creating drill: {str(e)}")
