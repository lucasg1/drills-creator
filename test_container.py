import requests

url = "http://127.0.0.1:8777/generate_image"

# Example payload matching your Flask server expectations
payload = {
    "metadata": {
        "hand": "22",
        "best_action": "F",
        "best_ev": 0.0,
        "mode": "icm",
        "field_size": 200,
        "field_left": "bubble",
        "position": "utg",
        "stack_depth": "20_125",
        "action": "rfi",
        "game_type": "MTTGeneral_ICM8m200PTBUBBLEMID",
        "street": "preflop",
        "action_sequence": "no_actions",
    },
    "spot_solution": {},
    "hand_data": {
        "hand": "22",
        "best_action": "F",
        "best_ev": 0.0,
        "F_strat": 100.0,
        "F_ev": 0.0,
        "R2_strat": 0.0,
        "R2_ev": -0.06933,
        "RAI_strat": 0.0,
        "RAI_ev": -1.04083,
    },
}

headers = {"Content-Type": "application/json"}

response = requests.post(url, json=payload, headers=headers)

# Save the received image if request is successful
if response.status_code == 200:
    with open("hand_image.png", "wb") as f:
        f.write(response.content)
    print("Image saved as hand_image.png")
else:
    print(f"Request failed with status code {response.status_code}")
    print("Response:", response.text)
