# Portfolio Update Functionality

## Overview

The system now supports updating portfolios directly from natural language queries. You can add, update, or remove bonds from your portfolio using conversational commands.

## How It Works

1. **Query Detection**: The orchestrator detects portfolio update queries based on keywords like "add", "update", "remove", "change", etc.
2. **Command Parsing**: A specialized parser agent extracts structured information (ISIN, bond name, quantity, price, etc.) from your natural language query.
3. **MongoDB Update**: The parsed command is executed using the PortfolioManager, which updates MongoDB directly.
4. **Response**: You receive confirmation with updated portfolio information.

## Supported Actions

### 1. Add Bond to Portfolio

**Examples:**
- "add 1000 units of HDFC Bank 7.50% 2025 bond at price 101.5"
- "buy 1 lakh units of SBI bond at ₹98.5"
- "add INE001A01036 to my portfolio with quantity 1500000 at price 101.5"

**Required Information:**
- Bond identifier (ISIN or bond name)
- Quantity
- Current price (or average cost)

### 2. Update Bond Information

**Examples:**
- "update quantity of INE001A01036 to 1500000"
- "change price of HDFC Bank bond to 101.5"
- "set quantity of SBI bond to 1 lakh"
- "update current price of INE001A01036 to 98.5"

**Required Information:**
- Bond identifier (ISIN or bond name)
- At least one field to update (quantity, current_price, avg_cost)

### 3. Remove Bond from Portfolio

**Examples:**
- "remove HDFC Bank bond from my portfolio"
- "delete INE001A01036"
- "remove SBI 7.35% 2027 bond"

**Required Information:**
- Bond identifier (ISIN or bond name)

## Implementation Details

### Components

1. **PortfolioManagerTool** (`tools/portfolio_tool.py`)
   - `add_bond()`: Add a new bond position
   - `update_bond()`: Update existing bond information
   - `remove_bond()`: Remove a bond position
   - `update_multiple_bonds()`: Batch update multiple bonds

2. **PortfolioUpdateParserAgent** (`agents/portfolio_update_parser.py`)
   - Parses natural language queries
   - Extracts action, ISIN, bond name, quantity, prices
   - Handles variations in language and units (lakh, crore, million)

3. **Orchestrator Integration** (`orchestrator_v3.py`)
   - `_handle_portfolio_update()`: Main handler for portfolio updates
   - Routes update queries to the handler
   - Executes updates and returns confirmation

### MongoDB Operations

All updates are performed directly on MongoDB:
- Updates are atomic (single transaction)
- Portfolio metrics are automatically recalculated
- Changes are persisted immediately

### Example Flow

```
User Query: "add 1000 units of HDFC Bank bond at price 101.5"
    ↓
Orchestrator detects portfolio update query
    ↓
PortfolioUpdateParser extracts:
  - action: "add"
  - bond_name: "HDFC Bank"
  - quantity: 1000
  - current_price: 101.5
    ↓
PortfolioManagerTool.add_bond() called
    ↓
MongoDB updated with new position
    ↓
Portfolio metrics recalculated
    ↓
Response: "✓ Successfully added to your portfolio..."
```

## Usage Examples

### Adding a Bond

```python
# Natural language query
query = "add 1 lakh units of HDFC Bank 7.50% 2025 bond at price ₹101.5"

# The system will:
# 1. Parse the command
# 2. Find or create the bond position
# 3. Add it to MongoDB
# 4. Recalculate portfolio metrics
```

### Updating Bond Quantity

```python
query = "update quantity of INE001A01036 to 1500000"

# The system will:
# 1. Find the bond by ISIN
# 2. Update the quantity
# 3. Recalculate market value and P&L
# 4. Save to MongoDB
```

### Removing a Bond

```python
query = "remove HDFC Bank bond from my portfolio"

# The system will:
# 1. Find the bond by name (matches partial names)
# 2. Remove the position
# 3. Recalculate portfolio metrics
# 4. Save to MongoDB
```

## Supported Units

The parser understands various quantity formats:
- **Numbers**: 1000, 1500000, 1.5M
- **Lakh**: 1 lakh = 100,000
- **Crore**: 1 crore = 10,000,000
- **Million**: 1M or 1 million = 1,000,000
- **Thousand**: 1K or 1 thousand = 1,000

## Price Formats

Prices can be specified in various ways:
- With currency: "₹101.5", "Rs. 98.5"
- Without currency: "101.5", "98.5"
- With context: "at price 101.5", "bought at 100"

## Error Handling

The system handles common errors:
- **Bond not found**: If ISIN or bond name doesn't match any position
- **Missing information**: If required fields (quantity, price) are missing
- **Invalid values**: If quantities or prices are invalid

## Testing

Run the test script to verify functionality:

```bash
cd bond-pipeline
python test_portfolio_updates.py
```

## Notes

- Updates require MongoDB to be available (file-based storage doesn't support updates)
- Bond names are matched partially (case-insensitive)
- If a bond doesn't exist when adding, it will be created
- Portfolio metrics (total value, weights, etc.) are automatically recalculated after updates

