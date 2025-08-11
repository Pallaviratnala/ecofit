from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse

app = FastAPI()

# Token to phone mapping - replace with your own secure auth later
VALID_TOKENS = {
    "EcoFitToken12345": "919441391981"
}

@app.post("/mcp/validate", response_class=PlainTextResponse)
async def validate(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = authorization.split(" ")[1]
    phone = VALID_TOKENS.get(token)
    if not phone:
        raise HTTPException(status_code=403, detail="Invalid token")

    # Return phone number as plain text (MCP expects plain string)
    return phone

@app.post("/mcp/carbon_score")
async def carbon_score(data: dict):
    # Here you can parse data and calculate carbon footprint
    # For demo, returning fixed carbon score & message
    return JSONResponse(content={
        "carbon_score": 123.45,
        "message": "Sample carbon footprint calculated"
    })
