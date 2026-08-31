import pdfplumber
import re

class PDF:
    def __init__(self, name="changes.pdf"):
        self.sp_repl = []
        self.sp_skip = []
        self.full_text = []
        self.lesson_times = [
            ("8:30", "9:15"),
            ("9:30", "10:15"),
            ("10:35", "11:20"),
            ("11:40", "12:25"),
            ("12:45", "13:30"),
            ("13:50", "14:35"),
            ("14:55", "15:40"),
            ("15:50", "16:35")
        ]
        self._extract_text_from_pdf(name)

    def _extract_text_from_pdf(self, name):
        """Извлекает текст из PDF и разбивает на строки, удаляя пустые."""
        try:
            with pdfplumber.open(name) as pdf:
                full_text = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        lines = text.split('\n')
                        for line in lines:
                            # Убираем лишние пробелы, но сохраняем табуляции (если они были заменены пробелами)
                            # В PDF часто табуляции превращаются в пробелы, поэтому делаем эвристику:
                            # Если строка содержит несколько слов и похожа на запись изменения, оставляем.
                            # Но проще: просто добавляем все непустые строки.
                            if line.strip():
                                self.full_text.append(line.strip())
                print("PDF text extracted, lines:", len(self.full_text))
        except Exception as e:
            print(f"Error reading PDF: {e}")
            self.full_text = []

    def return_date(self):
        """Возвращает дату из 4-й строки (индекс 3), если есть, иначе пустую строку."""
        if len(self.full_text) >= 4:
            return self.full_text[3].replace('\t', ' ')
        return ""

    def return_num_day(self):
        if len(self.full_text) >= 3:
            return self.full_text[2].split()[1]
        return ""

    def make_sp_skip(self):
        dict_replace = {
            'ПЕРВОМУ': 1,
            'ВТОРОМУ': 2,
            'ТРЕТЬЕМУ': 3,
            'ЧЕТВЕРТОМУ': 4,
            'ПЯТОМУ': 5,
            'ШЕСТОМУ': 6,
            'СЕДЬМОМУ': 7,
            'ВОСЬМОМУ': 8
        }
        for line in self.full_text:
            if 'приходит в школу к' in line or 'приходит\tв\tшколу\tк' in line:
                # В PDF табуляции могут быть заменены пробелами, но мы уже их не трогаем
                # Попробуем разбить по пробелам или табуляции
                parts = re.split(r'\t+|\s+', line)
                if len(parts) >= 6:
                    # parts: [класс, 'приходит', 'в', 'школу', 'к', 'ВТОРОМУ', ...]
                    # номер урока – последнее слово перед 'уроку' или сразу после 'к'
                    # Ищем слово в dict_replace
                    for word, num in dict_replace.items():
                        if word in line:
                            self.sp_skip.append((parts[0], num))
                            break
                print("Found lesson to skip (PDF)!")

    def make_sp_repl(self):
        for line in self.full_text:
            if 'урок' in line and 'урока не будет' not in line:
                # Пытаемся распарсить строку как замену
                parts = re.split(r'\t+|\s+', line)
                # Очищаем от лишних слов
                # Пример: "1 урок 6-5 математика Золотарева О.С. 312 каб."
                # Ищем номер урока (первая цифра)
                if not parts:
                    continue
                # Попробуем найти номер урока
                lesson_num = None
                for i, p in enumerate(parts):
                    if p.isdigit() and i+1 < len(parts) and (parts[i+1] == 'урок' or parts[i+1] == 'урока'):
                        lesson_num = int(p)
                        break
                if lesson_num is None:
                    continue
                # Ищем класс: строка с дефисом, например "6-5"
                class_name = None
                for p in parts:
                    if '-' in p and len(p) >= 3:
                        class_name = p
                        break
                if class_name is None:
                    continue
                # Ищем кабинет: строка с "каб." или просто номер
                room = ''
                for p in parts:
                    if 'каб' in p or (p.isdigit() and len(p) >= 2):
                        room = p.replace('каб.', '').strip()
                        break
                # Предмет и учитель – всё между классом и кабинетом
                # Упростим: берём все части после класса до кабинета
                start_idx = parts.index(class_name) if class_name in parts else -1
                end_idx = parts.index(room) if room and room in parts else -1
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    subject_parts = parts[start_idx+1:end_idx]
                    subject = ' '.join(subject_parts).strip()
                else:
                    subject = ''
                # Учитель – после кабинета (иногда перед "каб.")
                teacher = ''
                if room and room in parts:
                    idx = parts.index(room)
                    if idx + 1 < len(parts):
                        teacher = ' '.join(parts[idx+1:])
                # Формируем запись
                self.sp_repl.append([
                    lesson_num,
                    self.lesson_times[lesson_num - 1][0],
                    subject,
                    class_name,
                    room,
                    teacher,
                    "ИЗМЕНЕНО"
                ])
                print("found lesson to replace (PDF):", [lesson_num, subject, class_name, room, teacher])
            elif 'урока не будет' in line:
                # Отмена урока
                parts = re.split(r'\t+|\s+', line)
                lesson_num = None
                for p in parts:
                    if p.isdigit():
                        lesson_num = int(p)
                        break
                if lesson_num is not None:
                    # Ищем класс
                    class_name = None
                    for p in parts:
                        if '-' in p and len(p) >= 3:
                            class_name = p
                            break
                    if class_name:
                        self.sp_repl.append([
                            lesson_num,
                            self.lesson_times[lesson_num - 1][0],
                            '-',
                            class_name,
                            '-',
                            '-',
                            "ОТМЕНЕНО"
                        ])
                        print("founded lesson that wouldn't be today (PDF)")