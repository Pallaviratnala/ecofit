from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
import random

app = FastAPI()

VALID_TOKENS = {
    "EcoFitToken12345": "919441391981"
}

# -------------------
# Validation endpoint
# -------------------
@app.post("/mcp/validate", response_class=PlainTextResponse)
async def validate(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = authorization.split(" ")[1]
    phone = VALID_TOKENS.get(token)
    if not phone:
        raise HTTPException(status_code=403, detail="Invalid token")

    return phone

# -------------------
# Health check
# -------------------
@app.get("/status")
async def status():
    return {"status": "ok", "version": "1.0.0"}

# -------------------
# Carbon Score Assistant
# -------------------
CO2_FACTORS = {
    "transport": {"Car": 2.3, "Bus": 0.8, "Bicycle": 0.05, "Walking": 0.0, "Electric Scooter": 0.2},
    "shopping": {
        "Groceries & Food": 1.0,
        "Clothing & Fashion": 2.5,
        "Electronics & Gadgets": 3.0,
        "Home & Living": 1.5,
        "Beauty & Personal Care": 1.2
    },
    "electronics_freq": {"Every year": 2.5, "Every 2-3 years": 1.0, "Rarely": 0.3}
}

TIPS = [
    "Freeze bread to reduce food waste.",
    "Unplug chargers to avoid phantom energy loss.",
    "Use eco mode on washing machines.",
    "Buy refurbished electronics instead of new.",
    "Switch to LED lights for instant savings."
]

@app.post("/mcp/carbon_score")
async def carbon_score(request: Request):
    body = await request.json()
    mode = body.get("mode")

    # Step 1: Quiz mode
    if mode == "quiz":
        return JSONResponse(content={
            "intro": "Hey 🌍! Ready to discover your digital footprint? Answer these quick questions:",
            "questions": [
                {"id": "transport", "text": "How do you usually commute?",
                 "options": ["Car", "Bus", "Bicycle", "Walking", "Electric Scooter"]},
                {"id": "shopping", "text": "What do you shop usually?",
                 "options": ["Groceries & Food", "Clothing & Fashion", "Electronics & Gadgets", "Home & Living", "Beauty & Personal Care"]},
                {"id": "electronics_freq", "text": "How often do you buy new electronics?",
                 "options": ["Every year", "Every 2-3 years", "Rarely"]}
            ]
        })

    # Step 2: Calculate mode
    if mode == "calculate":
        transport = body.get("transport")
        shopping = body.get("shopping")
        electronics_freq = body.get("electronics_freq")

        if not transport or not shopping or not electronics_freq:
            raise HTTPException(status_code=400, detail="Missing answers")

        score = (
            CO2_FACTORS["transport"][transport] +
            CO2_FACTORS["shopping"][shopping] +
            CO2_FACTORS["electronics_freq"][electronics_freq]
        ) * 100  # scale to yearly kg CO2

        rank_percentile = random.randint(1, 100)
        trees = round(score / 21.77)  # 1 tree absorbs ~21.77 kg CO2/year
        car_km = round(score / 0.271)  # avg petrol car emits ~0.271 kg CO2/km

        return JSONResponse(content={
            "score": score,
            "rank": f"Wow! 🎉 You're in the top {rank_percentile}% of eco-friendly citizens.",
            "equivalence": f"That's like planting {trees} trees 🌳 or travelling {car_km} km 🚗.",
            "tips": random.sample(TIPS, 3)
        })

    # Step 3: Product mode
    if mode == "product":
        product_name = body.get("product")
        if not product_name:
            raise HTTPException(status_code=400, detail="Product name or URL required")

        base_score = random.uniform(50, 200)
        alt_score = round(base_score * 0.8, 2)

        return JSONResponse(content={
            "product": product_name,
            "carbon_score": round(base_score, 2),
            "alternative": {
                "name": f"Eco-friendly {product_name}",
                "carbon_score": alt_score,
                "reason": "Uses 30% recycled materials and energy-efficient manufacturing."
            }
        })

    # Step 4: Challenge mode
    if mode == "challenge":
        my_score = body.get("my_score")
        friend_score = body.get("friend_score")
        if my_score is None or friend_score is None:
            raise HTTPException(status_code=400, detail="Both my_score and friend_score are required")

        if my_score < friend_score:
            msg = "You're already beating your friend — keep it up! 💪"
        else:
            improvement = round((my_score - friend_score) / my_score * 100, 1)
            msg = f"Swap 2 car trips a week for cycling to beat them by {improvement}%!"

        return JSONResponse(content={"message": msg})

    # If mode not recognized
    raise HTTPException(status_code=400, detail="Invalid mode. Use quiz, calculate, product, or challenge.")
