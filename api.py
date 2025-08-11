from fastapi import FastAPI, Header, HTTPException, Request, status, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field, validator
import random
import logging
from typing import Optional
from rapidfuzz import fuzz  # For fuzzy matching; pip install rapidfuzz

app = FastAPI(
    title="EcoFit Carbon Coach API",
    description="API to calculate digital carbon footprint, suggest eco-friendly alternatives, and motivate users toward sustainable choices 🌍💚",
    version="2.0.0"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EcoFitAPI")

VALID_TOKENS = {
    "EcoFitToken12345": "919441391981"
}

CO2_FACTORS = {
    "transport": {
        "Car": 2.3, "Bus": 0.8, "Bicycle": 0.05, "Walking": 0.0, "Electric Scooter": 0.2
    },
    "shopping": {
        "Groceries & Food": 1.0,
        "Clothing & Fashion": 2.5,
        "Electronics & Gadgets": 3.0,
        "Home & Living": 1.5,
        "Beauty & Personal Care": 1.2
    },
    "electronics_freq": {
        "Every year": 2.5, "Every 2-3 years": 1.0, "Rarely": 0.3
    }
}

CATEGORY_EMOJIS = {
    "transport": {
        "Car": "🚗",
        "Bus": "🚌",
        "Bicycle": "🚴",
        "Walking": "🚶",
        "Electric Scooter": "🛴"
    },
    "shopping": {
        "Groceries & Food": "🛒",
        "Clothing & Fashion": "👗",
        "Electronics & Gadgets": "📱",
        "Home & Living": "🏠",
        "Beauty & Personal Care": "💄"
    },
    "electronics_freq": {
        "Every year": "📅",
        "Every 2-3 years": "📆",
        "Rarely": "⏳"
    }
}

UNIQUE_TIPS = {
    "transport": {
        "Car": [
            "Plan routes to avoid traffic jams — idling wastes fuel and CO₂!",
            "Carpool with friends to share the ride and emissions.",
            "Use synthetic motor oil to improve engine efficiency."
        ],
        "Bus": [
            "Travel during off-peak hours to reduce congestion and emissions.",
            "Advocate for electric buses in your community!",
            "Carry a reusable travel mug to avoid disposables."
        ],
        "Bicycle": [
            "Keep your bike tires well-inflated for easier rides.",
            "Use rechargeable LED lights for safer night riding.",
            "Use a backpack instead of plastic bags when shopping."
        ],
        "Walking": [
            "Walk to local shops to cut emissions and get exercise.",
            "Join walking groups to stay motivated and social.",
            "Choose eco-friendly footwear made from recycled materials."
        ],
        "Electric Scooter": [
            "Charge during off-peak hours to reduce grid load.",
            "Maintain your battery to extend its life.",
            "Recycle scooter batteries responsibly."
        ]
    },
    "shopping": {
        "Groceries & Food": [
            "Freeze leftovers to reduce food waste.",
            "Buy local, seasonal produce to cut transport emissions.",
            "Grow herbs or veggies at home."
        ],
        "Clothing & Fashion": [
            "Choose organic cotton or recycled fabrics.",
            "Participate in clothing swaps.",
            "Avoid fast fashion brands."
        ],
        "Electronics & Gadgets": [
            "Buy refurbished or certified pre-owned electronics.",
            "Extend device life by upgrading batteries or parts.",
            "Recycle electronics properly."
        ],
        "Home & Living": [
            "Use LED bulbs and smart power strips.",
            "Insulate your home to save heating/cooling energy.",
            "Pick furniture made from sustainable wood."
        ],
        "Beauty & Personal Care": [
            "Switch to biodegradable or refillable products.",
            "Avoid microbeads and heavy plastic packaging.",
            "Try DIY natural skincare recipes."
        ]
    },
    "electronics_freq": {
        "Every year": [
            "Try using devices for 2-3 years instead of every year.",
            "Donate old devices instead of discarding.",
            "Be mindful of cloud storage energy usage."
        ],
        "Every 2-3 years": [
            "Keep software updated to improve efficiency.",
            "Recycle chargers and cables responsibly.",
            "Backup data regularly."
        ],
        "Rarely": [
            "You’re eco-conscious already — keep it up! 💚",
            "Support brands with take-back programs.",
            "Share devices when possible."
        ]
    }
}

PRODUCT_DB = {
    "phone": {
        "carbon_score": 70,
        "alternatives": [
            {"name": "Refurbished phone model X", "carbon_score": 50,
             "reason": "Avoids new manufacturing emissions with recycled parts."},
            {"name": "Phone model Y with recycled aluminum", "carbon_score": 55,
             "reason": "Uses 30% recycled aluminum reducing CO₂ footprint."}
        ]
    },
    "laptop": {
        "carbon_score": 150,
        "alternatives": [
            {"name": "Eco-friendly laptop brand A", "carbon_score": 110,
             "reason": "Energy-efficient and fair-trade materials."},
            {"name": "Refurbished laptop model B", "carbon_score": 100,
             "reason": "Certified refurbished with extended warranty."}
        ]
    },
    "clothing": {
        "carbon_score": 40,
        "alternatives": [
            {"name": "Organic cotton shirt", "carbon_score": 25,
             "reason": "Uses less water and no synthetic pesticides."},
            {"name": "Recycled polyester jacket", "carbon_score": 30,
             "reason": "Made from recycled plastic bottles."}
        ]
    },
    "home": {
        "carbon_score": 60,
        "alternatives": [
            {"name": "Sustainably sourced wooden chair", "carbon_score": 45,
             "reason": "Uses certified sustainable wood."},
            {"name": "Energy-efficient LED lamp", "carbon_score": 40,
             "reason": "Consumes less electricity and lasts longer."}
        ]
    },
    "electronics": {
        "carbon_score": 100,
        "alternatives": [
            {"name": "Certified refurbished camera", "carbon_score": 75,
             "reason": "Reuses components to reduce manufacturing."},
            {"name": "Energy Star rated speaker", "carbon_score": 80,
             "reason": "Designed for low energy consumption."}
        ]
    },
    "beauty": {
        "carbon_score": 30,
        "alternatives": [
            {"name": "Biodegradable skincare set", "carbon_score": 20,
             "reason": "Natural ingredients and eco-friendly packaging."},
            {"name": "Refillable makeup products", "carbon_score": 22,
             "reason": "Reduces plastic waste and packaging footprint."}
        ]
    }
}

PRODUCT_KEYWORDS = {
    "phone": ["phone", "mobile", "cellphone", "smartphone", "iphone", "android phone", "refurbished phone",
              "handset", "cell", "mobile phone"],
    "laptop": ["laptop", "notebook", "macbook", "chromebook", "refurbished laptop", "computer", "pc", "ultrabook"],
    "clothing": ["clothing", "clothes", "shirt", "t-shirt", "jacket", "jeans", "dress", "pants", "apparel", "outfit",
                 "garment", "refurbished clothes", "organic cotton"],
    "home": ["furniture", "sofa", "table", "chair", "bed", "home decor", "curtain", "carpet", "lamp", "cushion"],
    "electronics": ["electronics", "gadget", "device", "camera", "headphone", "speaker", "tv", "monitor", "tablet", "console"],
    "beauty": ["beauty", "cosmetic", "makeup", "skincare", "cream", "lotion", "perfume", "personal care"]
}

FALLBACK_RESPONSES = [
    "Oops! We're still working on that one. Please try something else! 😊",
    "Hmm, I didn't quite get that. Could you try another input? 🌱",
    "Our eco-bot is learning new things every day. Try a different product or choice! 🌎",
    "Sorry, I don't have info on that yet, but stay tuned for updates! 💚",
    "I'm still growing my knowledge garden. Give me another try! 🌿"
]

def get_fallback_response() -> str:
    return random.choice(FALLBACK_RESPONSES)

class AnswersModel(BaseModel):
    transport: Optional[str]
    shopping: Optional[str]
    electronics_freq: Optional[str]

    @validator('transport')
    def check_transport(cls, v):
        if v is not None and v not in CO2_FACTORS["transport"]:
            raise ValueError(f"Invalid transport option '{v}'")
        return v

    @validator('shopping')
    def check_shopping(cls, v):
        if v is not None and v not in CO2_FACTORS["shopping"]:
            raise ValueError(f"Invalid shopping option '{v}'")
        return v

    @validator('electronics_freq')
    def check_electronics_freq(cls, v):
        if v is not None and v not in CO2_FACTORS["electronics_freq"]:
            raise ValueError(f"Invalid electronics frequency '{v}'")
        return v

class CarbonScoreRequest(BaseModel):
    mode: str = Field(..., description="Mode of the request: quiz, calculate, product, challenge")
    answers: Optional[AnswersModel] = None
    transport: Optional[str] = None
    shopping: Optional[str] = None
    electronics_freq: Optional[str] = None
    product: Optional[str] = None
    my_score: Optional[float] = None
    friend_score: Optional[float] = None

@app.post("/mcp/validate", response_class=PlainTextResponse)
async def validate(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        logger.warning("Unauthorized access attempt: Missing/invalid header")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")
    token = authorization.split(" ")[1]
    phone = VALID_TOKENS.get(token)
    if not phone:
        logger.warning(f"Unauthorized token attempt: {token}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")
    logger.info(f"Authorized token for phone {phone}")
    return PlainTextResponse(content=phone, headers={
        "Cache-Control": "no-store",
        "Pragma": "no-cache"
    })

@app.get("/status")
async def status():
    return {"status": "ok", "version": "2.0.0"}

def find_product_category(product_str: str) -> Optional[str]:
    product_str = product_str.lower()
    best_match = None
    highest_score = 0
    for category, keywords in PRODUCT_KEYWORDS.items():
        for kw in keywords:
            score = fuzz.partial_ratio(kw, product_str)
            if score > highest_score and score >= 80:
                highest_score = score
                best_match = category
    return best_match

@app.post("/mcp/carbon_score")
async def carbon_score(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(content={"message": "Invalid JSON format."}, status_code=400)

    mode = (body.get("mode") or "").lower()

    if mode == "quiz":
        return JSONResponse(content={
            "intro": "🌍 Welcome to EcoFit Carbon Coach! Let's find out your digital footprint with a few simple questions.",
            "questions": [
                {"id": "transport", "text": "How do you usually commute?", "options": list(CO2_FACTORS["transport"].keys())},
                {"id": "shopping", "text": "What do you shop usually?", "options": list(CO2_FACTORS["shopping"].keys())},
                {"id": "electronics_freq", "text": "How often do you buy new electronics?", "options": list(CO2_FACTORS["electronics_freq"].keys())}
            ],
            "note": "After completing, we'll show your footprint and tips tailored just for you! 🌱"
        })

    try:
        data = CarbonScoreRequest(**body)
    except Exception as e:
        return JSONResponse(content={"message": f"Validation error: {e}"}, status_code=400)

    if mode == "calculate":
        answers = data.answers or AnswersModel(
            transport=data.transport,
            shopping=data.shopping,
            electronics_freq=data.electronics_freq
        )
        if not (answers.transport and answers.shopping and answers.electronics_freq):
            return JSONResponse(content={"message": "Please provide all answers."}, status_code=400)
        total_score = CO2_FACTORS["transport"][answers.transport] + CO2_FACTORS["shopping"][answers.shopping] + CO2_FACTORS["electronics_freq"][answers.electronics_freq]
        tips = UNIQUE_TIPS["transport"][answers.transport] + UNIQUE_TIPS["shopping"][answers.shopping] + UNIQUE_TIPS["electronics_freq"][answers.electronics_freq]
        praise = "Wow! You are in the top 5% eco-conscious people! 🌟" if total_score < 2.5 else \
                 "Good job! You're doing well! 💪" if total_score < 4.5 else \
                 "There's room for improvement! 🌱"
        return JSONResponse(content={
            "carbon_score": round(total_score, 2),
            "praise": praise,
            "tips": tips
        })

    if mode == "product":
        if not data.product:
            return JSONResponse(content={"message": "Please provide a product."}, status_code=400)
        category = find_product_category(data.product)
        if not category or category not in PRODUCT_DB:
            return JSONResponse(content={"message": get_fallback_response()}, status_code=404)
        return JSONResponse(content={
            "product": data.product,
            "carbon_score": PRODUCT_DB[category]["carbon_score"],
            "alternatives": PRODUCT_DB[category]["alternatives"]
        })

    if mode == "challenge":
        if data.my_score is None or data.friend_score is None:
            return JSONResponse(content={"message": "Please provide both scores."}, status_code=400)
        msg = "You are more eco-friendly! 🌟" if data.my_score < data.friend_score else \
              "Your friend is more eco-conscious. 💪" if data.my_score > data.friend_score else \
              "Same footprint. Team effort! 🤝"
        return JSONResponse(content={"challenge_result": msg})

    return JSONResponse(content={"message": get_fallback_response()}, status_code=400)

@app.get("/")
async def root():
    return {"message": "Welcome to EcoFit Carbon Coach API 🌍💚"}

@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)
