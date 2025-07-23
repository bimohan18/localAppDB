from flask import Flask, request, jsonify
import oracledb

localAppDB = Flask(__name__)
# Oracle DB connection configuration
DB_CONFIG = {
    "username": "MASTERDBA",
    "password": "password",
    "dsn": "localhost:1521/XE"
}

def get_db_connection():
    """Establish and return a connection to the Oracle database."""
    try:
        connection = oracledb.connect(
            user=DB_CONFIG["username"],
            password=DB_CONFIG["password"],
            dsn=DB_CONFIG["dsn"]
        )
        return connection
    except oracledb.DatabaseError as e:
        print(f"Database connection error: {e}")
        return None

@localAppDB.route("/")
def home():
    return "Home"

@localAppDB.route("/readCustomer/<custid>",methods=["GET"])
def get_customer(custid):
    connection = get_db_connection()
    if not connection:
        return jsonify({"db connect error": "Failed to connect to the database"}), 500

    try:
        cursor = connection.cursor()
        #cursor.execute("SELECT 'HELLO','WORLD','!' FROM DUAL")  # Example query
        sql="SELECT * FROM CUSTOMERS WHERE CUST_DBID=:1"
        args=(custid,)
        cursor.execute(sql,args)
        rows = cursor.fetchall()

        if not rows:
            return jsonify({"error": f"No customer found with ID {custid}"}), 404

        columns = [col[0] for col in cursor.description]  # Get column names
        results = [dict(zip(columns, row)) for row in rows]
        return jsonify(results), 200
    except oracledb.DatabaseError as e:
        return jsonify({"sql execute error": str(e)}), 500
    finally:
        cursor.close()
        connection.close()

    # extra = request.args.get("extra")
    # if extra:
    #     cust_data["extra"] = extra
    #return jsonify(cust_data), 200

@localAppDB.route("/createCustomer",methods=["POST"])
def create_customer():
    if request.method == "POST":
        cust_data = request.get_json()

    return jsonify(cust_data), 201

@localAppDB.route("/deleteCustomer/<custname>", methods=["DELETE"])
def delete_customer(custname):
    if request.method == "DELETE":
        cust_data = request.get_json()

    return jsonify(cust_data), 204
if __name__ == "__main__":
    localAppDB.run(debug=True)