import os
import re


def rename_card_images(directory="cards-images"):
    """
    Rename card images from format like 'ace_of_clubs.png' to 'Ac.png'
    """
    # Define the mappings
    rank_mapping = {
        "ace": "A",
        "king": "K",
        "queen": "Q",
        "jack": "J",
        "2": "2",
        "3": "3",
        "4": "4",
        "5": "5",
        "6": "6",
        "7": "7",
        "8": "8",
        "9": "9",
        "10": "T",  # Using T for 10 as is common in poker notation
    }

    suit_mapping = {"clubs": "c", "diamonds": "d", "hearts": "h", "spades": "s"}

    # Regular expression to extract rank and suit from filenames
    pattern = r"(ace|king|queen|jack|10|[2-9])_of_(clubs|diamonds|hearts|spades)\.png"

    renamed_count = 0
    errors = []

    # Get full path to the directory
    dir_path = os.path.abspath(directory)
    print(f"Scanning directory: {dir_path}")

    # List all files in the directory
    for filename in os.listdir(dir_path):
        if not filename.endswith(".png"):
            continue

        match = re.match(pattern, filename)
        if match:
            rank, suit = match.groups()
            new_name = f"{rank_mapping[rank]}{suit_mapping[suit]}.png"
            old_path = os.path.join(dir_path, filename)
            new_path = os.path.join(dir_path, new_name)

            try:
                if os.path.exists(new_path):
                    print(f"Warning: {new_name} already exists, skipping {filename}")
                else:
                    os.rename(old_path, new_path)
                    print(f"Renamed: {filename} → {new_name}")
                    renamed_count += 1
            except Exception as e:
                errors.append(f"Error renaming {filename}: {str(e)}")
        else:
            print(f"Skipping: {filename} (doesn't match expected pattern)")

    # Print summary
    print(f"\nSummary:")
    print(f"Total files renamed: {renamed_count}")
    if errors:
        print(f"Errors encountered: {len(errors)}")
        for error in errors:
            print(f"  - {error}")


if __name__ == "__main__":
    rename_card_images()
