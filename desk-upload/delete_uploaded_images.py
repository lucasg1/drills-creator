#!/usr/bin/env python
"""
Script to delete wrongly uploaded images/questions from Flow Poker platform.
This script can be used to clean up failed or incorrect uploads.
"""

import os
import csv
import logging
import argparse
import time
import json
import asyncio
import aiohttp
from typing import List, Dict, Optional, Union
import sys
from dataclasses import dataclass
from flow_auth import make_authenticated_request, session_cookies

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("delete_uploaded_images.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("delete_uploaded_images")


@dataclass
class DeletionResult:
    """Class to track deletion results"""

    question_id: int
    success: bool = False
    error: Optional[str] = None
    status_code: Optional[int] = None


class FlowPokerImageDeleter:
    """Class to handle deletion of images/questions from Flow Poker platform"""

    def __init__(self):
        """Initialize the deleter - authentication is handled by flow_auth module"""
        logger.info("Initialized Flow Poker Image Deleter with authentication")

    def delete_question(self, question_id: int) -> DeletionResult:
        """
        Delete a single question/image by ID

        Args:
            question_id: The ID of the question to delete

        Returns:
            DeletionResult object with deletion status
        """
        result = DeletionResult(question_id=question_id)

        try:
            endpoint = f"resource/question/{question_id}"
            logger.info(f"Attempting to delete question ID: {question_id}")

            response = make_authenticated_request("DELETE", endpoint)

            if response is None:
                result.error = "Request failed - no response received"
                logger.error(f"No response received for question ID {question_id}")
                return result

            result.status_code = response.status_code

            if response.status_code == 200:
                result.success = True
                logger.info(f"Successfully deleted question ID: {question_id}")
            elif response.status_code == 404:
                result.error = "Question not found"
                logger.warning(f"Question ID {question_id} not found (404)")
            elif response.status_code == 403:
                result.error = "Access forbidden - check authentication"
                logger.error(f"Access forbidden for question ID {question_id} (403)")
            elif response.status_code == 401:
                result.error = "Unauthorized - authentication required"
                logger.error(f"Unauthorized access for question ID {question_id} (401)")
            else:
                result.error = f"HTTP {response.status_code}: {response.text[:100]}"
                logger.error(
                    f"Failed to delete question ID {question_id}: {result.error}"
                )

        except Exception as e:
            result.error = f"Unexpected error: {str(e)}"
            logger.error(
                f"Unexpected error deleting question ID {question_id}: {result.error}"
            )

        return result

    async def delete_question_async(
        self, session: aiohttp.ClientSession, question_id: int
    ) -> DeletionResult:
        """
        Delete a single question/image by ID asynchronously

        Args:
            session: aiohttp session for making requests
            question_id: The ID of the question to delete

        Returns:
            DeletionResult object with deletion status
        """
        result = DeletionResult(question_id=question_id)

        try:
            base_url = "https://www.flowpoker.com.br"
            endpoint = f"resource/question/{question_id}"
            full_url = f"{base_url}/{endpoint}"

            # Prepare headers (similar to flow_auth.py)
            headers = {
                "host": "www.flowpoker.com.br",
                "connection": "keep-alive",
                "sec-ch-ua-platform": '"Windows"',
                "authorization": "Basic THVjYXMgcHJvZ3JhbWFkb3I6THVjYXMgcHJvZ3JhbWFkb3I=",
                "x-requested-with": "XMLHttpRequest",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
                "accept": "application/json, text/plain, */*",
                "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
                "sec-ch-ua-mobile": "?0",
                "sec-fetch-site": "same-origin",
                "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty",
                "referer": "https://www.flowpoker.com.br/desk/",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7,fr;q=0.6,es;q=0.5",
            }

            # Add cookies from session_cookies
            cookies = {}
            if session_cookies.get("JSESSIONID"):
                cookies["JSESSIONID"] = session_cookies["JSESSIONID"]

            logger.info(f"Attempting to delete question ID: {question_id} (async)")

            async with session.delete(
                full_url, headers=headers, cookies=cookies, ssl=False
            ) as response:
                result.status_code = response.status

                if response.status == 200:
                    result.success = True
                    logger.info(f"Successfully deleted question ID: {question_id}")
                elif response.status == 404:
                    result.error = "Question not found"
                    logger.warning(f"Question ID {question_id} not found (404)")
                elif response.status == 403:
                    result.error = "Access forbidden - check authentication"
                    logger.error(
                        f"Access forbidden for question ID {question_id} (403)"
                    )
                elif response.status == 401:
                    result.error = "Unauthorized - authentication required"
                    logger.error(
                        f"Unauthorized access for question ID {question_id} (401)"
                    )
                else:
                    response_text = await response.text()
                    result.error = f"HTTP {response.status}: {response_text[:100]}"
                    logger.error(
                        f"Failed to delete question ID {question_id}: {result.error}"
                    )

        except Exception as e:
            result.error = f"Unexpected error: {str(e)}"
            logger.error(
                f"Unexpected error deleting question ID {question_id}: {result.error}"
            )

        return result

    def delete_questions_batch(self, question_ids: List[int]) -> List[DeletionResult]:
        """
        Delete questions in batch mode (synchronous wrapper for async method)

        Args:
            question_ids: List of question IDs to delete

        Returns:
            List of DeletionResult objects
        """
        return asyncio.run(self.delete_questions_batch_async(question_ids))

    async def delete_questions_batch_async(
        self, question_ids: List[int]
    ) -> List[DeletionResult]:
        """
        Delete multiple questions asynchronously in batch

        Args:
            question_ids: List of question IDs to delete

        Returns:
            List of DeletionResult objects
        """
        logger.info(f"Starting async batch deletion of {len(question_ids)} questions")

        # Create SSL context that allows unverified certificates
        connector = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=300)  # 5 minutes total timeout

        async with aiohttp.ClientSession(
            connector=connector, timeout=timeout
        ) as session:
            # Create tasks for all deletions
            tasks = [self.delete_question_async(session, qid) for qid in question_ids]

            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle any exceptions that occurred
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # Create a failure result for exceptions
                    error_result = DeletionResult(
                        question_id=question_ids[i],
                        success=False,
                        error=f"Task exception: {str(result)}",
                    )
                    final_results.append(error_result)
                    logger.error(
                        f"Task exception for question ID {question_ids[i]}: {result}"
                    )
                else:
                    final_results.append(result)

            logger.info(
                f"Completed async batch deletion of {len(question_ids)} questions"
            )
            return final_results

    def delete_question_range(
        self, start_id: int, end_id: int, delay: float = 1.0
    ) -> List[DeletionResult]:
        """
        Delete a range of questions

        Args:
            start_id: Starting question ID
            end_id: Ending question ID (inclusive)
            delay: Delay between deletions in seconds

        Returns:
            List of DeletionResult objects
        """
        results = []
        total_questions = end_id - start_id + 1

        logger.info(
            f"Starting deletion of question range: {start_id} to {end_id} ({total_questions} questions)"
        )

        for i, question_id in enumerate(range(start_id, end_id + 1), 1):
            result = self.delete_question(question_id)
            results.append(result)

            logger.info(f"Progress: {i}/{total_questions} deletions attempted")

            # Add delay between deletions to avoid overwhelming the server
            if i < total_questions and delay > 0:
                time.sleep(delay)

        return results

    def delete_questions_from_list(
        self, question_ids: List[int], delay: float = 1.0
    ) -> List[DeletionResult]:
        """
        Delete questions from a list of IDs

        Args:
            question_ids: List of question IDs to delete
            delay: Delay between deletions in seconds

        Returns:
            List of DeletionResult objects
        """
        results = []
        total_questions = len(question_ids)

        logger.info(f"Starting deletion of {total_questions} questions from list")

        for i, question_id in enumerate(question_ids, 1):
            result = self.delete_question(question_id)
            results.append(result)

            logger.info(f"Progress: {i}/{total_questions} deletions attempted")

            # Add delay between deletions to avoid overwhelming the server
            if i < total_questions and delay > 0:
                time.sleep(delay)

        return results


def read_question_ids_from_csv(csv_file: str) -> List[int]:
    """
    Read question IDs from a CSV file

    Args:
        csv_file: Path to CSV file containing question IDs

    Returns:
        List of question IDs
    """
    question_ids = []

    try:
        with open(csv_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Try different possible column names
                question_id = None
                for col in ["question_id", "id", "Question ID", "ID"]:
                    if col in row and row[col]:
                        try:
                            question_id = int(row[col])
                            break
                        except ValueError:
                            continue

                if question_id:
                    question_ids.append(question_id)
                else:
                    logger.warning(f"Could not find question ID in row: {row}")

        logger.info(f"Read {len(question_ids)} question IDs from {csv_file}")
        return question_ids

    except Exception as e:
        logger.error(f"Error reading CSV file {csv_file}: {str(e)}")
        return []


def save_deletion_results(results: List[DeletionResult], output_file: str):
    """
    Save deletion results to a CSV file

    Args:
        results: List of DeletionResult objects
        output_file: Path to output CSV file
    """
    try:
        with open(output_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Question ID", "Success", "Status Code", "Error"])

            for result in results:
                writer.writerow(
                    [
                        result.question_id,
                        result.success,
                        result.status_code or "",
                        result.error or "",
                    ]
                )

        logger.info(f"Deletion results saved to {output_file}")

    except Exception as e:
        logger.error(f"Error saving results to {output_file}: {str(e)}")


def print_deletion_summary(
    results: List[DeletionResult], execution_time: float, batch_mode: bool
):
    """
    Print a summary of deletion results

    Args:
        results: List of DeletionResult objects
        execution_time: Time taken to execute deletions in seconds
        batch_mode: Whether batch mode was used
    """
    total = len(results)
    successful = sum(1 for r in results if r.success)
    failed = total - successful

    logger.info("=" * 50)
    logger.info("DELETION SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total questions processed: {total}")
    logger.info(f"Successfully deleted: {successful}")
    logger.info(f"Failed deletions: {failed}")
    logger.info(f"Execution time: {execution_time:.2f} seconds")
    logger.info(f"Mode: {'Batch (concurrent)' if batch_mode else 'Sequential'}")
    if total > 0:
        logger.info(f"Average time per deletion: {execution_time/total:.2f} seconds")

    if failed > 0:
        logger.info("\nFailed deletions by error type:")
        error_counts = {}
        for result in results:
            if not result.success and result.error:
                error_type = result.error.split(":")[0]  # Get first part of error
                error_counts[error_type] = error_counts.get(error_type, 0) + 1

        for error_type, count in error_counts.items():
            logger.info(f"  {error_type}: {count}")

    logger.info("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description="Delete wrongly uploaded images/questions from Flow Poker platform. Use --batch for faster concurrent deletions."
    )

    # Mutually exclusive group for different deletion modes
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--range",
        nargs=2,
        type=int,
        metavar=("START", "END"),
        help="Delete a range of question IDs (e.g., --range 10699 10720)",
    )
    group.add_argument(
        "--ids",
        nargs="+",
        type=int,
        help="Delete specific question IDs (e.g., --ids 10699 10700 10701)",
    )
    group.add_argument("--csv", type=str, help="Delete question IDs from a CSV file")

    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between deletions in seconds (default: 1.0) - only used in sequential mode",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="deletion_results.csv",
        help="Output file for deletion results (default: deletion_results.csv)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Use batch mode to send all delete requests concurrently (faster)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate deletions without actually deleting (for testing)",
    )

    args = parser.parse_args()

    # Create deleter instance
    deleter = FlowPokerImageDeleter()

    # Determine which deletion mode to use
    question_ids = []

    if args.range:
        start_id, end_id = args.range
        if start_id > end_id:
            logger.error("Start ID must be less than or equal to end ID")
            return
        question_ids = list(range(start_id, end_id + 1))
        logger.info(
            f"Will delete question range: {start_id} to {end_id} ({len(question_ids)} questions)"
        )

    elif args.ids:
        question_ids = args.ids
        logger.info(f"Will delete {len(question_ids)} specific question IDs")

    elif args.csv:
        if not os.path.exists(args.csv):
            logger.error(f"CSV file not found: {args.csv}")
            return
        question_ids = read_question_ids_from_csv(args.csv)
        if not question_ids:
            logger.error("No valid question IDs found in CSV file")
            return

    if not question_ids:
        logger.error("No question IDs to delete")
        return

    # Show what will be deleted
    logger.info(
        f"Question IDs to delete: {question_ids[:10]}{'...' if len(question_ids) > 10 else ''}"
    )

    if args.dry_run:
        logger.info("DRY RUN MODE - No actual deletions will be performed")
        if args.batch:
            logger.info(
                f"Would delete {len(question_ids)} questions in batch mode (all at once)"
            )
        else:
            logger.info(
                f"Would delete {len(question_ids)} questions sequentially with {args.delay}s delay"
            )
        return

    # Confirm before proceeding
    if len(question_ids) > 5:
        mode_str = (
            "batch mode (all at once)"
            if args.batch
            else f"sequential mode with {args.delay}s delay"
        )
        confirmation = input(
            f"Are you sure you want to delete {len(question_ids)} questions using {mode_str}? (yes/no): "
        )
        if confirmation.lower() not in ["yes", "y"]:
            logger.info("Deletion cancelled by user")
            return

    # Perform deletions
    start_time = time.time()
    if args.batch:
        logger.info("Using batch mode - sending all delete requests concurrently")
        results = deleter.delete_questions_batch(question_ids)
    else:
        logger.info("Using sequential mode - sending delete requests one by one")
        results = deleter.delete_questions_from_list(question_ids, delay=args.delay)
    end_time = time.time()

    # Save results
    save_deletion_results(results, args.output)

    # Print summary
    print_deletion_summary(results, end_time - start_time, args.batch)


if __name__ == "__main__":
    main()
