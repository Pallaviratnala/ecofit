import asyncio
import os
from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp.server.auth.provider import AccessToken
from pydantic import Field

# Load env variables from system (Vercel injects env vars automatically)
TOKEN = os.environ.get("AUTH_TOKEN")
MY_NUMBER = os.environ.get("MY_NUMBER")

assert TOKEN, "AUTH_TOKEN missing"
assert MY_NUMBER, "MY_NUMBER missing"

class SimpleBearerAuthProvider(BearerAuthProvider):
    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(token=token, client_id="puch-client", scopes=["*"], expires_at=None)
        return None

mcp = FastMCP("EcoFit MCP Server", auth=SimpleBearerAuthProvider(TOKEN))

@mcp.tool
async def validate() -> str:
    return MY_NUMBER

@mcp.tool
async def greet(name: str = Field(description="User name")) -> str:
    return f"Hello, {name}! Welcome to EcoFit MCP Server."

async def main():
    print("🚀 MCP server running on /mcp/ path")
    await mcp.run_async("streamable-http", host="0.0.0.0", port=8080, path="/mcp/")

if __name__ == "__main__":
    asyncio.run(main())
