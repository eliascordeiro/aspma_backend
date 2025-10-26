import pymysql
import pymongo
from contextlib import contextmanager
from typing import Optional
from .settings import settings

class DatabaseManager:
    """Gerenciador centralizado de conexões de banco de dados."""
    _instance = None

    def __init__(self):
        self._mysql_pool = None
        self._mongo_client = None
        self._mongo_db = None

    @classmethod
    def init_app(cls, app=None):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def get_mysql_connection(cls):
        if cls._instance is None:
            cls.init_app()
        return cls._instance._mysql_connection_context()

    @contextmanager
    def _mysql_connection_context(self):
        connection = None
        try:
            connection = pymysql.connect(**settings.mysql_connection_params)
            yield connection
        except Exception as e:
            if connection:
                connection.rollback()
            raise e
        finally:
            if connection:
                connection.close()

    @classmethod
    def get_mongo_client(cls):
        if cls._instance is None:
            cls.init_app()
        inst = cls._instance
        if inst._mongo_db is None:
            try:
                if not settings.MONGO_URI:
                    return None
                inst._mongo_client = pymongo.MongoClient(settings.MONGO_URI)
                inst._mongo_db = inst._mongo_client[settings.MONGO_DATABASE]
            except Exception:
                inst._mongo_db = None
        return inst

    @property
    def mongo_db(self):
        if self._mongo_db is None:
            if not settings.MONGO_URI:
                raise ValueError("MONGO_URI não configurado")
            self._mongo_client = pymongo.MongoClient(settings.MONGO_URI)
            self._mongo_db = self._mongo_client[settings.MONGO_DATABASE]
        return self._mongo_db

    def test_connections(self) -> dict:
        results = {'mysql': False, 'mongo': False}
        try:
            with self._mysql_connection_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    results['mysql'] = True
        except Exception as e:
            results['mysql_error'] = str(e)
        try:
            if settings.MONGO_URI:
                self.mongo_db.command('ping')
                results['mongo'] = True
            else:
                results['mongo_error'] = 'MONGO_URI não configurado'
        except Exception as e:
            results['mongo_error'] = str(e)
        return results

# Instância global
_db = DatabaseManager.init_app()