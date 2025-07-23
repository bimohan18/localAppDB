# app/routes.py

import oracledb
import json
from flask import Response
from flask import request, jsonify
from app.models import get_db_connection
from flask import Blueprint

routes = Blueprint("routes", __name__)

@routes.route("/")
def home():
    return "Home"

@routes.route("/readCustomer/<custid>", methods=["GET"])
def get_customer(custid):
    try:
        # Ensure customer ID is a valid integer
        cust_id_int = int(custid)
    except ValueError:
        return jsonify({"error": f"Invalid customer ID: '{custid}'"}), 400
    connection = get_db_connection()
    if not connection:
        return jsonify({"db connect error": "Failed to connect to the database"}), 500

    try:
        cursor = connection.cursor()
        sql = """
            SELECT CU.CUST_DBID AS CUSTOMERID,
                CU.CUST_FIRSTNAME AS FIRSTNAME,
                CU.CUST_MIDDLENAME AS MIDDLENAME,
                CU.CUST_LASTNAME AS LASTNAME,
                CU.CUST_TYPE AS CUSTOMERTYPE,
                CU.CUST_DOCID AS IDNO,
                CU.CUST_DOCID_TYPE AS IDTYPE,
                CO.CNTCT_LINE1 AS LINE1,
                CO.CNTCT_LINE2 AS LINE2,
                CO.CNTCT_LINE3 AS LINE3,
                CO.CNTCT_CITY AS CITY,
                CO.CNTCT_ZIP AS ZIP,
                CO.CNTCT_STATE AS STATE,
                CO.CNTCT_COUNTRY AS COUNTRY,
                CO.CNTCT_EMAIL AS EMAIL,
                CO.CNTCT_PHONE AS PHONE,
                AC.ACC_TYPE AS ACCOUNTTYPE,
                AC.ACCOUNT_NO AS ACCOUNTNO,
                AC.ROUTING_NUMBER AS ROUTINGNO,
                AC.BALANCE AS TOTALBAL,
                AC.ACC_STATUS AS ACCOUNTSTATUS
            FROM CUSTOMERS CU
            JOIN CUSTOMER_CONTACTS_INFO CO ON CU.CUST_CONTACTID = CO.CUST_CONTACTID
            JOIN ACCOUNTS AC ON CU.CUST_ACCSLNO=AC.CUST_ACCSLNO
            WHERE CU.CUST_DBID=:1
            """
        cursor.execute(sql, (custid,))
        rows = cursor.fetchone()
        if rows:
            columns = [col[0] for col in cursor.description]
            # Convert row to dict
            flat_data = dict(zip(columns, rows))
            # Structure the JSON by grouping fields
            structured_data = {
                "customer": {
                    "id": flat_data["CUSTOMERID"],
                    "first_name": flat_data["FIRSTNAME"],
                    "middle_name": flat_data["MIDDLENAME"],
                    "last_name": flat_data["LASTNAME"],
                    "type": flat_data["CUSTOMERTYPE"],
                    "document_id": flat_data["IDNO"],
                    "document_type": flat_data["IDTYPE"]
                },
                "contact": {
                    "line1": flat_data["LINE1"],
                    "line2": flat_data["LINE2"],
                    "line3": flat_data["LINE3"],
                    "city": flat_data["CITY"],
                    "zip": flat_data["ZIP"],
                    "state": flat_data["STATE"],
                    "country": flat_data["COUNTRY"],
                    "email": flat_data["EMAIL"],
                    "phone": flat_data["PHONE"]
                },
                "account": {
                    "type": flat_data["ACCOUNTTYPE"],
                    "number": flat_data["ACCOUNTNO"],
                    "routing": flat_data["ROUTINGNO"],
                    "balance": flat_data["TOTALBAL"],
                    "status": flat_data["ACCOUNTSTATUS"]
                }
            }
            return Response(
                response=json.dumps(structured_data, indent=2),
                status=200,
                mimetype='application/json'
            )
            #return jsonify(structured_data), 200

        else:
            return jsonify({"error": f"No customer found with ID {custid}"}), 404
    except oracledb.DatabaseError as e:
        return jsonify({"sql execute error": str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@routes.route("/createCustomer", methods=["POST"])
def create_customer():
    cust_data = request.get_json()
    return jsonify(cust_data), 201
'''
    def get_next_value(cursor, table, column):
        cursor.execute(f"SELECT MAX({column}) FROM {table}")
    result = cursor.fetchone()[0]
    return (result or 0) + 1

    def generate_account_fields(cursor, acc_type, routing_base):
        cursor.execute("SELECT ACCTYPEID FROM ACCOUNT_TYPE_TABLE WHERE ACC_TYPE = :1", (acc_type,))
    acctype_id = cursor.fetchone()[0]

    cursor.execute("SELECT MAX(ACCOUNT_NO) FROM ACCOUNTS WHERE ACC_TYPE = :1", (acc_type,))
    last_account_no = cursor.fetchone()[0] or "0000000000"
    next_acc_suffix = str(int(last_account_no[-5:]) + 1).zfill(5)

    routing = routing_base[:len(routing_base)-4] + next_acc_suffix[-4:]

    account_no = acctype_id + next_acc_suffix  # If ACCTYPEID prefix is valid
    return routing, account_no

    cursor = connection.cursor()

    # Step 1: get next primary keys
    cust_dbid = get_next_value(cursor, "CUSTOMERS", "CUST_DBID")
    contact_id = get_next_value(cursor, "CUSTOMER_CONTACTS_INFO", "CUST_CONTACTID")
    acc_slno = get_next_value(cursor, "ACCOUNTS", "CUST_ACCSLNO")

    # Step 2: compute account fields
    routing, account_no = generate_account_fields(cursor, cust_data["account"]["type"], cust_data["account"]["routing"])

    # Step 3: insert into CONTACTS
    cursor.execute("""
        INSERT INTO CUSTOMER_CONTACTS_INFO (...) VALUES (:1, :2, ...)
    """, (contact_id, ...))

    # Step 4: insert into ACCOUNTS
    cursor.execute("""
        INSERT INTO ACCOUNTS (...) VALUES (:1, :2, ...)
    """, (acc_slno, account_no, routing, ...))

    # Step 5: insert into CUSTOMERS referencing both
    cursor.execute("""
        INSERT INTO CUSTOMERS (...) VALUES (:1, :2, ...)
    """, (cust_dbid, contact_id, acc_slno, ...))

    connection.commit()

    return jsonify({
            "message": "Customer created successfully",
            "customer_id": cust_dbid,
            "contact_id": contact_id,
            "account": {
                "slno": acc_slno,
                "number": account_no,
                "routing": routing
            }
        }), 201
'''
@routes.route("/deleteCustomer/<custname>", methods=["DELETE"])
def delete_customer(custname):
    cust_data = request.get_json()
    return jsonify(cust_data), 204
