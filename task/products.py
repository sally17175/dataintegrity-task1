from flask import Blueprint, request, jsonify
from database import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity

products_bp = Blueprint("products", __name__)

# 🟢 add new products
@products_bp.route("/products", methods=["POST"])
@jwt_required()
def add_product():
    data = request.json
    name = data.get("name")
    description = data.get("description", "")
    price = data.get("price")

    if not name or not price:
        return jsonify({"error": "Product name and price are required"}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("INSERT INTO products (name, description, price) VALUES (%s, %s, %s)", 
                       (name, description, price))
        connection.commit()
        return jsonify({"message": "✅ Product added successfully!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        connection.close()

# 🟢 show all products and serch
@products_bp.route("/products", methods=["GET"])
@jwt_required()
def get_products():
    name_filter = request.args.get("name")
    min_price = request.args.get("min_price")
    max_price = request.args.get("max_price")

    query = "SELECT * FROM products WHERE 1=1"
    params = []

    if name_filter:
        query += " AND name LIKE %s"
        params.append(f"%{name_filter}%")
    
    if min_price:
        query += " AND price >= %s"
        params.append(min_price)

    if max_price:
        query += " AND price <= %s"
        params.append(max_price)

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(query, tuple(params))
    products = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify({"products": products}), 200

# 🟢 search on products
@products_bp.route("/products/<int:product_id>", methods=["GET"])
@jwt_required()
def get_product(product_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()

    cursor.close()
    connection.close()

    if not product:
        return jsonify({"error": "❌ Product not found"}), 404

    return jsonify(product), 200

# 🟢 update the products
@products_bp.route("/products/<int:product_id>", methods=["PUT"])
@jwt_required()
def update_product(product_id):
    data = request.json
    name = data.get("name")
    description = data.get("description", "")
    price = data.get("price")

    if not name or not price:
        return jsonify({"error": "Product name and price are required"}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()

    if not product:
        return jsonify({"error": "❌ Product not found"}), 404

    try:
        cursor.execute("UPDATE products SET name = %s, description = %s, price = %s WHERE id = %s",
                       (name, description, price, product_id))
        connection.commit()
        return jsonify({"message": "✅ Product updated successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        connection.close()

# 🟢 delete the products
@products_bp.route("/products/<int:product_id>", methods=["DELETE"])
@jwt_required()
def delete_product(product_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()

    if not product:
        return jsonify({"error": "❌ Product not found"}), 404

    try:
        cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
        connection.commit()
        return jsonify({"message": "✅ Product deleted successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        connection.close()
