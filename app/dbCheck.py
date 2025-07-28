import oracledb

def check_oracle_db(username, password, dsn):
    try:
        # Attempt to connect
        connection = oracledb.connect(user=username, password=password, dsn=dsn)

        # Simple test query
        cursor = connection.cursor()
        cursor.execute("SELECT 1 FROM DUAL")
        result = cursor.fetchone()

        # Cleanup
        cursor.close()
        connection.close()

        # Return result
        if result and result[0] == 1:
            return "Oracle DB is up and responding!"
        else:
            return "Connected, but unexpected query result."
    except oracledb.DatabaseError as e:
        error, = e.args
        return f"Oracle DB check failed: {error.message}"

# Example usage
if __name__ == "__main__":
    USERNAME = "MASTERDBA"
    PASSWORD = "password"
    DSN = "localhost:1521/xe"  # e.g., "localhost:1521/XEPDB1"

    status = check_oracle_db(USERNAME, PASSWORD, DSN)
    print(status)