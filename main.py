from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
import os

app = FastAPI()


@app.get("/")
def home():
    return {"message": "Welcome to the Shopback API"}

#1 Intialize the connection Pool
#We set a minimum of 1 and maximum of 10 conections in the pool

try: 
    postgreSql_pool = pool.SimpleConnectionPool(
        1, 10,
        user="admin",
        password="password123",
        host="127.0.0.1",
        port="5432",
        database="shop_db"
    )
    print("Connection pool created successfully")
except Exception as e:
    print("Error while connection pool: {e}")

# Data Validation
# This is like a contract. FastAPI ensures the client sends the right data.
class ProductSchema(BaseModel):
    name: str
    description: str
    price: float
    stock_quantity: int

# 3 Post Route: CReate a Product
@app.post("/products")
def create_product(product: ProductSchema):
    # Borrow a connection from the pool
    conn = postgreSql_pool.getconn()
    try:
        # RealDictCursor makes results look like Python Dictionaries (JSON-like)
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            query = """
            INSERT INTO products (name, description, price, stock_quantity) 
            VALUES (%s, %s, %s, %s)
            RETURNING *;
            """
            cursor.execute(query, (product.name, product.description, product.price, product.stock_quantity))
            new_product = cursor.fetchone()
            conn.commit()
            return new_product
    except Exception as e:
        conn.rollback() #Undo the chnages if there's an error
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Always put the connection back in the pool
        postgreSql_pool.putconn(conn)

#4 GET Route: FETCH PRODUCTS
@app.get("/products")
def get_products(min_price: float = 0, limit: int = 5):
    conn = postgreSql_pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # USING %s as placeholder to prevent SQL injection protection
            query = "SELECT * FROM products WHERE price >= %s LIMIT %s"
            cursor.execute(query, (min_price, limit))
            return cursor.fetchall()
    finally: 
        postgreSql_pool.putconn(conn)