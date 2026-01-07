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

#5 CREATING NEW SCHEMA FOR CATEGORIES
class CategorySchema(BaseModel):
    name: str

#6 Post Route: to create a category

@app.post("/category")
def create_category(category: CategorySchema):
    conn = postgreSql_pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                'INSERT INTO categories (name) VALUES (%s) RETURNING *;',
                (category.name,)
            )
            new_cat = cursor.fetchone()
            conn.commit()
            return new_cat
    except Exception as e:
        conn.rollback()
        print(f"Database Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        postgreSql_pool.putconn(conn)

@app.get("/categories")
def get_categories():
    conn = postgreSql_pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Simple query to get everything from the categories table
            cursor.execute(
                "SELECT * FROM categories ORDER BY name ASC"
            )
            return cursor.fetchall()
    except Exception as e:
        conn.rollback()
        print(f"Database Error: {e}")
    finally:
        postgreSql_pool.putconn(conn)


@app.delete("/categories/{category_id}")
def delete_category(category_id: str):
    conn = postgreSql_pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            #Delete the category
            cursor.execute("DELETE FROM categories WHERE id = %s RETURNING *;", (category_id))
            delete_cat = cursor.fetchone()

            if not delete_cat:
                raise HTTPException(status_code=400, detail="Category not found")
            
            conn.commit()
            return {"message": f"Category '{delete_cat['name']}' deleted successfully"}
    except Exception as e:
         conn.rollback()
         print(f"Databas Error: {e}")
         raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        postgreSql_pool.putconn(conn)
#7 Get Route: Route to get the joined data
@app.get("/products-detailed")
def get_detailed_products():
    conn = postgreSql_pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # WE use LEFT JOIN to see the products even if they have no category
            query = """
                SELECT
                    p.id,
                    p.name AS product_name,
                    p.price,
                    c.name AS category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
            """
            cursor.execute(query)
            return cursor.fetchall()
    except Exception as e:
        print(f"Data base error: {e}")
        raise HTTPException(status_code=500, details='Internal Server Error')
    finally:
        postgreSql_pool.putconn(conn)

#8 Update Schema for connecting category to product tabel
class ProductUpdateSchema(BaseModel):
    category_id: int

#9 PUT Route: Update route for products

@app.put("/products/{product_id}")
def link_product_to_category(product_id: int, update_data: ProductUpdateSchema):
    conn = postgreSql_pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # The SQL UPDATE command
            query = """
                UPDATE products
                SET category_id = %s
                WHERE id = %s
                RETURNING *;
            """
            cursor.execute(query, (update_data.category_id, product_id))
            updated_product = cursor.fetchone()

            if not updated_product:
                raise HTTPException(status_code=404, detail="Product not found")
            
            conn.commit()
            return updated_product
    except Exception as e:
        conn.rollback()
        print(f"Database Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        postgreSql_pool.putconn(conn)