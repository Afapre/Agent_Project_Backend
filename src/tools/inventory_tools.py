"""Inventory forecasting agentic tools for multi-product stockout alerts."""

from __future__ import annotations

import json

from langchain.tools import tool

from src.ml.forecaster import InventoryForecaster


def create_inventory_tools() -> list:
    """Create Clara's inventory forecasting and reorder-alert tools."""


    forecaster = InventoryForecaster()

    @tool
    def inventory_forecast_alerts_tool(item_name: str = "") -> str:
        """Checks sales-velocity-based inventory forecasts and flags products that need reordering soon.

        Answers questions like "which products need attention?" or "when do I need to
        reorder [Product]?" by projecting stockout dates from historical consumption
        trends, factoring in international supply chain lead times, and recommending a reorder-by date.

        Args:
            item_name: Optional specific product/item name to check. If omitted, all
                tracked products are checked and only those needing attention are
                highlighted in the summary.
        """
        try:
            item_names = [item_name] if item_name else forecaster.list_items()
        except Exception as exc:
            return json.dumps({"error": str(exc)})

        forecasts = []
        alerts = []
        for name in item_names:
            try:
                # Pass international lead time (e.g., 60 days) and safety stock (15 days)
                forecast = forecaster.train_and_evaluate(name, lead_time_days=60, safety_stock_days=15)
            except ValueError:
                continue

            forecasts.append(forecast)

            if forecast["status"] != "Stable":
                alerts.append(
                    f"Based on current consumption velocity and international shipping lead times, you will need to place an order for "
                    f"{forecast['item_name']} by {forecast['recommended_reorder_date']} to avoid "
                    f"a stockout projected around {forecast['projected_stockout_date']} "
                    f"({forecast['status']})."
                )

        if not forecasts:
            message = (
                f"No historical inventory records found for '{item_name}'."
                if item_name
                else "No historical inventory records found."
            )
            return json.dumps({"message": message})

        products_needing_attention = [f["item_name"] for f in forecasts if f["status"] != "Stable"]
        summary = (
            "\n".join(alerts)
            if alerts
            else "All tracked products currently have healthy stock levels accounting for international lead times; no reorders are urgently needed."
        )

        return json.dumps(
            {
                "summary": summary,
                "products_needing_attention": products_needing_attention,
                "forecasts": forecasts,
            },
            indent=2,
        )

    return [inventory_forecast_alerts_tool]

# """Inventory forecasting agentic tools for multi-product stockout alerts."""

# from __future__ import annotations

# import json

# from langchain.tools import tool

# from src.ml.forecaster import InventoryForecaster


# def _status_for(days_remaining: int) -> str:
#     if days_remaining <= 14:
#         return "Critical Stockout Risk"
#     if days_remaining <= 30:
#         return "Low Stock"
#     return "Stable"


# def create_inventory_tools() -> list:
#     """Create Clara's inventory forecasting and reorder-alert tools."""

#     forecaster = InventoryForecaster()

#     @tool
#     def inventory_forecast_alerts_tool(item_name: str = "") -> str:
#         """Checks sales-velocity-based inventory forecasts and flags products that need reordering soon.

#         Answers questions like "which products need attention?" or "when do I need to
#         reorder [Product]?" by projecting stockout dates from historical consumption
#         trends and recommending a reorder-by date.

#         Args:
#             item_name: Optional specific product/item name to check. If omitted, all
#                 tracked products are checked and only those needing attention are
#                 highlighted in the summary.
#         """
#         try:
#             item_names = [item_name] if item_name else forecaster.list_items()
#         except Exception as exc:
#             return json.dumps({"error": str(exc)})

#         forecasts = []
#         alerts = []
#         for name in item_names:
#             try:
#                 forecast = forecaster.train_and_evaluate(name)
#             except ValueError:
#                 continue

#             forecast["status"] = _status_for(forecast["estimated_days_remaining"])
#             forecasts.append(forecast)

#             if forecast["status"] != "Stable":
#                 alerts.append(
#                     f"Based on current sales velocity, you will need to place an order for "
#                     f"{forecast['item_name']} by {forecast['recommended_reorder_date']} to avoid "
#                     f"a stockout projected around {forecast['projected_stockout_date']} "
#                     f"({forecast['status']})."
#                 )

#         if not forecasts:
#             message = (
#                 f"No historical inventory records found for '{item_name}'."
#                 if item_name
#                 else "No historical inventory records found."
#             )
#             return json.dumps({"message": message})

#         products_needing_attention = [f["item_name"] for f in forecasts if f["status"] != "Stable"]
#         summary = (
#             "\n".join(alerts)
#             if alerts
#             else "All tracked products currently have healthy stock levels; no reorders are urgently needed."
#         )

#         return json.dumps(
#             {
#                 "summary": summary,
#                 "products_needing_attention": products_needing_attention,
#                 "forecasts": forecasts,
#             },
#             indent=2,
#         )

#     return [inventory_forecast_alerts_tool]
