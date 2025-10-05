"""
Binance API service for fetching market data
"""
import pandas as pd
from binance.client import Client
from datetime import datetime
import sys
import os

# Add parent directory to path to import feature_engineering
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from feature_engineering import engineer_features


class BinanceService:
    def __init__(self, api_key=None, api_secret=None):
        """
        Initialize Binance client
        API keys are optional - public endpoints don't need authentication
        """
        self.client = Client(api_key, api_secret)

    def fetch_klines(self, symbol='BTCUSDT', interval='15m', limit=100):
        """
        Fetch candlestick data from Binance

        Args:
            symbol: Trading pair (default: BTCUSDT)
            interval: Timeframe (default: 15m)
            limit: Number of candles to fetch (default: 100)

        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Fetch klines from Binance
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )

            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])

            # Convert types
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')

            # Convert price/volume columns to float
            for col in ['open', 'high', 'low', 'close', 'volume',
                       'quote_asset_volume', 'taker_buy_base_asset_volume',
                       'taker_buy_quote_asset_volume']:
                df[col] = df[col].astype(float)

            df['number_of_trades'] = df['number_of_trades'].astype(int)

            # Drop the 'ignore' column
            df = df.drop('ignore', axis=1)

            # Set open_time as index
            df.set_index('open_time', inplace=True)

            return df

        except Exception as e:
            raise Exception(f"Error fetching data from Binance: {str(e)}")

    def fetch_latest_price(self, symbol='BTCUSDT'):
        """
        Fetch current price for a symbol

        Args:
            symbol: Trading pair

        Returns:
            float: Current price
        """
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            raise Exception(f"Error fetching price: {str(e)}")

    def get_signal_data(self, symbol='BTCUSDT', interval='15m', limit=100, swing_length=7):
        """
        Fetch data and calculate features for signal generation

        Args:
            symbol: Trading pair
            interval: Timeframe
            limit: Number of candles
            swing_length: Swing detection length

        Returns:
            tuple: (DataFrame with features, latest candle data)
        """
        try:
            # Fetch klines
            df = self.fetch_klines(symbol, interval, limit)

            # Engineer features using the imported function
            df_with_features = engineer_features(df, swing_length=swing_length)

            # Get latest candle
            latest = df_with_features.iloc[-1]

            return df_with_features, latest

        except Exception as e:
            raise Exception(f"Error preparing signal data: {str(e)}")
