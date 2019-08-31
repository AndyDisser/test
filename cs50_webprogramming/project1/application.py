import os
import requests

from flask import Flask, session, render_template, request, redirect, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/", methods=["GET", "POST"])
def index():

    return render_template("index.html")
@app.route("/login", methods=["POST", "GET"])
def login():
    """Log User in"""

    #Forget any users
    session.clear()

    username = request.form.get("username_login")
    password = request.form.get("password_login")

    if db.execute("SELECT username, password FROM users WHERE username = :username AND password = :password", {"username": username, "password": password}).rowcount== 1:
        session["username"] = username
        return redirect(url_for('books'))

    else:
        return render_template("error.html", message="Username or Password are wrong")

@app.route("/logout", methods=["POST", "GET"])
def logout():
    """User Logout"""
    session.clear()
    return render_template("index.html")

@app.route("/register", methods=["POST", "GET"])
def register():
    """Register new user"""
    username=request.form.get("username_register")
    password=request.form.get("password_register")

    if username:
        if db.execute("SELECT * FROM users WHERE username = :username", {"username" :username}).rowcount==0:
            db.execute("INSERT INTO users (username, password) VALUES (:username, :password)", {"username": username, "password": password})
            db.commit()
            registered = 1
            return render_template("index.html", registered=registered)
        else:
            wrong=1
            return render_template("index.html", message="The username is already taken. Please choose another one!", wrong= wrong)


@app.route("/books")
def books():
    """List all books"""
    books = db.execute("SELECT * FROM books").fetchall()
    return render_template("books.html", books=books)

@app.route("/search", methods=["POST"])
def search():
    """Search for books"""
    search_request = request.form.get('search')
    books = db.execute("SELECT * FROM books WHERE isbn LIKE :search OR title LIKE :search OR author LIKE :search", {"search": "%" + search_request + "%"}).fetchall()
    return render_template("books.html", books=books)


@app.route("/book/<isbn>/", methods=["GET", "POST"])
def book(isbn):
    """List details about a single book"""
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    session["reviews"]=[]
    # Make sure book exists.
    if book is None:
        return render_template("error.html", massage = "No such book")

    username = session["username"]

    # check whether the logged-in person has already submitted a review
    review_logged_in = db.execute("SELECT review FROM reviews WHERE username = :username AND isbn = :isbn", {"username": username, "isbn": isbn}).fetchall()

    if not review_logged_in:
        new_review = request.form.get("new_review")
        rating = request.form.get("rating")

        # check if the person has submitted the form
        if new_review:
            db.execute("INSERT INTO reviews (isbn, review, rating, username) VALUES (:isbn, :review, :rating, :username)", {"isbn": isbn, "review": new_review, "rating": rating, "username": username})
            db.commit()
            review_logged_in=1

    reviews = db.execute("SELECT * FROM reviews WHERE isbn = :isbn", {"isbn": isbn}).fetchall()
    key = "DeQ8yz6RLMrsvG7umkDAQQ"
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": key, "isbns": isbn})
    average_rating=res.json()['books'][0]['average_rating']
    work_ratings_count=res.json()['books'][0]['work_ratings_count']
    reviews=db.execute("SELECT * FROM reviews WHERE isbn = :isbn",{"isbn":isbn}).fetchall()
    for y in reviews:
        session['reviews'].append(y)
    book=db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn":isbn}).fetchone()
    return render_template("book.html",book=book,reviews=session['reviews'],average_rating=average_rating,work_ratings_count=work_ratings_count,username=username,review_logged_in=review_logged_in)

@app.route("/api/<string:isbn>")
def api(isbn):
    book=db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn":isbn}).fetchone()
    if book==None:
        return render_template('404.html')
    key = "DeQ8yz6RLMrsvG7umkDAQQ"
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": key, "isbns": isbn})
    average_rating=res.json()['books'][0]['average_rating']
    work_ratings_count=res.json()['books'][0]['work_ratings_count']
    x = {
    "title": book.title,
    "author": book.author,
    "year": book.year,
    "isbn": isbn,
    "review_count": work_ratings_count,
    "average_score": average_rating
    }
    api=json.dumps(x)
    return render_template("api.json",api=api)


if __name__=='__main__':
    app.run(debug=True)
