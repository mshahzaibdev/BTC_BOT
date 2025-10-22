"""
Backtest the ICT Trading Bot on Historical Data
Tests the feature engineering and signal generation pipeline
"""
import pandas as pd
import numpy as np
import joblib
import os
from datetime import datetime
from collections import Counter

# Import feature engineering from bot_integrated
import sys
sys.path.append(os.path.dirname(__file__))

# Load models
SCALER_PATH = './scaler.pkl'
KMEANS_PATH = './kmeans.pkl'
SWING_LENGTH = int(os.getenv('SWING_LENGTH', '15'))

print("="*80)
print("ICT TRADING BOT BACKTEST")
print("="*80)

# Feature columns
FEATURE_COLUMNS = [
    'FVG_flag', 'FVG_Top', 'FVG_Bottom',
    'OB_flag', 'OB_Top', 'OB_Bottom',
    'Swing_HighLow', 'Swing_Level'
]


def engineer_features_backtest(df: pd.DataFrame, swing_length=15):
    """Engineer features for backtest"""
    print(f"\n[FEATURE_ENG] Processing {len(df)} candles, swing_length={swing_length}")

    try:
        from smartmoneyconcepts import smc

        # Calculate features
        swings = smc.swing_highs_lows(df, swing_length=swing_length)
        fvg = smc.fvg(df)
        ob = smc.ob(df, swings)

        # Rename columns
        fvg_renamed = fvg.rename(columns={
            'FVG': 'FVG_flag',
            'Top': 'FVG_Top',
            'Bottom': 'FVG_Bottom',
            'MitigatedIndex': 'FVG_MitigatedIndex'
        })

        ob_renamed = ob.rename(columns={
            'OB': 'OB_flag',
            'Top': 'OB_Top',
            'Bottom': 'OB_Bottom',
            'OBVolume': 'OB_Volume',
            'MitigatedIndex': 'OB_MitigatedIndex',
            'Percentage': 'OB_Percentage'
        })

        swings_renamed = swings.rename(columns={
            'HighLow': 'Swing_HighLow',
            'Level': 'Swing_Level'
        })

        # Merge
        feat = pd.concat([
            df.reset_index(drop=True),
            fvg_renamed,
            ob_renamed,
            swings_renamed
        ], axis=1)

        feat = feat.fillna(0)
        print(f"[FEATURE_ENG] ✅ Complete: {len(feat)} rows, {len(feat.columns)} columns")

        return feat

    except Exception as e:
        print(f"[FEATURE_ENG] ❌ ERROR: {e}")
        raise


def predict_signal(candle_data, scaler, kmeans):
    """Predict signal from candle data"""
    try:
        # Extract features
        features = []
        for col in FEATURE_COLUMNS:
            value = candle_data[col] if col in candle_data else 0
            if pd.isna(value):
                value = 0
            features.append(value)

        # Scale and predict
        features_array = np.array(features).reshape(1, -1)
        features_scaled = scaler.transform(features_array)
        cluster = int(kmeans.predict(features_scaled)[0])

        # Map cluster to signal
        if cluster == 4:
            signal = 'BUY'
        elif cluster == 3:
            signal = 'SHORT'
        else:
            signal = 'NEUTRAL'

        return signal, cluster

    except Exception as e:
        print(f"[PREDICTION] ❌ ERROR: {e}")
        return 'ERROR', -1


def backtest_on_historical_data(csv_path, lookback=100, swing_length=15):
    """
    Run backtest on historical data

    Args:
        csv_path: Path to historical CSV file
        lookback: Number of candles to use for feature calculation
        swing_length: Swing detection length
    """
    print(f"\n[BACKTEST] Loading historical data from: {csv_path}")

    # Load data
    df = pd.read_csv(csv_path)
    print(f"[BACKTEST] Loaded {len(df)} candles")
    print(f"[BACKTEST] Date range: {df['open_time'].iloc[0]} to {df['open_time'].iloc[-1]}")

    # Convert columns to proper types
    df['open_time'] = pd.to_datetime(df['open_time'])
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    # Load models
    print(f"\n[BACKTEST] Loading models...")
    scaler = joblib.load(SCALER_PATH)
    kmeans = joblib.load(KMEANS_PATH)
    print(f"[BACKTEST] ✅ Models loaded")

    # Results storage
    results = []
    signal_changes = []
    last_signal = None

    print(f"\n[BACKTEST] Starting simulation with {lookback} candle lookback...")
    print("="*80)

    # Simulate checking signals every candle (like the bot does every 15 min)
    for i in range(lookback, len(df)):
        # Get lookback window
        window = df.iloc[i-lookback:i+1].copy()
        window = window.reset_index(drop=True)

        # Set proper index for SMC calculations
        window_for_smc = window.set_index('open_time')

        try:
            # Engineer features
            window_with_features = engineer_features_backtest(window_for_smc, swing_length=swing_length)

            # Get latest candle
            latest = window_with_features.iloc[-1]

            # Predict signal
            signal, cluster = predict_signal(latest, scaler, kmeans)

            # Record result
            current_time = df.iloc[i]['open_time']
            current_price = df.iloc[i]['close']

            result = {
                'timestamp': current_time,
                'price': current_price,
                'signal': signal,
                'cluster': cluster,
                'FVG_flag': latest.get('FVG_flag', 0),
                'OB_flag': latest.get('OB_flag', 0),
                'Swing_Level': latest.get('Swing_Level', 0)
            }
            results.append(result)

            # Track signal changes
            if signal != last_signal and signal in ['BUY', 'SHORT']:
                signal_changes.append({
                    'timestamp': current_time,
                    'price': current_price,
                    'signal': signal,
                    'cluster': cluster
                })
                print(f"\n[SIGNAL CHANGE] {signal} at {current_time}")
                print(f"   Price: ${current_price:,.2f}")
                print(f"   Cluster: {cluster}")

            last_signal = signal

            # Progress indicator
            if (i - lookback) % 100 == 0:
                progress = ((i - lookback) / (len(df) - lookback)) * 100
                print(f"[PROGRESS] {progress:.1f}% - Candle {i-lookback}/{len(df)-lookback}")

        except Exception as e:
            print(f"[ERROR] Failed at candle {i}: {e}")
            continue

    print("\n" + "="*80)
    print("BACKTEST COMPLETE")
    print("="*80)

    # Convert results to DataFrame
    results_df = pd.DataFrame(results)

    # Analysis
    print(f"\nRESULTS SUMMARY:")
    print(f"   Total Candles Analyzed: {len(results_df)}")
    print(f"   Date Range: {results_df['timestamp'].iloc[0]} to {results_df['timestamp'].iloc[-1]}")

    # Signal distribution
    signal_counts = Counter(results_df['signal'])
    print(f"\nSignal Distribution:")
    for signal, count in signal_counts.items():
        percentage = (count / len(results_df)) * 100
        print(f"   {signal}: {count} ({percentage:.1f}%)")

    # Cluster distribution
    cluster_counts = Counter(results_df['cluster'])
    print(f"\nCluster Distribution:")
    for cluster, count in sorted(cluster_counts.items()):
        percentage = (count / len(results_df)) * 100
        print(f"   Cluster {cluster}: {count} ({percentage:.1f}%)")

    # Signal changes
    print(f"\nTrading Signals (BUY/SHORT changes):")
    print(f"   Total Signal Changes: {len(signal_changes)}")

    if signal_changes:
        print(f"\n   Signal History:")
        for i, change in enumerate(signal_changes[:20], 1):  # Show first 20
            print(f"   {i}. {change['timestamp']} | {change['signal']} @ ${change['price']:,.2f} (Cluster {change['cluster']})")

        if len(signal_changes) > 20:
            print(f"   ... and {len(signal_changes) - 20} more signals")

    # Feature activity
    fvg_active = (results_df['FVG_flag'] == 1).sum()
    ob_active = (results_df['OB_flag'] == 1).sum()
    swing_active = (results_df['Swing_Level'] > 0).sum()

    print(f"\nFeature Activity:")
    print(f"   Fair Value Gaps (FVG): {fvg_active} candles ({(fvg_active/len(results_df)*100):.1f}%)")
    print(f"   Order Blocks (OB): {ob_active} candles ({(ob_active/len(results_df)*100):.1f}%)")
    print(f"   Swing Levels: {swing_active} candles ({(swing_active/len(results_df)*100):.1f}%)")

    # Save results
    output_file = 'backtest_results.csv'
    results_df.to_csv(output_file, index=False)
    print(f"\nResults saved to: {output_file}")

    # Save signal changes
    if signal_changes:
        signals_df = pd.DataFrame(signal_changes)
        signals_output = 'backtest_signals.csv'
        signals_df.to_csv(signals_output, index=False)
        print(f"Signal changes saved to: {signals_output}")

    print("\n" + "="*80)

    return results_df, signal_changes


if __name__ == '__main__':
    # Run backtest
    csv_path = r'E:\Gift Oversight\ai\ict trader app\app\backend\ict-backend\historical_data\BTCUSDT_15m_2025_10.csv'

    print("\nCONFIGURATION:")
    print(f"   Data File: {csv_path}")
    print(f"   Lookback: 100 candles")
    print(f"   Swing Length: {SWING_LENGTH}")
    print(f"   Scaler: {SCALER_PATH}")
    print(f"   KMeans: {KMEANS_PATH}")

    results_df, signal_changes = backtest_on_historical_data(
        csv_path=csv_path,
        lookback=100,
        swing_length=SWING_LENGTH
    )

    print("\nBacktest complete!")
