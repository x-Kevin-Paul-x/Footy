"""Package a static, read-only demo from already curated match assets."""
import argparse
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='backend/verification/tmp/demo')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / 'docs/demo/index.html', output / 'index.html')
    for name in ('demo.css', 'demo.js'):
        shutil.copy2(root / 'docs/demo' / name, output / name)
    # Share the frontend's actual theme tokens and tactile components. Tailwind
    # build directives are omitted from this standalone, buildless demo.
    frontend_css = (root / 'frontend/src/index.css').read_text(encoding='utf-8')
    theme_css = '\n'.join(line for line in frontend_css.splitlines() if not line.lstrip().startswith('@tailwind'))
    (output / 'frontend-theme.css').write_text(theme_css + '\n', encoding='utf-8')
    recordings = root / 'assets/matches/full-match-recordings'
    shutil.copy2(recordings / 'burnley-2-4-bournemouth.mp4', output / 'match.mp4')
    shutil.copy2(root / 'docs/evidence/calibration.json', output / 'calibration.json')
    shutil.copy2(root / 'docs/evidence/manager_evaluation.json', output / 'manager_evaluation.json')
    print(f'Read-only demo packaged at {output}')


if __name__ == '__main__':
    main()
