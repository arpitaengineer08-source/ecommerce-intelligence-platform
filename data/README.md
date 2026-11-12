# Data

| Folder | Content |
|---|---|
| `raw/` | Source CSVs (9 Olist files). Git-ignored. Generated automatically as **synthetic** data when missing. |
| `processed/` | Pipeline outputs: RFM, cohorts, forecast, churn scores, recommendations, `powerbi/` star-schema CSVs. |

## Using the real Olist dataset
1. Download *Brazilian E-Commerce Public Dataset by Olist* from Kaggle:
   https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce (free account, CC BY-NC-SA 4.0 licence).
2. Copy the 9 CSV files into `data/raw/` (overwrite the synthetic ones, keep the original file names).
3. Run `python run_pipeline.py --real`.

The raw data is not committed because of size and licence terms. A small synthetic sample is generated for demos and tests.

## Limits of the dataset (do not over-claim)
No product cost, inventory, web-session or cart data. Profit, stock-outs and cart abandonment cannot be computed from it.
