import pandas as pd
import numpy as np
import json
import argparse
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

def parse_json_data(filepath):
    # Load and flatten JSON transaction data into a DataFrame
    print(f"Loading data from {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            raw = json.load(file)
    except Exception as e:
        print(f"Oops, couldn't load JSON: {e}")
        return pd.DataFrame()

    print("Converting JSON to a table...")
    df = pd.json_normalize(raw)

    # Clean up column names for easier use
    name_map = {
        'userWallet': 'user_id',
        'action': 'type',
        'actionData.assetSymbol': 'asset_symbol',
        'actionData.amount': 'amount_raw',
        'actionData.assetPriceUSD': 'asset_price_usd',
        'actionData.principalAmount': 'principal_amount_raw',
        'actionData.borrowAssetPriceUSD': 'principal_price_usd',
        'actionData.collateralAmount': 'collateral_amount_raw',
        'actionData.collateralAssetPriceUSD': 'collateral_price_usd'
    }
    df.rename(columns={k: v for k, v in name_map.items() if k in df.columns}, inplace=True)

    # Convert timestamp to datetime if it exists
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')

    # Ensure numeric columns are properly typed and handle missing values
    numeric_cols = [
        'amount_raw', 'asset_price_usd',
        'principal_amount_raw', 'principal_price_usd',
        'collateral_amount_raw', 'collateral_price_usd'
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df.get(col, 0), errors='coerce')
    df[numeric_cols] = df[numeric_cols].fillna(0)

    # Calculate USD values for amounts
    df['amountUSD'] = df['amount_raw'] * df['asset_price_usd']
    df['principalAmountUSD'] = df['principal_amount_raw'] * df['principal_price_usd']
    df['collateralAmountUSD'] = df['collateral_amount_raw'] * df['collateral_price_usd']

    print(f"Parsed {len(df)} transactions.")
    return df

def build_features(df):
    # Create wallet-level features from transaction data
    print("Building features for each wallet...")
    features = []

    for wallet in df['user_id'].unique():
        txs = df[df['user_id'] == wallet].sort_values('timestamp')
        if txs.empty:
            continue

        # Calculate wallet age and transaction frequency
        age = (txs['timestamp'].max() - txs['timestamp'].min()).days
        count = len(txs)
        avg_gap = (age * 24) / count if count > 1 else 0

        # Analyze liquidations
        liq = txs[txs['type'] == 'liquidation']
        liq_count = len(liq)
        liq_usd = liq['principalAmountUSD'].sum()

        # Sum up deposits, borrows, and repays
        deposits = txs[txs['type'] == 'deposit']
        borrows = txs[txs['type'] == 'borrow']
        repays = txs[txs['type'] == 'repay']
        dep = deposits['amountUSD'].sum()
        bor = borrows['amountUSD'].sum()
        rep = repays['amountUSD'].sum()

        # Calculate health and repayment ratios
        health = dep / bor if bor else dep
        repay_ratio = min(rep / bor, 1.0) if bor else 1.0
        assets = txs['asset_symbol'].nunique()

        features.append({
            'wallet_id': wallet,
            'wallet_age_days': age,
            'transaction_count': count,
            'avg_time_between_txs_hours': avg_gap,
            'liquidation_count': liq_count,
            'total_liquidated_usd': liq_usd,
            'total_deposited_usd': dep,
            'total_borrowed_usd': bor,
            'health_ratio': health,
            'repay_to_borrow_ratio': repay_ratio,
            'unique_assets_used': assets
        })

    print(f"Extracted features for {len(features)} wallets.")
    return pd.DataFrame(features)

def credit_score_pipeline(features):
    # Generate credit scores based on weighted features
    print("\nCalculating credit scores...")
    if features.empty:
        print("No data to score.")
        return pd.DataFrame()

    # Define weights for scoring
    weights = {
        'wallet_age_days': 0.10,
        'transaction_count': 0.05,
        'avg_time_between_txs_hours': 0.05,
        'liquidation_count': -0.40,
        'health_ratio': 0.20,
        'repay_to_borrow_ratio': 0.15,
        'unique_assets_used': 0.05,
    }

    score_df = features[list(weights)]
    score_df['health_ratio'] = score_df['health_ratio'].replace([np.inf, -np.inf], 0)
    score_df['health_ratio'] = score_df['health_ratio'].clip(upper=score_df['health_ratio'].max())

    # Normalize features for consistent scoring
    scaler = MinMaxScaler()
    for col, w in weights.items():
        if w > 0:
            score_df[[col]] = scaler.fit_transform(score_df[[col]])

    # Compute weighted scores and scale to 0-1000
    score_values = np.dot(score_df.values, np.array(list(weights.values())))
    scaled = MinMaxScaler((0, 1000)).fit_transform(score_values.reshape(-1, 1))

    features['credit_score'] = scaled.astype(int)
    return features.sort_values(by='credit_score', ascending=False).reset_index(drop=True)

def plot_scores(df, output='score_distribution.png'):
    # Plot a histogram of credit scores
    print(f"Generating histogram and saving to {output}...")
    plt.figure(figsize=(10, 6))
    sns.histplot(df['credit_score'], bins=25, kde=True, color='steelblue')
    plt.title("Wallet Credit Scores")
    plt.xlabel("Score")
    plt.ylabel("Wallets")
    plt.tight_layout()
    plt.savefig(output)
    print("Histogram saved.")

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Generate credit scores from DeFi transaction data.")
    parser.add_argument("input_file", help="Path to JSON file with transactions.")
    parser.add_argument("--output_file", default="wallet_scores.csv", help="Output CSV file for scores.")
    args = parser.parse_args()

    # Run the pipeline
    tx_data = parse_json_data(args.input_file)
    if tx_data.empty:
        print("⚠ Failed to process input file.")
        exit()

    features = build_features(tx_data)
    results = credit_score_pipeline(features)

    if not results.empty:
        results.to_csv(args.output_file, index=False)
        print(f"Scores saved to {args.output_file}")
        print("Top 5 wallets:\n", results.head())
        plot_scores(results)
    else:
        print("No results to save — data is empty.")