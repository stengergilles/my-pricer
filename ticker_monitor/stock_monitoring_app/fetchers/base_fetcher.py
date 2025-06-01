
from abc import ABC, abstractmethod
import pandas as pd

class Fetcher(ABC):

    @abstractmethod
    def fetch_data(self, identifier: str, period: str, interval: str) -> pd.DataFrame:
        """
        Fetches historical market data for a given identifier over a specified
        period and interval.

        Args:
            identifier: The unique identifier for the asset (e.g., stock ticker, crypto ID).
            period: The duration for which to fetch data (e.g., "1y", "6mo", "max").
                    Specific format might depend on the API.
            interval: The time interval between data points (e.g., "1d", "1h", "5m").
                      Specific format might depend on the API.

        Returns:
            A pandas DataFrame containing the historical data, typically with columns
            like 'Open', 'High', 'Low', 'Close', 'Volume', and a DateTimeIndex.
        
        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
            Exception: Potentially other exceptions related to API communication,
                       data processing, or invalid parameters.        
        """
        pass

    @abstractmethod
    def get_service_name(self) -> str:
        """
        Returns the name of the fetching service (e.g., "CoinGecko", "Polygon.io").

        Returns:
            A string representing the service name.
        """
        pass
