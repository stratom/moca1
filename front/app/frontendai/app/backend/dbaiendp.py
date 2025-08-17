import oracledb

USER = "sys"
PASS = "oracle1"
DSN = "localhost:1525/FREEPDB1"

try:
    conn = oracledb.connect(user=USER, password=PASS, dsn=DSN, mode=oracledb.AUTH_MODE_SYSDBA)
    print("Conexión exitosa")
    conn.close()
except Exception as e:
    print("Error de conexión:", e)

