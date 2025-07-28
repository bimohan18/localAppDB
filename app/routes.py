# app/routes.py

import oracledb
import json
import re
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
    cursor = None
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
            status_code = 200
            response_data = Response(
                response=json.dumps(structured_data, indent=2),
                status=status_code,
                mimetype='application/json'
            )
            #return jsonify(structured_data), 200
        else:
            response_data = jsonify({"error": f"No customer found with ID {custid}"})
            status_code = 404
    except oracledb.DatabaseError as e:
        response_data = jsonify({"sql execute error": str(e)})
        status_code=500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

    return response_data, status_code

def validate_customer_fields(data):
    errors = []
    # Required fields
    required_map = {
        "name.first": data.get("name", {}).get("first"),
        "name.last": data.get("name", {}).get("last"),
        "type": data.get("type"),
        "document.id": data.get("document", {}).get("id"),
        "document.type": data.get("document", {}).get("type"),
        "address.line1": data.get("address", {}).get("line1"),
        "address.city": data.get("address", {}).get("city"),
        "address.zip": data.get("address", {}).get("zip"),
        "address.state": data.get("address", {}).get("state"),
        "address.country": data.get("address", {}).get("country"),
        "email": data.get("email"),
        "phone": data.get("phone"),
        "account.type": data.get("account", {}).get("type")
    }

    for field, value in required_map.items():
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append(f"{field} is required")

    # Format checks
    email = data.get("email", "")
    if not (isinstance(email, str) and email.count("@") == 1 and "." in email):
        errors.append("Email must contain one '@', at least one '.', and include 'co'")

    phone = data.get("phone")
    if not (isinstance(phone, int) and len(str(phone)) == 10):
        errors.append("Phone must be a 10-digit integer")

    doc_type = data.get("document", {}).get("type", "").upper()
    doc_id = data.get("document", {}).get("id", "")
    if doc_type == "SSN":
        if not (isinstance(doc_id, str) and doc_id.isdigit() and len(doc_id) == 9):
            errors.append("DOCID for SSN must be a 9-digit string")

    if data.get("type") not in {"Personal", "Organization"}:
        errors.append("Customer type must be 'Personal' or 'Organization'")

    if data.get("account", {}).get("type") not in {"CHECKING", "SAVINGS", "CD"}:
        errors.append("Account type must be 'CHECKING', 'SAVINGS', or 'CD'")

    return errors

@routes.route("/createCustomer", methods=["POST"])
def create_customer():
    cust_data = request.get_json()
    cursor=None
    field_errors = validate_customer_fields(cust_data)
    if field_errors:
        return jsonify({"error": "Field validation failed", "details": field_errors}), 400

    connection = get_db_connection()
    if not connection:
        return jsonify({"db connect error": "Failed to connect to the database"}), 500

    try:
        cursor = connection.cursor()
        # Phone uniqueness
        phone = cust_data.get("phone")
        cursor.execute("SELECT 1 FROM CUSTOMER_CONTACTS_INFO WHERE CNTCT_PHONE = :1", (phone,))
        if cursor.fetchone():
            return jsonify({
                "error": f"Phone '{phone}' already exists"
            }), 409
        #Routing Number existence Check
        cursor.execute("SELECT 1 FROM BRANCHES_INFO WHERE ROUTING_NUMBER = :1", (cust_data["account"]["routing"],))
        if not cursor.fetchone():
            return jsonify({
                "error": f"Invalid routing number '{cust_data['account']['routing']}' — not found in BRANCHES_INFO."
            }), 400
        # Check for existing DOCID
        cursor.execute("SELECT 1 FROM CUSTOMERS WHERE CUST_DOCID = :1", (cust_data["document"]["id"],))
        if cursor.fetchone():
             return jsonify({
                "error": f"DOCID '{cust_data['document']['id']}' already exists."
            }), 409
        # --- Helper Functions ---
        def get_next_value(cursor, table, column):
            cursor.execute(f"SELECT MAX({column}) FROM {table}")
            result = cursor.fetchone()[0]
            try:
                return int(result) + 1
            except (TypeError, ValueError) as e:
                raise ValueError(f"🔍 Failed to parse {result} from {table}.{column}: {e}")
        def get_next_value_with_prefix(cursor, table, column):
            cursor.execute(f"SELECT MAX({column}) FROM {table}")
            result = cursor.fetchone()[0]
            print(result)
            try:
                match = re.match(r"([A-Za-z]*)(\d+)", str(result))
                print(match)
                if match:
                    prefix = match.group(1)
                    print(prefix)
                    num = int(match.group(2))
                    print(num)
                    return f"{prefix}{num + 1:05}"  # e.g., C10026
                else:
                    raise ValueError(f"Invalid ID format: {result}")
            except (TypeError, ValueError) as e:
                print(f"⚠️ ID fallback triggered for {table}.{column}. Bad value: {result}. Error: {e}")
                return f"{prefix}00001"
        def compose_account_number(acc_type, routing_base, last_account_no, cursor):
            # Fetch account ID for the given type
            cursor.execute("SELECT ACC_ID FROM ACCOUNTS_INFO WHERE ACC_TYPE = :1", (acc_type,))
            acc_id_raw = cursor.fetchone()[0]
            acc_id = str(acc_id_raw).zfill(3)

            # Compute next suffix based on last account number
            suffix = str(int(str(last_account_no)[7:]) + 1).zfill(6)
            # str(last_no)[-6:] --> Grabs the last 6 characters; int()+1 --> converts to integer and adds 1;
            # str(int().zfill(6) --> converts back to 6 digit string by adding leading zeroes for remaining digits.            # Trim routing number to make room for acc_id + suffix
            routing_tail = routing_base[6:]

            # Compose the final account number
            return routing_tail + acc_id + suffix

        def generate_account_fields(cursor, acc_type, routing_base):
            cursor.execute("SELECT ACCOUNT_NO FROM ACCOUNTS WHERE CUST_ACCSLNO IN (SELECT MAX(CUST_ACCSLNO) FROM ACCOUNTS)")
            last_no = cursor.fetchone()[0] or 0
            account_no = compose_account_number(acc_type, routing_base, last_no, cursor)
            return routing_base, account_no

        # --- Generate Primary Keys ---
        cust_dbid = get_next_value(cursor, "CUSTOMERS", "CUST_DBID")
        contact_id = get_next_value_with_prefix(cursor, "CUSTOMER_CONTACTS_INFO", "CUST_CONTACTID")
        acc_slno = get_next_value_with_prefix(cursor, "ACCOUNTS", "CUST_ACCSLNO")

        # --- Generate Account Details ---
        routing, account_no = generate_account_fields(
            cursor, cust_data["account"]["type"], cust_data["account"]["routing"]
        )
        # --- Zip Code format update ---
        zip_code = str(cust_data["address"]["zip"]).zfill(5)

        # --- Insert into CUSTOMERS ---
        cursor.execute("""
            INSERT INTO CUSTOMERS (
                CUST_DBID,
                CUST_FIRSTNAME,
                CUST_MIDDLENAME,
                CUST_LASTNAME,
                CUST_TYPE,
                CUST_DOCID,
                CUST_DOCID_TYPE,
                CUST_CONTACTID,
                CUST_ACCSLNO
            ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9)
        """, (
            cust_dbid,
            cust_data["name"]["first"],
            cust_data["name"].get("middle", ""),
            cust_data["name"]["last"],
            cust_data["type"].upper(),
            cust_data["document"]["id"],
            cust_data["document"]["type"],
            contact_id,
            acc_slno
        ))

        # --- Insert into CONTACTS ---
        cursor.execute("""
            INSERT INTO CUSTOMER_CONTACTS_INFO (
                CUST_CONTACTID,
                CNTCT_LINE1,
                CNTCT_LINE2,
                CNTCT_LINE3,
                CNTCT_CITY,
                CNTCT_ZIP,
                CNTCT_STATE,
                CNTCT_COUNTRY,
                CNTCT_EMAIL,
                CNTCT_PHONE
            ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10)
        """, (
            contact_id,
            cust_data["address"]["line1"],
            cust_data["address"].get("line2", ""),
            cust_data["address"].get("line3", ""),
            cust_data["address"]["city"],
            zip_code,
            cust_data["address"]["state"],
            cust_data["address"]["country"],
            cust_data["email"],
            int(cust_data["phone"])
        ))

        # --- Insert into ACCOUNTS ---
        cursor.execute("""
            INSERT INTO ACCOUNTS (
                CUST_ACCSLNO,
                ACCOUNT_NO,
                ROUTING_NUMBER,
                ACC_TYPE,
                BALANCE,
                ACC_STATUS
            ) VALUES (:1, :2, :3, :4, :5, :6)
        """, (
            acc_slno,
            int(account_no),
            routing,
            cust_data["account"]["type"],
            200.00,
            "ACTIVE"
        ))

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

    except oracledb.DatabaseError as e:
        connection.rollback()
        return jsonify({"sql error": str(e)}), 500
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        connection.close()

@routes.route("/deleteCustomer/<custid>", methods=["DELETE"])
def delete_customer(custid):
    cursor = None
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
        # --- DELETE IN CUSOTMER_CONTACTS_INFO -----
        cursor.execute("DELETE FROM CUSTOMER_CONTACTS_INFO WHERE CUST_CONTACTID IN (SELECT CUST_ACCSLNO FROM CUSTOMERS WHERE CUST_DBID = :1)", (custid,))
        cursor.execute("DELETE FROM ACCOUNTS WHERE CUST_ACCSLNO IN (SELECT CUST_ACCSLNO FROM CUSTOMERS WHERE CUST_DBID = :1)", (custid,))
        cursor.execute("DELETE FROM CUSTOMERS WHERE CUST_DBID = :1", (custid,))
        connection.commit()
        status_code = 204
        response_data = Response(
            response='Customer Records Deleted',
            status=status_code,
            mimetype='application/json'
        )
    except oracledb.DatabaseError as e:
        response_data = jsonify({"sql execute error": str(e)})
        status_code=500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
    return response_data, status_code