import json
import os
import re
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from app.tasks import JAVA_TEMPLATE, PYTHON_TEMPLATE, TASKS

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "exam.db"
EXAM_MINUTES = int(os.getenv("EXAM_MINUTES", "90"))
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "local-exam-change-me")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS attempts (
          id INTEGER PRIMARY KEY, group_name TEXT NOT NULL, first_name TEXT NOT NULL,
          last_name TEXT NOT NULL, language TEXT NOT NULL, started_at TEXT NOT NULL,
          expires_at TEXT NOT NULL, submitted_at TEXT, total_score INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS solutions (
          attempt_id INTEGER NOT NULL, task_id INTEGER NOT NULL, code TEXT NOT NULL,
          passed INTEGER DEFAULT 0, total INTEGER DEFAULT 0, score INTEGER DEFAULT 0,
          efficiency TEXT DEFAULT '', similarity INTEGER DEFAULT 0, updated_at TEXT NOT NULL,
          PRIMARY KEY (attempt_id, task_id)
        );
        """)


def now():
    return datetime.now(timezone.utc)


def allowed_student(group, first, last):
    try:
        roster = json.loads((ROOT / "students.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return any(x.get("group") == group and x.get("first_name") == first and x.get("last_name") == last for x in roster)


def current_attempt():
    ident = session.get("attempt_id")
    if not ident:
        return None
    with db() as con:
        row = con.execute("SELECT * FROM attempts WHERE id = ?", (ident,)).fetchone()
    return row


def remaining(attempt):
    return max(0, int((datetime.fromisoformat(attempt["expires_at"]) - now()).total_seconds()))


def task_by_id(task_id):
    return next((x for x in TASKS if x["id"] == task_id), None)


def normalize(value):
    return " ".join(value.strip().split())


def is_correct_output(task, source, output, expected):
    """Task 5 may have more than one valid pair of indices."""
    if task["id"] != 5:
        return normalize(output) == normalize(expected)
    try:
        answer = [int(x) for x in output.split()]
        values = [int(x) for x in source.split()]
        n = values[0]
        numbers, target = values[1:n + 1], values[-1]
        left, right = answer
        return len(answer) == 2 and 0 <= left < right < n and numbers[left] + numbers[right] == target
    except (ValueError, IndexError):
        return False


def run_in_container(language, code, input_data):
    """Run only a single task invocation, isolated from host and network."""
    if len(code) > 15000:
        return None, "Код слишком длинный (лимит 15 000 символов)."
    (ROOT / "submissions").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="denis-exam-", dir=ROOT / "submissions") as temp:
        folder = Path(temp)
        # Docker daemon runs on the host. Under docker-compose it must receive
        # the host-side path of the shared submissions directory, not /app/….
        host_dir = os.getenv("EXECUTOR_HOST_DIR")
        executor_volume = os.getenv("EXECUTOR_VOLUME")
        if executor_volume:
            mount_spec, work_path = f"{executor_volume}:/work:ro", f"/work/{folder.name}"
        else:
            mount_folder = str(Path(host_dir) / folder.name) if host_dir else str(folder)
            mount_spec, work_path = f"{mount_folder}:/work:ro", "/work"
        if language == "python":
            (folder / "solution.py").write_text(code, encoding="utf-8")
            (folder / "main.py").write_text(
                "import solution\nimport sys\nresult = solution.solve(sys.stdin.read())\nprint(str(result))\n", encoding="utf-8")
            image, command = "python:3.12-alpine", ["python", f"{work_path}/main.py"]
        else:
            (folder / "Solution.java").write_text(code, encoding="utf-8")
            (folder / "Main.java").write_text(
                "import java.io.*; public class Main { public static void main(String[] a) throws Exception { "
                "String s=new String(System.in.readAllBytes()); System.out.println(Solution.solve(s)); } }", encoding="utf-8")
            image, command = "eclipse-temurin:21-jdk-alpine", ["sh", "-c", f"javac -d /tmp {work_path}/Solution.java {work_path}/Main.java && java -cp /tmp Main"]
        cmd = ["docker", "run", "--rm", "-i", "--network", "none", "--read-only", "--cap-drop", "ALL",
               "--security-opt", "no-new-privileges", "--pids-limit", "64", "--memory", "128m", "--cpus", "0.5",
               "--tmpfs", "/tmp:rw,noexec,nosuid,size=32m", "-v", mount_spec, "-e", "PYTHONDONTWRITEBYTECODE=1", image] + command
        try:
            result = subprocess.run(cmd, input=input_data, capture_output=True, text=True, timeout=4)
        except FileNotFoundError:
            return None, "Docker не найден. Установите и запустите Docker Desktop."
        except subprocess.TimeoutExpired:
            return None, "Превышен лимит времени выполнения (3 секунды)."
        if result.returncode != 0:
            error = (result.stderr or result.stdout or "Ошибка запуска").strip()
            return None, error[-1200:]
        return result.stdout, None


def efficiency_note(code, task_id, language):
    lower = code.lower()
    nested = len(re.findall(r"\b(for|while)\b", lower)) >= 2
    if task_id == 5:
        if any(x in lower for x in ("hashmap", "dictionary", "dict", "hashmap", "seen")):
            return "Похоже на эффективное решение O(n) с таблицей поиска."
        if nested:
            return "Вероятно O(n²): задача решается за O(n) через хеш-таблицу."
    if nested:
        return "Обнаружены несколько циклов: проверьте, нужны ли все вложенные проходы."
    return "Структура решения выглядит рационально для этой задачи."


def similarity(code, reference):
    words_a = set(re.findall(r"[a-zA-Z_]+", code.lower()))
    words_b = set(re.findall(r"[a-zA-Z_]+", reference.lower()))
    return round(100 * len(words_a & words_b) / max(1, len(words_a | words_b)))


@app.route("/")
def index():
    return render_template("welcome.html")


@app.get("/login")
def login():
    return render_template("index.html")


@app.post("/student/login")
def student_login():
    group = request.form.get("group", "").strip()
    first = request.form.get("first_name", "").strip()
    last = request.form.get("last_name", "").strip()
    if not allowed_student(group, first, last):
        return render_template("index.html", error="Такого студента нет в списке допуска."), 403
    with db() as con:
        open_attempt = con.execute("SELECT * FROM attempts WHERE group_name=? AND first_name=? AND last_name=? AND submitted_at IS NULL ORDER BY id DESC LIMIT 1", (group, first, last)).fetchone()
        if open_attempt and remaining(open_attempt) > 0:
            session["attempt_id"] = open_attempt["id"]
            return redirect(url_for("exam"))
    session["pending_student"] = {"group": group, "first": first, "last": last}
    return redirect(url_for("language"))


@app.route("/language", methods=["GET", "POST"])
def language():
    pending = session.get("pending_student")
    if not pending:
        return redirect(url_for("index"))
    if request.method == "POST":
        language = request.form.get("language")
        if language not in ("python", "java"):
            return redirect(url_for("language"))
        began = now()
        with db() as con:
            cur = con.execute("INSERT INTO attempts(group_name,first_name,last_name,language,started_at,expires_at) VALUES(?,?,?,?,?,?)",
                              (pending["group"], pending["first"], pending["last"], language, began.isoformat(), (began + timedelta(minutes=EXAM_MINUTES)).isoformat()))
            session["attempt_id"] = cur.lastrowid
        session.pop("pending_student", None)
        return redirect(url_for("exam"))
    return render_template("language.html")


@app.route("/exam")
def exam():
    attempt = current_attempt()
    if not attempt:
        return redirect(url_for("index"))
    if attempt["submitted_at"] or remaining(attempt) <= 0:
        return redirect(url_for("finish"))
    with db() as con:
        solved = {r["task_id"]: dict(r) for r in con.execute("SELECT * FROM solutions WHERE attempt_id=?", (attempt["id"],))}
    task_payload = []
    for task in TASKS:
        item = dict(task)
        saved = solved.get(task["id"])
        item["code"] = saved["code"] if saved else (PYTHON_TEMPLATE if attempt["language"] == "python" else JAVA_TEMPLATE)
        item["score"] = saved["score"] if saved else 0
        task_payload.append(item)
    return render_template("exam.html", attempt=attempt, tasks=task_payload, seconds=remaining(attempt))


@app.post("/api/run")
def api_run():
    attempt = current_attempt()
    if not attempt or attempt["submitted_at"] or remaining(attempt) <= 0:
        return jsonify(error="Экзамен недоступен."), 403
    payload = request.get_json(force=True)
    task = task_by_id(int(payload.get("task_id", 0)))
    code = payload.get("code", "")
    if not task or not isinstance(code, str):
        return jsonify(error="Неверные данные."), 400
    cases, passed, log = task["tests"], 0, []
    for source, expected in cases:
        output, error = run_in_container(attempt["language"], code, source)
        ok = error is None and is_correct_output(task, source, output, expected)
        passed += int(ok)
        log.append({"input": source, "expected": expected, "output": normalize(output) if output is not None else "", "ok": ok, "error": error})
        if error:
            break
    score = task["points"] if passed == len(cases) else 0
    note = efficiency_note(code, task["id"], attempt["language"])
    sim = similarity(code, task["reference"])
    with db() as con:
        con.execute("INSERT INTO solutions(attempt_id,task_id,code,passed,total,score,efficiency,similarity,updated_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(attempt_id,task_id) DO UPDATE SET code=excluded.code,passed=excluded.passed,total=excluded.total,score=excluded.score,efficiency=excluded.efficiency,similarity=excluded.similarity,updated_at=excluded.updated_at",
                    (attempt["id"], task["id"], code, passed, len(cases), score, note, sim, now().isoformat()))
    return jsonify(passed=passed, total=len(cases), score=score, log=log, efficiency=note, similarity=sim)


@app.post("/api/execute")
def api_execute():
    """Execute the student's current code on their own input without grading it."""
    attempt = current_attempt()
    if not attempt or attempt["submitted_at"] or remaining(attempt) <= 0:
        return jsonify(error="Экзамен недоступен."), 403
    payload = request.get_json(force=True)
    task = task_by_id(int(payload.get("task_id", 0)))
    code = payload.get("code", "")
    input_data = payload.get("input", "")
    if not task or not isinstance(code, str) or not isinstance(input_data, str):
        return jsonify(error="Неверные данные."), 400
    if len(input_data) > 4096:
        return jsonify(error="Входные данные слишком длинные (лимит 4096 символов)."), 400
    output, error = run_in_container(attempt["language"], code, input_data)
    if error:
        return jsonify(error=error), 422
    return jsonify(output=output)


@app.post("/api/save")
def api_save():
    attempt = current_attempt()
    payload = request.get_json(force=True)
    if not attempt or attempt["submitted_at"] or remaining(attempt) <= 0:
        return jsonify(error="Экзамен недоступен."), 403
    task = task_by_id(int(payload.get("task_id", 0)))
    code = payload.get("code", "")
    if not task or not isinstance(code, str): return jsonify(error="Неверные данные."), 400
    with db() as con:
        con.execute("INSERT INTO solutions(attempt_id,task_id,code,updated_at) VALUES(?,?,?,?) ON CONFLICT(attempt_id,task_id) DO UPDATE SET code=excluded.code,updated_at=excluded.updated_at", (attempt["id"], task["id"], code, now().isoformat()))
    return jsonify(ok=True)


@app.route("/finish", methods=["GET", "POST"])
def finish():
    attempt = current_attempt()
    if not attempt: return redirect(url_for("index"))
    with db() as con:
        if (request.method == "POST" or remaining(attempt) <= 0) and not attempt["submitted_at"]:
            total = con.execute("SELECT COALESCE(SUM(score), 0) FROM solutions WHERE attempt_id=?", (attempt["id"],)).fetchone()[0]
            con.execute("UPDATE attempts SET submitted_at=?, total_score=? WHERE id=?", (now().isoformat(), total, attempt["id"]))
            attempt = con.execute("SELECT * FROM attempts WHERE id=?", (attempt["id"],)).fetchone()
        records = con.execute("SELECT * FROM solutions WHERE attempt_id=? ORDER BY task_id", (attempt["id"],)).fetchall()
    return render_template("finish.html", attempt=attempt, records=records, tasks=TASKS)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("login") == os.getenv("ADMIN_LOGIN", "admin") and request.form.get("password") == os.getenv("ADMIN_PASSWORD", "admin"):
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        return render_template("admin_login.html", error="Неверный логин или пароль."), 403
    return render_template("admin_login.html")


@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"): return redirect(url_for("admin"))
    with db() as con:
        attempts = con.execute("SELECT * FROM attempts ORDER BY started_at DESC").fetchall()
    return render_template("admin_dashboard.html", attempts=attempts)


@app.route("/admin/attempt/<int:attempt_id>")
def admin_attempt(attempt_id):
    if not session.get("admin"): return redirect(url_for("admin"))
    with db() as con:
        attempt = con.execute("SELECT * FROM attempts WHERE id=?", (attempt_id,)).fetchone()
        records = con.execute("SELECT * FROM solutions WHERE attempt_id=? ORDER BY task_id", (attempt_id,)).fetchall()
    if not attempt: return "Не найдено", 404
    return render_template("admin_attempt.html", attempt=attempt, records=records, tasks=TASKS)


@app.get("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8000, debug=False)
