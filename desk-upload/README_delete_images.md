# Flow Poker Image Deletion Script

This script allows you to delete wrongly uploaded images/questions from the Flow Poker platform using the API with proper authentication.

## Features

- Automatic authentication using Flow Poker credentials
- Delete individual question IDs
- Delete ranges of question IDs
- Delete question IDs from a CSV file
- **Batch mode for concurrent deletions (much faster)**
- Dry run mode for testing
- Detailed logging and result reporting
- Configurable delays between deletions (sequential mode only)
- Results export to CSV
- Performance timing and statistics

## Installation

Make sure you have the required dependencies and the `flow_auth.py` module:

```bash
pip install requests aiohttp
```

Ensure that `flow_auth.py` is in the same directory as the deletion script.

## Authentication

The script automatically handles authentication using the Flow Poker credentials configured in `flow_auth.py`. No manual authentication setup is required.

## Usage

### Batch Mode (Recommended for Large Deletions)

For faster deletions, use the `--batch` flag to send all delete requests concurrently:

```bash
# Delete a range using batch mode (much faster)
python delete_uploaded_images.py --range 10699 10720 --batch

# Delete specific IDs using batch mode
python delete_uploaded_images.py --ids 10699 10700 10701 10705 --batch

# Delete from CSV using batch mode
python delete_uploaded_images.py --csv question_ids.csv --batch
```

### Sequential Mode (Default)

#### Delete a Range of Question IDs

```bash
python delete_uploaded_images.py --range 10699 10720
```

This will delete questions with IDs from 10699 to 10720 (inclusive).

#### Delete Specific Question IDs

```bash
python delete_uploaded_images.py --ids 10699 10700 10701 10705
```

This will delete only the specified question IDs.

#### Delete from CSV File

```bash
python delete_uploaded_images.py --csv question_ids.csv
```

The CSV file should have a column named `question_id` (or `id`, `Question ID`, `ID`). See `example_question_ids.csv` for the format.

### Advanced Options

```bash
python delete_uploaded_images.py --range 10699 10720 --delay 2.0 --output my_results.csv
```

- `--delay`: Time to wait between deletions (default: 1.0 seconds)
- `--output`: File to save deletion results (default: deletion_results.csv)
- `--dry-run`: Simulate deletions without actually deleting

### Dry Run Mode

Test your deletion command without actually deleting anything:

```bash
python delete_uploaded_images.py --range 10699 10720 --dry-run
```

## Examples

### Example 1: Delete a small range with confirmation

```bash
python delete_uploaded_images.py --range 10699 10705
```

### Example 2: Delete specific IDs with custom delay

```bash
python delete_uploaded_images.py --ids 10699 10700 10701 --delay 2.5
```

### Example 3: Bulk delete from CSV with custom output

```bash
python delete_uploaded_images.py --csv failed_uploads.csv --output cleanup_results.csv
```

### Example 4: Test before actual deletion

```bash
python delete_uploaded_images.py --csv question_ids.csv --dry-run
```

## CSV File Format

Your CSV file should contain question IDs in one of these column formats:

```csv
question_id
10699
10700
10701
```

Or:

```csv
id,description
10699,Wrong upload batch 1
10700,Wrong upload batch 1
10701,Wrong upload batch 1
```

## Output

The script will:

1. Log all operations to `delete_uploaded_images.log`
2. Show progress in the console
3. Save detailed results to a CSV file (default: `deletion_results.csv`)
4. Display a summary of successful and failed deletions

## Error Handling

The script handles various error conditions:

- **404 Not Found**: Question ID doesn't exist
- **403 Forbidden**: Access denied (check authentication)
- **401 Unauthorized**: Authentication required
- **Network errors**: Connection issues
- **Invalid data**: Malformed CSV files or invalid IDs

## Safety Features

- **Confirmation prompt**: For bulk deletions (more than 5 items)
- **Dry run mode**: Test without actual deletions
- **Detailed logging**: Track all operations
- **Rate limiting**: Configurable delays between deletions
- **Error recovery**: Continue processing even if some deletions fail

## Logs and Results

- **Log file**: `delete_uploaded_images.log` - Detailed operation log
- **Results file**: `deletion_results.csv` - Structured results for analysis

## Notes

- The script uses the same API endpoint pattern as shown in the browser developer tools
- Ensure you have proper permissions to delete questions
- Use reasonable delays to avoid overwhelming the server
- Always test with dry run mode first for bulk operations
- Keep backups of important data before deletion

## Troubleshooting

### Authentication Issues

The script uses the authentication system from `flow_auth.py`:

1. Ensure `flow_auth.py` is in the same directory
2. The script will automatically handle login and session management
3. If you get 401/403 errors, check that the credentials in `flow_auth.py` are correct

### Rate Limiting

If you get rate limited:

1. Increase the `--delay` parameter
2. Process in smaller batches
3. Contact Flow Poker support for guidance

### Network Issues

If you encounter connection problems:

1. Check your internet connection
2. Check the Flow Poker website is accessible
3. Try with smaller batches first

## Performance Comparison

### Batch Mode vs Sequential Mode

The script offers two modes of operation:

**Batch Mode (`--batch`)**:

- Sends all delete requests concurrently using async HTTP
- Much faster for large numbers of deletions
- Recommended for deleting 10+ items
- Example: 100 deletions might take 5-10 seconds

**Sequential Mode (default)**:

- Sends delete requests one by one
- Slower but more conservative approach
- Includes configurable delays between requests
- Example: 100 deletions with 1s delay takes ~100 seconds

### Performance Example

```bash
# Fast: Delete 50 questions in batch mode (~5-10 seconds)
python delete_uploaded_images.py --range 10000 10050 --batch

# Slow: Delete 50 questions sequentially with 1s delay (~50 seconds)
python delete_uploaded_images.py --range 10000 10050 --delay 1.0
```

### When to Use Each Mode

- **Use Batch Mode** for:

  - Large number of deletions (10+)
  - When you need fast execution
  - Cleaning up bulk upload mistakes

- **Use Sequential Mode** for:
  - Small number of deletions (< 10)
  - When you want to be more conservative
  - When server might be under load
