import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from typing import List

# Initialize the FastAPI app
app = FastAPI()

# --- Enable CORS ---
# This allows the API to be called from any frontend application
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# --- Load Data ---
# Load the telemetry data into a pandas DataFrame when the app starts
# Vercel places project files in '/var/task/', so we build the path
try:
    df = pd.read_json("q-vercel-latency.json")
except FileNotFoundError:
    # A fallback path for local development
    df = pd.read_json("api/q-vercel-latency.json")


# --- Define Request Body Model ---
# This uses Pydantic to ensure the incoming JSON has the correct structure
class LatencyRequest(BaseModel):
    regions: List[str] = Field(..., example=["emea", "amer"])
    threshold_ms: int = Field(..., example=174)


# --- API Endpoint ---
@app.post("/api/latency")
def get_latency_stats(request: LatencyRequest):
    """
    Accepts a POST request with regions and a threshold, then returns
    calculated metrics for each region.
    """
    results = {}
    
    # Loop through each region provided in the request body
    for region in request.regions:
        # Filter the DataFrame for the current region
        region_df = df[df['region'] == region]

        # If no data exists for that region, skip it
        if region_df.empty:
            continue

        # Calculate the required metrics
        avg_latency = region_df['latency_ms'].mean()
        p95_latency = region_df['latency_ms'].quantile(0.95)
        avg_uptime = region_df['uptime_pct'].mean()
        
        # Count how many records are above the provided threshold
        breaches = int((region_df['latency_ms'] > request.threshold_ms).sum())

        # Store the results for the region
        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 3),
            "breaches": breaches,
        }

    return results

# This is a Vercel convention for running the app
# You can also use this for local testing: uvicorn api.latency:app --reload
handler = app