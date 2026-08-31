import os
import pandas as pd
from datetime import datetime, timedelta

def generate_procurement_dataset(output_path: str = "src/ml/historical_inventory_data.csv"):
    """Generates 90 days of deterministic inventory history for forecast status testing.

    Targets with 75-day lead-time buffer logic:
    - Wheat Flour: Stable (>105 days remaining)
    - Liquid Glucose: Low Stock (76-105 days remaining)
    - Baking Soda: Critical Stockout Risk (<=75 days remaining)
    """

    # Each item is configured to end the 90-day history in a specific status band.
    items = {
        "Wheat Flour": {"daily_consumption": 500, "target_days_remaining": 140, "unit": "kg"},
        "Liquid Glucose": {"daily_consumption": 180, "target_days_remaining": 90, "unit": "liters"},
        "Baking Soda": {"daily_consumption": 40, "target_days_remaining": 30, "unit": "kg"},
    }

    history_days = 90
    start_date = datetime.now() - timedelta(days=90)
    records = []

    for item_name, specs in items.items():
        burn_rate = specs["daily_consumption"]
        target_days_remaining = specs["target_days_remaining"]

        # Keep stock trend linear so model burn-rate estimation remains stable.
        start_stock = burn_rate * (target_days_remaining + (history_days - 1))
        current_stock = float(start_stock)

        for day in range(history_days):
            current_date = start_date + timedelta(days=day)

            units_consumed = float(burn_rate)

            # Deplete stock
            current_stock = max(0, current_stock - units_consumed)

            records.append({
                "item_name": item_name,
                "date": current_date.strftime("%Y-%m-%d"),
                "units_sold": units_consumed,  # Represents units consumed in production
                "current_stock": current_stock
            })

    df = pd.DataFrame(records)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Dataset successfully generated and saved to: {output_path}")
    return output_path

if __name__ == "__main__":
    generate_procurement_dataset()