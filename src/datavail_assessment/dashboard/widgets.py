"""Lakeview widget builders, shared by every page of the dashboard.

Kept separate from the pages so a new page is a list of widgets rather
than a pile of JSON.
"""

from __future__ import annotations

GREEN = "#10B981"
AMBER = "#F59E0B"
RED = "#EF4444"
GREY = "#94A3B8"
BLUE = "#3B82F6"

# Adoption grades, worst to best.
ADOPTION_SECTION_COLORS = [
    {"value": "NOT ADOPTED", "color": RED},
    {"value": "EARLY", "color": AMBER},
    {"value": "DEVELOPING", "color": BLUE},
    {"value": "STRONG", "color": GREEN},
]
# Keyed on the phrases the chart displays, not the raw ACTIVE/MINIMAL/NONE
# stored in the table. A reader should not have to learn a vocabulary to
# read a pie chart.
ADOPTION_LABEL_COLORS = [
    {"value": "Not used", "color": RED},
    {"value": "Barely used", "color": AMBER},
    {"value": "In real use", "color": GREEN},
]


def dataset(name: str, display: str, sql: str) -> dict:
    return {"name": name, "displayName": display,
            "queryLines": [l + "\n" for l in sql.strip().splitlines()]}


def _query(dataset_name: str, fields: list[str]) -> list[dict]:
    return [{"name": "main_query",
             "query": {"datasetName": dataset_name,
                       "fields": [{"name": f, "expression": f"`{f}`"} for f in fields],
                       "disaggregated": True}}]


def text(name: str, lines: list[str], x, y, w, h) -> dict:
    return {"widget": {"name": name,
                       "multilineTextboxSpec": {"lines": [l + "\n" for l in lines]}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


def counter(name, ds, field, title, desc, x, y, w=3, h=4) -> dict:
    """`desc` may be empty - a tile whose title already says everything
    reads better without a subtitle repeating it."""
    frame = {"showTitle": True, "title": title}
    if desc:
        frame["showDescription"] = True
        frame["description"] = desc
    else:
        frame["showDescription"] = False
    return {"widget": {"name": name, "queries": _query(ds, [field]),
                       "spec": {"version": 2, "widgetType": "counter",
                                "encodings": {"value": {"fieldName": field,
                                                        "displayName": title}},
                                "frame": frame}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


def bar(name, ds, xf, yf, title, desc, x, y, w, h,
        colorf=None, mappings=None, stack=False) -> dict:
    enc = {"x": {"fieldName": xf, "scale": {"type": "quantitative"}},
           "y": {"fieldName": yf, "scale": {"type": "categorical"}}}
    fields = [xf, yf]
    if colorf:
        enc["color"] = {"fieldName": colorf,
                        "scale": {"type": "categorical", "mappings": mappings or []}}
        fields.append(colorf)
    return {"widget": {"name": name, "queries": _query(ds, fields),
                       "spec": {"version": 3, "widgetType": "bar", "encodings": enc,
                                "mark": {"layout": "stack" if stack else "group"},
                                "frame": {"showTitle": True, "title": title,
                                          "showDescription": True, "description": desc}}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


def table(name, ds, cols, title, desc, x, y, w, h) -> dict:
    return {"widget": {"name": name, "queries": _query(ds, [c[0] for c in cols]),
                       "spec": {"version": 2, "widgetType": "table",
                                "encodings": {"columns": [{"fieldName": c[0],
                                                           "displayName": c[1]} for c in cols]},
                                "frame": {"showTitle": True, "title": title,
                                          "showDescription": True, "description": desc}}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


def pie(name, ds, colorf, anglef, mappings, title, desc, x, y, w, h) -> dict:
    return {"widget": {"name": name, "queries": _query(ds, [colorf, anglef]),
                       "spec": {"version": 3, "widgetType": "pie",
                                "encodings": {
                                    "angle": {"fieldName": anglef,
                                              "scale": {"type": "quantitative"}},
                                    "color": {"fieldName": colorf,
                                              "scale": {"type": "categorical",
                                                        "mappings": mappings}}},
                                "frame": {"showTitle": True, "title": title,
                                          "showDescription": True, "description": desc}}},
            "position": {"x": x, "y": y, "width": w, "height": h}}
