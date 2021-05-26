import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

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


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///typingtest.db")

# Make sure API key is set
#if not os.environ.get("API_KEY"):
#   raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Welcome screen"""
    if session["user_id"] != "0":
        #import name from users table
        row = db.execute("SELECT username, tests_done, average_wpm FROM users WHERE id =:user", user=session["user_id"])
        name = row[0]['username']
        tests_done = row[0]['tests_done']
        average_wpm = row[0]['average_wpm']
        return render_template("index.html", name=name, tests_done=tests_done, average_wpm = average_wpm)

    else:
        return render_template("index.html")


@app.route("/selecttext", methods=["GET"])
@login_required
def selecttext():
    """Typing Test"""

    if request.method == "GET":
        rows = db.execute("SELECT title, text FROM texts")
        titles = []
        for row in rows:
            title = row['title']
            titles.append(title)
        return render_template("selecttext.html", titles=titles)

@app.route("/test", methods=["POST"])
@login_required
def test():
    """Return selected text"""
    selected_text = request.form.get("selected_text")
    rows = db.execute("SELECT key, text FROM texts WHERE title = :title", title=selected_text)
    text = rows[0]['text']
    key = rows[0]['key']
    db.execute("UPDATE users SET current_text = :current_text WHERE id = :user", current_text=key , user=session["user_id"])
    return render_template("test.html", text=text, title=selected_text)


@app.route("/submittest", methods=["GET", "POST"])
@login_required
def submittest():
    """Show results of test"""
    if request.method == "POST":
        timetaken = request.get_json()
        db.execute("UPDATE users SET current_timetaken = :timetaken WHERE id = :user", timetaken = timetaken, user = session["user_id"])
        return jsonify(status="success", timetaken=timetaken)

    if request.method == "GET":
        rows = db.execute("SELECT current_text, current_timetaken, error, input_text, original_input_text, errors_made FROM users WHERE id = :user", user = session["user_id"])
        for row in rows:
            text_key = row['current_text']
            timetaken = row['current_timetaken']
            error = row['error']
            input_text = row['input_text']
            original_input_text = row['original_input_text']
            errors_made = row['errors_made']

        if error == True:
            return redirect('/selecttext')

        # count number of characters from input_text
        original_count = len(original_input_text)
        adjusted_count = len(input_text)

        print("--------------------------------------------------WORD COUNT")
        print("original_count:", original_count)
        print("adjusted_count:", adjusted_count)
        # calculate cpm and wpm
        original_cpm = round(original_count / (timetaken / 60000))
        original_wpm = round(original_cpm / 5, 1)
        adjusted_cpm = round(adjusted_count / (timetaken / 60000))
        adjusted_wpm = round(adjusted_cpm / 5, 1)

        time_seconds = round(timetaken / 1000, 1)


        rows = db.execute("SELECT title FROM texts WHERE key = :text_key", text_key=text_key)
        for row in rows:
            title = row['title']

        db.execute("INSERT INTO history (user_id, text_key, wpm) VALUES (:user, :text_key, :wpm)", user=session["user_id"], text_key=text_key, wpm=adjusted_wpm)

        rows = db.execute("SELECT COUNT(wpm), AVG(wpm) FROM history WHERE user_id = :user", user=session["user_id"])
        print("----------------------------------calculate number of tests done and average wpm")
        print(rows)
        tests_done = rows[0]['COUNT(wpm)']
        average_wpm = round(rows[0]['AVG(wpm)'], 1)
        db.execute("UPDATE users SET tests_done = :tests_done, average_wpm = :average_wpm WHERE id =:user", tests_done=tests_done, average_wpm=average_wpm, user=session["user_id"])

        return render_template("results.html", title=title, timetaken=time_seconds, wpm=original_wpm, cpm=original_cpm, adjusted_cpm=adjusted_cpm, adjusted_wpm=adjusted_wpm, errors_made=errors_made)


@app.route("/submittext", methods=["POST"])
@login_required
def submittext():
    """Submit input text"""
    typed_text = request.form.get("typed_text")
    typed_text = typed_text.rstrip()
    print(typed_text, len(typed_text))
    typed_length = len(typed_text)

    if typed_length == 0:
        flash("Invalid input! Please try again")
        db.execute("UPDATE users SET error = :error WHERE id = :user", error=True, user=session["user_id"])
        return redirect ("/selecttext")

    db.execute("UPDATE users SET original_input_text = :input_text, error = :error WHERE id = :user", input_text=typed_text, error=False, user=session["user_id"])

    rows = db.execute("SELECT users.original_input_text, texts.text FROM users JOIN texts ON texts.key = users.current_text WHERE users.id = :user", user=session["user_id"])
    print(rows)
    for row in rows:
        input_text = (row['original_input_text']).split()
        text = (row['text']).split()
    print(input_text)
    print(text)
    print("-----------------------------------------------------------------COMPARE input_text AND text")


    # remove additional words from input text
    if len(input_text) > len(text):
        for i in range(len(input_text) - 1, len(text) - 2, -1):
            print(i)
            print(input_text)
            print("----------------------------------------CHECK removal of text")
            del input_text[i]
        # error checking
        errors = 0
        for i in range(len(text) - 1):
            print(input_text[i])
            print(text[i])
            print("------------------------------------------COMPARING TEXTS")
            if input_text[i] != text[i]:
                errors += 1
                print("number of errors:", errors)



    # adds random words in input_text if length shorter than text

    if len(input_text) < len(text):
        unedited_input_text = input_text.copy()
        print("difference in length:", len(text) - len(input_text))
        for i in range(len(text) - len(input_text)):
            print(i)
            input_text.append("thisisagarbageword")
            print(input_text)
            print("---------------------------------------CHECK addition of garbage word")

        # error checking
        errors = 0
        for i in range(len(text) - 1):
            print(input_text[i])
            print(text[i])
            print("------------------------------------------COMPARING TEXTS")
            if input_text[i] != text[i]:
                errors += 1
                print("number of errors:", errors)

        input_text = unedited_input_text

    # if correct length

    else:
        errors = 0
        for i in range(len(text)):
            print("target value of i:", len(text))
            print("value of i:", i)
            print(input_text[i])
            print(text[i])
            print("------------------------------------------COMPARING TEXTS")
            if input_text[i] != text[i]:
                errors += 1
                print("number of errors:", errors)

    edited_text = text
    print("-----------------------------------------------------------------------compared TEXT:", edited_text)
    i = 0
    while i < len(input_text):
        print(i)
        if input_text[i] != edited_text[i]:
            print("-----------------------------------------DIFFERENCE IN TEXT @ i value!")
            del input_text[i]
            del edited_text[i]
            print(input_text)
            print(edited_text)
            print("---------------------------------------------DELETION OF input_text")
        else:
            i += 1
    print("----------------------------------------------final updated TEXT:", )




    # rejoin input text
    updated_input_text = ' '.join(input_text)
    print(updated_input_text)
    print("--------------------UPDATED INPUT_TEXT--------------------")
    db.execute("UPDATE users SET errors_made = :errors_made, input_text = :input_text WHERE id = :user", errors_made=errors, input_text=updated_input_text, user=session["user_id"])



@app.route("/history")
@login_required
def history():
    """Show history of tests taken"""
    rows = db.execute("SELECT username FROM users WHERE id = :user", user=session["user_id"])
    name = rows[0]['username']

    table = db.execute("SELECT history.text_key, history.wpm, history.time, texts.title FROM history JOIN texts ON history.text_key = texts.key WHERE user_id = :user", user=session["user_id"])
    return render_template("history.html", name=name, table=table)

@app.route("/deletehistory")
@login_required
def deletehistory():
    """Delete history for user"""
    db.execute("DELETE FROM history WHERE user_id = :user", user=session["user_id"])
    db.execute("UPDATE users SET tests_done = 0, average_wpm = 0 WHERE id = :user", user=session["user_id"])
    flash("Deleted!")
    return redirect("/history")


@app.route("/upload", methods=["POST", "GET"])
@login_required
def upload():
    """Allows registered users to upload their own text to the database"""
    if request.method == "GET":
        if session["user_id"] == 0:
            print("guest account cannot upload texts ------------------------------")
            flash("You must register an account to upload texts.")
            return redirect("/")
        else:
            return render_template("upload.html")

    if request.method == "POST":
        titleupload = request.form.get("titleupload")
        titleupload = titleupload.rstrip()
        textupload = request.form.get("textupload")
        textupload = textupload.rstrip()
        db.execute("INSERT INTO texts (title, text) VALUES (:title, :text)", title=titleupload, text=textupload)

        flash("Upload successful!")
        return redirect("/")


@app.route("/statistics")
@login_required
def statistics():
    """Shows statistics of all recorded tests"""
    # calculate total avg wpm
    total_sum = 0
    total_test = 0
    rows = db.execute("SELECT tests_done, average_wpm FROM users")
    for row in rows:
        tests_done = row['tests_done']
        average_wpm = row['average_wpm']
        total_test += tests_done
        wpm_sum = tests_done * average_wpm
        total_sum += wpm_sum
    total_avg_wpm = round(total_sum / total_test, 1)

    # calculate user average wpm

    rows = db.execute("SELECT average_wpm FROM users WHERE id = :user", user=session["user_id"])
    average_wpm = rows[0]['average_wpm']

    rows = db.execute("SELECT text_key, wpm FROM history WHERE user_id = :user", user=session["user_id"])
    max_wpm = 0
    max_text_key = 0
    min_wpm = 10000
    min_text_key = 0
    for row in rows:
        if row['wpm'] > max_wpm:
            max_wpm = row['wpm']
            max_text_key = row['text_key']
        if row['wpm'] < min_wpm:
            min_wpm = row['wpm']
            min_text_key = row['text_key']

    if max_wpm == 0:
        max_wpm = 'NULL'
        min_wpm = 'NULL'

    rows = db.execute("SELECT tests_done, average_wpm FROM users WHERE id = :user", user=session["user_id"])
    tests_done = rows[0]['tests_done']
    average_wpm = rows[0]['average_wpm']

    return render_template("statistics.html", tests_done=tests_done, average_wpm=average_wpm, total_test=total_test, total_avg_wpm=total_avg_wpm,
                                            max_wpm=max_wpm, max_text_key=max_text_key, min_wpm=min_wpm, min_text_key=min_text_key)

@app.route("/guestlogin", methods=["POST"])
def guestlogin():
    """Log in as guest"""

    session.clear()
    session["user_id"] = 0
    return redirect("/")

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
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")

    elif request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)


        else:
            new_username = request.form.get("username")
            # Query database for username
            user = db.execute("SELECT * FROM users WHERE username = :username", username=new_username)
            # Ensure username created is unique
            if len(user) != 0:
                return apology("Username has been taken", 403)

            else:
                # Ensure both passwords are the same
                if request.form.get("password") != request.form.get("password-again"):
                    return apology("Password mismatch", 403)

                hashkey = generate_password_hash(request.form.get("password"))

                # Insert data into users table
                db.execute("INSERT INTO users (username, hash) VALUES (:username, :hashkey)", username=new_username, hashkey=hashkey)
                user_id = db.execute("SELECT id FROM users WHERE username = :name", name=new_username)
                session["user_id"] = user_id[0]['id']
                flash("Registered!")
                return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)


@app.route("/test1", methods=["GET", "POST"])
@login_required
def testing1():
    """send result"""
    if request.method == "POST":
        timetaken = request.get_json()
        print(timetaken)
        db.execute("UPDATE users SET current_timetaken = :timetaken WHERE id = :user", timetaken = timetaken, user = session["user_id"])
        return jsonify(status="success", timetaken=timetaken)

    if request.method == "GET":
        return render_template("test1.html")

@app.route("/test2", methods=["GET"])
@login_required
def testing2():
    """Show results of test1"""
    if request.method == "GET":
        rows = db.execute("SELECT current_text, current_timetaken FROM users WHERE id = :user", user = session["user_id"])
        for row in rows:
            text = row['current_text']
            timetaken = row['current_timetaken']
        return render_template("test2.html", text=text, timetaken=timetaken)

