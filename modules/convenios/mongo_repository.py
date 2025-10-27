import os
from config.database import DatabaseManager
from datetime import datetime, timedelta


_DEV_CODE_STORE = {
    # 'codigo_convenio': '123456'
}
_DEV_CODE_REVERSE = {
    # '123456': 'codigo_convenio'
}


class ConveniosMongoRepository:
    """Operações MongoDB para convênios (tentativas, códigos, cache login)."""

    def __init__(self):
        self._db = None
        # Fallback em memória apenas para desenvolvimento/teste
        self._use_dev_fallback = os.getenv('DEV_ESQUECEU_CODE_FALLBACK', 'false').lower() in ('1','true','yes')
        client = DatabaseManager.get_mongo_client()
        db_attr = getattr(client, '_mongo_db', None) if client is not None else None
        if db_attr is not None:
            self._db = db_attr

    def _coll(self, name: str):
        return self._db.get_collection(name) if self._db is not None else None

    # Login cache / status
    def get_login_doc(self, codigo: str):
        try:
            c = self._coll('login_convenios')
            return c.find_one({'codigo': codigo}) if c is not None else None
        except Exception:
            return None

    # Tentativas
    def get_tentativas(self, codigo: str) -> int:
        try:
            c = self._coll('tentativas_convenio')
            if c is None:
                return 0
            doc = c.find_one({'codigo': codigo})
            return doc.get('tentativas', 0) if doc else 0
        except Exception:
            return 0

    def incrementar_tentativas(self, codigo: str) -> int:
        try:
            c = self._coll('tentativas_convenio')
            if c is None:
                return 0
            c.find_one_and_update({'codigo': codigo}, {'$inc': {'tentativas': 1}}, upsert=True)
            doc = c.find_one({'codigo': codigo})
            return doc.get('tentativas', 1) if doc else 1
        except Exception:
            return 0

    def reset_tentativas(self, codigo: str):
        try:
            c = self._coll('tentativas_convenio')
            if c is not None:
                c.find_one_and_delete({'codigo': codigo})
        except Exception:
            return

    def bloquear_login(self, codigo: str):
        try:
            c = self._coll('login_convenios')
            if c is not None:
                c.find_one_and_update({'codigo': codigo}, {'$set': {'bloqueio': 'SIM'}}, upsert=True)
        except Exception:
            return

    # Código de alteração de senha
    def armazenar_codigo_email(self, codigo_convenio: str, codigo: str):
        # Se for uma chave sintética de e-mail (dev bypass), não tente Mongo
        if isinstance(codigo_convenio, str) and codigo_convenio.startswith('email:'):
            if self._use_dev_fallback:
                _DEV_CODE_STORE[codigo_convenio] = codigo
                _DEV_CODE_REVERSE[codigo] = codigo_convenio
            return
        try:
            c = self._coll('codigo_altera_senha_convenio')
            if c is not None:
                c.find_one_and_update({'codigo_convenio': codigo_convenio}, {'$set': {'codigo': codigo}}, upsert=True)
                return
        except Exception:
            # Se falhar e fallback habilitado, armazena em memória
            pass
        if self._use_dev_fallback:
            _DEV_CODE_STORE[codigo_convenio] = codigo
            _DEV_CODE_REVERSE[codigo] = codigo_convenio

    def validar_codigo_email(self, codigo_convenio: str, codigo: str) -> bool:
        try:
            c = self._coll('codigo_altera_senha_convenio')
            if c is None:
                # Fallback em memória
                if self._use_dev_fallback:
                    return _DEV_CODE_STORE.get(codigo_convenio) == codigo
                return False
            return c.find_one({'codigo_convenio': codigo_convenio, 'codigo': codigo}) is not None
        except Exception:
            if self._use_dev_fallback:
                return _DEV_CODE_STORE.get(codigo_convenio) == codigo
            return False

    def validar_codigo_global(self, codigo: str):
        try:
            c = self._coll('codigo_altera_senha_convenio')
            if c is None:
                # Fallback em memória
                if self._use_dev_fallback:
                    codigo_convenio = _DEV_CODE_REVERSE.get(codigo)
                    if codigo_convenio:
                        return {'codigo_convenio': codigo_convenio, 'codigo': codigo}
                return None
            return c.find_one({'codigo': codigo})
        except Exception:
            if self._use_dev_fallback:
                codigo_convenio = _DEV_CODE_REVERSE.get(codigo)
                if codigo_convenio:
                    return {'codigo_convenio': codigo_convenio, 'codigo': codigo}
            return None

    def remover_codigo(self, codigo_convenio: str):
        try:
            c = self._coll('codigo_altera_senha_convenio')
            if c is not None:
                c.delete_one({'codigo_convenio': codigo_convenio})
                return
        except Exception:
            pass
        if self._use_dev_fallback:
            code = _DEV_CODE_STORE.pop(codigo_convenio, None)
            if code:
                _DEV_CODE_REVERSE.pop(code, None)

    # Atualização de senha (Mongo)
    def atualizar_senha_mongo(self, codigo_convenio: str, senha_hash: bytes):
        try:
            login = self._coll('login_convenios')
            tent = self._coll('tentativas_convenio')
            if login is not None:
                login.find_one_and_update({'codigo': codigo_convenio}, {'$set': {'senha': senha_hash, 'bloqueio': 'NAO'}}, upsert=True)
            if tent is not None:
                tent.find_one_and_delete({'codigo': codigo_convenio})
        except Exception:
            return

    def buscar_por_email(self, email: str):
        try:
            c = self._coll('login_convenios')
            if c is None:
                return None
            return c.find_one({'email': email.lower()})
        except Exception:
            return None

    # ==== WhatsApp de-dup (pre/confirm) ====
    _DEDUP_CACHE = {}

    def _dedup_key(self, stage: str, matricula: str, id_compra: str) -> str:
        stage = (stage or '').strip().lower() or 'pre'
        return f"{stage}:{(matricula or '').strip()}:{(id_compra or '').strip()}"

    def has_whatsapp_event(self, stage: str, matricula: str, id_compra: str, ttl_seconds: int = 180):
        """Verifica se já registramos envio para (stage, matricula, id_compra) dentro do TTL.

        Usa Mongo quando disponível; caso contrário, fallback em memória com TTL simples.
        """
        key = self._dedup_key(stage, matricula, id_compra)
        # Primeiro tenta Mongo
        try:
            c = self._coll('whatsapp_events')
            if c is not None:
                doc = c.find_one({'_id': key})
                if not doc:
                    return False
                ts = doc.get('created_at')
                if isinstance(ts, datetime):
                    return (datetime.utcnow() - ts) <= timedelta(seconds=ttl_seconds)
                return True
        except Exception:
            pass
        # Fallback em memória
        now = datetime.utcnow()
        ts = self._DEDUP_CACHE.get(key)
        if ts and isinstance(ts, datetime) and (now - ts) <= timedelta(seconds=ttl_seconds):
            return True
        # Limpeza eventual
        try:
            for k, v in list(self._DEDUP_CACHE.items()):
                if not isinstance(v, datetime) or (now - v) > timedelta(seconds=ttl_seconds):
                    self._DEDUP_CACHE.pop(k, None)
        except Exception:
            pass
        return False

    def record_whatsapp_event(self, stage: str, matricula: str, id_compra: str):
        """Registra evento de envio (idempotente)."""
        key = self._dedup_key(stage, matricula, id_compra)
        now = datetime.utcnow()
        try:
            c = self._coll('whatsapp_events')
            if c is not None:
                c.find_one_and_update({'_id': key}, {'$set': {'created_at': now}}, upsert=True)
                return
        except Exception:
            pass
        self._DEDUP_CACHE[key] = now
