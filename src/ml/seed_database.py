import os
import pandas as pd
from datetime import datetime
from src.data_logic.postgres import SessionLocal
from src.models.inventory_model import InventoryHistory

def seed_inventory_data(csv_path: str = "src/ml/historical_inventory_data.csv"):
    """Reads the generated CSV dataset, shifts dates relative to today, and seeds it into PostgreSQL."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found at {csv_path}. Run generate_mock_data.py first.")

    df = pd.read_csv(csv_path)
    
    # Convert CSV date column to datetime
    df["date"] = pd.to_datetime(df["date"])
    
    # Find the maximum date currently in the CSV
    max_csv_date = df["date"].max()
    
    # Calculate the offset required to make the last date equal to today's date
    today = datetime.now().date()
    date_offset = today - max_csv_date.date()
    
    with SessionLocal() as session:
        # Clear existing mock records to avoid duplication on re-runs
        session.query(InventoryHistory).delete()
        
        records_added = 0
        for _, row in df.iterrows():
            # Shift historical date forward by the calculated offset
            shifted_date = (row["date"] + date_offset).date()
            
            inventory_record = InventoryHistory(
                item_name=row["item_name"],
                date=shifted_date,
                units_sold=float(row["units_sold"]),
                current_stock=float(row["current_stock"])
            )
            session.add(inventory_record)
            records_added += 1
            
        session.commit()
        print(f"Successfully seeded {records_added} inventory history records anchored to today ({today}).")

if __name__ == "__main__":
    seed_inventory_data()

# def seed_inventory_data(csv_path: str = "src/ml/historical_inventory_data.csv"):
#     """Reads the generated CSV dataset and seeds it into the PostgreSQL database."""
#     if not os.path.exists(csv_path):
#         raise FileNotFoundError(f"Dataset not found at {csv_path}. Run generate_mock_data.py first.")

#     df = pd.read_csv(csv_path)
    
#     with SessionLocal() as session:
#         # Clear existing mock records to avoid duplication on re-runs
#         session.query(InventoryHistory).delete()
        
#         records_added = 0
#         for _, row in df.iterrows():
#             inventory_record = InventoryHistory(
#                 item_name=row["item_name"],
#                 date=datetime.strptime(row["date"], "%Y-%m-%d").date(),
#                 units_sold=float(row["units_sold"]),
#                 current_stock=float(row["current_stock"])
#             )
#             session.add(inventory_record)
#             records_added += 1
            
#         session.commit()
#         print(f"Successfully seeded {records_added} inventory history records into PostgreSQL.")

# if __name__ == "__main__":
#     seed_inventory_data()