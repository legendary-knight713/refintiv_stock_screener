import requests
import json
import pandas as pd
import os
from refinitiv.api.constants import USER_NAME, PASSWORD
from datetime import datetime
from typing import Dict, Any, List, Optional

class RefinitivAPI:
    """
    Refinitiv DSWS API wrapper that provides the same interface as BorsdataAPI
    """
    
    def __init__(self, username: str = None, password: str = None):
        """
        Initialize Refinitiv API with credentials
        :param username: DSWS username (defaults to constants)
        :param password: DSWS password (defaults to constants)
        """
        self.username = username or USER_NAME
        self.password = password or PASSWORD
        self._token = None
        self._token_expiry = None
        
    def _get_token(self) -> str:
        """Get or refresh authentication token"""
        if self._token is None:
            self._token = self.get_datastream_token(self.username, self.password)
        return self._token
    
    def _convert_dsws_to_borsdata_format(self, dsws_data: Dict[str, List], instrument_id: int) -> pd.DataFrame:
        """
        Convert DSWS response format to Borsdata pandas format
        :param dsws_data: DSWS response data from fetch_datastream_timeseries
        :param instrument_id: Instrument ID to use
        :return: pandas DataFrame in Borsdata format
        """
        rows = []
        
        for datatype, date_value_pairs in dsws_data.items():
            for date, value in date_value_pairs:
                if date is not None and value is not None:
                    # Convert date to year and period
                    year = date.year
                    period = date.month  # For quarterly data, this would be 1,4,7,10
                    
                    rows.append({
                        'insId': instrument_id,
                        'year': year,
                        'period': period,
                        'kpiValue': value
                    })
        
        return pd.DataFrame(rows)

    @staticmethod
    def get_datastream_token(username, password):
        """
        Request and return an authentication token from Datastream Web Service.

        :param username: str, your Datastream username
        :param password: str, your Datastream password
        :return: str, token string
        :raises Exception if the request fails
        """
        token_url = f"https://product.datastream.com/dswsclient/V1/DSService.svc/rest/Token?username={username}&password={password}"
        
        response = requests.get(token_url)

        if response.status_code != 200:
            raise Exception(f"Failed to get token: Status {response.status_code}, Response: {response.text}")
        
        # Token is returned as a quoted string, so strip quotes if any
        response_json = response.text.strip('"')
        
        data = json.loads(response_json)
        
        token = data["TokenValue"]
        
        return token

    def fetch_datastream_timeseries(self, instrument, datatypes, start, end, frequency, kind=1):
        """
        Fetch time series data from Datastream Web Service using REST API.

        :param token: str, authentication token from token endpoint
        :param instrument: str, e.g. "VOD"
        :param datatypes: list of str, e.g. ["PL", "PH"]
        :param start: str, start date, relative e.g. '-30D' or absolute '2025-01-01'
        :param end: str, end date, relative e.g. '-20D' or absolute '2025-01-31'
        :param frequency: str, typically 'D' for daily, 'Q' for quarterly etc.
        :param kind: int, usually 1 for calendar day selection
        :return: dict with parsed data, keys are datatypes, each value is list of tuples (date, value)
        """

        # Get token
        token = self._get_token()

        url = "https://product.datastream.com/dswsclient/V1/DSService.svc/rest/GetData"

        # Build request payload structure
        payload = {
            "DataRequest": {
                "DataTypes": [{"Value": dtype} for dtype in datatypes],
                "Date": {
                    "Start": start,
                    "End": end,
                    "Frequency": frequency,
                    "Kind": kind
                },
                "Instrument": {
                    "Value": instrument
                },
            },
            "TokenValue": token
        }
        
        headers = {'Content-Type': 'application/json'}

        # POST request
        response = requests.post(url, data=json.dumps(payload), headers=headers)

        if response.status_code != 200:
            raise Exception(f"API request failed with status {response.status_code}: {response.text}")

        resp_json = response.json()

        # --- Handle missing or null Dates ---
        raw_dates = resp_json.get("DataResponse", {}).get("Dates")
        if not raw_dates:
            raise ValueError("No 'Dates' returned in response. Possibly no data available.")
        
        dates = []
        for d in raw_dates:
            # Extract milliseconds from /Date(...)/ format
            try:
                ms = int(d[d.find('(')+1 : d.find(')')].split('+')[0])
                dt = datetime.utcfromtimestamp(ms / 1000)
                dates.append(f"{dt.year}.{dt.month}.{dt.day}")
            except Exception:
                dates.append(None)

        data_by_type = {}

        # Parse each DataType and its values aligned with dates
        for i, dt_item in enumerate(resp_json.get("DataResponse", {}).get("DataTypeValues", [])):
            dtype = dt_item.get("DataType") or datatypes  # Use provided datatype or fallback to index
            data_by_type[dtype] = []

            for sym_val in dt_item.get("SymbolValues", []):
                # "Value" is list with time series matching dates array length
                values = sym_val.get("Value", [])
                if not isinstance(values, list):
                    values = [values]
                # Pair dates with values by index
                series = [(dates[j], values[j]) for j in range(min(len(dates), len(values)))]
                data_by_type[dtype].extend(series)

        return data_by_type
    
    def get_kpi_data_instrument(self, ins_id: int, kpi_id: str, calc_group: str, calc: str) -> pd.DataFrame:
        """
        Get KPI data for a single instrument (matching BorsdataAPI interface)
        :param ins_id: Instrument ID (will be used as mock ID)
        :param kpi_id: KPI field code (e.g., 'PL', 'PH', 'DEPS')
        :param calc_group: Time period (e.g., '1year', '3year') - not used in DSWS
        :param calc: Calculation type (e.g., 'latest', 'mean') - not used in DSWS
        :return: pandas DataFrame in Borsdata format
        """
        # Map calc_group to date range
        date_mapping = {
            '1year': ('-1Y', '-0D'),
            '3year': ('-3Y', '-0D'),
            '5year': ('-5Y', '-0D'),
            '7year': ('-7Y', '-0D'),
            '10year': ('-10Y', '-0D'),
            '15year': ('-15Y', '-0D')
        }
        
        start_date, end_date = date_mapping.get(calc_group, ('-1Y', '-0D'))
        
        # For now, use a mock instrument symbol - this should be replaced with actual symbol mapping
        instrument_symbol = f"STOCK_{ins_id}"  # Placeholder
        
        try:
            token = self._get_token()
            dsws_data = self.fetch_datastream_timeseries(
                token=token,
                instrument=instrument_symbol,
                datatypes=[kpi_id],
                start=start_date,
                end=end_date,
                frequency='D'  # Daily data
            )
            
            return self._convert_dsws_to_borsdata_format(dsws_data, ins_id)
            
        except Exception as e:
            print(f"Error fetching KPI data for instrument {ins_id}: {e}")
            return pd.DataFrame()
    
    def get_kpi_data_all_instruments(self, kpi_id: str, calc_group: str, calc: str) -> pd.DataFrame:
        """
        Get KPI data for all instruments (matching BorsdataAPI interface)
        :param kpi_id: KPI field code
        :param calc_group: Time period
        :param calc: Calculation type
        :return: pandas DataFrame in Borsdata format
        """
        # For now, return empty DataFrame - this would need a list of instruments
        # In a real implementation, you would iterate through all instruments
        return pd.DataFrame()
    
    def get_instruments(self) -> pd.DataFrame:
        """
        Get instruments data (matching BorsdataAPI interface)
        :return: pandas DataFrame with instruments
        """
        # Mock instruments data with required columns for UI compatibility
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        PACKAGE_ROOT = os.path.dirname(BASE_DIR)
        stocks_json_path = os.path.join(PACKAGE_ROOT, 'data', 'stocks.json')
        
        with open(stocks_json_path, 'r') as f:
            stocks_json = json.load(f)
        return pd.DataFrame(stocks_json)
    
    def get_countries(self) -> pd.DataFrame:
        """
        Get countries data (matching BorsdataAPI interface)
        :return: pandas DataFrame with countries
        """
        # Mock countries data - in real implementation, this would come from RDP
        mock_countries = [
            {'id': 1, 'name': 'United States'},
            {'id': 2, 'name': 'United Kingdom'},
            {'id': 3, 'name': 'Germany'},
            {'id': 4, 'name': 'France'},
            {'id': 5, 'name': 'Japan'},
        ]
        return pd.DataFrame(mock_countries)
    
    def get_markets(self) -> pd.DataFrame:
        """
        Get markets data (matching BorsdataAPI interface)
        :return: pandas DataFrame with markets
        """
        # Mock markets data with countryId for filtering
        mock_markets = [
            {'id': 1, 'name': 'NYSE', 'countryId': 1},
            {'id': 2, 'name': 'NASDAQ', 'countryId': 1},
            {'id': 3, 'name': 'LSE', 'countryId': 2},
            {'id': 4, 'name': 'DAX', 'countryId': 3},
            {'id': 5, 'name': 'CAC', 'countryId': 4},
        ]
        return pd.DataFrame(mock_markets)
    
    def get_sectors(self) -> pd.DataFrame:
        """
        Get sectors data (matching BorsdataAPI interface)
        :return: pandas DataFrame with sectors
        """
        # Mock sectors data
        mock_sectors = [
            {'id': 1, 'name': 'Technology'},
            {'id': 2, 'name': 'Healthcare'},
            {'id': 3, 'name': 'Financial Services'},
            {'id': 4, 'name': 'Consumer Goods'},
            {'id': 5, 'name': 'Energy'},
        ]
        return pd.DataFrame(mock_sectors)
    
    def get_branches(self) -> pd.DataFrame:
        """
        Get branches data (matching BorsdataAPI interface)
        :return: pandas DataFrame with branches
        """
        # Mock branches data with sectorId for filtering
        mock_branches = [
            {'id': 1, 'name': 'Software', 'sectorId': 1},
            {'id': 2, 'name': 'Hardware', 'sectorId': 1},
            {'id': 3, 'name': 'Biotechnology', 'sectorId': 2},
            {'id': 4, 'name': 'Pharmaceuticals', 'sectorId': 2},
            {'id': 5, 'name': 'Banking', 'sectorId': 3},
            {'id': 6, 'name': 'E-commerce', 'sectorId': 4},
        ]
        return pd.DataFrame(mock_branches)

# Example of usage:
if __name__ == "__main__":
    # Test the RefinitivAPI class
    api = RefinitivAPI()
    
    # Test KPI data fetching
    try:
        kpi_data = api.get_kpi_data_instrument(
            ins_id=1, 
            kpi_id="PL", 
            calc_group="1year", 
            calc="latest"
        )
    except Exception as e:
        print("Error:", e)
