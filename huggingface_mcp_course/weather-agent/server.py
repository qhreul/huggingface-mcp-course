from mcp.server.fastmcp import FastMCP

# create a new FastMCP server
mcp = FastMCP("Weather Service")

# Tool Implementation
@mcp.tool()
def get_weather(location: str) -> str:
    """
    Get the current weather for a specified location
    :param location: location for which we want to retrieve the weather
    :return: the weather information at specified location
    """
    return f'Weather in {location}: Sunny, 72°F'

# Resource Implementation
@mcp.resource("weather://{location}")
def weather_resource(location: str) -> str:
    """
    Get the weather information for a specified location from a external resource
    :param location: location for which we want to retrieve the weather
    :return: the weather information at specified location
    """
    return f'Weather data for {location}: Sunny, 72°F'

@mcp.prompt()
def weather_report(location: str) -> str:
    """
    Create a weather report prompt
    :param location: location for which we want to retrieve the weather
    :return: User prompt to be executed
    """
    return f'You are a weather reporter. Weather report for {location}?'


# Run the server
if __name__ == "__main__":
    mcp.run()