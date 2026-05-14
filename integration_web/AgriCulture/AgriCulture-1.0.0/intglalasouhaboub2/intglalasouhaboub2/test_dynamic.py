import requests
import json

url = "http://localhost:8000/api/crispr/predict"

payload1 = {
    "sequence": "AAAAAAAAAAAAAAAAAAAA",
    "chromatin": 1,
    "leaf_exp": 2,
    "t0_exp": 1,
    "region": "Exon"
}

payload2 = {
    "sequence": "GGGGGGGGGGGGGGGGGGGG",
    "chromatin": 0,
    "leaf_exp": 0,
    "t0_exp": 2,
    "region": "Intron"
}

try:
    r1 = requests.post(url, json=payload1)
    print(f"Res 1: {r1.json()}")
    r2 = requests.post(url, json=payload2)
    print(f"Res 2: {r2.json()}")
except Exception as e:
    print(f"Error: {e}")
