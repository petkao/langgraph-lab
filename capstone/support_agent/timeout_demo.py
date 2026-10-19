
import time
import requests

url = "https://httpbin.org/delay/5"

try:
    print("Calling external API...")

    response = requests.get(url, timeout=2)
    response.raise_for_status()

    print("API response:", response.status_code)

except requests.exceptions.Timeout:
    print("ERROR: API request timed out")

except requests.exceptions.RequestException as exc:
    print("ERROR: API request failed:", exc)
