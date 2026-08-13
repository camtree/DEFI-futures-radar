import json
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
RDF_DIR = BASE_DIR / "rdf"
CATALOGS_JSONLD = RDF_DIR / "datacatalogs" / "datacatalogs.jsonld"
AGENTS_JSONLD = RDF_DIR / "agents" / "agents.jsonld"
DATASETS_JSONLD = RDF_DIR / "datasets" / "datasets.jsonld"
BASE_IRI = "https://data.futures-radar.example/"
DCTERMS = "http://purl.org/dc/terms/"
DCAT = "http://www.w3.org/ns/dcat#"
FOAF = "http://xmlns.com/foaf/0.1/"
SKOS = "http://www.w3.org/2004/02/skos/core#"
REGIONAL_SPATIAL_VALUES = {
    "Africa",
    "Americas",
    "Asia",
    "Europe",
    "European Union",
    "Global South",
    "Latin America",
    "Middle East",
    "North America",
    "Oceania",
    "South America",
}

app = Flask(__name__)

# -----------------------------------------------------------------------
# Utility functions
# -----------------------------------------------------------------------



def read_jsonld_nodes(path):
    """
    Reads a JSON-LD file and returns its nodes as a list.
    :param path: Path to the JSON-LD file.
    :return: List of nodes.
    """
    with path.open("r", encoding="utf-8") as jsonld_file:
        data = json.load(jsonld_file)
    return data if isinstance(data, list) else [data]

def first_value(node, predicate):
    """
    Returns the first value of a node or list of values - to deal with arrays on length 1 in JSON-LD files
    :param node: The JSON-LD node.
    :param predicate: The predicate to look for.
    :return: The first value or an empty string if not found.
    """
    values = node.get(predicate, [])
    if not values:
        return ""
    value = values[0]
    return value.get("@value") or value.get("@id") or ""


def values_for(node, predicate):
    """
    Returns all values for a JSON-LD predicate as strings.
    :param node: The JSON-LD node.
    :param predicate: The predicate to look for.
    :return: List of values or IDs.
    """
    return [
        value.get("@value") or value.get("@id")
        for value in node.get(predicate, [])
        if value.get("@value") or value.get("@id")
    ]


def compact_iri(iri):
    """
    Compacts an IRI by removing the base IRI and replacing it with a namespace prefix.
    For display purposes only, only needed as a fallback if there is no label or name for the agent or catalog.
    :param iri: The IRI to compact.
    :return: The compacted IRI.
    """
    if iri.startswith(BASE_IRI):
        namespace, name = iri.removeprefix(BASE_IRI).split("/", 1)
        return f"{namespace}:{name}"
    return iri

# ------------------------------------------------------------------------
# Metadata loaders
# ------------------------------------------------------------------------
def load_agents():
    """
    Loads agents from the JSON-LD file and returns a dictionary of agents.
    :return: Dictionary of agents.
    """
    agents = {}
    for agent in read_jsonld_nodes(AGENTS_JSONLD):
        agent_id = agent.get("@id", "")
        agents[agent_id] = {
            "id": compact_iri(agent_id),
            "name": first_value(agent, f"{FOAF}name") or compact_iri(agent_id),
            "label": first_value(agent, f"{SKOS}altLabel"),
            "homepage": first_value(agent, f"{FOAF}homepage"),
        }
    return agents


def load_datasets():
    """
    Loads datasets from the JSON-LD file and returns a dictionary of datasets.
    :return: Dictionary of datasets.
    """
    if not DATASETS_JSONLD.exists():
        return {}

    datasets = {}
    for dataset in read_jsonld_nodes(DATASETS_JSONLD):
        dataset_id = dataset.get("@id", "")
        datasets[dataset_id] = {
            "iri": dataset_id,
            "id": compact_iri(dataset_id),
            "title": first_value(dataset, f"{DCTERMS}title") or compact_iri(dataset_id),
            "description": first_value(dataset, f"{DCTERMS}description"),
            "identifier": first_value(dataset, f"{DCTERMS}identifier"),
            "landing_page": first_value(dataset, f"{DCAT}landingPage"),
            "spatial": first_value(dataset, f"{DCTERMS}spatial"),
            "temporal": first_value(dataset, f"{DCTERMS}temporal"),
            "language": first_value(dataset, f"{DCTERMS}language"),
            "part_of": values_for(dataset, f"{DCTERMS}isPartOf"),
        }
    return datasets


def load_data_catalogs():
    """
    Loads catalogs from the JSON-LD file and returns a dictionary of catalogs.
    :return:
    """
    agents = load_agents()
    datasets = load_datasets()
    catalogs = []

    for catalog in read_jsonld_nodes(CATALOGS_JSONLD):
        catalog_id = catalog.get("@id", "")
        agent_id = first_value(catalog, f"{DCTERMS}publisher")
        agent = agents.get(agent_id, {})
        catalog_dataset_ids = set(values_for(catalog, f"{DCAT}dataset"))
        linked_datasets = [
            dataset
            for dataset in datasets.values()
            if dataset["iri"] in catalog_dataset_ids or catalog_id in dataset["part_of"]
        ]
        catalogs.append(
            {
                "iri": catalog_id,
                "id": compact_iri(catalog_id),
                "title": first_value(catalog, f"{DCTERMS}title") or compact_iri(catalog_id),
                "description": first_value(catalog, f"{DCTERMS}description"),
                "homepage": first_value(catalog, f"{FOAF}homepage"),
                "landing_page": first_value(catalog, f"{DCAT}landingPage"),
                "language": first_value(catalog, f"{DCTERMS}language"),
                "spatial": first_value(catalog, f"{DCTERMS}spatial"),
                "agent_id": compact_iri(agent_id),
                "agent_name": agent.get("name", compact_iri(agent_id)),
                "agent_label": agent.get("label", ""),
                "agent_homepage": agent.get("homepage", ""),
                "datasets": sorted(
                    linked_datasets,
                    key=lambda dataset: dataset["title"].casefold(),
                ),
            }
        )

    return catalogs


def selected_catalog_from(catalogs, selected_id):
    if selected_id:
        for catalog in catalogs:
            if catalog["id"] == selected_id:
                return catalog
    return catalogs[0] if catalogs else None


def catalog_group_name(catalog):
    spatial = catalog.get("spatial", "")
    if spatial == "Global":
        return "Global"
    if spatial in REGIONAL_SPATIAL_VALUES:
        return "Regional"
    if spatial:
        return "National"
    return "Other"


def grouped_catalogs_from(catalogs):
    grouped = {name: [] for name in ("Global", "Regional", "National", "Other")}
    for catalog in catalogs:
        grouped[catalog_group_name(catalog)].append(catalog)

    return [
        {
            "name": name,
            "catalogs": sorted(items, key=lambda catalog: catalog["title"].casefold()),
        }
        for name, items in grouped.items()
        if items
    ]


def flatten_grouped_catalogs(grouped_catalogs):
    return [
        catalog
        for group in grouped_catalogs
        for catalog in group["catalogs"]
    ]

# -----------------------------------------------------------------
# Wrapper for the rdf refresh in utilities
# -----------------------------------------------------------------
def run_rdf_refresh():
    from utilities.rdf_refresh import refresh_rdf_outputs
    return refresh_rdf_outputs(base_dir=BASE_DIR)


#---------------------------------------------------------------
# ROUTES
#---------------------------------------------------------------
@app.route('/')
def index():
    return redirect(url_for("list_data_catalogs"))

@app.route("/data-catalogs")
def list_data_catalogs():
    catalogs = load_data_catalogs()
    grouped_catalogs = grouped_catalogs_from(catalogs)
    selected_catalog = selected_catalog_from(
        flatten_grouped_catalogs(grouped_catalogs),
        request.args.get("catalog"),
    )
    return render_template(
        "index.html",
        catalog_groups=grouped_catalogs,
        selected_catalog=selected_catalog,
    )

@app.route("/admin")
def admin():
    return render_template("admin.html", converted=False, error=None, results=[])

@app.route("/admin/refresh-rdf")
def refresh_rdf():
    try:
        results = run_rdf_refresh()
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
