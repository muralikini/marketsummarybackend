from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from breeze_connect import BreezeConnect
from datetime import datetime, timedelta
import yfinance as yf

app = FastAPI(title="Breeze Backend")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== MODELS ====================
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


# ==================== BREEZE ENDPOINTS ====================

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

        today = datetime.now().strftime("%Y-%m-%dT06:00:00.000Z")
        from_date = (datetime.now() - timedelta(days=1825)).strftime("%Y-%m-%dT06:00:00.000Z")

        holdings = breeze.get_portfolio_holdings(
            exchange_code="NSE",
            from_date=from_date,
            to_date=today,
            stock_code="",
            portfolio_type="holdings"
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


# ==================== MARKET DATA ENDPOINTS (Using yfinance) ====================

@app.get("/api/market/nasdaq")
async def get_nasdaq():
    try:
        ticker = yf.Ticker("^IXIC")
        hist = ticker.history(period="1d")
        price = ticker.info.get("regularMarketPrice") or hist["Close"].iloc[-1]
        return {"success": True, "symbol": "NASDAQ", "price": round(float(price), 2)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/dow")
async def get_dow():
    try:
        ticker = yf.Ticker("^DJI")
        hist = ticker.history(period="1d")
        price = ticker.info.get("regularMarketPrice") or hist["Close"].iloc[-1]
        return {"success": True, "symbol": "DOW", "price": round(float(price), 2)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/crude")
async def get_crude_oil():
    try:
        ticker = yf.Ticker("CL=F")  # WTI Crude Oil Futures
        hist = ticker.history(period="1d")
        price = ticker.info.get("regularMarketPrice") or hist["Close"].iloc[-1]
        return {"success": True, "symbol": "Crude Oil (WTI)", "price": round(float(price), 2)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ROOT ====================
@app.get("/")
def root():
    return {"message": "Breeze Backend is running successfully"}