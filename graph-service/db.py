import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load graph-service/.env explicitly (not just cwd's .env) so this works
# regardless of which directory uvicorn is launched from.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

NEO4J_URI = os.environ.get("NEO4J_URI")
NEO4J_USERNAME = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")

_driver = None


def get_driver():
    """Singleton Neo4j driver — reused across requests instead of opening
    a new connection per call."""
    global _driver
    if _driver is None:
        if not NEO4J_URI or not NEO4J_PASSWORD:
            raise RuntimeError(
                "NEO4J_URI / NEO4J_PASSWORD are not set. Check your .env "
                "or Codespace secrets before starting the service."
            )
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    return _driver


def run_schema_init():
    """Runs once at startup. Ensures the :Person.id uniqueness constraint
    exists so every MERGE (p:Person {id: $id}) is safe to call repeatedly
    (from Runeet's seed script, signup flow, or manual testing) without
    creating duplicate nodes for the same UUID."""
    driver = get_driver()

    def _init(tx):
        tx.run(
            "CREATE CONSTRAINT person_id_unique IF NOT EXISTS "
            "FOR (p:Person) REQUIRE p.id IS UNIQUE"
        )

    with driver.session(database=NEO4J_DATABASE) as session:
        session.execute_write(_init)


def close_driver():
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
