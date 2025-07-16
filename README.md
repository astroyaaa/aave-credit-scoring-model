# Aave Wallet Credit Scoring Model

This project offers a reliable, rule-based algorithm that gives Aave wallets a credit score ranging from 0 to 1000.  Higher ratings indicate dependable usage, while lower scores imply risky or uncommon behavior. The score is based only on a wallet's past transaction behavior.

## Methodology & Scoring Logic

A rule-based, unsupervised model is used to calculate the credit score.  We define creditworthiness using a set of clear, explicable criteria that are derived from raw transaction data because there is no "ground truth" for a good or bad wallet.

The fundamental idea is that a "good" wallet is one that avoids liquidation, manages its debt sensibly, and participates in the protocol for an extended period of time.  A wallet is considered "bad" if it is liquidated, has a lot of low-value transactions, or borrows money and doesn't pay it back.

### Key Features Engineered

The following characteristics, which are determined for every wallet, form the basis of the model:

-   **`wallet_age_days`**: The number of days between the wallet's first and last transaction. *Rationale: Rewards long-term, consistent users.*
-   **`transaction_count`**: The total number of transactions. *Rationale: Measures user activity level.*
-   **`avg_time_between_txs_hours`**: The average time between consecutive transactions. *Rationale: Helps distinguish human users from high-frequency bots.*
-   **`liquidation_count`**: The number of times a wallet's position has been liquidated. *Rationale: This is the strongest signal of high-risk behavior and is heavily penalized.*
-   **`health_ratio`**: A proxy for the Aave Health Factor, calculated as `Total USD Deposited / Total USD Borrowed`. *Rationale: A high ratio indicates the user maintains a safe buffer of collateral against their debt.*
-   **`repay_to_borrow_ratio`**: The ratio of `Total USD Repaid / Total USD Borrowed`. *Rationale: A ratio near 1.0 is a powerful indicator of a responsible borrower.*
-   **`unique_assets_used`**: The number of different crypto assets the wallet has interacted with. *Rationale: A proxy for user sophistication and diversification.*

### Scoring Process

The final score is calculated in a four-step process:

1.  **Feature Engineering**: The raw transaction log is processed to compute the features listed above for every unique wallet.
2.  **Normalization**: All features are scaled to a common range (0-1) using a Min-Max Scaler. This prevents features with naturally large values from overpowering features with small values.
3.  **Weighted Summation**: Each normalized feature is multiplied by a predefined weight, reflecting its importance in our credit model. Negative features like `liquidation_count` have negative weights. The results are summed to produce a "raw score".
4.  **Final Scaling**: The raw scores are scaled to the final 0-1000 range to produce the definitive credit score.

## How to Run the Scorer

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd <repo-folder-name>
    ```
2.  **Set up a Python virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On macOS/Linux
    .\venv\Scripts\activate  # On Windows
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: You will need to create a `requirements.txt` file with `pip freeze > requirements.txt`)*
4.  **Place data:**
    Download the transaction data JSON file and place it in a `data/` directory.
5.  **Run the script:**
    ```bash
    python credit_scorer.py data/user-wallet-transactions.json
    ```
    This will generate `wallet_scores.csv` and `score_distribution.png` in the root directory.
