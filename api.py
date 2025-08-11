from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, model_validator, ValidationError
from typing import Optional
import random
import logging
from rapidfuzz import fuzz

app = FastAPI(
    title="EcoFit Carbon Coach MCP",
    description="MCP server for EcoFit Carbon Coach: footprint quiz, product suggestions, sustainability tips.",
    version="2.0.0"
)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EcoFitAPI")

# ==== CONFIG ====
VALID_TOKENS = {"EcoFitToken12345": "919441391981"}

CO2_FACTORS = {
    "transport": {
        "Car": 2.3, "Bus": 0.8, "Bicycle": 0.05,
        "Walking": 0.0, "Electric Scooter": 0.2
    },
    "shopping": {
        "Groceries & Food": 1.0,
        "Clothing & Fashion": 2.5,
        "Electronics & Gadgets": 3.0,
        "Home & Living": 1.5,
        "Beauty & Personal Care": 1.2
    },
    "electronics_freq": {
        "Every year": 2.5,
        "Every 2-3 years": 1.0,
        "Rarely": 0.3
    }
}

UNIQUE_TIPS = {
    "transport": {
        "Car": ["Plan routes to avoid traffic jams — idling wastes fuel and CO₂!", "Carpool to reduce your footprint."],
        "Bus": ["Travel during off-peak hours to reduce congestion.", "Advocate for electric buses."],
        "Bicycle": ["Keep your bike tires inflated.", "Use LED rechargeable lights for safety."],
        "Walking": ["Walk to local shops instead of driving.", "Join walking groups for motivation!"],
        "Electric Scooter": ["Charge during off-peak hours.", "Recycle batteries responsibly."]
    },
    "shopping": {
        "Groceries & Food": ["Freeze leftovers to reduce waste.", "Buy seasonal produce."],
        "Clothing & Fashion": ["Choose organic cotton or recycled fabrics.", "Clothing swaps are eco and fun."],
        "Electronics & Gadgets": ["Buy refurbished devices.", "Recycle electronics properly."],
        "Home & Living": ["Use LED bulbs.", "Insulate your home to save energy."],
        "Beauty & Personal Care": ["Switch to biodegradable or refillable products.", "Avoid microbeads."]
    },
    "electronics_freq": {
        "Every year": ["Try using devices for 2-3 years instead of replacing annually.", "Donate old gadgets instead of discarding."],
        "Every 2-3 years": ["Update software to improve efficiency.", "Recycle chargers properly."],
        "Rarely": ["You’re eco-conscious already — keep it up! 💚", "Support brands with take-back programs."]
    }
}

PRODUCT_DB = {
    "phone": {"carbon_score": 70, "alternatives": [
        {"name": "Refurbished phone model X", "carbon_score": 50, "reason": "Avoids new manufacturing emissions"},
        {"name": "Phone Y with recycled aluminium", "carbon_score": 55, "reason": "Uses recycled materials"}
    ]},
    "laptop": {"carbon_score": 150, "alternatives": [
        {"name": "Eco-friendly laptop brand A", "carbon_score": 110, "reason": "Energy-efficient and fair-trade materials"},
        {"name": "Refurbished laptop model B", "carbon_score": 100, "reason": "Certified refurbished with warranty"}
    ]},
    "clothing": {"carbon_score": 40, "alternatives": [
        {"name": "Organic cotton shirt", "carbon_score": 25, "reason": "Uses less water and no pesticides"},
        {"name": "Recycled polyester jacket", "carbon_score": 30, "reason": "Made from recycled bottles"}
    ]}
}

PRODUCT_KEYWORDS = {
    "phone": ["phone", "mobile", "smartphone", "iphone", "android phone", "cellphone"],
    "laptop": ["laptop", "notebook", "macbook", "chromebook", "computer"],
    "clothing": ["clothing", "shirt", "t-shirt", "jacket", "jeans", "dress", "apparel", "garment"]
}

FALLBACK_RESPONSES = [
    "Oops! Please try something else! 😊",
    "Hmm… Could you try another input? 🌱",
    "Still learning that one. Try another?"
]

# ==== HELPERS ====
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

# ==== MODELS ====
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

# ==== MCP HANDSHAKE ROUTES ====
@app.get("/mcp")
async def mcp_root():
    return {
        "name": "EcoFit MCP Server",
        "description": "Carbon footprint quiz, calculation, product suggestions",
        "tools": ["validate", "carbon_score"]
    }

@app.post("/mcp")
async def mcp_post():
    return {
        "tools": [
            {"name": "validate", "description": "Validate token and return phone number"},
            {"name": "carbon_score", "description": "Quiz, footprint calc, product tips"}
        ]
    }

# ==== MCP TOOLS ====
@app.post("/mcp/validate", response_class=PlainTextResponse)
async def validate(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ")[1]
    phone = VALID_TOKENS.get(token)
    if not phone:
        raise HTTPException(status_code=403, detail="Invalid token")
    return PlainTextResponse(phone, headers={"Cache-Control": "no-store", "Pragma": "no-cache"})

@app.post("/mcp/carbon_score")
async def carbon_score(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(content={"message": "Invalid JSON"}, status_code=400)
    mode = (body.get("mode") or "").lower()

    if mode == "quiz":
        return {
            "intro": "🌍 Welcome to EcoFit Carbon Coach! Let's find out your digital footprint.",
            "questions": [
                {"id": "transport", "text": "How do you usually commute?", "options": list(CO2_FACTORS["transport"].keys())},
                {"id": "shopping", "text": "What do you usually shop?", "options": list(CO2_FACTORS["shopping"].keys())},
                {"id": "electronics_freq", "text": "How often do you buy electronics?", "options": list(CO2_FACTORS["electronics_freq"].keys())}
            ],
            "note": "After completing, we'll show your footprint and tips!"
        }

    try:
        data = CarbonScoreRequest(**body)
    except ValidationError as e:
        return JSONResponse(content={"message": str(e)}, status_code=400)

    if mode == "calculate":
        ans = data.answers or AnswersModel(
            transport=data.transport, shopping=data.shopping, electronics_freq=data.electronics_freq
        )
        if not (ans.transport and ans.shopping and ans.electronics_freq):
            return {"message": "Please provide all answers."}
        score = (CO2_FACTORS["transport"][ans.transport] +
                 CO2_FACTORS["shopping"][ans.shopping] +
                 CO2_FACTORS["electronics_freq"][ans.electronics_freq])
        tips = UNIQUE_TIPS["transport"][ans.transport] + UNIQUE_TIPS["shopping"][ans.shopping] + UNIQUE_TIPS["electronics_freq"][ans.electronics_freq]
        return {"carbon_score": round(score, 2), "praise": "Good job!" if score < 4.5 else "There's room for improvement!", "tips": tips}

    if mode == "product":
        if not data.product:
            return {"message": "Please provide a product."}
        category = find_product_category(data.product)
        if not category or category not in PRODUCT_DB:
            return {"message": get_fallback_response()}
        return {"product": data.product,
                "carbon_score": PRODUCT_DB[category]["carbon_score"],
                "alternatives": PRODUCT_DB[category]["alternatives"]}

    if mode == "challenge":
        if data.my_score is None or data.friend_score is None:
            return {"message": "Please provide both scores."}
        msg = "You are more eco-friendly! 🌟" if data.my_score < data.friend_score \
              else "Your friend is more eco-conscious. 💪" if data.my_score > data.friend_score \
              else "Same footprint. 🤝"
        return {"challenge_result": msg}

    return {"message": get_fallback_response()}

# ==== ROOT / STATUS ====
@app.get("/")
async def root():
    return {"message": "Welcome to EcoFit Carbon Coach API 🌍💚"}

@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)
