import os
# Optional: Load .env file if you prefer using python-dotenv
# from dotenv import load_dotenv
# load_dotenv()

class AppSettings:
    """
    Holds application settings, primarily loaded from environment variables.
    """
    def __init__(self):
        # Polygon API Key (Required)
        self.POLYGON_API_KEY: str | None = os.getenv("POLYGON_API_KEY")

        # CoinGecko API Key (Optional)
        # Set your environment variable name if different (e.g., CG_PRO_KEY, CG_DEMO_KEY)
        self.COINGECKO_API_KEY: str | None = os.getenv("COINGECKO_API_KEY")

        # Example of other potential settings
        # self.DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "usd")

# Create a single instance of the settings to be imported by other modules
settings = AppSettings()

# Perform essential checks after loading
if settings.POLYGON_API_KEY is None:
    print("Warning: POLYGON_API_KEY environment variable not set. PolygonFetcher will fail.")
    # Depending on your application's needs, you might want to raise an error here immediately:
    # raise ValueError("Required environment variable POLYGON_API_KEY is not set.")

if settings.COINGECKO_API_KEY is None:
    print("Info: COINGECKO_API_KEY environment variable not set. CoinGeckoFetcher will use public API rates/limits.")

