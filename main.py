from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from breeze_connect import BreezeConnect
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Breeze Backend")

# Allow frontend to call this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BreezeCredentials(BaseModel):
    api_key: str
    secret_key: str
    session_token: str

@app.post("/api/holdings")
async def get_holdings(creds: BreezeCredentials):
    try:
        breeze = BreezeConnect(api_key=creds.api_key)
        breeze.generate_session(
            api_secret=creds.secret_key,
            session_token=creds.session_token
        )
        
        # Fetch Demat Holdings
        holdings = breeze.get_demat_holdings()
        
        if holdings.get("Status") != 200:
            raise HTTPException(status_code=400, detail=holdings.get("Error", "Failed to fetch holdings"))
        
        return {"success": True, "data": holdings.get("Success", [])}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {"message": "Breeze Backend is running"}