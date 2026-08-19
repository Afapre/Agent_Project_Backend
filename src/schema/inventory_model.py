from pydantic import BaseModel, Field

class InventoryForecast(BaseModel):
    item_name: str
    evaluation_mae_units: float
    daily_burn_rate: float
    current_stock: float
    estimated_days_remaining: int
    projected_stockout_date: str
    recommended_reorder_date: str
    status: str = Field(default="Stable") # e.g., "Stable", "Low Stock"
    lead_time_buffer_days: int


class InventoryTrendPoint(BaseModel):
    date: str
    predicted_stock: float


class InventoryForecastSummary(BaseModel):
    forecasts: list[InventoryForecast]
    products_needing_attention: list[str]
