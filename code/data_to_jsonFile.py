import json
import parsing_excel
from parsing_word import *
import pprint
import os
import sys


def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(__file__)


def make_jsonFile():
    base = get_base_path()
    docx_path = os.path.join(base, 'downloads', 'changes.docx')
    pdf_path = os.path.join(base, 'downloads', 'changes.pdf')
    xls_path = os.path.join(base, 'downloads', 'rasp.xls')

    # ---------- Загрузка изменений (DOCX или PDF) ----------
    doc_Word = None
    try:
        doc_Word = Word(name=docx_path)
        print("Loaded changes from DOCX")
    except Exception as e:
        print(f"Error reading DOCX: {e}")
        try:
            from parsing_pdf import PDF
            doc_Word = PDF(name=pdf_path)
            print("Loaded changes from PDF")
        except Exception as e2:
            print(f"Error reading PDF: {e2}")
            # Создаём заглушку, чтобы не падать
            class EmptyWord:
                sp_repl = []
                sp_skip = []
                def make_sp_skip(self): pass
                def make_sp_repl(self): pass
                def return_date(self): return ""
            doc_Word = EmptyWord()

    doc_Word.make_sp_skip()
    doc_Word.make_sp_repl()

    # ---------- Загрузка Excel ----------
    try:
        doc_Xls = parsing_excel.Excel(name=xls_path)
    except Exception as e:
        print(f"Error reading rasp.xls: {e}")
        # Возвращаем пустые данные, но с сохранением информации об изменениях
        return {
            "fromWord": {
                "replace": doc_Word.sp_repl,
                "skip": doc_Word.sp_skip,
                "day": doc_Word.return_date()
            },
            "fromExcel": {
                "sp_classes": [],
                "sp_rooms": [],
                "sp_subjects": [],
                "schedule": {}
            }
        }

    doc_Xls.make_sp_classes()
    doc_Xls.load_rooms()
    doc_Xls.load_subjects()

    excel_classes = doc_Xls.sp_classes

    # ---------- Сборка данных ----------
    data_return = {
        "fromWord": {
            "replace": doc_Word.sp_repl,
            "skip": doc_Word.sp_skip,
            "day": doc_Word.return_date()
        },
        "fromExcel": {
            "sp_classes": doc_Xls.sp_classes,
            "sp_rooms": doc_Xls.sp_rooms,
            "sp_subjects": doc_Xls.sp_sbj,
            "schedule": {}
        }
    }

    days_of_week = ["ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА", "СУББОТА"]
    for day in days_of_week:
        data_return["fromExcel"]["schedule"][day] = {}
        for class_name in excel_classes:
            data_return["fromExcel"]["schedule"][day][class_name] = doc_Xls.make_rasp_by_dayclass(day, class_name)

    # ---------- Преобразование множеств в списки (если вдруг появятся) ----------
    if 'fromExcel' in data_return:
        for key in ['sp_classes', 'sp_rooms', 'sp_subjects']:
            if key in data_return['fromExcel'] and isinstance(data_return['fromExcel'][key], set):
                data_return['fromExcel'][key] = list(data_return['fromExcel'][key])

    # Отладочный вывод (можно оставить или убрать)
    print('\n\n', data_return.keys(), '\n', data_return["fromWord"].keys(), '\n', data_return["fromExcel"].keys())
    print('\n', data_return["fromExcel"]["sp_classes"])
    print('\n', data_return["fromExcel"]["sp_subjects"])
    print('\n', data_return["fromExcel"]["sp_rooms"])

    return data_return
