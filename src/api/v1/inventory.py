from fastapi import FastAPI, HTTPException,APIRouter
from src.ml.forecaster import InventoryForecaster 
from src.schema.inventory_model import InventoryForecast, InventoryForecastSummary

forecaster = InventoryForecaster()
router = APIRouter()


# def _build_forecast(item_name: str) -> dict:
#     forecast_data = forecaster.train_and_evaluate(item_name)
#     days = forecast_data["estimated_days_remaining"]
#     if days <= 14:
#         forecast_data["status"] = "Critical Stockout Risk"
#     elif days <= 30:
#         forecast_data["status"] = "Low Stock"
#     else:
#         forecast_data["status"] = "Stable"
#     return forecast_data

def _build_forecast(item_name: str) -> dict:
    forecast_data = forecaster.train_and_evaluate(item_name, lead_time_days=60, safety_stock_days=15)
    return forecast_data

@router.get("/forecast/{item_name}", response_model=InventoryForecast)
async def get_inventory_forecast(item_name: str):
    try:
        return _build_forecast(item_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecast/{item_name}/trend")
async def get_inventory_forecast_trend(item_name: str, days_out: int = 30):
    try:
        return forecaster.predict_future_trend(item_name, days_out=days_out)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary", response_model=InventoryForecastSummary)
async def get_inventory_summary():
    try:
        item_names = forecaster.list_items()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    forecasts = []
    for item_name in item_names:
        try:
            forecasts.append(_build_forecast(item_name))
        except ValueError:
            continue

    forecasts.sort(key=lambda f: f["estimated_days_remaining"])
    attention_items = [f["item_name"] for f in forecasts if f["status"] != "Stable"]

    return {"forecasts": forecasts, "products_needing_attention": attention_items}
