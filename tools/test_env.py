import requests
import pandas as pd
print("Requests version:", requests.__version__)
print("Pandas version:", pd.__version__)
response = requests.get("https://httpbin.org/get")
print("Status code:", response.status_code)
print("JSON keys:", list(response.json().keys()))
