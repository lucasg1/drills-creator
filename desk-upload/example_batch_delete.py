#!/usr/bin/env python
"""
Example script showing how to use the batch deletion functionality
"""

import subprocess
import sys


def run_batch_delete_example():
    """
    Example of how to use the batch deletion functionality
    """

    print("=== Flow Poker Batch Deletion Examples ===\n")

    print("1. Dry run with batch mode (test without actual deletion):")
    cmd1 = [
        "python",
        "delete_uploaded_images.py",
        "--ids",
        "10001",
        "10002",
        "10003",
        "--batch",
        "--dry-run",
    ]
    print(f"Command: {' '.join(cmd1)}")
    print(
        "This will show what would be deleted in batch mode without actually deleting anything.\n"
    )

    print("2. Delete a range using batch mode (fast):")
    cmd2 = [
        "python",
        "delete_uploaded_images.py",
        "--range",
        "10001",
        "10010",
        "--batch",
    ]
    print(f"Command: {' '.join(cmd2)}")
    print("This will delete questions 10001-10010 concurrently (all at once).\n")

    print("3. Delete from CSV using batch mode:")
    cmd3 = [
        "python",
        "delete_uploaded_images.py",
        "--csv",
        "question_ids.csv",
        "--batch",
    ]
    print(f"Command: {' '.join(cmd3)}")
    print("This will delete all question IDs from the CSV file concurrently.\n")

    print("4. Sequential mode with delay (slower but more conservative):")
    cmd4 = [
        "python",
        "delete_uploaded_images.py",
        "--range",
        "10001",
        "10010",
        "--delay",
        "0.5",
    ]
    print(f"Command: {' '.join(cmd4)}")
    print("This will delete questions one by one with 0.5 second delay between each.\n")

    print("Performance comparison:")
    print("- Batch mode: ~10 deletions in 5-10 seconds")
    print("- Sequential mode: ~10 deletions in 10+ seconds (depending on delay)")
    print(
        "\nRecommendation: Use batch mode for 10+ deletions, sequential for smaller batches."
    )

    # Ask user if they want to run a test
    choice = input("\nWould you like to run a dry-run test with batch mode? (y/n): ")
    if choice.lower() in ["y", "yes"]:
        print("\nRunning dry-run test...")
        try:
            result = subprocess.run(cmd1, capture_output=True, text=True)
            print("STDOUT:")
            print(result.stdout)
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
        except Exception as e:
            print(f"Error running command: {e}")


if __name__ == "__main__":
    run_batch_delete_example()
