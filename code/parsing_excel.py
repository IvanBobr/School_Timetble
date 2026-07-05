import pandas as pd
import math
import pprint


class Excel:
    def __init__(self, name):
        self.df = pd.read_excel(name)
        self.sp_classes = []
        self.classes = dict()
        self.sp_sbj = []
        self.sp_rooms = []
        self.time_lesson = [
            ("8:30", "9:15"),
            ("9:30", "10:15"),
            ("10:35", "11:20"),
            ("11:40", "12:25"),
            ("12:45", "13:30"),
            ("13:50", "14:35"),
            ("14:55", "15:40"),
            ("15:50", "16:35")]
        self.cols = self.df.columns.tolist()

    def make_sp_classes(self):
        for col in self.df.columns:
            if "-" in col:  # название класса
                self.sp_classes.append(col)
            # print(col)
        print(self.sp_classes)

    def return_sp_classes(self):
        return self.sp_classes

    def make_rasp_class(self, name_class):
        sp_class = []
        last_day = 'Понедельник'
        for index, row in self.df.iterrows():
            # print(row, type(row))
            # print(row["Unnamed: 0"])
            if isinstance(row["Unnamed: 0"], type(
                    "dcs")) and row["Unnamed: 0"] in "ПонедельникВторникСредаЧетвергПятницаСуббота":
                last_day = row["Unnamed: 0"]
            # print(row['№'])
            if isinstance(row[name_class], type("cffwdec")):
                sp_class.append((int(row['№']),
                                 self.time_lesson[int(row['№']) - 1],
                                 row[name_class],
                                 name_class,
                                 1,
                                 '-',
                                 "ПО РАСПИСАНИЮ",
                                 last_day))
        self.classes[name_class] = sp_class
        print(*sp_class, sep='\n')

    def load_subjects(self):
        for index, row in self.df.iterrows():
            for i in self.sp_classes:
                if isinstance(row[i], type("fwefw")
                              ) and row[i] not in self.sp_sbj:
                    self.sp_sbj.append(row[i])
        print(self.sp_sbj)

    def load_rooms(self):
        for index, row in self.df.iterrows():
            for i in self.sp_classes:
                kab_1, kab_2 = self.cols[self.cols.index(
                    i) + 1], self.cols[self.cols.index(i) + 2]
                if isinstance(
                        row[kab_1],
                        type("cddw")) and row[kab_1] not in self.sp_rooms:
                    self.sp_rooms.append(row[kab_1])
                if isinstance(
                        row[kab_2],
                        type("wefw")) and row[kab_2] not in self.sp_rooms:
                    self.sp_rooms.append(row[kab_2])
        print(self.sp_rooms)

    def make_rasp_by_dayclass(self, day, grade):
        bool_inday = False
        rasp_today = []
        for index, row in self.df.iterrows():
            day_name = row["Unnamed: 0"]
            if isinstance(day_name, str) and day_name.upper() == day.upper():
                bool_inday = True
            elif isinstance(day_name, str) and day_name.upper() != day.upper() and bool_inday:
                bool_inday = False
                break
            if bool_inday:
                num_class_kab = self.cols.index(grade)
                if str(row[self.cols[num_class_kab]]) != "nan":
                    rasp_today.append([
                        str(row[self.cols[1]]),  # № урока
                        self.time_lesson[int(row[self.cols[1]]) - 1][0], # время начала урока
                        row[self.cols[num_class_kab]],  # урок
                        grade,  # класс
                        (str(row[self.cols[num_class_kab + 1]]) + '/' + str(row[self.cols[num_class_kab + 2]])).replace("А", "") if str(
                            row[self.cols[num_class_kab + 2]]) != "nan" else str(row[self.cols[num_class_kab + 1]]).replace("А", ""), # кабинет
                        "-",  # учитель
                        "ПО РАСПИСАНИЮ"  # статус
                    ])
        return rasp_today

    def make_rasp_by_dayclass(self, day, grade):
        bool_inday = False
        rasp_today = []
        for index, row in self.df.iterrows():
            cell_value = row["Unnamed: 0"]
            if isinstance(cell_value, str) and cell_value.upper() == day.upper():
                bool_inday = True
            elif isinstance(cell_value, str) and cell_value.upper() != day.upper() and bool_inday:
                bool_inday = False
                break

            if bool_inday:
                num_class_kab = self.cols.index(grade)
                if str(row[self.cols[num_class_kab]]) != "nan":
                    rasp_today.append([
                        str(row[self.cols[1]]),
                        self.time_lesson[int(row[self.cols[1]]) - 1][0],
                        row[self.cols[num_class_kab]],
                        grade,
                        (str(row[self.cols[num_class_kab + 1]]) + '/' + str(row[self.cols[num_class_kab + 2]])).replace("А", "") 
                            if str(row[self.cols[num_class_kab + 2]]) != "nan" 
                            else str(row[self.cols[num_class_kab + 1]]).replace("А", ""),
                        "-",
                        "ПО РАСПИСАНИЮ"
                    ])
        return rasp_today