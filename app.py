# EXPORT API_KEY: export API_KEY=pk_3565dd0c50b54643b90fa7ae9f1c6bc0
import os
import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")
# create a purchase history table


# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/home")
@login_required
def home():
    """Show portfolio of stocks"""
    s_name = []
    s_price = []
    s_amount = []
    s_value = []
    stock_value = 0
    check_stock_amount = '0.0'
    u_name = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    stock_name = db.execute("SELECT symbol FROM purchases WHERE username = ? AND amount != ?", u_name[0]['username'], check_stock_amount)
    stock_amount = db.execute("SELECT amount FROM purchases WHERE username = ? AND amount != ?", u_name[0]['username'], check_stock_amount)

    user_name = u_name[0]['username']
    for i in stock_name:
        s_name.append(i['symbol'])

    for j in s_name:
        s_price.append(lookup(j)['price'])

    for i in stock_amount:
        s_amount.append(round(i['amount'],0))

    for i in range(len(s_amount)):
        s_value.append(s_price[i] * s_amount[i])

    for x in s_value:
        stock_value = stock_value + x

    user_balance = db.execute("SELECT cash FROM users WHERE username = ?", u_name[0]['username'])
    current_balance = round(user_balance[0]['cash'], 2)
    total_balance = round(float(stock_value), 2)

    total = round(float(current_balance) + float(stock_value), 2)
    profit_loss = round(total_balance - 10000, 2)

    return render_template('home.html', stock_name=stock_name, stock_amount=stock_amount, current_balance=current_balance, s_price=s_price, s_value=s_value, total_balance=total_balance, user_name=user_name, profit_loss=profit_loss, total=total)



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    users_name = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    balance = db.execute("SELECT cash FROM users WHERE username = ?", users_name[0]['username'])
    spent_funds = db.execute("select SUM(cost) from purchases where username=?", users_name[0]['username'])

    if request.method == "POST":
        user_symbol = request.form.get("symbol")
        user_shares = request.form.get("shares")
        user_symbol = user_symbol.upper()
        user_shares = round(int(user_shares))
       
        if len(str(user_symbol)) < 1:
            return apology("You need to enter a symbol/amount of shares.", 400)
        if user_shares < 1:
            return apology("You need to enter a amount greater than 1.", 400)

        current_price = lookup(user_symbol)["price"]
        balance = db.execute("SELECT cash FROM users WHERE username = ?", users_name[0]['username'])
        # users_balance is in string
        users_balance = balance[0]['cash']

        users_amount = user_shares
        users_cost = int(users_amount) * float(current_price)
        users_purchase_price = current_price
    
        # db.execute("CREATE TABLE ? ( ?, ?, ?, ?)", users_name, users_name, users_stock_symbol, users_purchase_price, datetime.datetime.now())
        # db.execute("DROP TABLE purchases;")
        
        # db.execute("CREATE TABLE purchases (id INTEGER PRIMARY KEY, username TEXT NOT NULL, symbol TEXT, price FLOAT, amount FLOAT, cost FLOAT, date DATETIME)")

        
        if current_price * int(user_shares) > users_balance:
            return apology("You have insufficient balance", 400)
        
        else:
            check_symbol = db.execute("SELECT symbol FROM purchases WHERE username = ?", users_name[0]['username'])
            if user_symbol not in [s['symbol'] for s in check_symbol]:
                db.execute("INSERT INTO purchases (username, symbol, price, amount, cost) VALUES (:username, :symbol, :price, :amount, :cost)", username=users_name[0]['username'], symbol=str(user_symbol), price=float(users_purchase_price), amount=int(users_amount), cost=float(users_cost))
            else:
                initial_amount = db.execute("SELECT amount FROM purchases WHERE symbol = ? AND username = ?", user_symbol, users_name[0]['username'])
                initial_cost = db.execute("SELECT cost FROM purchases WHERE symbol = ? AND username = ?", user_symbol, users_name[0]['username'])
                updated_amount = str(float(initial_amount[0]['amount']) + float(users_amount))
                updated_cost = str(float(initial_cost[0]['cost']) + float(users_cost))
                db.execute("UPDATE purchases SET amount = ?, cost = ? WHERE symbol = ? AND username = ?", updated_amount, updated_cost, user_symbol, users_name[0]['username'])
            
            blnce = db.execute("SELECT cash FROM users WHERE username = ?", users_name[0]['username'])
            curr_blnce = blnce[0]['cash']
            spent_funds = db.execute("select SUM(cost) from purchases where username=?", users_name[0]['username'])
            users_balance = float(curr_blnce) - float(current_price * int(user_shares))
            db.execute("UPDATE users SET cash=? where username=?", str(users_balance), users_name[0]['username'])
            db.execute("INSERT INTO history (username, symbol, price, shares, date) VALUES (:username, :symbol, :price, :shares, :date)", username=users_name[0]['username'], symbol=str(user_symbol), price=float(users_purchase_price), shares=int(users_amount), date=datetime.datetime.now().strftime("%c"))

        return redirect("/home")
      
    else:
        return render_template("buy.html", balance=balance, spent_funds=spent_funds)



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    users_name = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    user_history = db.execute("SELECT symbol, shares, price, date FROM history WHERE username = ?", users_name[0]['username'])
    # shares = db.execute("SELECT shares FROM history WHERE ")
    return render_template('transactions.html', user_history=user_history)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/home")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/login")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        user_quote = request.form.get('symbol')

        if user_quote.strip() != "":
            # return apology("You must input a symbol", 400)

            if lookup(user_quote) == None:
                return apology("Invalid symbol", 400)
            else:
                quotes = lookup(user_quote)
                return render_template("quoted.html", quotes=quotes)
        else:
            return apology("No input", 400)
    else:
        return render_template("quote.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        user_name = request.form.get('username')
        user_password = request.form.get('password')
        user_confirmation = request.form.get('confirmation')
        user_cash = request.form.get('cash')

        if user_name.strip() == "":
            return apology("must provide username", 400)
        elif user_password == "":
            return apology("must provide password", 400)
        elif user_confirmation == "":
            return apology("must confirm password", 400)



        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        if user_password != user_confirmation:
            return apology("password must be same", 400)
        if len(rows) == 1:
            return apology("Username already exists! try another username", 400)
        else:
            db.execute("INSERT INTO users (username, hash, cash) VALUES(:username, :password, :cash)", username=user_name, password=generate_password_hash(user_password), cash=user_cash)
            # db.execute("UPDATE users SET cash = ?", user_cash)

            return redirect("/home")



    else:
        return render_template("register.html")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        symbol = request.form.get("stocks")
        amount = request.form.get("amount")
        u_name = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])

        if symbol == '' or amount == '':
            return apology("Please select a stock symbol and enter an amount to sell")
        else:
            u_name = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
            stock_name = db.execute("SELECT symbol FROM purchases WHERE username = ?", u_name[0]['username'])
            stocks = [x['symbol'] for x in stock_name]

            stock_amount = db.execute("SELECT amount FROM purchases WHERE username = ? AND symbol = ?", u_name[0]['username'], symbol)
            s_amount = float(stock_amount[0]['amount'])
            price = db.execute("SELECT price FROM purchases WHERE username = ? AND symbol = ?", u_name[0]['username'], symbol)
            s_price = float(price[0]['price'])
            cash_balance = db.execute("SELECT cash FROM users WHERE username = ?", u_name[0]['username'])
            balance = float(cash_balance[0]['cash'])
            
            if float(amount) > s_amount:
                return apology("Too much shares", 400)
            else:
                s_amount = s_amount - float(amount)
                cost = s_amount * s_price
                current_stock_price = lookup(symbol)["price"]
                sold_stock_value = (float(amount) * float(current_stock_price)) + balance

                db.execute("UPDATE purchases SET amount = ?, cost = ? WHERE symbol = ? AND username = ?", str(s_amount), str(cost), symbol, u_name[0]['username'])
                db.execute("UPDATE users SET cash = ? WHERE username = ?", str(sold_stock_value), u_name[0]['username'])
                sold = "-" + str(amount)
                db.execute("INSERT INTO history (username, symbol, price, shares, date) VALUES (:username, :symbol, :price, :shares, :date)", username=u_name[0]['username'], symbol=str(symbol), price=float(current_stock_price), shares=int(sold), date=datetime.datetime.now().strftime("%c"))
                
                return redirect("home")
    check_stock_amount = '0.0'
    u_name = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    stock_name = db.execute("SELECT symbol FROM purchases WHERE username = ? AND amount != ?", u_name[0]['username'], check_stock_amount)
    stocks = [x['symbol'] for x in stock_name]

    return render_template('sell.html', stock_name=stocks)






@app.route("/")
def index():
    top_stocks = ["MSFT", 'NFLX', "AMZN", "UBER", "PYPL", "AAPL", "FB"]
    data = [lookup(stock) for stock in top_stocks]
    return render_template('index.html', data=data)









def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)


if __name__ == '__main__':
    app.run(debug=True)