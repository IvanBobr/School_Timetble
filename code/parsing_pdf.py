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
                            for num_i in range (1, num):
                                self.sp_skip.append((parts[0], num_i))
                            
                            break
                print("Found lesson to skip (PDF)!")

    def make_sp_repl(self):
        for line in self.full_text:
            # В одной строке может быть несколько уроков: "2 урок 5-8 ... 2 урок 5-12 ..."
            # Разбиваем по шаблону "N урок"
            chunks = re.split(r'(?=\d+\s+урок)', line)
            for chunk in chunks:
                chunk = chunk.strip()
                if not chunk:
                    continue

                # Отмена урока: "N урок X-Y урока не будет"
                cancel_match = re.match(r'(\d+)\s+урок\s+(\d+-\d+)\s+урока\s+не\s+будет', chunk)
                if cancel_match:
                    lesson_num = int(cancel_match.group(1))
                    class_name = cancel_match.group(2)
                    if 1 <= lesson_num <= len(self.lesson_times):
                        self.sp_repl.append([
                            lesson_num,
                            self.lesson_times[lesson_num - 1][0],
                            '-', class_name, '-', '-', "ОТМЕНЕНО"
                        ])
                        print(f"Cancelled (PDF): {class_name}, урок {lesson_num}")
                    continue

                # Замена: "N урок X-Y <остаток>"
                m = re.match(r'(\d+)\s+урок\s+(\d+-\d+)\s+(.*)', chunk)
                if not m:
                    continue

                lesson_num = int(m.group(1))
                class_name = m.group(2)
                rest = m.group(3).strip()

                # Убираем "каб." в конце (если есть)
                rest = re.sub(r'\s*каб\.?\s*$', '', rest).strip()

                # ---------- Кабинет ----------
                # Может быть "313", "404/321", "320/121"
                room_match = re.search(r'(\d+(?:/\d+)?)\s*$', rest)
                if room_match:
                    room = room_match.group(1)
                    rest = rest[:room_match.start()].strip()
                else:
                    room = ''

                # ---------- Учитель(я) ----------
                # Формат: "Слово И.О." или "Слово И.О./Слово И.О."
                # Ищем в конце строки, перед кабинетом
                teacher_pattern = (
                    r'([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ]\.)+)'      # первый учитель
                    r'(?:/'                                  # опциональный слэш
                    r'([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ]\.)+))?'     # второй учитель
                    r'\s*$'
                )
                teacher_match = re.search(teacher_pattern, rest)

                if teacher_match:
                    if teacher_match.group(2):
                        teacher = f"{teacher_match.group(1)}/{teacher_match.group(2)}"
                    else:
                        teacher = teacher_match.group(1)
                    subject = rest[:teacher_match.start()].strip()
                else:
                    teacher = ''
                    subject = rest

                # ---------- Формируем запись ----------
                if 1 <= lesson_num <= len(self.lesson_times):
                    self.sp_repl.append([
                        lesson_num,
                        self.lesson_times[lesson_num - 1][0],
                        subject,
                        class_name,
                        room,
                        teacher,
                        "ИЗМЕНЕНО"
                    ])
                    print(f"Replaced (PDF): {class_name}, урок {lesson_num}, "
                        f"предмет='{subject}', каб.='{room}', учитель='{teacher}'")