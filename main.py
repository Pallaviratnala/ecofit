from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse

app = FastAPI()

# Token to phone mapping
VALID_TOKENS = {
    "EcoFitToken12345": "919441391981"
}

# Simple CO2 emission factors (kg CO2 per unit)
EMISSION_FACTORS = {
    "phone": 70.0,
    "laptop": 200.0,
    "tshirt": 10.0,
    "shoes": 14.0
}

@app.post("/mcp/validate", response_class=PlainTextResponse)
async def validate(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = authorization.split(" ")[1]
    phone = VALID_TOKENS.get(token)
    if not phone:
        raise HTTPException(status_code=403, detail="Invalid token")

    return phone

@app.post("/mcp/carbon_score")
async def carbon_score(data: dict):
    product = data.get("product", "").lower()
    quantity = data.get("quantity", 1)

    if product not in EMISSION_FACTORS:
        raise HTTPException(status_code=400, detail="Unknown product type")

    # Calculate carbon footprint
    carbon_score = EMISSION_FACTORS[product] * quantity

    return JSONResponse(content={
        "product": product,
        "quantity": quantity,
        "carbon_score": round(carbon_score, 2),
        "message": f"Estimated carbon footprint for {quantity} {product}(s) is {round(carbon_score, 2)} kg CO₂."
    })

@app.get("/status")
async def status():
    return {"status": "ok", "version": "1.0.0"}
