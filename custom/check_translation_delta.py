"""Stop an unattended merge when new literal launcher labels lack Chinese."""
import ast
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def labels(source):
    return {node.args[0].value for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == '_' and node.args and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)}


def main():
    sys.path.insert(0, str(ROOT / 'launcher'))
    import bbport_lang
    import bbport_zh
    table = dict(bbport_lang.table('zh'))
    table.update(bbport_zh.TRANSLATIONS)
    missing = set()
    for path in (ROOT / 'launcher').glob('*.py'):
        relative = path.relative_to(ROOT).as_posix()
        old = subprocess.run(['git', 'show', sys.argv[1] + ':' + relative], cwd=ROOT,
                             capture_output=True)
        previous = labels(old.stdout.decode('utf-8')) if old.returncode == 0 else set()
        for key in labels(path.read_text(encoding='utf-8')) - previous:
            if key and key not in table and not any('\u3400' <= c <= '\u9fff' for c in key):
                missing.add(key)
    if missing:
        raise SystemExit('New launcher text needs Chinese translation: ' + repr(sorted(missing)))
    print('New literal launcher labels have Chinese translations.')


if __name__ == '__main__':
    main()
