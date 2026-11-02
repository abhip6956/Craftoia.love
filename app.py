from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "craftoria.db"

aapp = Flask(__name__, template_folder=".", static_folder=".", static_url_path="/static")
app.secret_key = "change-this-secret-key-before-publishing"


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'customer'
    );
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        image_url TEXT,
        stock INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        customer_name TEXT NOT NULL,
        address TEXT NOT NULL,
        phone TEXT NOT NULL,
        total REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'Placed',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id)
    );
    """)
    manager = conn.execute("SELECT id FROM users WHERE email = ?", ("manager@craftoria.love",)).fetchone()
    if manager is None:
        conn.execute(
            "INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
            ("Craftoria Manager", "manager@craftoria.love",
             generate_password_hash("Craft@123"), "manager")
        )
    count = conn.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"]
    if count == 0:
        sample_products = [
            ("Handmade Gift Box", "A thoughtful handmade gift box for special moments.", 499, "", 12),
            ("Crochet Flower Bouquet", "A colourful crochet bouquet made with care.", 799, "", 8),
            ("Personalised Keychain", "A cute personalised keychain for everyday use.", 149, "", 25),
            ("Decorative Candle", "A decorative candle for a warm and cosy space.", 299, "", 15),
        ]
        conn.executemany(
            "INSERT INTO products (name,description,price,image_url,stock) VALUES (?,?,?,?,?)",
            sample_products
        )
    conn.commit()
    conn.close()

# Is line se Render par start hote hi database aur table automatic ban jayegi
init_db()


def customer_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id") or session.get("role") != "customer":
            flash("Please log in with your customer account first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def manager_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id") or session.get("role") != "manager":
            flash("Manager login is required.", "warning")
            return redirect(url_for("manager_login"))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def cart_count():
    cart = session.get("cart", {})
    return {"cart_count": sum(int(q) for q in cart.values())}


@app.route("/")
def home():
    conn = get_db()
    products = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("index.html", products=products)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 6:
            flash("Please enter all details. Password must be at least 6 characters.", "danger")
            return redirect(url_for("register"))
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                (name, email, generate_password_hash(password), "customer")
            )
            conn.commit()
            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("This email is already registered.", "danger")
        finally:
            conn.close()
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        if user and user["role"] == "customer" and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = "customer"
            session["cart"] = {}
            return redirect(url_for("home"))
        flash("Invalid customer email or password.", "danger")
    return render_template("login.html", manager=False)


@app.route("/manager/login", methods=["GET", "POST"])
def manager_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ? AND role = 'manager'", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = "manager"
            return redirect(url_for("manager_dashboard"))
        flash("Invalid manager ID or password.", "danger")
    return render_template("login.html", manager=True)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    if product is None:
        flash("Product not found.", "danger")
        return redirect(url_for("home"))
    return render_template("product.html", product=product)


@app.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    if product is None or product["stock"] <= 0:
        flash("This product is currently unavailable.", "danger")
        return redirect(url_for("home"))
    cart = session.get("cart", {})
    key = str(product_id)
    cart[key] = int(cart.get(key, 0)) + 1
    if cart[key] > product["stock"]:
        cart[key] = product["stock"]
        flash("Maximum available stock added.", "warning")
    else:
        flash("Product added to your cart.", "success")
    session["cart"] = cart
    return redirect(request.referrer or url_for("home"))


@app.route("/cart")
def cart():
    cart_data = session.get("cart", {})
    items = []
    total = 0
    conn = get_db()
    for product_id, quantity in cart_data.items():
        product = conn.execute("SELECT * FROM products WHERE id = ?", (int(product_id),)).fetchone()
        if product:
            subtotal = product["price"] * int(quantity)
            items.append({"product": product, "quantity": int(quantity), "subtotal": subtotal})
            total += subtotal
    conn.close()
    return render_template("cart.html", items=items, total=total)


@app.route("/cart/update", methods=["POST"])
def update_cart():
    cart_data = session.get("cart", {})
    new_cart = {}
    conn = get_db()
    for product_id in list(cart_data.keys()):
        try:
            quantity = int(request.form.get("quantity_" + product_id, "0"))
        except ValueError:
            quantity = 0
        product = conn.execute("SELECT stock FROM products WHERE id = ?", (int(product_id),)).fetchone()
        if product and quantity > 0:
            new_cart[product_id] = min(quantity, product["stock"])
    conn.close()
    session["cart"] = new_cart
    flash("Cart updated.", "success")
    return redirect(url_for("cart"))


@app.route("/checkout", methods=["GET", "POST"])
@customer_required
def checkout():
    cart_data = session.get("cart", {})
    if not cart_data:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("cart"))
    conn = get_db()
    items = []
    total = 0
    for product_id, quantity in cart_data.items():
        product = conn.execute("SELECT * FROM products WHERE id = ?", (int(product_id),)).fetchone()
        if product and int(quantity) <= product["stock"]:
            subtotal = product["price"] * int(quantity)
            items.append((product, int(quantity), subtotal))
            total += subtotal
    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        address = request.form.get("address", "").strip()
        phone = request.form.get("phone", "").strip()
        if not customer_name or not address or not phone:
            flash("Please fill in your name, address and phone number.", "danger")
        elif not items:
            flash("Your cart has no available products.", "danger")
        else:
            cur = conn.execute(
                "INSERT INTO orders (user_id,customer_name,address,phone,total) VALUES (?,?,?,?,?)",
                (session["user_id"], customer_name, address, phone, total)
            )
            order_id = cur.lastrowid
            for product, quantity, subtotal in items:
                conn.execute(
                    "INSERT INTO order_items (order_id,product_id,product_name,quantity,price) VALUES (?,?,?,?,?)",
                    (order_id, product["id"], product["name"], quantity, product["price"])
                )
                conn.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product["id"]))
            conn.commit()
            conn.close()
            session["cart"] = {}
            flash("Order placed successfully. Payment method: Cash on Delivery.", "success")
            return redirect(url_for("my_orders"))
    conn.close()
    return render_template("checkout.html", items=items, total=total)


@app.route("/my-orders")
@customer_required
def my_orders():
    conn = get_db()
    orders = conn.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (session["user_id"],)
    ).fetchall()
    conn.close()
    return render_template("orders.html", orders=orders, manager=False)


@app.route("/manager")
@manager_required
def manager_dashboard():
    conn = get_db()
    products = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    orders = conn.execute(
        "SELECT orders.*, users.email FROM orders JOIN users ON orders.user_id=users.id ORDER BY orders.id DESC"
    ).fetchall()
    customers = conn.execute("SELECT COUNT(*) AS n FROM users WHERE role='customer'").fetchone()["n"]
    total_sales = conn.execute("SELECT COALESCE(SUM(total),0) AS n FROM orders").fetchone()["n"]
    conn.close()
    return render_template("manager.html", products=products, orders=orders,
                           customers=customers, total_sales=total_sales)


@app.route("/manager/product/add", methods=["GET", "POST"])
@manager_required
def add_product():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        image_url = request.form.get("image_url", "").strip()
        try:
            price = float(request.form.get("price", "0"))
            stock = int(request.form.get("stock", "0"))
        except ValueError:
            price, stock = 0, -1
        if not name or price <= 0 or stock < 0:
            flash("Enter a product name, a valid price and a valid stock quantity.", "danger")
        else:
            conn = get_db()
            conn.execute(
                "INSERT INTO products (name,description,price,image_url,stock) VALUES (?,?,?,?,?)",
                (name, description, price, image_url, stock)
            )
            conn.commit()
            conn.close()
            flash("Product added.", "success")
            return redirect(url_for("manager_dashboard"))
    return render_template("product_form.html", product=None)


@app.route("/manager/product/edit/<int:product_id>", methods=["GET", "POST"])
@manager_required
def edit_product(product_id):
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        conn.close()
        flash("Product not found.", "danger")
        return redirect(url_for("manager_dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        image_url = request.form.get("image_url", "").strip()
        try:
            price = float(request.form.get("price", "0"))
            stock = int(request.form.get("stock", "0"))
        except ValueError:
            price, stock = 0, -1
        if not name or price <= 0 or stock < 0:
            flash("Please enter valid product details.", "danger")
        else:
            conn.execute(
                "UPDATE products SET name=?,description=?,price=?,image_url=?,stock=? WHERE id=?",
                (name, description, price, image_url, stock, product_id)
            )
            conn.commit()
            conn.close()
            flash("Product updated.", "success")
            return redirect(url_for("manager_dashboard"))
    conn.close()
    return render_template("product_form.html", product=product)


@app.route("/manager/product/delete/<int:product_id>", methods=["POST"])
@manager_required
def delete_product(product_id):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    flash("Product deleted.", "success")
    return redirect(url_for("manager_dashboard"))


@app.route("/manager/order/status/<int:order_id>", methods=["POST"])
@manager_required
def update_order_status(order_id):
    status = request.form.get("status", "Placed")
    allowed = ["Placed", "Processing", "Shipped", "Delivered", "Cancelled"]
    if status not in allowed:
        status = "Placed"
    conn = get_db()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()
    flash("Order status updated.", "success")
    return redirect(url_for("manager_dashboard"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
