# CP-012 StockSense: Predictive Inventory Reorder Engine

## Team

Ananya Venugopal Madguni (1AT24IS016), Deekshitha (1AT24IS048), Python track

## How to run

```bash
python main.py
```

*(Note: Replace `main.py` with your actual Python filename if different. Requires Python 3.6+ with no external dependencies.)*

## Features that work

1. **Maintain items:** Add new inventory items, update settings (average daily usage, lead time, reorder level, unit cost), and list all items with current stock levels.

2. **Record stock-in / stock-out movements with date:** Log incoming stock (assigning batch IDs and optional expiry dates) and outgoing stock (automatically deducting from earliest-expiring batches first).

3. **Flag items that will run out before a new order can arrive:** Identify and alert on items whose remaining days of stock are less than the supplier lead time, or whose stock is at/below the reorder level.

4. **Suggest order quantity to cover a chosen number of days:** Calculate optimal reorder quantities and estimated costs for flagged items based on lead time plus a user-defined target coverage period.

5. **Show full movement history of any item:** Display a chronological audit log of all stock-in and stock-out transactions, dates, notes, and running balances for any selected item.

6. **ABC classification by consumption value (Stretch):** Categorize inventory into Class A (top 80% annual consumption value), Class B (next 15%), and Class C (remaining 5%).

7. **Batch tracking with expiry dates + expired stock flagging (Stretch):** Track individual stock batches, highlight items expiring within 30 days or already expired, and write off expired inventory.

## Sample run

```text
StockSense loaded with sample data.

================ StockSense ================
 1. Add item
 2. Update item settings
 3. List items
 4. Record stock-in
 5. Record stock-out
 6. Flag stockout risks
 7. Suggest reorder quantities
 8. Show movement history
 9. ABC classification        (stretch)
10. Batches & expiry report   (stretch)
11. Write off expired stock   (stretch)
 0. Exit
============================================
Choose an option: 3

--- All Items ---
ID  Name                    Stock  Avg/day  Lead  Reorder     Cost
------------------------------------------------------------------
1   USB Cable                  50     10.0     7       60     2.50
2   Phone Case                 15      8.0    10       50     4.00
3   Protein Bar               110      5.0     5       30     1.20
4   Face Cream                 30      1.0    14       10    12.00
5   Laptop Stand               15      0.5    21        5    25.00

================ StockSense ================
 1. Add item
 2. Update item settings
 3. List items
 4. Record stock-in
 5. Record stock-out
 6. Flag stockout risks
 7. Suggest reorder quantities
 8. Show movement history
 9. ABC classification        (stretch)
10. Batches & expiry report   (stretch)
11. Write off expired stock   (stretch)
 0. Exit
============================================
Choose an option: 6

--- Stockout Risk Report ---
  [!] ID 1 USB Cable: runs out in 5.0 days, supplier needs 7; stock 50 at/below reorder level 60
  [!] ID 2 Phone Case: runs out in 1.9 days, supplier needs 10; stock 15 at/below reorder level 50

  2 item(s) flagged.

================ StockSense ================
 1. Add item
 2. Update item settings
 3. List items
 4. Record stock-in
 5. Record stock-out
 6. Flag stockout risks
 7. Suggest reorder quantities
 8. Show movement history
 9. ABC classification        (stretch)
10. Batches & expiry report   (stretch)
11. Write off expired stock   (stretch)
 0. Exit
============================================
Choose an option: 7

--- Reorder Suggestions ---
Cover how many days of demand after delivery? 14
  ID 1 USB Cable: order 160 units (approx cost 400.00)
  ID 2 Phone Case: order 177 units (approx cost 708.00)

================ StockSense ================
 1. Add item
 2. Update item settings
 3. List items
 4. Record stock-in
 5. Record stock-out
 6. Flag stockout risks
 7. Suggest reorder quantities
 8. Show movement history
 9. ABC classification        (stretch)
10. Batches & expiry report   (stretch)
11. Write off expired stock   (stretch)
 0. Exit
============================================
Choose an option: 9

--- ABC Classification (annual consumption value) ---
Class  ID  Name                    Annual value   Cum %
-------------------------------------------------------
A      2   Phone Case                  11680.00   36.7%
A      1   USB Cable                    9125.00   65.3%
A      5   Laptop Stand                 4562.50   79.7%
A      4   Face Cream                   4380.00   93.4%
B      3   Protein Bar                  2190.00  100.0%

================ StockSense ================
 1. Add item
 2. Update item settings
 3. List items
 4. Record stock-in
 5. Record stock-out
 6. Flag stockout risks
 7. Suggest reorder quantities
 8. Show movement history
 9. ABC classification        (stretch)
10. Batches & expiry report   (stretch)
11. Write off expired stock   (stretch)
 0. Exit
============================================
Choose an option: 0
Goodbye!
```
