# 2025/6/25
# zhangzhong
# https://modelcontextprotocol.io/quickstart/server

from typing import Any
import httpx

# from mcp.server.fastmcp import FastMCP
from fastmcp import FastMCP

# The FastMCP class uses Python type hints and docstrings to automatically generate tool definitions, making it easy to create and maintain MCP tools.

# Initialize FastMCP server
mcp = FastMCP(name="weather")

# Constants
NWS_API_BASE = "https://api.weather.gov"  # 这是一个独立的API服务
# 那我们这个server其实也只是转调别人的API而已
USER_AGENT = "weather-app/1.0"


async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json",
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return None


def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""


# https://modelcontextprotocol.io/quickstart/server#implementing-tool-execution
# The tool execution handler is responsible for actually executing the logic of each tool.
@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    url: str = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data: dict[str, Any] | None = await make_nws_request(url=url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or not alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts: list[str] = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)


# 好像mcp的tool都是返回一个string
@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)


if __name__ == "__main__":
    # Initialize and run the server
    # [06/25/25 21:05:39] INFO     Starting MCP server 'weather' with transport 'sse' on http://0.0.0.0:8000/sse/
    mcp.run(transport="sse", host="0.0.0.0", port=8000)
