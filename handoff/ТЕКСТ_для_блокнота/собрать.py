# СОБРАТЬ ПАПКИ ИЗ ТЕКСТА. Положите все части ЧАСТЬ_*.txt в одну папку рядом с этим
# скриптом и запустите:   python3 собрать.py
# Нужен только Python 3. Создаёт папку METACOD_ПЕРЕДАЧА_02102026 со всеми файлами.
import glob, os, re
MARK, END = '#####METACOD-ФАЙЛ#####', '#####METACOD-КОНЕЦ#####'
текст = ''
for p in sorted(glob.glob('ЧАСТЬ_*.txt'), key=lambda s: int(re.search(r'ЧАСТЬ_(\d+)', s).group(1))):
    текст += open(p, encoding='utf-8-sig').read().replace('\r\n', '\n')
n = 0
for блок in текст.split(MARK + ' ')[1:]:
    шапка, _, тело = блок.partition('\n')
    путь, _, пометка = шапка.partition(' | ')
    путь = путь.strip()
    тело = тело.split('\n' + END + '\n', 1)[0]
    if not путь or '..' in путь: continue
    if 'не входит' in пометка: continue   # картинки и двоичные файлы в тексте не переносятся
    цель = os.path.join('METACOD_ПЕРЕДАЧА_02102026', путь)
    os.makedirs(os.path.dirname(цель), exist_ok=True)
    open(цель, 'w', encoding='utf-8', newline='\n').write(тело)
    n += 1
print('собрано файлов:', n)
