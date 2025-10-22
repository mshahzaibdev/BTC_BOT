"""
ML Prediction service for signal generation
"""
import joblib
import numpy as np
import pandas as pd
import os


class PredictionService:
    def __init__(self, scaler_path='../scaler.pkl', kmeans_path='../kmeans.pkl'):
        """
        Initialize prediction service with trained models

        Args:
            scaler_path: Path to StandardScaler pickle file
            kmeans_path: Path to KMeans pickle file
        """
        try:
            # Load models
            self.scaler = joblib.load(scaler_path)
            self.kmeans = joblib.load(kmeans_path)
            print(f"✅ Models loaded successfully")
            print(f"   - Scaler: {scaler_path}")
            print(f"   - KMeans: {kmeans_path}")
        except Exception as e:
            raise Exception(f"Error loading models: {str(e)}")

        # Define feature columns (must match training)
        self.feature_columns = [
            'FVG_flag',
            'FVG_Top',
            'FVG_Bottom',
            'OB_flag',
            'OB_Top',
            'OB_Bottom',
            'Swing_HighLow',
            'Swing_Level'
        ]

    def predict_signal(self, candle_data):
        """
        Predict trading signal from candle data

        Args:
            candle_data: Series or dict with SMC features

        Returns:
            dict: {
                'signal': 'buy' | 'short' | 'neutral',
                'cluster': int (0-4),
                'explanation': str,
                'features': dict of feature values
            }
        """
        try:
            # Extract features
            features = []
            feature_dict = {}

            for col in self.feature_columns:
                value = candle_data[col] if col in candle_data else 0
                # Handle NaN values
                if pd.isna(value):
                    value = 0
                features.append(value)
                feature_dict[col] = float(value)

            # Convert to numpy array and reshape for prediction
            features_array = np.array(features).reshape(1, -1)

            # Scale features
            features_scaled = self.scaler.transform(features_array)

            # Predict cluster
            cluster = int(self.kmeans.predict(features_scaled)[0])

            # Map cluster to signal
            if cluster == 4:
                signal = 'buy'
                explanation = "Cluster 4 detected - Bullish pattern identified"
            elif cluster == 3:
                signal = 'short'
                explanation = "Cluster 3 detected - Bearish pattern identified"
            else:
                signal = 'neutral'
                explanation = f"Cluster {cluster} detected - No clear directional bias"

            return {
                'signal': signal,
                'cluster': cluster,
                'explanation': explanation,
                'features': feature_dict
            }

        except Exception as e:
            raise Exception(f"Error predicting signal: {str(e)}")

    def get_cluster_info(self, cluster_id):
        """
        Get information about a specific cluster

        Args:
            cluster_id: Cluster number (0-4)

        Returns:
            dict: Cluster information
        """
        cluster_descriptions = {
            0: {
                'name': 'Neutral Zone A',
                'description': 'No strong directional indicators',
                'action': 'Wait for clearer signal'
            },
            1: {
                'name': 'Neutral Zone B',
                'description': 'Mixed signals, uncertain market structure',
                'action': 'Avoid trading'
            },
            2: {
                'name': 'Neutral Zone C',
                'description': 'Choppy price action',
                'action': 'Stay on sidelines'
            },
            3: {
                'name': 'Bearish Pattern',
                'description': 'Smart Money Concepts indicate selling pressure',
                'action': 'Consider SHORT positions'
            },
            4: {
                'name': 'Bullish Pattern',
                'description': 'Smart Money Concepts indicate buying pressure',
                'action': 'Consider LONG positions'
            }
        }

        return cluster_descriptions.get(cluster_id, {
            'name': 'Unknown',
            'description': 'Invalid cluster ID',
            'action': 'Error'
        })
