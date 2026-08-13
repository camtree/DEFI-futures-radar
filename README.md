# DEFI Futures Radar 

This is a (currently private) repository for documentation, datasets, application profiles and prototypes.
It is associated with a [Github project space](https://github.com/users/camtree/projects/4) which is used for planning and task management.

## Data Explorer

The Flask app is a small local data catalogue explorer. It reads generated
JSON-LD files from `rdf/` and displays available data catalogues with linked
publisher information.

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
flask --app app run
```

Open:

- `http://127.0.0.1:5000/data-catalogs`
- `http://127.0.0.1:5000/admin`

The admin page includes a `Refresh RDF` action which regenerates Turtle and
JSON-LD outputs.

## Refresh RDF Outputs

The CSV files under `data/` use RDF-style column names such as `@id`,
`rdf:type`, `foaf:name`, and `dcterms:title`.

Generate Turtle and JSON-LD files:

```bash
python utilities/rdf_refresh.py
```

By default this writes files to `rdf/`, preserving the folder names from
`data/`, for example `rdf/agents/agents.ttl` and
`rdf/datacatalogs/datacatalogs.jsonld`.
