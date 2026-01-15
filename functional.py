import json
import time
import random
import statistics
from typing import List, Dict, Any

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, XSD

CT = Namespace("http://example.org/cheese-trace#")


def percentile(xs: List[float], p: float) -> float:
    if not xs:
        return float("nan")
    xs2 = sorted(xs)
    k = int(round((p / 100.0) * (len(xs2) - 1)))
    return xs2[k]


def _safe_json(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, str):
        try:
            return json.loads(obj)
        except Exception:
            return {}
    return {}


def translate_lot_to_rdf(lot_data: dict) -> Graph:
    """
    Translate a row from public.lots(lot_id, product_type, attrs) into RDF.
    Uses attrs JSONB for links:
      - attrs.sourceFarmId -> ct:sourcedFrom
      - attrs.sourceMilkId -> ct:derivedFromMilk
      - attrs.riskAssessment.zoonosisIndicator -> ct:hasZoonosisRisk/ct:level
      - attrs.skipQualityTest=true -> omit QualityTestEvent (for compliance test)
    """
    g = Graph()
    g.bind("ct", CT)

    lot_id = lot_data["lot_id"]
    lot_uri = URIRef("urn:epc:id:sgtin:" + str(lot_id))

    ptype = lot_data.get("product_type")
    if ptype == "milk":
        g.add((lot_uri, RDF.type, CT.MilkBatch))
    elif ptype == "cheese":
        g.add((lot_uri, RDF.type, CT.CheeseBatch))

    attrs = _safe_json(lot_data.get("attrs"))

    # sourcedFrom (for milk)
    farm_id = attrs.get("sourceFarmId")
    if farm_id:
        farm_uri = URIRef("urn:farm:" + str(farm_id))
        g.add((farm_uri, RDF.type, CT.Farm))
        g.add((lot_uri, CT.sourcedFrom, farm_uri))

    # derivedFromMilk (for cheese)
    source_milk_id = attrs.get("sourceMilkId")
    if source_milk_id:
        milk_uri = URIRef("urn:epc:id:sgtin:" + str(source_milk_id))
        g.add((lot_uri, CT.derivedFromMilk, milk_uri))

    # riskAssessment
    ra = attrs.get("riskAssessment")
    if isinstance(ra, dict):
        risk_node = BNode()
        g.add((lot_uri, CT.hasZoonosisRisk, risk_node))
        g.add((risk_node, RDF.type, CT.ZoonosisRisk))
        level = ra.get("zoonosisIndicator", "low")
        g.add((risk_node, CT.level, Literal(level)))

    # Synthetic QualityTestEvent for milk unless skipped
    if ptype == "milk" and not attrs.get("skipQualityTest", False):
        ev_uri = URIRef("urn:event:qualitytest:" + str(lot_id))
        g.add((ev_uri, RDF.type, CT.QualityTestEvent))
        g.add((ev_uri, CT.hasRelatedBatch, lot_uri))
        g.add((ev_uri, CT.eventTime, Literal(time.time(), datatype=XSD.decimal)))

    return g


def materialize_risk_propagation(global_graph: Graph) -> int:
    """
    Materialize rule:
      MilkBatch risk level High/Critical => derived CheeseBatch requiresQuarantine true
    """
    added = 0
    q_milk = """
    PREFIX ct: <http://example.org/cheese-trace#>
    SELECT DISTINCT ?milk WHERE {
      ?milk a ct:MilkBatch ;
            ct:hasZoonosisRisk ?risk .
      ?risk ct:level ?lvl .
      FILTER(?lvl IN ("High", "Critical"))
    }
    """
    high_milks = {row.milk for row in global_graph.query(q_milk)}

    for milk_uri in high_milks:
        q_cheese = f"""
        PREFIX ct: <http://example.org/cheese-trace#>
        SELECT DISTINCT ?cheese WHERE {{
          ?cheese a ct:CheeseBatch ;
                  ct:derivedFromMilk <{milk_uri}> .
        }}
        """
        for row in global_graph.query(q_cheese):
            cheese_uri = row.cheese
            triple = (cheese_uri, CT.requiresQuarantine, Literal(True, datatype=XSD.boolean))
            if triple not in global_graph:
                global_graph.add(triple)
                added += 1

    return added


def run_functional_checks(global_graph: Graph) -> None:
    # 1) Risk propagation must hold for at least one chain
    q1 = """
    PREFIX ct: <http://example.org/cheese-trace#>
    ASK {
      ?milk a ct:MilkBatch ;
            ct:hasZoonosisRisk ?risk .
      ?risk ct:level ?lvl .
      FILTER(?lvl IN ("High", "Critical")) .
      ?cheese a ct:CheeseBatch ;
              ct:derivedFromMilk ?milk ;
              ct:requiresQuarantine true .
    }
    """
    ok1 = bool(list(global_graph.query(q1))[0])
    print(f"[CHECK] Risk propagation quarantine: {'PASS' if ok1 else 'FAIL'}")

    # 2) Traceability: show cheese -> milk -> farm for high-risk cases
    q2 = """
    PREFIX ct: <http://example.org/cheese-trace#>
    SELECT ?cheese ?milk ?farm ?lvl WHERE {
      ?milk a ct:MilkBatch ;
            ct:sourcedFrom ?farm ;
            ct:hasZoonosisRisk ?risk .
      ?risk ct:level ?lvl .
      FILTER(?lvl IN ("High", "Critical")) .
      ?cheese a ct:CheeseBatch ;
              ct:derivedFromMilk ?milk .
    }
    """
    rows = list(global_graph.query(q2))
    print(f"[CHECK] Traceability query results: {len(rows)} row(s)")
    for r in rows[:5]:
        print(f"  cheese={r.cheese} milk={r.milk} farm={r.farm} level={r.lvl}")

    # 3) Compliance: find milk batches missing QualityTestEvent (we force exactly 1)
    q3 = """
    PREFIX ct: <http://example.org/cheese-trace#>
    SELECT ?milk WHERE {
      ?milk a ct:MilkBatch .
      FILTER NOT EXISTS {
        ?ev a ct:QualityTestEvent ;
            ct:hasRelatedBatch ?milk .
      }
    }
    """
    missing = list(global_graph.query(q3))
    print(f"[CHECK] Milk batches missing QualityTestEvent: {len(missing)} (expected 1)")
    print(f"[CHECK] Compliance missing-quality-test detection: {'PASS' if len(missing)==1 else 'FAIL'}")
    if len(missing) != 1:
        for m in missing[:5]:
            print(f"  missing={m.milk}")


def main(
    dsn: str = "dbname=traceability user=postgres password=xarisis host=127.0.0.1 port=5433",
    n_updates: int = 500,
    high_risk_rate: float = 0.05,
) -> None:
    # Listener connection
    lconn = psycopg2.connect(dsn)
    lconn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    lcur = lconn.cursor()
    lcur.execute("LISTEN rdf_sync_channel;")

    # Writer connection
    wconn = psycopg2.connect(dsn)
    wconn.autocommit = True
    wcur = wconn.cursor()

    latencies: List[float] = []
    global_graph = Graph()
    global_graph.bind("ct", CT)

    # Deterministic functional cases
    forced_high_milk_id = "LOT0000000"
    forced_cheese_id = "LOT0000001"          # derived from forced_high_milk_id
    forced_missing_qt_milk_id = "LOT0000002" # milk missing quality test
    forced_farm_id = "FARM001"

    time.sleep(0.2)

    for i in range(n_updates):
        lot_id = f"LOT{i:07d}"
        product_type = "milk" if (i % 2 == 0) else "cheese"

        # Build attrs JSON according to your schema
        attrs: Dict[str, Any] = {}

        # For milk: link to a farm
        if product_type == "milk":
            attrs["sourceFarmId"] = forced_farm_id

        # For cheese: link to previous milk (alternating pattern)
        if product_type == "cheese":
            attrs["sourceMilkId"] = f"LOT{i-1:07d}"

        # Force high-risk milk
        if lot_id == forced_high_milk_id:
            attrs["riskAssessment"] = {"zoonosisIndicator": "High"}
        elif random.random() < high_risk_rate and product_type == "milk":
            attrs["riskAssessment"] = {"zoonosisIndicator": random.choice(["High", "Critical"])}
        else:
            attrs["riskAssessment"] = {"zoonosisIndicator": "low"}

        # Force exactly one missing quality test
        if lot_id == forced_missing_qt_milk_id:
            attrs["skipQualityTest"] = True

        # Force cheese LOT0000001 derived from LOT0000000
        if lot_id == forced_cheese_id:
            product_type = "cheese"
            attrs["sourceMilkId"] = forced_high_milk_id

        t0 = time.perf_counter()

        # Insert/Upsert (only the columns you have!)
        wcur.execute(
            """
            INSERT INTO public.lots(lot_id, product_type, attrs)
            VALUES (%s, %s, %s::jsonb)
            ON CONFLICT (lot_id) DO UPDATE SET
              product_type = EXCLUDED.product_type,
              attrs = EXCLUDED.attrs
            """,
            (lot_id, product_type, json.dumps(attrs)),
        )

        # Wait for NOTIFY from trigger, then translate and merge into global graph
        got = False
        while not got:
            lconn.poll()
            while lconn.notifies:
                notify = lconn.notifies.pop(0)
                payload = json.loads(notify.payload)
                if payload.get("table") == "lots":
                    row = payload.get("data", {})
                    frag = translate_lot_to_rdf(row)
                    for triple in frag:
                        global_graph.add(triple)
                    got = True
                    break

        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    # Materialize rule and run SPARQL checks
    added = materialize_risk_propagation(global_graph)
    print(f"[INFO] Materialized quarantine triples added: {added}")
    run_functional_checks(global_graph)

    # Performance summary
    median = statistics.median(latencies)
    p95 = percentile(latencies, 95)

    print(f"\n[PERF] n_updates={n_updates}")
    print(f"[PERF] translation_latency_ms_median={median:.2f}")
    print(f"[PERF] translation_latency_ms_p95={p95:.2f}")

    wconn.close()
    lconn.close()


if __name__ == "__main__":
    main()
