# DEFI Futures Radar 

This is a (currently private) repository for documentation, datasets, application profiles and prototypes.
It is associated with a [Github project space](https://github.com/users/camtree/projects/4) which is used for planning and task management.

## Convert CSV data to RDF

The CSV files under `data/` use RDF-style column names such as `@id`,
`rdf:type`, `foaf:name`, and `dcterms:title`.

Install dependencies:

```bash
pip install -r requirements.txt
```

Generate Turtle and JSON-LD files:

```bash
python scripts/convert_csv_to_rdf.py
```

By default this writes files to `rdf/`, preserving the folder names from
`data/`, for example `rdf/agents/agents.ttl` and
`rdf/datacatalogs/datacatalogs.jsonld`.
