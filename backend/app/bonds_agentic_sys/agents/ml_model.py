"""
MCP-Driven ML Model Agent - Uses real MCP tools with LTP
Predicts bond returns based on 21-day price forecasts from MCP server
Uses last_traded_price from CSV as current price
"""

from typing import Dict, List, Any, Optional
from schemas_v2 import MLPrediction
import json
from utils.bond_cache import get_bond_cache


def _parse_mcp_result(result):
    """Parse MCP JSON result"""
    if isinstance(result, str):
        try:
            return json.loads(result)
        except:
            return result
    return result


def _safe_get(obj, key, default=None):
    """Safely get attribute from dict or Pydantic model"""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _safe_float(value, default=0.0):
    """Convert value to float, handling strings and None"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class MLModelAgent:
    """
    Machine learning predictions using Live Data from MCP server.
    All calculations fetched from MCP - no approximations.
    """

    def __init__(self, config, mcp_client=None):
        self.config = config
        self.mcp_client = mcp_client
        self.bond_cache = get_bond_cache()  # Initialize bond data cache
        print(f"ML Agent initialized (MCP-Driven Mode)")
        print(f"   MCP client available: {self.mcp_client is not None}")
        print(f"   Bond data cache enabled (24h TTL)")

    async def predict_batch(
        self,
        bonds: List[Dict],
        yield_curve: Optional[Dict] = None,
        yield_forecasts: Optional[Any] = None,
        rbi_policy: Optional[Dict] = None,
        news_items: Optional[List[Any]] = None,
        use_pathway: bool = True,
    ) -> Dict[str, MLPrediction]:
        """
        Generate predictions using Real-Time MCP calculations.
        """
        predictions = {}

        if not bonds:
            print(" ML Agent: No bonds provided")
            return {}

        if not self.mcp_client:
            print(" ML Agent: MCP client required but not available")
            return {}

        print(f"\n{'=' * 80}")
        print(f"🔮 MCP-DRIVEN PREDICTIONS (21-day forecast)")
        print(f"{'=' * 80}")
        print(f" Processing {len(bonds)} bonds using live MCP calculations...")

        # Generate predictions for each bond
        for i, bond in enumerate(bonds, 1):
            isin = _safe_get(bond, "isin", "")
            if not isin:
                isin = _safe_get(bond, "symbol", "")
            if not isin:
                print(f"\n Bond {i}: No ISIN/symbol found, skipping")
                continue

            print(f"\n{'=' * 60}")
            print(f" Bond {i}/{len(bonds)}: {isin}")
            print(f"{'=' * 60}")

            # Fetch comprehensive bond analytics from MCP
            prediction = await self._generate_mcp_prediction(isin, bond)

            if prediction:
                predictions[isin] = prediction
            else:
                print(f"    Failed to generate prediction for {isin}")

        print(f"\n{'=' * 80}")
        print(f" Generated {len(predictions)} MCP-driven predictions")
        print(f"{'=' * 80}\n")

        return predictions

    async def _generate_mcp_prediction(
        self, isin: str, bond: Dict
    ) -> Optional[MLPrediction]:
        """
        Generate prediction using pure MCP data - no approximations
        """
        try:
            # Step 1: Get comprehensive bond details (check cache first)
            bond_details = await self.bond_cache.get_bond_details(isin)

            if bond_details:
                print(f"    Using cached bond details for {isin}")
            else:
                print(f"    Fetching comprehensive bond details from MCP...")
                bond_details = await self.mcp_client.get_bond_details(
                    isin, days_ahead=0
                )
                bond_details = _parse_mcp_result(bond_details)

                if bond_details and "error" not in bond_details:
                    # Cache the result
                    await self.bond_cache.set_bond_details(isin, bond_details)

            if not bond_details or "error" in bond_details:
                print(
                    f"    Failed to fetch bond details: {bond_details.get('error', 'Unknown') if bond_details else 'No data'}"
                )
                return None

            # Extract current values - prefer LTP over theoretical price
            last_traded_price = _safe_float(bond_details.get("last_traded_price", 0.0))
            current_price = (
                last_traded_price
                if last_traded_price > 0
                else _safe_float(bond_details.get("current_price", 0.0))
            )
            current_ytm = _safe_float(bond_details.get("ytm", 0.0))
            modified_duration = _safe_float(bond_details.get("modified_duration", 0.0))
            convexity = _safe_float(bond_details.get("convexity", 0.0))
            years_to_maturity = _safe_float(bond_details.get("years_to_maturity", 0.0))

            print(f"    Current Price (LTP): ₹{current_price:.2f}")
            print(f"    Current YTM: {current_ytm:.3f}%")
            print(f"     Modified Duration: {modified_duration:.3f}")
            print(f"    Convexity: {convexity:.3f}")
            print(f"   📅 Years to Maturity: {years_to_maturity:.2f}")

            if current_price == 0:
                print(f"    Invalid current price")
                return None

            # Step 2: Get predicted price (day 21) - check cache first
            price_21d = await self.bond_cache.get_bond_price(isin, days_ahead=21)

            if price_21d:
                print(f"    Using cached price prediction (21d) for {isin}")
            else:
                print(f"    Fetching predicted price (day 21)...")
                price_21d = await self.mcp_client.get_bond_price(isin, days_ahead=21)
                price_21d = _parse_mcp_result(price_21d)

                if price_21d and "error" not in price_21d:
                    # Cache the result
                    await self.bond_cache.set_bond_price(isin, 21, price_21d)

            if not price_21d or "error" in price_21d:
                print(
                    f"    Failed to fetch predicted price: {price_21d.get('error', 'Unknown') if price_21d else 'No data'}"
                )
                return None

            predicted_price = _safe_float(price_21d.get("estimated_price", 0.0))
            predicted_ytm = _safe_float(price_21d.get("ytm_percent", 0.0))

            print(f"    Predicted Price (21d): ₹{predicted_price:.2f}")
            print(f"    Predicted YTM (21d): {predicted_ytm:.3f}%")

            if predicted_price == 0:
                print(f"    Invalid predicted price")
                return None

            # Step 3: Calculate returns
            print(f"\n    Calculating Returns:")
            print(f"   {'-' * 50}")

            # Price change (capital gain/loss)
            price_change = predicted_price - current_price
            price_change_pct = (
                (price_change / current_price) if current_price != 0 else 0.0
            )

            print(f"    Price Change: ₹{price_change:.2f}")
            print(f"    Price Change %: {price_change_pct * 100:.4f}%")

            # Yield change
            yield_change = predicted_ytm - current_ytm
            yield_change_decimal = yield_change / 100.0  # Convert to decimal
            print(f"    Yield Change: {yield_change:.3f} bps")

            # Carry (coupon income for 21 days)
            holding_period = 21.0 / 365.0
            carry_return = (
                current_ytm / 100.0
            ) * holding_period  # Convert YTM to decimal

            print(f"   💵 Carry Return (21 days): {carry_return * 100:.4f}%")

            # Total expected return = Capital gain + Carry
            total_expected_return = price_change_pct + carry_return

            print(f"\n    TOTAL EXPECTED RETURN: {total_expected_return * 100:.4f}%")
            print(f"      = Price Change ({price_change_pct * 100:.4f}%)")
            print(f"      + Carry ({carry_return * 100:.4f}%)")

            # Step 4: Calculate confidence score
            confidence = self._calculate_confidence(
                modified_duration=modified_duration,
                years_to_maturity=years_to_maturity,
                yield_change=abs(yield_change_decimal),
                price_change_pct=abs(price_change_pct),
            )

            print(f"    Confidence Score: {confidence * 100:.1f}%")

            # Create prediction object
            prediction = MLPrediction(
                isin=isin,
                expected_return=float(total_expected_return),
                predicted_price=float(predicted_price),
                confidence=float(confidence),
                model_type="MCP_21Day_LTP_Forecast",
                features_used=[
                    "mcp_ltp",
                    "mcp_predicted_price_21d",
                    "mcp_ytm_current",
                    "mcp_ytm_predicted",
                    "mcp_duration",
                    "carry_21days",
                ],
            )

            print(f"    Prediction Generated")

            return prediction

        except Exception as e:
            print(f"    Error generating prediction for {isin}: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _calculate_confidence(
        self,
        modified_duration: float,
        years_to_maturity: float,
        yield_change: float,
        price_change_pct: float,
    ) -> float:
        """
        Calculate confidence score based on bond characteristics and market conditions
        """
        confidence = 0.85  # Base confidence

        # Adjust for duration risk
        if modified_duration > 10:
            confidence -= 0.15  # High duration = lower confidence
        elif modified_duration > 7:
            confidence -= 0.10
        elif modified_duration < 3:
            confidence += 0.05  # Low duration = higher confidence

        # Adjust for maturity
        if years_to_maturity < 1:
            confidence += 0.05  # Near maturity = higher confidence
        elif years_to_maturity > 15:
            confidence -= 0.10  # Long maturity = lower confidence

        # Adjust for yield volatility
        if yield_change > 0.02:  # >2% change
            confidence -= 0.15  # High volatility = lower confidence
        elif yield_change > 0.01:  # >1% change
            confidence -= 0.10
        elif yield_change < 0.005:  # <0.5% change
            confidence += 0.05  # Low volatility = higher confidence

        # Adjust for extreme price movements
        if abs(price_change_pct) > 0.10:  # >10% price change
            confidence -= 0.10

        # Ensure confidence stays in valid range
        confidence = max(0.30, min(0.95, confidence))

        return confidence


def create_ml_agent(config, mcp_client=None) -> MLModelAgent:
    """Factory function"""
    if not mcp_client:
        print(" WARNING: ML Agent created without MCP client - predictions will fail")
    return MLModelAgent(config, mcp_client)
