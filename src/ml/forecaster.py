import pandas as pd
from datetime import timedelta
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from src.data_logic.postgres import SessionLocal
from src.models.inventory_model import InventoryHistory

class InventoryForecaster:
    def __init__(self):
        self.model = LinearRegression()

    def list_items(self) -> list[str]:
        """Returns the distinct product/item names tracked in inventory history."""
        with SessionLocal() as session:
            rows = session.query(InventoryHistory.item_name).distinct().all()
            return sorted(r[0] for r in rows)

    def load_from_db(self, item_name: str) -> pd.DataFrame:
        """Fetches historical records for a specific item directly from PostgreSQL."""
        with SessionLocal() as session:
            records = session.query(InventoryHistory).filter(
                InventoryHistory.item_name.ilike(item_name)
            ).order_by(InventoryHistory.date.asc()).all()

            if not records:
                raise ValueError(f"No historical records found in database for item: {item_name}")

            data = [{
                "date": r.date,
                "units_sold": r.units_sold,
                "current_stock": r.current_stock
            } for r in records]

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df["day_index"] = (df["date"] - df["date"].min()).dt.days
        return df

    # def train_and_evaluate(self, item_name: str) -> dict:
    #     df = self.load_from_db(item_name)
        
    #     X = df[["day_index"]]
    #     y = df["current_stock"]
        
    #     X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    #     self.model.fit(X_train, y_train)
        
    #     predictions = self.model.predict(X_test)
    #     mae = mean_absolute_error(y_test, predictions)
        
    #     self.model.fit(X, y)
    #     daily_burn_rate = abs(self.model.coef_[0])
        
    #     latest_stock = df["current_stock"].iloc[-1]
    #     latest_date = df["date"].iloc[-1]
        
    #     days_remaining = int(latest_stock / daily_burn_rate) if daily_burn_rate > 0 else 999
    #     stockout_date = latest_date + timedelta(days=days_remaining)
        
    #     return {
    #         "item_name": item_name,
    #         "evaluation_mae_units": round(mae, 2),
    #         "daily_burn_rate": round(daily_burn_rate, 2),
    #         "current_stock": int(latest_stock),
    #         "estimated_days_remaining": days_remaining,
    #         "projected_stockout_date": stockout_date.strftime("%Y-%m-%d"),
    #         "recommended_reorder_date": (latest_date + timedelta(days=max(0, days_remaining - 14))).strftime("%Y-%m-%d")
    #     }
    
    def train_and_evaluate(self, item_name: str, lead_time_days: int = 60, safety_stock_days: int = 15) -> dict:
        df = self.load_from_db(item_name)
        
        X = df[["day_index"]]
        y = df["current_stock"]
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
        self.model.fit(X_train, y_train)
        
        predictions = self.model.predict(X_test)
        mae = mean_absolute_error(y_test, predictions)
        
        self.model.fit(X, y)
        daily_burn_rate = abs(self.model.coef_[0])
        
        latest_stock = df["current_stock"].iloc[-1]
        latest_date = df["date"].iloc[-1]
        
        days_remaining = int(latest_stock / daily_burn_rate) if daily_burn_rate > 0 else 999
        stockout_date = latest_date + timedelta(days=days_remaining)
        
        # --- NEW LOGIC: International Supply Chain Buffers ---
        critical_threshold = lead_time_days + safety_stock_days # e.g., 60 + 15 = 75 days
        reorder_trigger_date = latest_date + timedelta(days=max(0, days_remaining - critical_threshold))
        
        if days_remaining <= critical_threshold:
            status = "Critical Stockout Risk (Reorder Now)"
        elif days_remaining <= (critical_threshold + 30):
            status = "Low Stock (Prepare PO)"
        else:
            status = "Stable"

        return {
            "item_name": item_name,
            "evaluation_mae_units": round(mae, 2),
            "daily_burn_rate": round(daily_burn_rate, 2),
            "current_stock": int(latest_stock),
            "estimated_days_remaining": days_remaining,
            "projected_stockout_date": stockout_date.strftime("%Y-%m-%d"),
            "recommended_reorder_date": reorder_trigger_date.strftime("%Y-%m-%d"),
            "status": status,
            "lead_time_buffer_days": critical_threshold
        }

    def predict_future_trend(self, item_name: str, days_out: int = 30) -> list[dict]:
        df = self.load_from_db(item_name)
        latest_stock = df["current_stock"].iloc[-1]
        latest_date = df["date"].iloc[-1]
        
        X = df[["day_index"]]
        y = df["current_stock"]
        self.model.fit(X, y)
        daily_burn_rate = abs(self.model.coef_[0])
        
        trend_timeline = []
        for i in range(days_out):
            projected_date = latest_date + timedelta(days=i)
            projected_stock = max(0, latest_stock - (daily_burn_rate * i))
            trend_timeline.append({
                "date": projected_date.strftime("%Y-%m-%d"),
                "predicted_stock": round(projected_stock, 1)
            })
            
        return trend_timeline