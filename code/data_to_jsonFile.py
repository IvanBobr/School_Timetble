import json
import parsing_excel
from parsing_word import *
import pprint

def make_jsonFile():    
    # try:
    #     doc_Word = Word(name="../downloads/changes.docx")
    # except Exception as e:
    #     print(f"Error reading changes.docx: {e}")
    #     return {"fromWord": {"replace": [], "skip": [], "day": ""}, "fromExcel": {...}}
    
    # Пытаемся загрузить изменения из .docx или .pdf
    doc_Word = None
    try:
        doc_Word = Word(name="../downloads/changes.docx")
    except Exception as e:
        print(f"Error reading changes.docx: {e}")
        try:
            from parsing_pdf import PDF
            doc_Word = PDF(name="../downloads/changes.pdf")
            print("Using PDF parser for changes")
        except Exception as e2:
            print(f"Error reading changes.pdf: {e2}")
            # Если ни один файл не найден, возвращаем пустые данные
            return {"fromWord": {"replace": [], "skip": [], "day": ""}, "fromExcel": {...}}

    doc_Word.make_sp_skip()
    doc_Word.make_sp_repl()

    # print("")
    # print("\n список пропущенных: \n", doc_Word.sp_skip)
    # print("\n список замененных: \n", doc_Word.sp_repl)

    try:
        doc_Xls = parsing_excel.Excel(name="../downloads/rasp.xls")
    except Exception as e:
        print(f"Error reading rasp.xls: {e}")
        return {"fromWord": {"replace": [], "skip": [], "day": ""}, "fromExcel": {...}}
    doc_Xls.make_sp_classes()
    doc_Xls.load_rooms()
    doc_Xls.load_subjects()

    excel_classes = doc_Xls.sp_classes
    data_return = {"fromWord": {"replace": doc_Word.sp_repl, "skip": doc_Word.sp_skip, "day": doc_Word.return_date()}, "fromExcel": {"sp_classes": doc_Xls.sp_classes, "sp_rooms": doc_Xls.sp_rooms, "sp_subjects": doc_Xls.sp_sbj}}
    days_of_week = ["ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА", "СУББОТА"]
    data_return["fromExcel"]["schedule"] = {}
    for day in days_of_week:
        data_return["fromExcel"]["schedule"][day] = {}  
        for class_name in excel_classes:
                    data_return["fromExcel"]["schedule"][day][class_name] = doc_Xls.make_rasp_by_dayclass(day, class_name)


    print('\n\n', data_return.keys(), '\n', data_return["fromWord"].keys(), '\n', data_return["fromExcel"].keys())
    print('\n', data_return["fromExcel"]["sp_classes"])
    print('\n', data_return["fromExcel"]["sp_subjects"])
    print('\n', data_return["fromExcel"]["sp_rooms"])
    # print("\n список классов: \n", excel_classes)
    # print("\n список комнат: \n", doc_Xls.sp_rooms)
    # print("\n список уроков: \n", doc_Xls.sp_sbj)

    # print("\n\n\n")
    # pprint.pprint(data_return)

    # print("\n\n\n", data_return["fromExcel"]["schedule"]["ВТОРНИК"]["6-6"][0])
    
    return data_return