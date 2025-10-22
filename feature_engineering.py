# feature_engineering.py

from smartmoneyconcepts import smc
import pandas as pd

def engineer_features(df: pd.DataFrame, swing_length=7):
    # SMC features
    swings = smc.swing_highs_lows(df, swing_length=swing_length)
    fvg = smc.fvg(df)
    ob = smc.ob(df, swings)
    
    # Rename columns for clustering model
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
    # Merge into one DataFrame (like in notebook)
    feat = pd.concat([
        df.reset_index(drop=True),
        fvg_renamed,
        ob_renamed,
        swings_renamed
    ], axis=1)
    # Fill NaNs for safety
    feat = feat.fillna(0)
    return feat
