#!/usr/bin/env python3
"""Dry-run script to verify Portkey integration without making LLM calls.

It prints the environment variables, generates Portkey headers using
`get_portkey_headers()` and instantiates the OpenAI client wrapper.
"""
import os
import json
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # Manual .env loader fallback
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    if k not in os.environ:
                        os.environ[k] = v
    except FileNotFoundError:
        pass

# Ensure project root is on sys.path so `src` package can be imported when
# running this script from the `scripts/` directory.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.portkey_config import get_portkey_headers, get_portkey_openai_client

print('--- Environment Variables ---')
for k in ('PORTKEY_API_KEY', 'PORTKEY_GATEWAY_URL', 'CUSTOM_BEARER_TOKEN', 'LLM_MODEL_NAME', 'X-PORTKEY_PROVIDER', 'OPENAI_API_KEY'):
    print(f"{k}={os.getenv(k)!r}")

print('\n--- Generating Portkey Headers ---')
try:
    headers = get_portkey_headers({'test': 'dry-run', 'script': 'portkey_dryrun'})
    print(json.dumps(headers, indent=2))
except Exception as e:
    print('ERROR generating headers:', e)

print('\n--- Creating Portkey/OpenAI client ---')
try:
    client = get_portkey_openai_client()
    print('Client gateway:', getattr(client, '_gateway', None))
    print('Has native portkey client:', hasattr(client, 'portkey_client'))
    if hasattr(client, 'portkey_client'):
        print('Portkey client class:', client.portkey_client.__class__.__name__)
except Exception as e:
    print('ERROR creating client:', e)

print('\nDry-run finished.')
