#!/usr/bin/env python
"""Runner de desenvolvimento para a aplicação MVC (com Swagger).

Uso:
    python run_dev.py

Opções via env:
    PORT=8000 python run_dev.py
    LOG_LEVEL=DEBUG python run_dev.py

Carrega a app via factory `create_app()` em `app_mvc.py` garantindo
que o Swagger e blueprints modernos sejam registrados.
"""
import os
import logging
from app_mvc import create_app
from werkzeug.serving import WSGIRequestHandler

app = create_app()


class QuietBadRequestHandler(WSGIRequestHandler):
    """Suprime logs de handshakes TLS enviados por engano em porta HTTP.

    Quando um cliente faz `https://` para uma porta que serve HTTP puro,
    o primeiro byte 0x16 (ContentType Handshake TLS) causa 'Bad request version'.
    Isso polui stdout durante dev. Se SUPPRESS_TLS_NOISE=0, comportamento padrão.
    """
    SUPPRESS = os.getenv('SUPPRESS_TLS_NOISE', '1') not in ('0', 'false', 'False')

    def send_error(self, code, message=None):  # type: ignore[override]
        if self.SUPPRESS and code == 400 and message and 'Bad request version' in message:
            logging.getLogger('tls-noise').debug('Suprimido log TLS malformado: %s', message)
            try:
                # Resposta mínima silenciosa
                self.connection.close()
            except Exception:  # pragma: no cover - defensivo
                pass
            return
        return super().send_error(code, message)

    def handle_one_request(self):  # type: ignore[override]
        """Intercepta handshake TLS (ClientHello) antes que gere log de BAD REQUEST.

        Detecta primeiros bytes: 0x16 0x03 (TLS Handshake + versão) e encerra a conexão
        sem ruído. Mantém comportamento padrão em outros casos.
        """
        if not self.SUPPRESS:
            return super().handle_one_request()
        try:
            import socket
            self.connection.setblocking(False)
            try:
                peek = self.connection.recv(5, socket.MSG_PEEK)
            finally:
                self.connection.setblocking(True)
            if peek and len(peek) >= 3 and peek[0] == 0x16 and peek[1] == 0x03:
                logging.getLogger('tls-noise').debug('Descartado ClientHello TLS em porta HTTP')
                try:
                    self.connection.close()
                except Exception:  # pragma: no cover
                    pass
                return
        except Exception:  # pragma: no cover
            # Em qualquer falha, cair para fluxo normal
            pass
        return super().handle_one_request()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "true").lower() == "true"
    # Bind em 0.0.0.0 para facilitar acesso em containers / WSL
    request_handler = QuietBadRequestHandler if os.getenv('SUPPRESS_TLS_NOISE', '1') not in ('0', 'false', 'False') else WSGIRequestHandler
    app.logger.info('Iniciando dev server | porta=%s debug=%s suppress_tls_noise=%s', port, debug, request_handler is QuietBadRequestHandler)
    app.run(host="0.0.0.0", port=port, debug=debug, request_handler=request_handler)
