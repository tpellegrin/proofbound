"""Print category totals in sorted order."""
import argparse
import sys
from summary import totals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file')
    args = parser.parse_args()
    with open(args.file, newline='', encoding='utf-8') as stream:
        result = totals(stream)
    for category, amount in sorted(result.items()):
        print(f'{category}: {amount}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
