import numpy as np
from neo4j import GraphDatabase, basic_auth
from config import Config
from typing import List


class Neo4jConnector:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._driver = GraphDatabase.driver(
            cfg.neo4j_uri,
            auth=basic_auth(cfg.neo4j_user, cfg.neo4j_password),
        )


    def close(self):
        self._driver.close()


    def run(self, query: str, params: dict = None) -> List[dict]:
        params = params or {}
        with self._driver.session() as session:
            result = session.run(query, params)
            return [record.data() for record in result]