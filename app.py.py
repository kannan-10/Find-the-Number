from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import random, time, json, os

app = Flask(__name__)
app.secret_key = "change_this_secret_in_prod"

LEADERBOARD_FILE = "leaderboard.json"

def load_leaderboard():
    if not os.path.exists(LEADERBOARD_FILE):
        return []
    with open(LEADERBOARD_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return []

def save_leaderboard(lb):
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(lb, f, indent=2)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    mode = request.form.get("mode", "classic")
    lowest = int(request.form.get("lowest", 1))
    highest = int(request.form.get("highest", 100))
    attempts = request.form.get("attempts")
    attempts = int(attempts) if attempts else None
    hint_mode = request.form.get("hint") == "on"
    timer_mode = request.form.get("timer") == "on"

    session["answer"] = random.randint(lowest, highest)
    session["lowest"] = lowest
    session["highest"] = highest
    session["low_bound"] = lowest
    session["high_bound"] = highest
    session["guesses"] = 0
    session["attempts"] = attempts
    session["hint_mode"] = hint_mode
    session["timer_mode"] = timer_mode
    session["start_time"] = time.time() if timer_mode else None
    session["mode_name"] = mode
    return redirect(url_for("game"))

@app.route("/game", methods=["GET", "POST"])
def game():
    message = ""
    correct = False
    if request.method == "POST":
        if "answer" not in session:
            return redirect(url_for("index"))
        guess_raw = request.form.get("guess", "")
        if not guess_raw.lstrip("-").isdigit():
            message = "Enter a valid integer."
        else:
            guess = int(guess_raw)
            session["guesses"] = session.get("guesses", 0) + 1
            answer = session["answer"]
            lowest = session["lowest"]
            highest = session["highest"]
            if guess < lowest or guess > highest:
                message = "Out of range."
            elif guess < answer:
                message = "Too low."
                if session.get("hint_mode"):
                    session["low_bound"] = max(session["low_bound"], guess+1)
            elif guess > answer:
                message = "Too high."
                if session.get("hint_mode"):
                    session["high_bound"] = min(session["high_bound"], guess-1)
            else:
                correct = True
                elapsed = time.time() - session["start_time"] if session.get("timer_mode") else None
                score = calculate_score(answer, session["guesses"], session.get("attempts"), elapsed)
                session["last_result"] = {"score": score, "guesses": session["guesses"], "elapsed": elapsed}
                # store no name yet; redirect to finish to enter name
                return redirect(url_for("finish"))
            # check attempts limit
            if session.get("attempts") and session["guesses"] >= session["attempts"]:
                session["last_result"] = {"score": 0, "guesses": session["guesses"], "elapsed": None, "failed": True}
                return redirect(url_for("finish"))

    return render_template("game.html",
        low_bound=session.get("low_bound", session.get("lowest", 1)),
        high_bound=session.get("high_bound", session.get("highest", 100)),
        guesses=session.get("guesses", 0),
        attempts=session.get("attempts"),
        message=message
    )

def calculate_score(answer, guesses, attempts_limit, elapsed):
    base = 100
    guess_penalty = (guesses - 1) * 5
    attempt_bonus = 0
    if attempts_limit:
        attempt_bonus = max(0, (attempts_limit - guesses) * 3)
    time_bonus = 0
    if elapsed is not None:
        time_bonus = max(0, int(30 - elapsed))
    return max(0, base - guess_penalty + attempt_bonus + time_bonus)

@app.route("/finish", methods=["GET", "POST"])
def finish():
    if "last_result" not in session:
        return redirect(url_for("index"))
    last = session["last_result"]
    failed = last.get("failed", False)
    if request.method == "POST":
        name = request.form.get("name", "Anonymous").strip() or "Anonymous"
        score = last.get("score", 0)
        mode = session.get("mode_name", "custom")
        lb = load_leaderboard()
        lb.append({"name": name, "score": score, "mode": mode, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        lb = sorted(lb, key=lambda x: x["score"], reverse=True)[:20]
        save_leaderboard(lb)
        return redirect(url_for("leaderboard"))
    return render_template("finish.html", last=last, failed=failed)

@app.route("/leaderboard")
def leaderboard():
    lb = load_leaderboard()
    return render_template("leaderboard.html", lb=lb)

if __name__ == "__main__":
    app.run(debug=True)
