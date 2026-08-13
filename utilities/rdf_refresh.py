#!/usr/bin/env python3
"""Refresh Turtle and JSON-LD RDF outputs from source data."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import DCAT, DCTERMS, FOAF, RDF as RDF_NS, SKOS, XSD


BASE = Namespace("https://data.futures-radar.example/")
DEFAULT_DATA_DIR = Path("data")
DEFAULT_OUTPUT_DIR = Path("rdf")

# CSV column names and cell values use compact RDF names, for example
# dcterms:title or agent:oecd. These prefixes define how those CURIEs expand.
NAMESPACES = {
    "agent": Namespace(f"{BASE}agent/"),
    "catalog": Namespace(f"{BASE}catalog/"),
    "dataset": Namespace(f"{BASE}dataset/"),
    "dcat": DCAT,
    "dcterms": DCTERMS,
    "foaf": FOAF,
    "rdf": RDF_NS,
    "skos": SKOS,
    "xsd": XSD,
}

RESOURCE_PREDICATES = {
    "dcat:dataset",
    "dcat:distribution",
    "dcat:inSeries",
    "dcat:landingPage",
    "dcat:service",
    "dcat:themeTaxonomy",
    "dcterms:accessRights",
    "dcterms:accrualPeriodicity",
    "dcterms:conformsTo",
    "dcterms:isPartOf",
    "dcterms:isReferencedBy",
    "dcterms:license",
    "dcterms:publisher",
    "dcterms:subject",
    "foaf:homepage",
}


def bind_namespaces(graph: Graph) -> None:
    """Bind prefixes so Turtle output stays readable."""
    for prefix, namespace in NAMESPACES.items():
        graph.bind(prefix, namespace)


def expand_curie(value: str) -> URIRef:
    """Expand a compact RDF name such as agent:oecd to a full URIRef."""
    prefix, name = value.split(":", 1)
    try:
        return URIRef(NAMESPACES[prefix][name])
    except KeyError as exc:
        raise ValueError(f"Unknown CURIE prefix {prefix!r} in {value!r}") from exc


def to_uri(value: str) -> URIRef:
    """Treat absolute URLs and known CURIEs as RDF resources."""
    if value.startswith(("http://", "https://")):
        return URIRef(value)
    if ":" in value:
        return expand_curie(value)
    return URIRef(BASE[value])


def to_predicate(column_name: str) -> URIRef:
    """Map an RDF-shaped CSV column header to a predicate URI."""
    if column_name == "rdf:type":
        return RDF.type
    return expand_curie(column_name)


def object_for(predicate_name: str, value: str):
    """Return a resource for link-like predicates, otherwise a string literal."""
    if predicate_name == "rdf:type" or predicate_name in RESOURCE_PREDICATES:
        return to_uri(value)
    return Literal(value)


def iter_csv_files(data_dir: Path) -> Iterable[Path]:
    """Find source CSV files recursively so data subfolders become RDF subfolders."""
    return sorted(data_dir.glob("**/*.csv"))


def convert_csv(csv_path: Path, data_dir: Path, output_dir: Path) -> tuple[Path, Path, int]:
    """Convert one RDF-shaped CSV file into matching Turtle and JSON-LD files."""
    graph = Graph()
    bind_namespaces(graph)

    row_count = 0
    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames or "@id" not in reader.fieldnames:
            raise ValueError(f"{csv_path} must include an @id column")

        # Ignore empty trailing columns from spreadsheet exports.
        columns = [name for name in reader.fieldnames if name]
        for row in reader:
            subject_id = (row.get("@id") or "").strip()
            if not subject_id:
                # Blank rows are common in edited spreadsheets and should not
                # create anonymous or invalid RDF resources.
                continue

            row_count += 1
            subject = to_uri(subject_id)
            for column_name in columns:
                if column_name == "@id":
                    continue

                value = (row.get(column_name) or "").strip()
                if not value:
                    continue

                graph.add((subject, to_predicate(column_name), object_for(column_name, value)))

    # Preserve the source folder structure under rdf/, for example
    # data/agents/agents.csv -> rdf/agents/agents.jsonld.
    relative_parent = csv_path.parent.relative_to(data_dir)
    target_dir = output_dir / relative_parent
    target_dir.mkdir(parents=True, exist_ok=True)

    ttl_path = target_dir / f"{csv_path.stem}.ttl"
    jsonld_path = target_dir / f"{csv_path.stem}.jsonld"
    graph.serialize(destination=ttl_path, format="turtle")
    graph.serialize(destination=jsonld_path, format="json-ld", indent=2)

    return ttl_path, jsonld_path, row_count


def refresh_rdf_outputs(
    data_dir: Path = DEFAULT_DATA_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    base_dir: Path | None = None,
) -> list[dict[str, Path | int]]:
    """Refresh all generated RDF files and return paths for the admin page."""
    csv_files = list(iter_csv_files(data_dir))
    if not csv_files:
        raise ValueError(f"No CSV files found under {data_dir}")

    results = []
    for csv_path in csv_files:
        ttl_path, jsonld_path, row_count = convert_csv(csv_path, data_dir, output_dir)
        results.append(
            {
                "source_path": display_path(csv_path, base_dir),
                "ttl_path": display_path(ttl_path, base_dir),
                "jsonld_path": display_path(jsonld_path, base_dir),
                "row_count": row_count,
            }
        )

    return results


def display_path(path: Path, base_dir: Path | None) -> Path:
    """Show project-relative paths when called from the Flask app."""
    if base_dir is None:
        return path
    try:
        return path.relative_to(base_dir)
    except ValueError:
        return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    try:
        results = refresh_rdf_outputs(args.data_dir, args.output_dir)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    for result in results:
        print(
            f"{result['source_path']}: converted {result['row_count']} rows -> "
            f"{result['ttl_path']}, {result['jsonld_path']}"
        )


if __name__ == "__main__":
    main()
