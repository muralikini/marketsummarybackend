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

@app.post("/api/historical")
async def get_historical_data(creds: BreezeCredentials, request: dict):
    try:
        breeze = BreezeConnect(api_key=creds.api_key)
        breeze.generate_session(
            api_secret=creds.secret_key,
            session_token=creds.session_token
        )

        stock_code = request.get("stock_code")
        interval = request.get("interval", "1day")           # 1day, 1hour, 15minute etc.
        from_date = request.get("from_date")                 # Format: "2021-01-01T06:00:00.000Z"
        to_date = request.get("to_date")                     # Format: "2026-06-08T06:00:00.000Z"

        if not stock_code or not from_date or not to_date:
            raise HTTPException(status_code=400, detail="stock_code, from_date and to_date are required")

        data = breeze.get_historical_data(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            stock_code=stock_code,
            exchange_code="NSE",
            product_type="cash"
        )

        if data.get("Status") != 200:
            raise HTTPException(status_code=400, detail=data.get("Error", "Failed to fetch historical data"))

        return {"success": True, "data": data.get("Success", [])}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
            portfolio_type="holdings"          # You can also try "EQ" or "FNO"
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
    return {"message": "Breeze Backend is running"}