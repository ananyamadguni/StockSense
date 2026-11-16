"""
CP-012 StockSense: Predictive Inventory Reorder Engine
Menu-driven console application (Python, in-memory data only).

Core features
  1. Maintain items (stock, avg daily usage, lead time, reorder level)
  2. Record stock-in / stock-out movements with date
  3. Flag items that will run out before a new order can arrive
  4. Suggest order quantity to cover a chosen number of days
  5. Show full movement history of any item
Stretch features
  6. ABC classification by consumption value
  7. Batch tracking with expiry dates + expired stock flagging
"""

import math
from datetime import date, datetime, timedelta

# ---------------------------------------------------------------
# Data (in memory)
#   items[item_id] = {
#       "name", "stock", "avg_daily", "lead_time", "reorder_level",
#       "unit_cost", "batches": [ {"batch": str, "qty": int, "expiry": date|None} ],
#       "history": [ {"date": date, "type": "IN"/"OUT", "qty": int,
#                     "note": str, "balance": int} ]
#   }
# ---------------------------------------------------------------
items = {}
next_id = 1


# ---------------------------------------------------------------
# Safe input helpers: invalid input never crashes the program
# ---------------------------------------------------------------
def read_text(prompt):
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("  ! Input cannot be empty.")


def read_int(prompt, minimum=0, maximum=None):
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print("  ! Please enter a whole number.")
            continue
        if value < minimum:
            print(f"  ! Value must be at least {minimum}.")
        elif maximum is not None and value > maximum:
            print(f"  ! Value must be at most {maximum}.")
        else:
            return value


def read_float(prompt, minimum=0.0):
    while True:
        raw = input(prompt).strip()
        try:
            value = float(raw)
        except ValueError:
            print("  ! Please enter a number.")
            continue
        if value != value or value in (float("inf"), float("-inf")):
            print("  ! Invalid number.")
        elif value < minimum:
            print(f"  ! Value must be at least {minimum}.")
        else:
            return value


def read_date(prompt, allow_blank_today=True, allow_blank_none=False):
    """Reads YYYY-MM-DD. Blank = today (movements) or None (expiry)."""
    while True:
        raw = input(prompt).strip()
        if raw == "":
            if allow_blank_none:
                return None
            if allow_blank_today:
                return date.today()
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            print("  ! Use the format YYYY-MM-DD (e.g. 2026-11-15).")


def pick_item(prompt="Enter item ID: "):
    if not items:
        print("  ! No items yet. Add an item first.")
        return None
    item_id = read_int(prompt, minimum=1)
    if item_id not in items:
        print("  ! No item with that ID.")
        return None
    return item_id


# ---------------------------------------------------------------
# Core feature 1: item master
# ---------------------------------------------------------------
def add_item(name, stock, avg_daily, lead_time, reorder_level, unit_cost,
             expiry=None, when=None):
    global next_id
    item = {
        "name": name,
        "stock": 0,
        "avg_daily": avg_daily,
        "lead_time": lead_time,
        "reorder_level": reorder_level,
        "unit_cost": unit_cost,
        "batches": [],
        "history": [],
    }
    items[next_id] = item
    new_id = next_id
    next_id += 1
    if stock > 0:
        stock_in(new_id, stock, when or date.today(), "Opening stock", expiry)
    return new_id


def add_item_menu():
    print("\n--- Add New Item ---")
    name = read_text("Item name: ")
    for existing in items.values():
        if existing["name"].lower() == name.lower():
            print("  ! An item with this name already exists.")
            return
    stock = read_int("Opening stock (units): ")
    avg_daily = read_float("Average daily usage (units/day): ")
    lead_time = read_int("Supplier lead time (days): ")
    reorder_level = read_int("Reorder level (units): ")
    unit_cost = read_float("Unit cost: ")
    expiry = None
    if stock > 0:
        expiry = read_date("Expiry date of opening stock (YYYY-MM-DD, blank = none): ",
                           allow_blank_none=True)
    item_id = add_item(name, stock, avg_daily, lead_time, reorder_level,
                       unit_cost, expiry)
    print(f"  Item added with ID {item_id}.")


def update_item_menu():
    print("\n--- Update Item Settings ---")
    item_id = pick_item()
    if item_id is None:
        return
    it = items[item_id]
    print(f"Updating '{it['name']}' (press Enter to keep current value)")
    for key, label, kind in [
        ("avg_daily", "Average daily usage", "float"),
        ("lead_time", "Lead time (days)", "int"),
        ("reorder_level", "Reorder level", "int"),
        ("unit_cost", "Unit cost", "float"),
    ]:
        raw = input(f"{label} [{it[key]}]: ").strip()
        if raw == "":
            continue
        try:
            value = float(raw) if kind == "float" else int(raw)
            if value < 0:
                raise ValueError
            it[key] = value
        except ValueError:
            print(f"  ! Invalid value, kept {it[key]}.")
    print("  Item updated.")


def list_items():
    print("\n--- All Items ---")
    if not items:
        print("  (no items)")
        return
    print(f"{'ID':<4}{'Name':<22}{'Stock':>7}{'Avg/day':>9}{'Lead':>6}{'Reorder':>9}{'Cost':>9}")
    print("-" * 66)
    for item_id, it in items.items():
        print(f"{item_id:<4}{it['name'][:21]:<22}{it['stock']:>7}{it['avg_daily']:>9.1f}"
              f"{it['lead_time']:>6}{it['reorder_level']:>9}{it['unit_cost']:>9.2f}")


# ---------------------------------------------------------------
# Core feature 2: movements
# ---------------------------------------------------------------
def log_movement(it, when, kind, qty, note):
    it["history"].append({"date": when, "type": kind, "qty": qty,
                          "note": note, "balance": it["stock"]})


def stock_in(item_id, qty, when, note="Stock in", expiry=None):
    it = items[item_id]
    it["stock"] += qty
    batch_no = f"B{len(it['batches']) + 1}"
    it["batches"].append({"batch": batch_no, "qty": qty, "expiry": expiry})
    log_movement(it, when, "IN", qty, f"{note} [{batch_no}]")


def stock_out(item_id, qty, when, note="Stock out"):
    """Returns False if not enough stock. Uses earliest-expiry-first."""
    it = items[item_id]
    if qty > it["stock"]:
        return False
    it["stock"] -= qty
    remaining = qty
    # earliest expiry first; batches without expiry go last
    order = sorted(it["batches"], key=lambda b: (b["expiry"] is None, b["expiry"] or date.max))
    for b in order:
        if remaining == 0:
            break
        take = min(b["qty"], remaining)
        b["qty"] -= take
        remaining -= take
    it["batches"] = [b for b in it["batches"] if b["qty"] > 0]
    log_movement(it, when, "OUT", qty, note)
    return True


def stock_in_menu():
    print("\n--- Record Stock-In ---")
    item_id = pick_item()
    if item_id is None:
        return
    qty = read_int("Quantity received: ", minimum=1)
    when = read_date("Date (YYYY-MM-DD, blank = today): ")
    expiry = read_date("Batch expiry date (YYYY-MM-DD, blank = none): ",
                       allow_blank_none=True)
    if expiry is not None and expiry < when:
        print("  ! Warning: this batch is already expired on receipt.")
    note = input("Note (optional): ").strip() or "Stock in"
    stock_in(item_id, qty, when, note, expiry)
    print(f"  Recorded. New stock: {items[item_id]['stock']}")


def stock_out_menu():
    print("\n--- Record Stock-Out ---")
    item_id = pick_item()
    if item_id is None:
        return
    it = items[item_id]
    print(f"Available stock of '{it['name']}': {it['stock']}")
    qty = read_int("Quantity issued: ", minimum=1)
    when = read_date("Date (YYYY-MM-DD, blank = today): ")
    note = input("Note (optional): ").strip() or "Stock out"
    if stock_out(item_id, qty, when, note):
        print(f"  Recorded. New stock: {it['stock']}")
    else:
        print("  ! Not enough stock. Movement rejected.")


# ---------------------------------------------------------------
# Core feature 3: stockout flagging
# ---------------------------------------------------------------
def days_of_stock(it):
    if it["avg_daily"] <= 0:
        return None  # no usage, never runs out
    return it["stock"] / it["avg_daily"]


def flag_stockouts():
    print("\n--- Stockout Risk Report ---")
    if not items:
        print("  (no items)")
        return
    flagged = 0
    for item_id, it in items.items():
        days_left = days_of_stock(it)
        reasons = []
        if days_left is not None and days_left < it["lead_time"]:
            reasons.append(f"runs out in {days_left:.1f} days, supplier needs {it['lead_time']}")
        if it["stock"] <= it["reorder_level"]:
            reasons.append(f"stock {it['stock']} at/below reorder level {it['reorder_level']}")
        if reasons:
            flagged += 1
            print(f"  [!] ID {item_id} {it['name']}: " + "; ".join(reasons))
    if flagged == 0:
        print("  All items are safe.")
    else:
        print(f"\n  {flagged} item(s) flagged.")


# ---------------------------------------------------------------
# Core feature 4: reorder suggestion
# Order qty = usage over (lead time + target days) - current stock
# ---------------------------------------------------------------
def suggest_quantity(it, target_days):
    needed = it["avg_daily"] * (it["lead_time"] + target_days) - it["stock"]
    return max(0, math.ceil(needed))


def reorder_suggestions():
    print("\n--- Reorder Suggestions ---")
    if not items:
        print("  (no items)")
        return
    target = read_int("Cover how many days of demand after delivery? ", minimum=1)
    found = False
    for item_id, it in items.items():
        days_left = days_of_stock(it)
        flagged = (days_left is not None and days_left < it["lead_time"]) \
            or it["stock"] <= it["reorder_level"]
        if not flagged:
            continue
        qty = suggest_quantity(it, target)
        if qty > 0:
            found = True
            print(f"  ID {item_id} {it['name']}: order {qty} units "
                  f"(approx cost {qty * it['unit_cost']:.2f})")
    if not found:
        print("  No flagged items need an order.")


# ---------------------------------------------------------------
# Core feature 5: movement history
# ---------------------------------------------------------------
def show_history():
    print("\n--- Movement History ---")
    item_id = pick_item()
    if item_id is None:
        return
    it = items[item_id]
    print(f"History of '{it['name']}'")
    if not it["history"]:
        print("  (no movements)")
        return
    print(f"{'Date':<12}{'Type':<6}{'Qty':>6}{'Balance':>9}  Note")
    print("-" * 56)
    ordered = sorted(enumerate(it["history"]), key=lambda p: (p[1]["date"], p[0]))
    for _, m in ordered:
        print(f"{m['date']!s:<12}{m['type']:<6}{m['qty']:>6}{m['balance']:>9}  {m['note']}")


# ---------------------------------------------------------------
# Stretch 1: ABC classification (A = top 80% of value, B = next 15%, C = rest)
# ---------------------------------------------------------------
def abc_classification():
    print("\n--- ABC Classification (annual consumption value) ---")
    if not items:
        print("  (no items)")
        return
    rows = []
    for item_id, it in items.items():
        rows.append((item_id, it["name"], it["avg_daily"] * 365 * it["unit_cost"]))
    rows.sort(key=lambda r: r[2], reverse=True)
    total = sum(r[2] for r in rows)
    if total <= 0:
        print("  No consumption value yet (set usage and cost).")
        return
    print(f"{'Class':<7}{'ID':<4}{'Name':<22}{'Annual value':>14}{'Cum %':>8}")
    print("-" * 55)
    cumulative = 0.0
    for item_id, name, value in rows:
        before = cumulative
        cumulative += value
        # class decided by share BEFORE adding, so the top item is always A
        share_before = before / total * 100
        cls = "A" if share_before < 80 else ("B" if share_before < 95 else "C")
        print(f"{cls:<7}{item_id:<4}{name[:21]:<22}{value:>14.2f}{cumulative / total * 100:>7.1f}%")


# ---------------------------------------------------------------
# Stretch 2: batches and expiry
# ---------------------------------------------------------------
def batch_report():
    print("\n--- Batches & Expiry ---")
    if not items:
        print("  (no items)")
        return
    today = date.today()
    soon = today + timedelta(days=30)
    expired_total = 0
    for item_id, it in items.items():
        if not it["batches"]:
            continue
        print(f"ID {item_id} {it['name']}:")
        for b in it["batches"]:
            exp = b["expiry"]
            if exp is None:
                status = "no expiry"
            elif exp < today:
                status = "*** EXPIRED ***"
                expired_total += b["qty"]
            elif exp <= soon:
                status = "expires within 30 days"
            else:
                status = "ok"
            print(f"   {b['batch']:<5} qty {b['qty']:>5}  expiry {exp or '-'!s:<11} {status}")
    if expired_total:
        print(f"\n  Total expired units still on shelf: {expired_total}")


def write_off_expired():
    print("\n--- Write Off Expired Stock ---")
    if not items:
        print("  (no items)")
        return
    today = date.today()
    count = 0
    for it in items.values():
        for b in list(it["batches"]):
            if b["expiry"] is not None and b["expiry"] < today:
                it["stock"] -= b["qty"]
                it["batches"].remove(b)
                log_movement(it, today, "OUT", b["qty"], f"Expired write-off [{b['batch']}]")
                count += 1
    print(f"  {count} expired batch(es) written off." if count else "  Nothing expired.")


# ---------------------------------------------------------------
# Demo data and main menu
# ---------------------------------------------------------------
def load_demo_data():
    today = date.today()
    a = add_item("USB Cable", 120, 10, 7, 60, 2.50, None, today - timedelta(days=20))
    b = add_item("Phone Case", 40, 8, 10, 50, 4.00, None, today - timedelta(days=20))
    c = add_item("Protein Bar", 80, 5, 5, 30, 1.20, today + timedelta(days=20), today - timedelta(days=20))
    d = add_item("Face Cream", 30, 1, 14, 10, 12.00, today - timedelta(days=5), today - timedelta(days=60))
    e = add_item("Laptop Stand", 15, 0.5, 21, 5, 25.00, None, today - timedelta(days=20))
    stock_out(a, 40, today - timedelta(days=10), "Order #1001")
    stock_out(a, 30, today - timedelta(days=3), "Order #1042")
    stock_out(b, 25, today - timedelta(days=6), "Order #1030")
    stock_in(c, 50, today - timedelta(days=2), "Restock", today + timedelta(days=90))
    stock_out(c, 20, today - timedelta(days=1), "Order #1050")


MENU = """
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
============================================"""

ACTIONS = {
    1: add_item_menu, 2: update_item_menu, 3: list_items,
    4: stock_in_menu, 5: stock_out_menu, 6: flag_stockouts,
    7: reorder_suggestions, 8: show_history, 9: abc_classification,
    10: batch_report, 11: write_off_expired,
}


def main():
    load_demo_data()
    print("StockSense loaded with sample data.")
    while True:
        print(MENU)
        choice = read_int("Choose an option: ", minimum=0, maximum=11)
        if choice == 0:
            print("Goodbye!")
            break
        ACTIONS[choice]()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting. Goodbye!")
