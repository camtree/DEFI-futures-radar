import csv
from pathlib import Path

from flask import Flask, redirect, render_template, url_for


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RDF_DIR = BASE_DIR / "rdf"
CATALOGS_CSV = BASE_DIR / "data" / "datacatalogs" / "datacatalogs.csv"
AGENTS_CSV = BASE_DIR / "data" / "agents" / "agents.csv"

app = Flask(__name__)


def read_csv_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return [
            {key: (value or "").strip() for key, value in row.items() if key}
            for row in reader
            if (row.get("@id") or "").strip()
        ]


def load_agents():
    return {agent["@id"]: agent for agent in read_csv_rows(AGENTS_CSV)}


def load_data_catalogs():
    agents = load_agents()
    catalogs = []

    for catalog in read_csv_rows(CATALOGS_CSV):
        agent_id = catalog.get("dcterms:publisher", "")
        agent = agents.get(agent_id, {})
        catalogs.append(
            {
                "id": catalog.get("@id", ""),
                "title": catalog.get("dcterms:title", catalog.get("@id", "")),
                "description": catalog.get("dcterms:description", ""),
                "homepage": catalog.get("foaf:homepage", ""),
                "landing_page": catalog.get("dcat:landingPage", ""),
                "language": catalog.get("dcterms:language", ""),
                "spatial": catalog.get("dcterms:spatial", ""),
                "agent_id": agent_id,
                "agent_name": agent.get("foaf:name", agent_id),
                "agent_label": agent.get("skos:altLabel", ""),
                "agent_homepage": agent.get("foaf:homepage", ""),
            }
        )

    return catalogs


def run_csv_conversion():
    from scripts.convert_csv_to_rdf import convert_csv, iter_csv_files

    results = []
    for csv_path in iter_csv_files(DATA_DIR):
        ttl_path, jsonld_path, row_count = convert_csv(csv_path, DATA_DIR, RDF_DIR)
        results.append(
            {
                "csv_path": csv_path.relative_to(BASE_DIR),
                "ttl_path": ttl_path.relative_to(BASE_DIR),
                "jsonld_path": jsonld_path.relative_to(BASE_DIR),
                "row_count": row_count,
            }
        )
    return results


@app.route('/')
def index():
    return redirect(url_for("list_data_catalogs"))


@app.route("/data-catalogs")
def list_data_catalogs():
    catalogs = load_data_catalogs()
    return render_template("index.html", catalogs=catalogs)


@app.route("/admin")
def admin():
    return render_template("admin.html", converted=False, error=None, results=[])


@app.route("/admin/convert-csv-to-rdf")
def convert_csv_to_rdf():
    try:
        results = run_csv_conversion()
    except ModuleNotFoundError as exc:
        if exc.name != "rdflib":
            raise
        return render_template(
            "admin.html",
            converted=False,
            error="rdflib is not installed in this Python environment. Run pip install -r requirements.txt, then try again.",
            results=[],
        )

    return render_template("admin.html", converted=True, error=None, results=results)


if __name__ == '__main__':
    app.run()
