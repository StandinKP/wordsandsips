from datetime import datetime
from random import randint
from flask  import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pyrebase
import secrets
from functools import wraps
from flask_cors import CORS


app = Flask(__name__)
app.secret_key = "sgdfsgfsgfdgfgdgfgfdgsdf"

CORS(app)

#Connecting Database to app 
firebaseConfig = {
  "apiKey": "AIzaSyCGuEitG3Xd0czAG2wzVXONANGrocCfMws",
  "authDomain": "words-and-sips.firebaseapp.com",
  "databaseURL": "https://words-and-sips-default-rtdb.asia-southeast1.firebasedatabase.app",
  "projectId": "words-and-sips",
  "storageBucket": "words-and-sips.appspot.com",
  "messagingSenderId": "636972441572",
  "appId": "1:636972441572:web:8a62641e6b9664c3d071f1",
  "measurementId": "G-64L58BNDME",
}

firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()


# Check if user logged in
def is_admin(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            if session['type'] == 'admin':
                return f(*args, **kwargs)
        else:
            flash('Please Login First', 'secondary')
            return redirect(url_for('login'))
    return wrap


# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Please Login First', 'secondary')
            return redirect(url_for('login'))
    return wrap


@app.route('/') 
def index():
    return render_template("index.html")

@app.route('/checkout') 
def checkout():
    cart_dict = session["cart"]["products"]
    cart = []
    total = 0
    for product_id in list(cart_dict.keys()):
        pro = db.child("menu").child(product_id).get().val()
        cart.append({
            "product_id": product_id,
            "name": pro.get("name"),
            "quantity": int(cart_dict[product_id]),
            "amount": int(pro.get("price")) * int(cart_dict[product_id]),
            "category": pro.get("category")
        })
        total += int(pro.get("price")) * int(cart_dict[product_id])
    return render_template("checkout.html", cart=cart, total=total)


@app.route('/remove_from_cart/<string:product_id>')
def remove_from_cart(product_id):
    product = db.child("menu").child(product_id).get().val()
    price = product["price"]
    session["cart"]["cart_total"] -= int(price) * int(session["cart"]["products"][product_id])
    del session["cart"]["products"][product_id]
    flash("Item deleted from cart!", "info")
    return redirect(url_for("checkout"))


@app.route('/confirm_order')
def confirm_order():
    cart_dict = session["cart"]["products"]
    cart = []
    for product_id in list(cart_dict.keys()):
        pro = db.child("menu").child(product_id).get().val()
        amount = int(pro.get("price")) * int(cart_dict[product_id])
        cart.append({
            "product_id": product_id,
            "name": pro.get("name"),
            "quantity": int(cart_dict[product_id]),
            "amount": amount ,
            "category": pro.get("category"),
        })
    order_id = randint(1, 99999)
    cart.append({
        "entry_fee": session["service_charge"]
    })
    data = {
        "name": session["name"],
        "order_no": order_id,
        "order": cart,
        "total": session["cart"]["cart_total"] + session["service_charge"],
        'location': session["location"],
        "start_time": session["start_time"],
        "status": "OPEN"
    }
    if session["location"] == "inside":
        data.update({"quantity": session["quantity"]})
    res = db.child("orders").push(data)
    session["cart"] = {"products": {}, "cart_total": 0}
    session["service_charge"] = 0
    print(res)
    flash("Order placed", "success")
    return redirect(url_for("menu"))


@app.route('/add_product/<string:order_id>')
def add_product(order_id):
    print(order_id)
    order = db.child("orders").child(order_id).get().val()
    if "cigarettes" in order.keys():
        res = db.child("orders").child(order_id).child("order").push({"cigarettes": order["cigarettes"] + 1, "total": order["total"] + 20})
    else:
        res = db.child("orders").child(order_id).child("order").push({"cigarettes": 1, "total": order["total"] + 20})
    flash("Product addedd successfully", "success")
    return redirect(url_for("dashboard"))

@app.route("/update_quantity/<product_id>/<quantity>")
def update_product_quantity(product_id, quantity):
    if "cart" in session:
        print("OLD CART:", session["cart"])
        product_dict = session["cart"]["products"]
        product_dict[product_id] = quantity
        cart_total = 0
        for product_id, quantity in product_dict.items():
            product = db.child("menu").child(product_id).get().val()
            price = product["price"]
            cart_total += int(price) * int(quantity)
        session["cart"]["cart_total"] = cart_total
        print("NEW CART:", session["cart"])
        session["cart"] = {"products": product_dict, "cart_total": cart_total}
        flash("Quantity updated!", "info")
    return redirect(url_for("checkout"))


@app.route('/checkin', methods = ['GET','POST'])
def checkin():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        location = request.form['location']
        table = request.form['table']
        quantity = int(request.form['quantity'])
        start_time = request.form['start_time']
        data = {
            "name": name,
            "phone": phone,
            "type":'customer',
            "location": location,
            "table": table,
            "quantity": quantity,
            "start_time": start_time
        }
        results = db.child("users").push(data)
        session["name"] = name
        session["phone"] = phone
        session["id"] = results["name"]
        session['location'] = location
        session['table'] = table
        session["cart"] = {"products": {}, "cart_total":0}
        session["quantity"] = quantity
        session["start_time"] = start_time
        if location == 'inside':
            session["service_charge"] = 100 * quantity
        return redirect(url_for('menu'))


@app.route('/manage_tabs')
def manage_tabs():
    


    return render_template("manage_tabs.html")

@app.route('/menu')
def menu():
    menu  = db.child("menu").get().val()
    categories = set([menu[item]["category"] for item in menu.keys()])
    return render_template("menu.html", menu=menu, categories=categories)


@app.route('/manage_menu', methods=['GET', 'POST'])
def manage_menu():
    if request.method == "POST":
        category = request.form.get("category")
        item_name = request.form.get("item_name")
        active_status = bool(request.form.get("active_status"))
        price = int(request.form.get("price"))
        data = {"active": active_status,
        "name": item_name,
        "category": category,
        "price": price}
        res = db.child("menu").push(data)
        flash("Product successfully added!", "success")
   

    menu  = db.child("menu").get().val()
    print(menu)
    return render_template("manage_menu.html", menu = menu)

@app.route("/delete_menu/<id>")
def delete_menu(id):
    print(id)
    res = db.child("menu").child(id).remove()
    flash("Deleted successfully", "success")
    return jsonify({
        "success": True
    })


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        admin = db.child("admin").get().val()
        if email == admin["email"] and password == admin["password"]:
            session["logged_in"] = True
            session["email"] = email
            session['type'] = 'admin'
            print('password matched')
            return redirect(url_for('dashboard'))
        


    return render_template("login.html")


@app.route('/admin/dashboard', methods=['GET', 'POST'])
@is_admin
def dashboard():
    orders = db.child("orders").order_by_child("status").equal_to("OPEN").get().val()
    return render_template("dashboard.html", orders=orders)


@app.route('/checkout_order/<string:order_id>', methods=['GET', 'POST'])
def checkout_order(order_id):
    order = db.child("orders").child(order_id).update({"status": "CLOSED"})
    print(order)
    return redirect(url_for("dashboard"))


@app.route('/order_history')
def order_history():
    orders = db.child("orders").order_by_child("status").equal_to("CLOSED").get().val()

    return render_template("order_history.html", orders=orders)
    

@app.route('/delete_order/<string:id>')
def delete_order(id):
    db.child("orders").child(id).remove()
    return redirect(url_for("order_history"))

@app.route('/add_member', methods=["POST"])
def add_member():
    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("name")
    res = db.child("users").push({
        "name": name,
        "email": email,
        "password": password,
        "type": "tab"
    })
    flash("Added successfully", "success")
    return redirect(url_for("manage_tabs"))


@app.route('/admin/logout/')
@is_logged_in
def logout():
    if 'logged_in' in session:
        session.clear()
        flash('Successfully logged out','success')
        return redirect(url_for('login'))
    else:
        flash('You are not Logged in','secondary')
        return redirect(url_for('login'))

@app.route('/add_to_cart/<string:product_id>')
def add_to_cart(product_id):
    item  = db.child("menu").child(product_id).get().val()
    if "cart" in session:
        product_dict = session["cart"]["products"]
        if product_id in product_dict:
            # add number
            product_dict[product_id] += 1
        else:
            # add key value
            product_dict[product_id] = 1
        total_price = int(session["cart"]["cart_total"])
        total_price += int(item["price"])
        session["cart"] = {"products": product_dict, "cart_total": total_price}
    else:
        session["cart"] = {
            "products": {product_id: 1},
            "cart_total": int(item["price"]),
        }
    flash("Added product to cart", "success")
    return redirect(url_for("menu"))

    
if __name__ == '__main__':
    app.run(debug=True, port=7001)
    