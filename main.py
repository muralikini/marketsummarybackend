from fastapi import FastAPI, HTTPException,APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from breeze_connect import BreezeConnect
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import yfinance as yf
from .market_routes import router as market_router

app.include_router(market_router)


load_dotenv()
router = APIRouter()
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

class HistoricalRequest(BaseModel):
    api_key: str
    secret_key: str
    session_token: str
    stock_code: str
    from_date: str
    to_date: str
    interval: str = "1day"

@app.post("/api/historical")
async def get_historical(data: HistoricalRequest):
    try:
        breeze = BreezeConnect(api_key=data.api_key)
        breeze.generate_session(
            api_secret=data.secret_key,
            session_token=data.session_token
        )

        historical_data = breeze.get_historical_data_v2(
            interval=data.interval,
            from_date=data.from_date,
            to_date=data.to_date,
            stock_code=data.stock_code,
            exchange_code="NSE",
            product_type="cash"
        )

        if historical_data.get("Status") != 200:
            raise HTTPException(
                status_code=400, 
                detail=historical_data.get("Error", "Failed to fetch historical data")
            )

        return {"success": True, "data": historical_data.get("Success", [])}

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

    @router.get("/api/market/nasdaq")
async def get_nasdaq():
    try:
        ticker = yf.Ticker("^IXIC")
        price = ticker.info.get("regularMarketPrice") or ticker.history(period="1d")["Close"].iloc[-1]
        return {"success": True, "symbol": "NASDAQ", "price": round(float(price), 2)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/market/dow")
async def get_dow():
    try:
        ticker = yf.Ticker("^DJI")
        price = ticker.info.get("regularMarketPrice") or ticker.history(period="1d")["Close"].iloc[-1]
        return {"success": True, "symbol": "DOW", "price": round(float(price), 2)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/market/crude")
async def get_crude_oil():
    try:
        ticker = yf.Ticker("CL=F")  # WTI Crude Oil
        price = ticker.info.get("regularMarketPrice") or ticker.history(period="1d")["Close"].iloc[-1]
        return {"success": True, "symbol": "Crude Oil (WTI)", "price": round(float(price), 2)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {"message": "Breeze Backend is running"}
