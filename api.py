from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, model_validator, ValidationError
from typing import Optional
import random
import logging
from rapidfuzz import fuzz

app = FastAPI(
    title="EcoFit Carbon Coach API",
    description="API to calculate digital carbon footprint, suggest eco-friendly alternatives, and motivate users toward sustainable choices 🌍💚",
    version="2.0.0"
)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EcoFitAPI")

VALID_TOKENS = {"EcoFitToken12345": "919441391981"}

CO2_FACTORS = {
    "transport": {"Car": 2.3, "Bus": 0.8, "Bicycle": 0.05, "Walking": 0.0, "Electric Scooter": 0.2},
    "shopping": {
        "Groceries & Food": 1.0, "Clothing & Fashion": 2.5, "Electronics & Gadgets": 3.0,
        "Home & Living": 1.5, "Beauty & Personal Care": 1.2
    },
    "electronics_freq": {"Every year": 2.5, "Every 2-3 years": 1.0, "Rarely": 0.3}
}

UNIQUE_TIPS = {
    "transport": {"Car": ["Plan routes to avoid traffic jams — idling wastes fuel and CO₂!"],
                  "Bus": ["Travel during off-peak hours to reduce congestion and emissions."],
                  "Bicycle": ["Keep your bike tires well-inflated for easier rides."],
                  "Walking": ["Walk to local shops to cut emissions and get exercise."],
                  "Electric Scooter": ["Charge during off-peak hours to reduce grid load."]},
    "shopping": {"Groceries & Food": ["Freeze leftovers to reduce food waste."],
                 "Clothing & Fashion": ["Choose organic cotton or recycled fabrics."],
                 "Electronics & Gadgets": ["Buy refurbished or certified pre-owned electronics."],
                 "Home & Living": ["Use LED bulbs and smart power strips."],
                 "Beauty & Personal Care": ["Switch to biodegradable or refillable products."]},
    "electronics_freq": {"Every year": ["Try using devices for 2-3 years instead of every year."],
                         "Every 2-3 years": ["Keep software updated to improve efficiency."],
                         "Rarely": ["You’re eco-conscious already — keep it up! 💚"]}
}

PRODUCT_DB = {
    "phone": {"carbon_score": 70, "alternatives": [{"name": "Refurbished phone model X", "carbon_score": 50}]},
    "laptop": {"carbon_score": 150, "alternatives": [{"name": "Eco-friendly laptop brand A", "carbon_score": 110}]}
}

PRODUCT_KEYWORDS = {
    "phone": ["phone", "mobile", "smartphone", "iphone", "android phone"],
    "laptop": ["laptop", "notebook", "macbook", "chromebook"]
}

FALLBACK_RESPONSES = [
    "Oops! We're still working on that one. Please try something else! 😊",
    "Hmm, I didn't quite get that. Could you try another input? 🌱"
]

def get_fallback_response() -> str:
    return random.choice(FALLBACK_RESPONSES)

def find_product_category(product_str: str) -> Optional[str]:
    product_str = product_str.lower()
    best_match, highest_score = None, 0
    for category, keywords in PRODUCT_KEYWORDS.items():
        for kw in keywords:
            score = fuzz.partial_ratio(kw, product_str)
            if score > highest_score and score >= 80:
                highest_score, best_match = score, category
    return best_match

class AnswersModel(BaseModel):
    transport: Optional[str]
    shopping: Optional[str]
    electronics_freq: Optional[str]

    @model_validator(mode="before")
    def validate_choices(cls, values):
        if values.get('transport') and values['transport'] not in CO2_FACTORS["transport"]:
            raise ValueError(f"Invalid transport option '{values['transport']}'")
        if values.get('shopping') and values['shopping'] not in CO2_FACTORS["shopping"]:
            raise ValueError(f"Invalid shopping option '{values['shopping']}'")
        if values.get('electronics_freq') and values['electronics_freq'] not in CO2_FACTORS["electronics_freq"]:
            raise ValueError(f"Invalid electronics frequency '{values['electronics_freq']}'")
        return values

class CarbonScoreRequest(BaseModel):
    mode: str
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")
    token = authorization.split(" ")[1]
    phone = VALID_TOKENS.get(token)
    if not phone:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")
    return PlainTextResponse(phone, headers={"Cache-Control": "no-store", "Pragma": "no-cache"})

@app.post("/mcp/carbon_score")
async def carbon_score(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(content={"message": "Invalid JSON format."}, status_code=400)

    mode = (body.get("mode") or "").lower()

    if mode == "quiz":
        return {
            "intro": "🌍 Welcome to EcoFit Carbon Coach! Let's find out your digital footprint with a few simple questions.",
            "questions": [
                {"id": "transport", "text": "How do you usually commute?", "options": list(CO2_FACTORS["transport"].keys())},
                {"id": "shopping", "text": "What do you shop usually?", "options": list(CO2_FACTORS["shopping"].keys())},
                {"id": "electronics_freq", "text": "How often do you buy new electronics?", "options": list(CO2_FACTORS["electronics_freq"].keys())}
            ],
            "note": "After completing, we'll show your footprint and tips tailored just for you! 🌱"
        }

    try:
        data = CarbonScoreRequest(**body)
    except ValidationError as e:
        return JSONResponse(content={"message": f"Validation error: {e}"}, status_code=400)

    if mode == "calculate":
        answers = data.answers or AnswersModel(transport=data.transport, shopping=data.shopping, electronics_freq=data.electronics_freq)
        if not (answers.transport and answers.shopping and answers.electronics_freq):
            return {"message": "Please provide all answers."}
        total_score = CO2_FACTORS["transport"][answers.transport] + CO2_FACTORS["shopping"][answers.shopping] + CO2_FACTORS["electronics_freq"][answers.electronics_freq]
        tips = UNIQUE_TIPS["transport"][answers.transport] + UNIQUE_TIPS["shopping"][answers.shopping] + UNIQUE_TIPS["electronics_freq"][answers.electronics_freq]
        praise = "Wow! You are in the top 5% eco-conscious people! 🌟" if total_score < 2.5 else "Good job! You're doing well! 💪" if total_score < 4.5 else "There's room for improvement! 🌱"
        return {"carbon_score": round(total_score, 2), "praise": praise, "tips": tips}

    if mode == "product":
        if not data.product:
            return {"message": "Please provide a product."}
        category = find_product_category(data.product)
        if not category or category not in PRODUCT_DB:
            return {"message": get_fallback_response()}
        return {"product": data.product, "carbon_score": PRODUCT_DB[category]["carbon_score"], "alternatives": PRODUCT_DB[category]["alternatives"]}

    if mode == "challenge":
        if data.my_score is None or data.friend_score is None:
            return {"message": "Please provide both scores."}
        msg = "You are more eco-friendly! 🌟" if data.my_score < data.friend_score else "Your friend is more eco-conscious. 💪" if data.my_score > data.friend_score else "Same footprint. Team effort! 🤝"
        return {"challenge_result": msg}

    return {"message": get_fallback_response()}

@app.get("/")
async def root():
    return {"message": "Welcome to EcoFit Carbon Coach API 🌍💚"}

@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)

@app.get("/status")
async def status():
    return {"status": "ok", "version": "2.0.0"}
