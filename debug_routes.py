#!/usr/bin/env python3
"""Utilitário para inspecionar as rotas carregadas da aplicação Flask.

Uso básico:
  python debug_routes.py
  python debug_routes.py --filter docs
  python debug_routes.py --json | jq '.'

Saída inclui: regra, métodos, endpoint, blueprint e se tem docstring (para ajudar a saber se já foi documentado no Swagger via flasgger – docstring simples > 0 chars).
Retorna código de saída 2 se as rotas de Swagger /api/docs/ ou /api/docs/apispec.json estiverem ausentes.
"""
from __future__ import annotations
import argparse, json, sys
from importlib import import_module
from typing import List, Dict, Any

SWAGGER_UI_ROUTE = '/api/docs/'
SWAGGER_SPEC_ROUTE = '/api/docs/apispec.json'


def load_app():
    """Tenta obter a instância global `app` de app_mvc, caindo para create_app()."""
    try:
        mod = import_module('app_mvc')
    except Exception as exc:  # pragma: no cover
        print(f"[ERRO] Falha ao importar app_mvc: {exc}", file=sys.stderr)
        raise SystemExit(1)
    if hasattr(mod, 'app'):  # Preferir instância global (evita duplicar inicialização)
        return getattr(mod, 'app')
    if hasattr(mod, 'create_app'):
        return mod.create_app()
    print('[ERRO] app_mvc não expõe app nem create_app()', file=sys.stderr)
    raise SystemExit(1)


def collect_routes(app, substring: str | None = None) -> List[Dict[str, Any]]:
    routes = []
    for rule in app.url_map.iter_rules():
        methods = sorted(m for m in rule.methods if m not in ('HEAD', 'OPTIONS'))
        endpoint = rule.endpoint
        view_func = app.view_functions.get(endpoint)
        doc = (view_func.__doc__ or '').strip() if view_func else ''
        blueprint = endpoint.split('.')[0] if '.' in endpoint else ''
        info = {
            'rule': str(rule),
            'methods': methods,
            'endpoint': endpoint,
            'blueprint': blueprint or None,
            'has_docstring': bool(doc),
            'doc_preview': doc.split('\n', 1)[0][:90] if doc else ''
        }
        if substring and substring not in info['rule'] and substring not in endpoint:
            continue
        routes.append(info)
    routes.sort(key=lambda r: r['rule'])
    return routes


def analyze(routes: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = {}
    for r in routes:
        counts[r['rule']] = counts.get(r['rule'], 0) + 1
    duplicates = [rule for rule, c in counts.items() if c > 1]
    has_swagger_ui = any(r['rule'] == SWAGGER_UI_ROUTE for r in routes)
    has_swagger_spec = any(r['rule'] == SWAGGER_SPEC_ROUTE for r in routes)
    undocumented = [r for r in routes if not r['has_docstring'] and r['rule'].startswith('/api/')]
    return {
        'total': len(routes),
        'duplicates': duplicates,
        'swagger_ui_present': has_swagger_ui,
        'swagger_spec_present': has_swagger_spec,
        'undocumented_api_routes': len(undocumented)
    }


def main():
    parser = argparse.ArgumentParser(description='Inspeciona rotas da aplicação Flask.')
    parser.add_argument('--filter', dest='flt', help='Filtrar por substring em rule ou endpoint')
    parser.add_argument('--json', action='store_true', help='Saída completa em JSON')
    parser.add_argument('--summary', action='store_true', help='Mostra apenas resumo agregado')
    args = parser.parse_args()

    app = load_app()
    routes = collect_routes(app, args.flt)
    summary = analyze(routes)

    if args.json:
        print(json.dumps({'summary': summary, 'routes': routes}, ensure_ascii=False, indent=2))
    else:
        print('Resumo:')
        print(f"  Total rotas: {summary['total']}")
        print(f"  Swagger UI: {'OK' if summary['swagger_ui_present'] else 'FALTA'}")
        print(f"  Swagger Spec: {'OK' if summary['swagger_spec_present'] else 'FALTA'}")
        print(f"  Duplicadas: {summary['duplicates'] or 'Nenhuma'}")
        print(f"  API sem docstring (prefixo /api/): {summary['undocumented_api_routes']}")
        if not args.summary:
            print('\nRotas:')
            for r in routes:
                methods = ','.join(r['methods']) or '-'
                docflag = '✓' if r['has_docstring'] else '·'
                print(f"{r['rule']:<40} {methods:<15} {r['endpoint']:<40} {docflag}")
            print('\nLegenda: ✓ possui docstring, · sem docstring')

    # Exit codes para CI/debug
    if not summary['swagger_ui_present'] or not summary['swagger_spec_present']:
        # 2: recurso essencial ausente
        sys.exit(2)

if __name__ == '__main__':
    main()
