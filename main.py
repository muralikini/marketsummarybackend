from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from breeze_connect import BreezeConnect
from datetime import datetime, timedelta

app = FastAPI(title="Breeze Backend - Portfolio Holdings")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

        # Get today's date and a date 5 years ago for broader results
        today = datetime.now().strftime("%Y-%m-%dT06:00:00.000Z")
        from_date = (datetime.now() - timedelta(days=1825)).strftime("%Y-%m-%dT06:00:00.000Z")

        # Using get_portfolio_holdings with better parameters
        holdings = breeze.get_portfolio_holdings(
            exchange_code="NSE",
            from_date=from_date,
            to_date=today,
            stock_code="",
            portfolio_type="allholding"          # You can also try "EQ" or "FNO"
        )

        if holdings.get("Status") != 200:
            raise HTTPException(
                status_code=400, 
                detail=holdings.get("Error", "Failed to fetch portfolio holdings")
            )

        return {
            "success": True, 
            "data": holdings.get("Success", [])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {"message": "Breeze Backend is running - Portfolio Holdings"}
