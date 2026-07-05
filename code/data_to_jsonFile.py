import json
import parsing_excel
from parsing_word import *
import pprint

def make_jsonFile():    
    doc_Word = Word(name="../downloads/changes.docx")
    doc_Word.make_sp_skip()
    doc_Word.make_sp_repl()

    # print("")
    # print("\n список пропущенных: \n", doc_Word.sp_skip)
    # print("\n список замененных: \n", doc_Word.sp_repl)

    doc_Xls = parsing_excel.Excel(name="../downloads/rasp.xls")
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

    # json_data = json.dumps(data_return)
    # with open("../downloads/dson_data.txt", "w") as f:
    #     f.write(json_data)

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