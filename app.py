from flask import Flask, request
from flask_mysqldb import MySQL
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# WebSocket setup
socketio = SocketIO(app, cors_allowed_origins="*")

# Database configuration
app.config["MYSQL_HOST"] = "sql7.freesqldatabase.com"
app.config["MYSQL_USER"] = "sql7751314"
app.config["MYSQL_PASSWORD"] = "U9isixmKa5"
app.config["MYSQL_DB"] = "sql7751314"
app.config["MYSQL_PORT"] = 3306

mysql = MySQL(app)

@socketio.on("sell_product")
def handle_sell(data):
    """
    Handle product sale via WebSocket.
    """
    vending_machine_code = data["vendingMachineCode"]
    uid = data["uid"]
    password = data["password"]
    product_code = data["productCode"]
    product_price = data["productPrice"]
    
    try:
        cursor = mysql.connection.cursor()

        # Verify vending machine
        cursor.execute("SELECT vendingMachineId FROM vendingmachines WHERE vendingMachineCode = %s", (vending_machine_code,))
        vending_machine = cursor.fetchone()
        if not vending_machine:
            emit("sell_response", {"error": "Invalid vending machine code"})
            return
        vending_machine_id = vending_machine[0]

        # Verify user
        cursor.execute("SELECT userId, balance FROM users WHERE uid = %s AND password = %s", (uid, password))
        user = cursor.fetchone()
        if not user:
            emit("sell_response", {"error": "Invalid user credentials"})
            return
        user_id, balance = user

        # Check if balance is sufficient
        if balance < product_price:
            emit("sell_response", {"error": "Insufficient balance"})
            return

        # Update user's balance
        new_balance = balance - product_price
        cursor.execute("UPDATE users SET balance = %s WHERE userId = %s", (new_balance, user_id))

        # Record the sale
        sale_table = f"sales{vending_machine_id}"
        cursor.execute(
            f"INSERT INTO {sale_table} (productName, SalePrice, saleTime) VALUES (%s, %s, NOW())",
            (product_code, product_price)
        )

        # Record the purchase
        purchase_table = f"purchases{user_id}"
        cursor.execute(
            f"INSERT INTO {purchase_table} (price, date) VALUES (%s, NOW())",
            (product_price,)
        )

        # Commit the changes
        mysql.connection.commit()
        cursor.close()

        emit("sell_response", {"message": "Sale successful"})

    except Exception as e:
        emit("sell_response", {"error": str(e)})


@socketio.on("update_price")
def handle_update_price(data):
    """
    Handle product price update via WebSocket.
    """
    vending_machine_code = data["vendingMachineCode"]
    product_code = data["productCode"]
    new_price = data["newPrice"]
    
    try:
        cursor = mysql.connection.cursor()

        # Verify vending machine
        cursor.execute("SELECT vendingMachineId FROM vendingmachines WHERE vendingMachineCode = %s", (vending_machine_code,))
        vending_machine = cursor.fetchone()
        if not vending_machine:
            emit("update_response", {"error": "Invalid vending machine code"})
            return
        vending_machine_id = vending_machine[0]

        # Update the product price
        query = """
            UPDATE products 
            SET productPrice = %s 
            WHERE vendingMachineId = %s AND productCode = %s
        """
        cursor.execute(query, (new_price, vending_machine_id, product_code))
        mysql.connection.commit()
        cursor.close()

        emit("update_response", {"message": "Product price updated successfully"})

    except Exception as e:
        emit("update_response", {"error": str(e)})


if __name__ == "__main__":
    socketio.run(app, debug=True)
