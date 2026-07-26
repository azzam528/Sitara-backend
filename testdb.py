from app.core.database import engine

try:
    connection = engine.connect()
    print("✅ Berhasil terkoneksi ke PostgreSQL!")
    connection.close()
except Exception as e:
    print("❌ Gagal terkoneksi:")
    print(e)