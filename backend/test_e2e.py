"""End-to-end check against the running services (backend on :8000, model on :8001).

    python test_e2e.py            # prints every exchange and a pass/fail line per check

It talks to the server the way the phone app does. It is a script, not a unit test, because it needs
both services up and the answers depend on today's data.
"""
import json
import sys
import urllib.request
import uuid

URL = "http://127.0.0.1:8000"
failed = []


def call(path, body=None):
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def check(name, ok, info=""):
    print(f"   [{'ok' if ok else 'FAIL'}] {name}" + (f"  ({info})" if info and not ok else ""))
    if not ok:
        failed.append(name)


class Chat:
    def __init__(self):
        self.sid = uuid.uuid4().hex

    def send(self, **body):
        m = call("/converse", {"sessionId": self.sid, "lang": "en", **body})
        said = body.get("text") or f"(tap) {body.get('reply', body)}"
        print(f"\n> {said}")
        print(f"  {m['text']}")
        if m.get("detail"):
            print(f"    detail: {m['detail'][:260]}{'...' if len(m['detail']) > 260 else ''}")
        for c in m.get("cards") or []:
            if c["type"] == "rotation":
                print(f"    plan: {[(p['year'], p['crop']) for p in c['plan']]}  reasons: {c['reasons']}  avoid: {c.get('avoid')}")
            elif c["type"] == "chart":
                print(f"    chart: {c['series']['title']} | {c['series']['source']['name']}")
        if m.get("replies"):
            print(f"    taps: {[o['label'] for o in m['replies']['options']]}")
        print(f"    understood by: {m.get('understoodBy', '-')}, worded by: {m.get('wordedBy', '-')}")
        return m


def options(m):
    return [o["value"] for o in (m.get("replies") or {}).get("options", [])]


print("=== the screens' data")
me, fields, overview, insights = call("/me"), call("/fields"), call("/overview"), call("/insights")
print("  fields:", [(f["properties"]["name"], f["properties"]["crop"], f["properties"]["health"], f["properties"]["healthLabel"])
                    for f in fields["features"]])
print("  overview:", overview["headline"], overview["attention"], [(s["label"], s["value"]) for s in overview["stats"]])
print("  data cards:", [(c["id"], c["scope"], c["takeaway"]) for c in insights["cards"]])
check("every field has a satellite reading", all(f["properties"]["health"] != "unknown" for f in fields["features"]))
check("data screen has the field greenness chart", insights["cards"][0]["id"] == "green" and insights["cards"][0]["scope"] == "field")
zones = {f["properties"]["id"]: call(f"/fields/{f['properties']['id']}/zones") for f in fields["features"]}
print("  zones:", {k: len(v["points"]) for k, v in zones.items()})
check("zones only for flagged fields", all((len(zones[f["properties"]["id"]]["points"]) > 0) == (f["properties"]["health"] == "weak_spot")
                                           for f in fields["features"]))
history = call("/fields/vm")
check("field history", len(history["history"]) == 3)

print("\n=== rotation, typed question with field and priority")
c = Chat()
m = c.send(text="what should I plant on valea mare next year, we are short of water")
check("goes straight to a plan", any(x["type"] == "rotation" for x in m.get("cards") or []), m["text"])
check("names the field", m.get("fieldId") == "vm")
m = c.send(reply={"id": "next", "value": "why"})
check("why names its sources and the rain record", "Sources:" in (m.get("detail") or "") and "NASA POWER" in m["detail"])
m = c.send(reply={"id": "next", "value": "limits"})
check("limits card", any(x["type"] == "limits" for x in m.get("cards") or []))

print("\n=== rotation, step by step with taps")
c = Chat()
m = c.send(text="help me pick the next crop")
check("asks which field", m["replies"]["id"] == "field")
m = c.send(reply={"id": "field", "value": "pv"})
check("asks the priority", m["replies"]["id"] == "priority")
m = c.send(reply={"id": "priority", "value": "soil"})
plan = next(x for x in m["cards"] if x["type"] == "rotation")
check("soil priority picks a nitrogen crop", plan["plan"][0]["crop"] in ("Peas", "Soybean"), plan["plan"][0]["crop"])
m = c.send(reply={"id": "next", "value": "priority"})
m = c.send(reply={"id": "priority", "value": "income"})
check("income says there is no price data", "no price data" in (m.get("detail") or ""))

print("\n=== field health")
c = Chat()
m = c.send(text="how is valea mare doing")
check("health answer from the satellite, with chart", "Sentinel-2" in (m.get("detail") or "") and bool(m.get("cards")))
check("never names a cause", "not why" in m["detail"])
m = c.send(text="is my corn ok?")
check("finds the corn field", m.get("fieldId") == "dv", str(m.get("fieldId")))
c = Chat()
m = c.send(text="How is Lunca Jiului doing?", fieldId="lj", intent="health")  # the button on the map screen
check("map button works", m.get("fieldId") == "lj")

print("\n=== sourced answers")
c = Chat()
m = c.send(text="when should I sow winter wheat?")
check("sowing answer, sources under it", "October" in m["text"] and "Partal" in (m.get("detail") or ""), m["text"])
check("no source marks in the sentence", "[" not in m["text"], m["text"])
m = c.send(text="can I plant rapeseed after sunflower?")
check("gap answer, sources under it", "rapeseed" in m["text"] and "Sources:" in (m.get("detail") or ""), m["text"])
m = c.send(text="how hot is too hot for corn at flowering")
check("heat answer has both levels", "35" in m["text"] and "40" in m["text"], m["text"])
m = c.send(text="is heat dangerous for peas")
check("refuses when there is no sourced value", m["text"] == "I have no sourced value for that yet.", m["text"])
m = c.send(text="when do I sow?")
if m.get("replies", {}).get("id") == "crop":
    m = c.send(reply={"id": "crop", "value": "rapeseed"})
check("asks for the crop when it is missing, then answers", "September" in m["text"], m["text"])
m = c.send(text="what kind of soil do I have on Pădurea Veche?")
check("soil answer from SoilGrids", "clay" in m["text"] and "SoilGrids" in (m.get("detail") or ""), m["text"])
m = c.send(text="has it been dry lately?")
check("weather answer", "area" in m["text"])
m = c.send(text="where does this data come from")
check("limits", any(x["type"] == "limits" for x in m.get("cards") or []))
m = c.send(text="what is the price of diesel")
check("out of scope is refused politely", "outside" in m["text"], m["text"])

print("\n" + ("ALL CHECKS PASSED" if not failed else f"{len(failed)} FAILED: {failed}"))
sys.exit(1 if failed else 0)
