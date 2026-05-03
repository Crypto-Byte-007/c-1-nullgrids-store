from flask import Flask, request, jsonify, session
import hashlib
import json
import os

app = Flask(__name__)

# Secret key from Railway variables
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

# Flag from Railway variables
FLAG = os.getenv("FLAG", "nullgrids{test_flag}")

PRODUCTS = {
    "TOOL_001": {
        "name": "NullGrids Pro License",
        "price": 999.99
    },

    "TOOL_002": {
        "name": "Dev Starter Pack",
        "price": 49.99
    },

    "TOOL_003": {
        "name": "Admin Toolkit",
        "price": 0.01
    }
}

DISCOUNT_CODES = {
    "SAVE10": 0.10,
    "INTERN": 0.50,
}


def compute_order_hash(items, discount):

    payload = json.dumps(
        items,
        sort_keys=True
    ) + str(discount)

    return hashlib.sha256(
        payload.encode()
    ).hexdigest()[:16]


@app.route("/")
def index():

    return """
    <html>
    <head>
        <title>NullGrids Store</title>
    </head>

    <body style='font-family:monospace;background:#111;color:#0f0;padding:40px'>

        <h1>NullGrids Internal Store</h1>

        <p>Endpoints:</p>

        <ul>
            <li>GET /products</li>
            <li>POST /cart/add</li>
            <li>POST /checkout</li>
            <li>POST /pay</li>
        </ul>

        <p>
            Premium rewards require spending over $500
        </p>

    </body>
    </html>
    """


@app.route("/health")
def health():
    return "OK"


@app.route("/products")
def products():

    visible = {
        k: v for k, v in PRODUCTS.items()
        if v["price"] >= 1.0
    }

    return jsonify(visible)


@app.route("/api/discount/validate", methods=["POST"])
def discount_validate():

    try:
        data = request.get_json(
            force=True,
            silent=True
        ) or {}

    except Exception:
        data = {}

    code = data.get("code", "")

    if code == "ADMIN_FREE":

        return jsonify({
            "valid": False,
            "msg": "Code expired"
        }), 403

    if code in DISCOUNT_CODES:

        return jsonify({
            "valid": True,
            "discount": DISCOUNT_CODES[code]
        })

    return jsonify({
        "valid": False,
        "msg": "Invalid code"
    })


@app.route("/cart/add", methods=["POST"])
def cart_add():

    try:
        data = request.get_json(
            force=True,
            silent=True
        ) or {}

    except Exception:
        data = {}

    pid = data.get("product_id", "")

    qty = int(data.get("qty", 1))

    if pid not in PRODUCTS:

        return jsonify({
            "error": "Product not found"
        }), 404

    if qty < 1:

        return jsonify({
            "error": "Invalid quantity"
        }), 400

    cart = session.get("cart", {})

    cart[pid] = cart.get(pid, 0) + qty

    session["cart"] = cart

    return jsonify({
        "cart": cart,
        "msg": "Item added"
    })


@app.route("/checkout", methods=["POST"])
def checkout():

    cart = session.get("cart", {})

    if not cart:

        return jsonify({
            "error": "Cart is empty"
        }), 400

    data = request.get_json(force=True) or {}

    discount_code = data.get(
        "discount_code",
        ""
    )

    total = sum(
        PRODUCTS[pid]["price"] * qty
        for pid, qty in cart.items()
        if pid in PRODUCTS
    )

    discount_pct = DISCOUNT_CODES.get(
        discount_code,
        0.0
    )

    total_after = round(
        total * (1 - discount_pct),
        2
    )

    is_premium = total > 500

    order = {
        "items": cart,
        "raw_total": total,
        "discount_pct": discount_pct,
        "final_total": total_after,
        "premium_order": is_premium
    }

    order["hash"] = compute_order_hash(
        cart,
        discount_pct
    )

    session["pending_order"] = order

    return jsonify(order)


@app.route("/pay", methods=["POST"])
def pay():

    data = request.get_json(force=True)

    pending = session.get("pending_order")

    if not pending:

        return jsonify({
            "error": "No pending order"
        }), 400

    submitted_hash = data.get(
        "order_hash",
        ""
    )

    total_paid = float(
        data.get("total_paid", -1)
    )

    # Vulnerable business logic
    if submitted_hash != pending["hash"]:

        return jsonify({
            "error": "Hash mismatch"
        }), 403

    if total_paid < 0:

        return jsonify({
            "error": "Invalid payment amount"
        }), 400

    unlocked_premium = (
        pending.get("premium_order")
        or total_paid > 500
    )

    if unlocked_premium:

        return jsonify({
            "status": "Payment accepted",
            "receipt": "Premium order confirmed",
            "access_token": FLAG
        })

    return jsonify({
        "status": "Payment accepted",
        "receipt": f"Standard order for ${total_paid}",
        "note": "Upgrade to premium"
    })


if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 8080)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
