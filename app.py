import os, sys, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "JobSpy"))
from flask import Flask, Response, jsonify, render_template, request
from jobspy import scrape_jobs

app = Flask(__name__)

AUTH_USER = os.environ.get("APP_USER")
AUTH_PASS = os.environ.get("APP_PASSWORD")


@app.before_request
def require_login():
    if not (AUTH_USER and AUTH_PASS):
        return
    a = request.authorization
    if not a or a.username != AUTH_USER or a.password != AUTH_PASS:
        return Response("Login required", 401, {"WWW-Authenticate": 'Basic realm="Job Search"'})

SITES = ["linkedin", "indeed", "naukri", "glassdoor", "zip_recruiter", "google", "bayt"]


@app.get("/")
def index():
    return render_template("index.html", sites=SITES)


@app.post("/api/search")
def search():
    d = request.get_json(force=True)
    sites = [s for s in d.get("sites", []) if s in SITES] or SITES[:3]
    term = d.get("search_term", "").strip()
    proxies = [p.strip() for p in (d.get("proxies") or "").splitlines() if p.strip()] or None
    try:
        df = scrape_jobs(
            site_name=sites,
            search_term=term,
            google_search_term=d.get("google_search_term") or f"{term} jobs near {d.get('location','')}".strip(),
            location=d.get("location") or None,
            results_wanted=int(d.get("results_wanted") or 15),
            hours_old=int(d["hours_old"]) if d.get("hours_old") else None,
            is_remote=bool(d.get("is_remote")),
            job_type=d.get("job_type") or None,
            country_indeed=d.get("country") or "india",
            description_format="markdown",
            proxies=proxies,
        )
    except Exception as e:
        return jsonify(error=str(e)), 500
    cols = ["site", "title", "company", "location", "job_type", "date_posted",
            "min_amount", "max_amount", "currency", "interval", "job_url", "is_remote"]
    df = df[[c for c in cols if c in df.columns]].astype(object).where(df.notna(), None)
    rows = [{k: (None if isinstance(v, float) and math.isnan(v) else str(v) if v is not None and not isinstance(v, (int, float, bool)) else v)
             for k, v in r.items()} for r in df.to_dict("records")]
    return jsonify(jobs=rows)


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5050)), debug=False)
