from .settings import Settings, settings  # nova API

# Fallback: se existir módulo raiz config.py com classe Config (legacy), tenta importar dinamicamente
try:  # pragma: no cover (apenas em ambientes onde o arquivo legacy permanece)
	from importlib import import_module as _im
	_legacy = _im('config')  # pode resolver para este pacote; conferimos atributo
	if hasattr(_legacy, 'Config') and 'Config' not in globals():
		Config = getattr(_legacy, 'Config')  # type: ignore
except Exception:  # pragma: no cover
	pass

__all__ = ['Settings', 'settings', 'Config']
