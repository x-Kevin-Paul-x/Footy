"""Explicit byte-only conversion for locally trusted historical recordings."""
import argparse

from logic.grf_state_archive import GRFStateArchiveReader, GRFStateArchiveWriter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('destination')
    parser.add_argument('--match-id', required=True)
    parser.add_argument('--trusted-local', action='store_true', required=True)
    args = parser.parse_args()
    with GRFStateArchiveReader(args.source, trusted_legacy=args.trusted_local) as reader:
        with GRFStateArchiveWriter(args.destination, args.match_id) as writer:
            for state in reader.iter_states():
                writer.append(state)


if __name__ == '__main__':
    main()
