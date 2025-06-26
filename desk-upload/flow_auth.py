"""
Authentication module for Flow Poker API interactions
"""

import json
import logging
import requests
from urllib3.exceptions import InsecureRequestWarning
from requests.exceptions import ConnectionError, Timeout, RequestException
from ssl import SSLError

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG for more verbose output
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("flow_auth.log"), logging.StreamHandler()],
)
logger = logging.getLogger("flow_auth")

# Suppress only the specific InsecureRequestWarning when we need to disable verification
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Initialize session cookies
session_cookies = {}


def pretty_print_response(response):
    """Format and print response data in a readable way"""
    logger.debug(f"Status Code: {response.status_code}")
    logger.debug("Headers:")
    for key, value in response.headers.items():
        logger.debug(f"  {key}: {value}")
    logger.debug("\nContent:")
    try:
        # Try to parse as JSON
        content = response.json()
        logger.debug(json.dumps(content, indent=2))
    except json.JSONDecodeError:
        # If not valid JSON, print text
        logger.debug(response.text)


def make_flowpoker_request(
    method,
    endpoint,
    custom_headers=None,
    json_data=None,
    disable_ssl_verify=False,
    cookies=None,
    files=None,
    data=None,
):
    """Make a request to the FLOW Poker API with error handling

    Args:
        method (str): HTTP method (GET, POST, etc.)
        endpoint (str): API endpoint to call (without the base URL)
        custom_headers (dict, optional): Additional headers to include
        json_data (dict, optional): JSON data to send in the request body
        disable_ssl_verify (bool, optional): Set to True to disable SSL verification
        cookies (dict, optional): Cookies to include in the request
        files (dict, optional): Files to upload
        data (dict, optional): Form data to send

    Returns:
        requests.Response or None: The response object or None if request failed
    """
    base_url = "https://www.flowpoker.com.br"

    # Remove any double slashes if endpoint already has "resource/"
    if endpoint.startswith("resource/"):
        full_url = f"{base_url}/{endpoint}"
    else:
        full_url = f"{base_url}/{endpoint}"

    logger.debug(f"Making {method} request to: {full_url}")

    # Start with base headers
    req_headers = {
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

    # Add any custom headers
    if custom_headers:
        req_headers.update(custom_headers)

    # Add content-type for JSON data
    if json_data:
        req_headers["content-type"] = "application/json;charset=UTF-8"

    logger.debug(f"Request headers: {req_headers}")
    if json_data:
        logger.debug(f"JSON data: {json.dumps(json_data)}")

    try:
        session = requests.Session()
        if cookies:
            for key, value in cookies.items():
                session.cookies.set(key, value)

        response = session.request(
            method=method,
            url=full_url,
            headers=req_headers,
            json=json_data,
            verify=not disable_ssl_verify,
            timeout=30,  # Increased timeout
            files=files,
            data=data,
        )

        logger.debug(f"Response status: {response.status_code}")
        if response.status_code >= 400:
            logger.debug(f"Error response: {response.text}")

        return response
    except SSLError as e:
        logger.error(f"SSL Error: {e}")
        if not disable_ssl_verify:
            logger.info("Trying again with SSL verification disabled...")
            return make_flowpoker_request(
                method, endpoint, custom_headers, json_data, True, cookies, files, data
            )
        return None
    except (ConnectionError, Timeout) as e:
        logger.error(f"Connection or Timeout Error: {e}")
        return None
    except RequestException as e:
        logger.error(f"Request Error: {e}")
        return None


def refresh_session():
    """Logs in and refreshes the JSESSIONID cookie"""
    global session_cookies
    login_response = make_flowpoker_request(
        "GET", "resource/login", disable_ssl_verify=True
    )
    if login_response:
        jsessionid = login_response.cookies.get("JSESSIONID")
        if jsessionid:
            session_cookies["JSESSIONID"] = jsessionid
            logger.info(f"New JSESSIONID obtained: {jsessionid}")
            return True
        else:
            logger.error("No JSESSIONID found in login response.")
    return False


def make_authenticated_request(method, endpoint, json_data=None, files=None, data=None):
    """Make an authenticated request using the stored JSESSIONID"""
    global session_cookies

    if not session_cookies.get("JSESSIONID"):
        logger.info("No JSESSIONID available, trying login...")
        if not refresh_session():
            logger.error("Login failed. Cannot proceed.")
            return None

    # Add content-type header for JSON
    custom_headers = {}
    if json_data:
        custom_headers["content-type"] = "application/json;charset=UTF-8"

    # Display JSESSIONID for debugging
    logger.debug(f"Using JSESSIONID: {session_cookies.get('JSESSIONID')}")

    response = make_flowpoker_request(
        method=method,
        endpoint=endpoint,
        custom_headers=custom_headers,
        json_data=json_data,
        disable_ssl_verify=True,
        cookies=session_cookies,
        files=files,
        data=data,
    )

    # Handle session expiration (e.g., 401 or 403)
    if response and response.status_code in (401, 403):
        logger.info("Session expired or unauthorized. Re-authenticating...")
        if refresh_session():
            return make_flowpoker_request(
                method=method,
                endpoint=endpoint,
                json_data=json_data,
                disable_ssl_verify=True,
                cookies=session_cookies,
                files=files,
                data=data,
            )
        else:
            logger.error("Re-authentication failed.")
            return None

    return response


# Initialize session when the module is imported
def initialize_session():
    """Initialize the session by logging in and getting a JSESSIONID"""
    global session_cookies

    # Get JSESSIONID by making a login request
    logger.info("Initializing session with Flow Poker...")
    login_response = make_flowpoker_request(
        "GET", "resource/login", disable_ssl_verify=True
    )

    if login_response:
        # Extract JSESSIONID
        jsessionid = login_response.cookies.get("JSESSIONID")
        if jsessionid:
            session_cookies["JSESSIONID"] = jsessionid
            logger.info(f"JSESSIONID obtained: {jsessionid}")

            # Make a second request to the desk page to ensure the session is fully established
            desk_response = make_flowpoker_request(
                "GET",
                "desk/",
                cookies={"JSESSIONID": jsessionid},
                disable_ssl_verify=True,
            )

            if desk_response and desk_response.status_code == 200:
                logger.info("Session fully established")
                return True
            else:
                logger.warning("Session may not be fully established")
                return True
        else:
            logger.error("JSESSIONID not found in response cookies")
            return False
    else:
        logger.error("Failed to get a response from the server.")
        return False


# Initialize session when the module is imported
initialize_session()
