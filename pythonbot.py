from binance.client import Client
import decimal
import time

# Binance API credentials
api_key = 'NUl186slPRcuxbmvXpF8uoRhVkjyy9Boe95y1pKbuhntWzhePGPWgQEJepkBdIZM'
api_secret = '6viaY7nDHvqDLmmzhrrqMeqfsH54QTlHRbPu4FLxWlb44ysrPcsjEX9b0R9agmtT'

# Connect to Binance API
client = Client(api_key, api_secret, testnet=False)

# Set trading pair and amount to buy in TUSD
symbol = "BTCTUSD"

# Set initial profit to zero
total_profit = decimal.Decimal("0")

while True:
    try:
        # Check TUSD balance
        account = client.get_account()
        balances = account["balances"]
        tusd_balance = next((item for item in balances if item["asset"] == "TUSD"), None)
        initial_balance = decimal.Decimal(next((a["free"] for a in client.get_account()["balances"] if a["asset"] == "TUSD"), 0))
        num_open_orders = len(client.get_open_orders(symbol=symbol))
        open_order_value = decimal.Decimal(0)

        if num_open_orders > 0:
            for order in client.get_open_orders(symbol=symbol):
                if order['side'] == 'SELL' and order['type'] == 'LIMIT':
                    open_order_value += decimal.Decimal(order['price']) * decimal.Decimal(order['origQty'])

        total_balance = initial_balance + (open_order_value)
        # Lookup-Tabelle für tusd_amounts basierend auf num_open_orders
        tusd_amount_lookup = {
            0: 0.1,
            1: 0.1,
            2: 0.11,
            3: 0.11,
            4: 0.11,
            5: 0.11,
            6: 0.11,
            7: 0.125,
            8: 0.125,
        }

        # tusd_amount berechnen basierend auf num_open_orders
        if num_open_orders in tusd_amount_lookup:
            tusd_amount = total_balance * decimal.Decimal(tusd_amount_lookup[num_open_orders])
        else:
            tusd_amount = total_balance
        tusd_amount = tusd_amount // 1

        print(f"Current TUSD Balance: {tusd_balance['free']}. Total Balance (including {num_open_orders} open limit sell orders): {(total_balance):.4f}")

        if tusd_balance is not None and decimal.Decimal(tusd_balance["free"]) >= decimal.Decimal(tusd_amount):

            # Execute market buy order for the specified amount in TUSD
            order = client.order_market_buy(symbol=symbol, quoteOrderQty=tusd_amount)

            # Get the average price of the buy order
            avg_price = decimal.Decimal(order["fills"][0]["price"])

            # Calculate the sell price with 0.02% profit
            profit = 0.0002
            profit_percent = decimal.Decimal(profit)
            sell_price = avg_price * (decimal.Decimal(1) + profit_percent)

            # Format the sell price to the proper number of decimal places
            symbol_info = client.get_symbol_info(symbol)
            price_filter = next(filter(lambda f: f['filterType'] == 'PRICE_FILTER', symbol_info['filters']))
            decimals = int(price_filter['tickSize'].index('1') - 1)
            sell_price = round(sell_price, decimals)

            # Create limit sell order with the calculated sell price
            quantity = decimal.Decimal(order["executedQty"])
            client.order_limit_sell(symbol=symbol, quantity=quantity, price=sell_price)
            print(f"Market Buy order for {tusd_amount} TUSD executed. Limit Sell order placed at {sell_price} TUSD.")

            # Get the number of open limit orders
            open_orders = client.get_open_orders(symbol=symbol)
            num_open_orders = len(open_orders)

            # Calculate total TUSD amount reserved for open limit orders
            total_reserved = decimal.Decimal("0")
            for order in open_orders:
                total_reserved += decimal.Decimal(order["origQty"]) * decimal.Decimal(order["price"])
            total_reserved += decimal.Decimal(tusd_amount) * num_open_orders

            # Get the current TUSD balance and calculate the available balance
            account = client.get_account()
            balances = account["balances"]
            tusd_balance = next((item for item in balances if item["asset"] == "TUSD"), None)
            if tusd_balance is not None:
                available_balance = decimal.Decimal(tusd_balance["free"]) - total_reserved
            else:
                print("No TUSD balance found.")
        else:
            print("Insufficient TUSD balance to execute Market Buy order.")

        # Überprüfen, ob Gebühren gezahlt wurden, alle 3 Stunden
        if int(time.time()) % (60 * 60 * 3) == 0:
            if client.get_trade_fee()["success"]:
                print("Fees have been paid. Stopping the program.")
                break
            else:
                print("$$$ No fees $$$")

    except Exception as e:
        print(f"Error occurred: {e}")

    # Wartezeiten Lookup-Tabelle basierend auf num_open_orders
    wait_time_lookup = {
        0: (60 * 5),
        1: (60 * 10),
        2: (60 * 20),
        3: (60 * 40),
        4: (60 * 60),
        5: (60 * 60),
        6: (60 * 60 * 1.5),
        7: (60 * 60 * 2),
        8: (60 * 60 * 2),
    }
    # Wait-Zeit berechnen basierend auf num_open_orders
    if num_open_orders in wait_time_lookup:
        wait_time = wait_time_lookup[num_open_orders]
    else:
        wait_time = 600 # standardmäßig 10 Minuten warten

    # Wartezeit anzeigen
    minutes, seconds = divmod(wait_time, 60)
    # assuming that minutes and seconds are float values
    formatted_minutes = int(minutes)
    formatted_seconds = int(seconds)
    print(f"wait for: {formatted_minutes:02d}min {formatted_seconds:02d}sec")
    print("-----------------------------------------------------------------")

    # Pause für die berechnete Zeit
    time.sleep(wait_time)

