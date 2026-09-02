import re
src = open(r'app\services\intelligence_engine.py', encoding='utf-8').read()
for i, line in enumerate(src.splitlines(), 1):
    if re.search(r'"(confirmed|inferred|possible|probable|insufficient)"', line):
        print(i, line.strip())