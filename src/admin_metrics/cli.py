import argparse
from pathlib import Path

from .pipeline import run


def main():
    parser = argparse.ArgumentParser(description='Santander Admin Metrics · observação a cada hora')
    parser.add_argument('command', choices=['collect', 'build'])
    parser.add_argument('--root', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path, default=Path('site'))
    parser.add_argument('--config', type=Path, default=Path('config'))
    args = parser.parse_args()
    payload = run(args.root, args.output, args.config, refresh=args.command == 'collect')
    print({'run_id': payload['meta']['run_id'], 'rows': len(payload['latest']), 'sources': len(payload['reporters'])})


if __name__ == '__main__':
    main()
