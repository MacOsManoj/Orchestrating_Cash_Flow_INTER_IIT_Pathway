"""
Bond Maturity Filter Utility
Filters bonds by maturity date
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dateutil.parser import parse as parse_date


class MaturityFilter:
    """Filter bonds by maturity within N years"""
    def __init__(self, max_years: int = 10):
        """
        Args:
            max_years: Maximum years to maturity (default 10)
        """
        self.max_years = max_years
        self.cutoff_date = datetime.now() + timedelta(days=365.25 * max_years)

    def filter_bonds(self, bonds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter bonds by maturity date

        Args:
            bonds: List of bond dictionaries

        Returns:
            Filtered list of bonds maturing within max_years
        """
        filtered = []

        for bond in bonds:
            # Get maturity date
            maturity = self._get_maturity_date(bond)

            if maturity and maturity <= self.cutoff_date:
                filtered.append(bond)

        return filtered

    def _get_maturity_date(self, bond: Dict[str, Any]) -> Optional[datetime]:
        """Extract and parse maturity date from bond"""

        # Try different field names
        date_fields = ["maturity_date", "maturity", "mat_date", "maturity_dt"]

        for field in date_fields:
            if field in bond:
                date_str = bond[field]

                if isinstance(date_str, datetime):
                    return date_str

                if isinstance(date_str, str):
                    try:
                        return parse_date(date_str)
                    except:
                        continue

        # Try to extract from name (e.g., "HDFC 7.25% 2033")
        if "name" in bond:
            name = bond["name"]
            # Look for 4-digit year
            import re

            match = re.search(r"\b(20\d{2})\b", name)
            if match:
                year = int(match.group(1))
                # Assume June 30 as maturity date
                return datetime(year, 6, 30)

        return None

    def is_within_maturity(self, bond: Dict[str, Any]) -> bool:
        """Check if single bond is within maturity range"""
        maturity = self._get_maturity_date(bond)
        return maturity is not None and maturity <= self.cutoff_date
    def get_years_to_maturity(self, bond: Dict[str, Any]) -> Optional[float]:
        """Get years remaining to maturity"""
        maturity = self._get_maturity_date(bond)
        if maturity:
            delta = maturity - datetime.now()
            return delta.days / 365.25
        return None
    def filter_summary(self, original_count: int, filtered_count: int) -> str:
        """Generate filter summary message"""
        removed = original_count - filtered_count
        pct = (removed / original_count * 100) if original_count > 0 else 0
        return (
            f" Maturity Filter Applied:\n"
            f"   • Original bonds: {original_count}\n"
            f"   • Filtered bonds: {filtered_count}\n"
            f"   • Removed (>10Y): {removed} ({pct:.1f}%)\n"
            f"   • Cutoff date: {self.cutoff_date.strftime('%Y-%m-%d')}"
        )


# Global filter instance (can be configured)
MATURITY_FILTER = MaturityFilter(max_years=10)


def filter_bonds_by_maturity(
    bonds: List[Dict[str, Any]], max_years: int = 10
) -> List[Dict[str, Any]]:
    """
    Convenience function to filter bonds

    Args:
        bonds: List of bond dictionaries
        max_years: Maximum years to maturity

    Returns:
        Filtered list of bonds
    """
    filter_obj = MaturityFilter(max_years=max_years)
    return filter_obj.filter_bonds(bonds)
