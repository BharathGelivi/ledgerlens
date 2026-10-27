"""Launch the local workspace with an explicitly selected, isolated dataset."""
import argparse
import os
from pathlib import Path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', choices=['demo', 'sandbox'], default='demo')
    parser.add_argument('--port', type=int, default=8011)
    options = parser.parse_args()
    os.environ['LEDGERLENS_DATA'] = str(Path(__file__).resolve().parent / 'data' / options.dataset)
    import uvicorn
    uvicorn.run('api:app', app_dir=str(Path(__file__).resolve().parent), host='127.0.0.1', port=options.port)
