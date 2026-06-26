from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from breeze_connect import BreezeConnect
from datetime import datetime, timedelta
from typing import Optional, List
import firebase_admin
from firebase_admin import credentials, firestore
import json
import yfinance as yf
from fastapi import APIRouter
from kiteconnect import KiteConnect


# ==================== Firebase Initialization ====================
# Make sure firebase-key.json is uploaded to your Render project
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()
portfolio_collection = db.collection("portfolio")

app = FastAPI(title="Breeze Backend")

# CORS Middleware
# CORS Middleware - Improved for GitHub Pages + Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://muralikini.github.io",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"  # Keep this as fallback
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ==================== MODELS ====================
class BreezeCredentials(BaseModel):
    api_key: str
    secret_key: str
    session_token: str
    stock_code: str = ""

class HistoricalRequest(BaseModel):
    api_key: str
    secret_key: str
    session_token: str
    stock_code: str
    from_date: str
    to_date: str
    interval: str = "1day"

# Portfolio Item Model
class PortfolioItem(BaseModel):
    type: str
    name: str
    quantity: float
    avg_price: float
    scheme_code: Optional[str] = None
    current_price: Optional[float] = None

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

@app.post("/api/live-quote")
async def get_live_quote(creds: BreezeCredentials):
    try:
        breeze = BreezeConnect(api_key=creds.api_key)
        breeze.generate_session(
            api_secret=creds.secret_key,
            session_token=creds.session_token
        )

        # Get live quote
        quote = breeze.get_quotes(
            stock_code=creds.stock_code,           # e.g. "NIFTY" or "NIFTYMC100"
            exchange_code="NSE",
            product_type="cash",
            expiry_date="",
            right="",
            strike_price=""
        )

        if quote.get("Status") != 200:
            raise HTTPException(
                status_code=400, 
                detail=quote.get("Error", "Failed to fetch live quote")
            )

        return {
            "success": True, 
            "data": quote.get("Success", [])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))    

@app.post("/api/live-price")
async def get_live_price(creds: BreezeCredentials):
    try:
        breeze = BreezeConnect(api_key=creds.api_key)
        breeze.generate_session(
            api_secret=creds.secret_key,
            session_token=creds.session_token
        )

        quote = breeze.get_quotes(
            stock_code=creds.stock_code,
            exchange_code="NSE",
            product_type="cash"
        )

        if quote.get("Status") != 200:
            raise HTTPException(status_code=400, detail=quote.get("Error", "Failed to fetch price"))

        data = quote.get("Success", [{}])[0]
        ltp = float(data.get('ltp') or data.get('last_traded_price') or 0)

        return {
            "success": True,
            "stock_code": creds.stock_code,
            "ltp": ltp
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== MARKET DATA ENDPOINTS (Using yfinance) ====================

@app.get("/api/market/nasdaq")
async def get_nasdaq():
    try:
        ticker = yf.Ticker("^IXIC")
        hist = ticker.history(period="1d")
        
        # More reliable way to get price
        if not hist.empty:
            price = hist["Close"].iloc[-1]
        else:
            price = ticker.info.get("regularMarketPrice", 0)
            
        return {"success": True, "symbol": "NASDAQ", "price": round(float(price), 2)}
    except Exception as e:
        print(f"NASDAQ Error: {str(e)}")  # This will show in Render logs
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/dow")
async def get_dow():
    try:
        ticker = yf.Ticker("^DJI")
        hist = ticker.history(period="1d")
        
        if not hist.empty:
            price = hist["Close"].iloc[-1]
        else:
            price = ticker.info.get("regularMarketPrice", 0)
            
        return {"success": True, "symbol": "DOW", "price": round(float(price), 2)}
    except Exception as e:
        print(f"DOW Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/crude")
async def get_crude_oil():
    try:
        ticker = yf.Ticker("CL=F")  # WTI Crude Oil
        hist = ticker.history(period="1d")
        
        if not hist.empty:
            price = hist["Close"].iloc[-1]
        else:
            price = ticker.info.get("regularMarketPrice", 0)
            
        return {"success": True, "symbol": "Crude Oil (WTI)", "price": round(float(price), 2)}
    except Exception as e:
        print(f"Crude Oil Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== PORTFOLIO (Firebase) ====================
@app.get("/api/portfolio")
async def get_portfolio():
    try:
        docs = portfolio_collection.stream()
        data = [doc.to_dict() for doc in docs]
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.delete("/api/portfolio")
async def delete_portfolio_item(payload: dict):
    try:
        broker = payload.get("broker", "Manual")
        doc_id = f"{payload.get('type')}_{broker}_{payload.get('name')}"
        portfolio_collection.document(doc_id).delete()
        return {"success": True}
    except Exception as e:
        raise HTTPException(500, str(e))

class BulkPortfolio(BaseModel):
    items: List[dict]


@app.post("/api/portfolio")
async def save_portfolio_item(item: dict):
    try:
        broker = item.get("broker", "Manual")
        doc_id = f"{item.get('type')}_{broker}_{item.get('name')}"
        portfolio_collection.document(doc_id).set(item, merge=True)
        return {"success": True, "message": "Saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/bulk")
async def bulk_save_portfolio(data: dict):
    try:
        items = data.get("items", [])
        for item in items:
            broker = item.get("broker", "Manual")
            doc_id = f"{item.get('type')}_{broker}_{item.get('name')}"
            portfolio_collection.document(doc_id).set(item, merge=True)
        return {"success": True, "message": f"Saved {len(items)} items"}
    except Exception as e:
        raise HTTPException(500, str(e))
    
@app.post("/api/live-mf-nav")
async def get_mf_nav(request: dict):
    """Get latest NAV for Mutual Fund using public API"""
    try:
        scheme_code = request.get("scheme_code")
        if not scheme_code:
            raise HTTPException(status_code=400, detail="scheme_code is required")

        # Using mfapi.in - very reliable for Indian MFs
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://api.mfapi.in/mf/{scheme_code}")
            data = response.json()

            if data.get("status") == "SUCCESS":
                nav = float(data["data"][0]["nav"])
                return {"success": True, "nav": nav, "scheme": data["meta"]["scheme_name"]}
            else:
                raise HTTPException(status_code=404, detail="MF scheme not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))    
    
# ==================== ZERODHA ENDPOINT ====================
class ZerodhaHoldingsRequest(BaseModel):
    api_key: str
    access_token: str

@app.post("/api/zerodha/holdings")
async def get_zerodha_holdings(request: dict):
    try:
        api_key = request.get("api_key", "r5ecqcr9rq47o7w6")
        access_token = request.get("access_token")

        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(access_token)
        
        holdings = kite.holdings()
        
        return {
            "success": True,
            "data": holdings
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== ZERODHA TOKEN EXCHANGE ====================
@app.post("/api/zerodha/exchange-token")
async def exchange_zerodha_token(data: dict):
    try:
        api_key = "r5ecqcr9rq47o7w6"
        api_secret = "23v98y0g6935ip4k3onv7yvby4ncrne8"

        kite = KiteConnect(api_key=api_key)
        
        # Correct way to call generate_session
        session_data = kite.generate_session(
            data.get("request_token"), 
            api_secret
        )
        
        access_token = session_data["access_token"]

        return {
            "success": True,
            "access_token": access_token
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

  
# ==================== ROOT ====================
@app.get("/")
def root():
    return {"message": "Breeze Backend is running successfully"}