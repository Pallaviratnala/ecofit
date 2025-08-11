from mcp.server.fastapi import FastAPIMCPServer, tool
from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from typing import Optional, Dict, Any
import random
from rapidfuzz import fuzz

# Create MCP tool server instance
mcp = FastAPIMCPServer()

# FastAPI app (for REST endpoints)
app = mcp.app

# =========================
# CONFIG + DATA
# =========================
VALID_TOKENS = {"EcoFitToken12345": "919441391981"}

CO2_FACTORS = {
    "transport": {"Car": 2.3, "Bus": 0.8, "Bicycle": 0.05, "Walking": 0.0, "Electric Scooter": 0.2},
    "shopping": {
        "Groceries & Food": 1.0, "Clothing & Fashion": 2.5,
        "Electronics & Gadgets": 3.0, "Home & Living": 1.5,
        "Beauty & Personal Care": 1.2
    },
    "electronics_freq": {"Every year": 2.5, "Every 2-3 years": 1.0, "Rarely": 0.3}
}

UNIQUE_TIPS = {
    "transport": {
        "Car": ["Plan routes to avoid traffic jams!", "Carpool to reduce your footprint."],
        "Bus": ["Travel off-peak to cut emissions.", "Support electric buses."],
        "Bicycle": ["Check tire pressure often.", "Use rechargeable lights."],
        "Walking": ["Walk to nearby shops.", "Join walking clubs for fun!"],
        "Electric Scooter": ["Charge off-peak.", "Recycle batteries properly."]
    },
    "shopping": {
        "Groceries & Food": ["Freeze leftovers.", "Buy seasonal produce."],
        "Clothing & Fashion": ["Use organic cotton.", "Join clothing swaps."],
        "Electronics & Gadgets": ["Buy refurbished devices.", "Recycle old electronics."],
        "Home & Living": ["Use LED bulbs.", "Insulate your home."],
        "Beauty & Personal Care": ["Switch to refillables.", "Avoid microbeads."]
    },
    "electronics_freq": {
        "Every year": ["Keep devices longer.", "Donate or recycle gadgets."],
        "Every 2-3 years": ["Update software.", "Recycle chargers."],
        "Rarely": ["You're eco-conscious!", "Support take-back programs."]
    }
}

PRODUCT_DB = {
    "phone": {"carbon_score": 70, "alternatives": [
        {"name": "Refurbished phone model X", "carbon_score": 50, "reason": "Avoids manufacturing emissions"},
        {"name": "Phone Y recycled aluminium", "carbon_score": 55, "reason": "Uses recycled aluminium"}]},
    "laptop": {"carbon_score": 150, "alternatives": [
        {"name": "Eco laptop brand A", "carbon_score": 110, "reason": "Energy-efficient materials"},
        {"name": "Refurbished laptop B", "carbon_score": 100, "reason": "Certified refurbished"}]},
    "clothing": {"carbon_score": 40, "alternatives": [
        {"name": "Organic cotton shirt", "carbon_score": 25, "reason": "Uses less water"},
        {"name": "Recycled polyester jacket", "carbon_score": 30, "reason": "From recycled bottles"}]}
}

PRODUCT_KEYWORDS = {
    "phone": ["phone", "mobile", "smartphone", "iphone", "android phone", "cellphone"],
    "laptop": ["laptop", "notebook", "macbook", "chromebook", "computer"],
    "clothing": ["clothing", "shirt", "t-shirt", "jacket", "jeans", "dress", "apparel", "garment"]
}

FALLBACK_MSGS = [
    "Oops! Please try something else! 😊",
    "Hmm… Could you try another input? 🌱",
    "Still learning that one. Try another?"
]

# =========================
# HELPERS
# =========================
def fallback() -> str:
    return random.choice(FALLBACK_MSGS)

def find_category(name: str) -> Optional[str]:
    name = name.lower()
    best_match, high_score = None, 0
    for cat, keywords in PRODUCT_KEYWORDS.items():
        for kw in keywords:
            score = fuzz.partial_ratio(kw, name)
            if score > high_score and score >= 80:
                high_score, best_match = score, cat
    return best_match

# =========================
# MCP TOOLS
# =========================
@tool(name="validate", description="Validate token and return phone number in {country_code}{number} format.")
async def validate_tool(authorization: str) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ")[1]
    phone = VALID_TOKENS.get(token)
    if not phone:
        raise HTTPException(status_code=403, detail="Invalid token")
    return phone

@tool(name="about", description="Return metadata about this MCP server.")
async def about_tool() -> Dict[str, str]:
    return {
        "name": "EcoFit MCP Server",
        "description": "An MCP server for EcoFit Carbon Coach — carbon footprint quizzes, eco tips, and product suggestions."
    }

@tool(name="carbon_score", description="Handle eco footprint quizzes, calculations, product suggestions, and challenges.")
async def carbon_score_tool(
    mode: str,
    transport: Optional[str] = None,
    shopping: Optional[str] = None,
    electronics_freq: Optional[str] = None,
    product: Optional[str] = None,
    my_score: Optional[float] = None,
    friend_score: Optional[float] = None
) -> Any:
    mode = (mode or "").lower()
    if mode == "quiz":
        return {
            "intro": "🌍 Welcome to EcoFit Carbon Coach! Let's find out your digital footprint.",
            "questions": [
                {"id": "transport", "text": "How do you usually commute?", "options": list(CO2_FACTORS["transport"].keys())},
                {"id": "shopping", "text": "What do you usually shop?", "options": list(CO2_FACTORS["shopping"].keys())},
                {"id": "electronics_freq", "text": "How often do you buy electronics?", "options": list(CO2_FACTORS["electronics_freq"].keys())}
            ]
        }
    if mode == "calculate":
        if not (transport and shopping and electronics_freq):
            return {"message": "Please provide all answers."}
        score = (
            CO2_FACTORS["transport"][transport] +
            CO2_FACTORS["shopping"][shopping] +
            CO2_FACTORS["electronics_freq"][electronics_freq]
        )
        tips = UNIQUE_TIPS["transport"][transport] + UNIQUE_TIPS["shopping"][shopping] + UNIQUE_TIPS["electronics_freq"][electronics_freq]
        return {"carbon_score": round(score, 2), "praise": "Good job!" if score < 4.5 else "Needs improvement!", "tips": tips}
    if mode == "product":
        if not product:
            return {"message": "Please provide a product."}
        category = find_category(product)
        if not category or category not in PRODUCT_DB:
            return {"message": fallback()}
        return {
            "product": product,
            "carbon_score": PRODUCT_DB[category]["carbon_score"],
            "alternatives": PRODUCT_DB[category]["alternatives"]
        }
    if mode == "challenge":
        if my_score is None or friend_score is None:
            return {"message": "Please provide both scores."}
        if my_score < friend_score:
            return {"challenge_result": "You are more eco-friendly! 🌟"}
        elif my_score > friend_score:
            return {"challenge_result": "Your friend is more eco-conscious. 💪"}
        else:
            return {"challenge_result": "Same footprint. 🤝"}
    return {"message": fallback()}

# =========================
# BACKWARD-COMPATIBLE REST ENDPOINTS
# =========================
@app.get("/mcp")
async def mcp_root():
    return {"tools": ["validate", "carbon_score", "about"]}

@app.post("/mcp/validate", response_class=PlainTextResponse)
async def validate_rest(authorization: str = Header(None)):
    return await validate_tool(authorization)

@app.post("/mcp/about")
async def about_rest():
    return await about_tool()

@app.post("/mcp/carbon_score")
async def carbon_score_rest(body: dict):
    return await carbon_score_tool(**body)

@app.get("/")
async def root():
    return {"message": "Welcome to EcoFit Carbon Coach API 🌍💚"}
