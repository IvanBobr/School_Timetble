from docx import Document
import pprint

class Word:
    def __init__(self, name="changes.docx"):
        self.sp_repl = []
        self.sp_skip = []
        self.doc = Document(name)
        self.full_text = []
        for paragraph in self.doc.paragraphs:
            print(paragraph.text)
            self.full_text.append(paragraph.text)
        if not self.full_text:
            raise 
        self.lesson_times = [
            ("8:30", "9:15"),
            ("9:30", "10:15"),
            ("10:35", "11:20"),
            ("11:40", "12:25"),
            ("12:45", "13:30"),
            ("13:50", "14:35"),
            ("14:55", "15:40"),
            ("15:50", "16:35")]
        print(self.full_text)

    def get_addres(self):
        print(self.full_text[0].replace("\t", " "))

    def return_num_day(self):
        return self.full_text[2].split()[1]

    def return_date(self):
        return self.full_text[3].replace('\t', " ")

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
        for i in self.full_text:
            if 'приходит\tв\tшколу\tк' in i:
                print("Found lesson to skip!")
                sp_inf = i.split('\t')
                self.sp_skip.append((sp_inf[0], dict_replace[sp_inf[5]]))
        # print(self.sp_skip)

    def make_sp_repl(self):
        for i in self.full_text:
            # print(i)
            if 'урок\t' in i and "урока\tне\tбудет" not in i:
                print("found lesson to replace", end='\t')
                objedin = "объединение" in i
                sp_inf = [j for j in i.replace("\tкаб.", "").replace("объединение", "").split('\t') if j]
                print(sp_inf)
                
                if any([subject.lower() in i.lower() for subject in ["МХК", "ТВиС", "ИЗО", "ОВД", "СП", "ОБЗР"]]):
                    lesson = sp_inf[1]
                    lesson_index_end = 1
                else:
                    lesson_index_start = 0
                    lesson_index_end = 0
                    
                    for index in range(0, len(sp_inf)):
                        if "-" in sp_inf[index]:
                            lesson_index_start = index + 1
                        if lesson_index_start and sp_inf[index][0].isalpha() and sp_inf[index][0].isupper():
                            lesson_index_end = index - 1
                    lesson = ""
                    for index in range(lesson_index_start, lesson_index_end):
                        lesson += sp_inf[index] + " "
                    lesson = lesson.strip()
                
                teacher = " ".join(sp_inf[lesson_index_start+1+lesson.count(" "):lesson_index_start+3+lesson.count(" ")])
                
                self.sp_repl.append([
                    int(sp_inf[0]), # № урока
                    self.lesson_times[int(sp_inf[0]) - 1][0], # время начала урока
                    lesson, # урок
                    sp_inf[2], # класс
                    sp_inf[-1].split()[0] if len(sp_inf) > 4 else "", # кабинет
                    teacher, # учитель 
                    "ИЗМЕНЕНО" # статус
                ])
            elif 'урок\t' in i:
                print("founded lesson that wouldn't be today")
                sp_inf = [j for j in i.split('\t') if j]
                self.sp_repl.append([
                    int(sp_inf[0]),
                    self.lesson_times[int(sp_inf[0]) - 1][0],
                    '-',
                    sp_inf[2],
                    '-',
                    '-',
                    "ОТМЕНЕНО"
                ])
        print(*self.sp_repl, sep="\n")
        
class StructureError(Exception):
    """Базовый класс для всех исключений структур данных"""

    pass        

class EmptyStructureError(StructureError):
    """Ошибка при поиске несуществующего значения"""

    def __init__(self, value=None, message="No values in structure"):
        super().__init__(message)