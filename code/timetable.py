import tkinter as tk
from tkinter import ttk, font
from datetime import datetime, date
import re
import download_fromServer
from json import loads


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("📋 Школьное расписание")
        self.root.configure(bg='black')

        self.bg_color = '#000033'
        self.text_color = '#00FFFF'
        self.highlight_color = '#FFFF00'
        self.warning_color = '#FF3300'
        self.cancelled_bg = '#DC143C'
        self.cancelled_fg = '#FFFFFF'

        # Шрифты
        self.title_font = font.Font(family="Courier", size=36, weight="bold")
        self.header_font = font.Font(family="Courier", size=24, weight="bold")
        self.data_font = font.Font(family="Courier", size=18)
        self.small_font = font.Font(family="Courier", size=14)
        self.button_font = font.Font(family="Courier", size=16, weight="bold")

        # Время уроков
        self.lesson_times = [
            ("08:30", "09:15"),
            ("09:30", "10:15"),
            ("10:45", "11:30"),
            ("11:45", "12:30"),
            ("12:45", "13:30"),
            ("13:45", "14:30"),
            ("14:45", "15:30"),
            ("15:45", "16:30")
        ]

        # Дни недели
        self.days_of_week = ["ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА", "СУББОТА", "ВОСКРЕСЕНЬЕ"]
        weekday_index = datetime.now().weekday()
        self.day_today = self.days_of_week[weekday_index % 6]

        self.data = download_fromServer.fetch_schedule()

        if self.data is not None:
            download_fromServer.save_schedule_to_cache(self.data)
        else:
            print("Server unavailable, trying to load cached data...")
            self.data = download_fromServer.load_schedule_from_cache()
            if self.data is None:
                self.data = {
                    "fromExcel": {
                        "sp_classes": [],
                        "sp_rooms": [],
                        "sp_subjects": [],
                        "schedule": {}
                    },
                    "fromWord": {
                        "replace": [],
                        "skip": [],
                        "day": ""
                    }
                }
                print("No cached data available, using empty schedule")


        self.rasp_wth_changes = self.make_rasp_wth_changes()

        self.all_classes = sorted(self.data["fromExcel"]["sp_classes"], key=lambda x: (int(x.split('-')[0]), int(x.split('-')[1])))

        self.class_groups = self.create_class_groups()
        self.current_group_index = 0
        self.current_day_index = 0

        self.show_all_lessons = True
        self.current_class = None

        self.clock_job = None

        self.setup_window()
        self.show_all_classes_schedule()
        self.root.mainloop()   

    def create_class_groups(self):
        """Создание групп классов для постраничного просмотра"""
        if not self.all_classes:
            return [{'name': '5-е классы', 'classes': []}]

        groups = {}

        for class_name in self.all_classes:
            # Извлекаем номер класса (первая цифра)
            match = re.match(r'^(\d+)', class_name)
            if match:
                grade = match.group(1)
                if grade not in groups:
                    groups[grade] = []
                groups[grade].append(class_name)

        # Сортируем группы по номеру класса
        sorted_groups = []
        for grade in sorted(groups.keys(), key=int):
            sorted_groups.append({
                'name': f'{grade}-е классы',
                'classes': sorted(groups[grade])
            })

        # Если группы не создались, создаем одну группу со всеми классами
        if not sorted_groups:
            sorted_groups.append({
                'name': 'Все классы',
                'classes': self.all_classes
            })

        return sorted_groups

    def parse_day_month(self, date_str):
        if not date_str or " " not in date_str:
            return None   # или вернуть None, чтобы затем не применять изменения
        month_map = {
            'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
            'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
            'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
        }
        
        day_str, month_str = date_str.split()
        day = int(day_str)
        month = month_map[month_str.lower()]
        year = date.today().year  # берем текущий год
        
        return date(year, month, day)

    def make_rasp_wth_changes(self):
        # Проверка наличия данных
        if (not self.data or
            "fromExcel" not in self.data or
            "schedule" not in self.data["fromExcel"] or
            "fromWord" not in self.data):
            return {}

        data_return = self.data["fromExcel"]["schedule"]
        day_str = self.data["fromWord"].get("day", "")

        # Если дата не указана или не парсится – не применяем изменения
        if not day_str or " " not in day_str:
            return data_return

        date_changes = self.parse_day_month(day_str)
        if date_changes is None:
            return data_return

        today = date.today()
        print(f"Date from changes: {date_changes}, today: {today}")

        # Применяем изменения только если дата совпадает
        if date_changes == today:
            data_replace = self.data["fromWord"]["replace"]
            data_skip = self.data["fromWord"]["skip"]
            print("Applying changes...")

            for change in data_replace:
                class_torepl = change[3]
                num_torepl = change[0]
                if (self.day_today in data_return and
                    class_torepl in data_return[self.day_today]):
                    if num_torepl - 1 < len(data_return[self.day_today][class_torepl]):
                        data_return[self.day_today][class_torepl][num_torepl - 1] = change
                    else:
                        data_return[self.day_today][class_torepl].append(change)

            for change in data_skip:
                class_torepl = change[0]
                num_torepl = change[1]
                if (self.day_today in data_return and
                    class_torepl in data_return[self.day_today] and
                    num_torepl - 1 < len(data_return[self.day_today][class_torepl])):
                    data_return[self.day_today][class_torepl][num_torepl - 1][2] = '-'
                    data_return[self.day_today][class_torepl][num_torepl - 1][4] = '-'
                    data_return[self.day_today][class_torepl][num_torepl - 1][5] = '-'
                    data_return[self.day_today][class_torepl][num_torepl - 1][6] = 'ОТМЕНЕНО'

        return data_return

    def setup_window(self):
        """Настройка главного окна"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Используем почти весь экран
        window_width = int(screen_width * 0.95)
        window_height = int(screen_height * 0.95)

        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.resizable(True, True)

        # Горячие клавиши
        self.root.bind('<F11>', lambda e: self.root.attributes('-fullscreen',
                                                               not self.root.attributes('-fullscreen')))
        self.root.bind('<Escape>', lambda e: self.root.attributes('-fullscreen', False))

    def clear_window(self):
        """Очистка окна"""
        # Отменяем таймер обновления часов
        if hasattr(self, 'clock_job') and self.clock_job:
            self.root.after_cancel(self.clock_job)
            self.clock_job = None

        # Удаляем все виджеты
        for widget in self.root.winfo_children():
            widget.destroy()

    def create_header(self, title):
        """Создание заголовка окна"""
        header_frame = tk.Frame(self.root, bg='black')
        header_frame.pack(fill=tk.X, padx=20, pady=10)

        # Заголовок
        title_label = tk.Label(header_frame,
                               text=title,
                               font=self.title_font,
                               fg=self.highlight_color,
                               bg='black')
        title_label.pack(side=tk.LEFT)

        # Часы
        self.clock_label = tk.Label(header_frame,
                                    font=self.title_font,
                                    fg=self.text_color,
                                    bg='black')
        self.clock_label.pack(side=tk.RIGHT)

        # Обновление времени
        self.update_clock()

        return header_frame

    def create_status_bar(self, text):
        """Создание информационной строки"""
        info_frame = tk.Frame(self.root, bg='#001122', height=60)
        info_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        info_frame.pack_propagate(False)

        info_label = tk.Label(info_frame,
                              text=text,
                              font=self.data_font,
                              fg=self.highlight_color,
                              bg='#001122')
        info_label.pack(pady=15)

        return info_frame

    def create_footer(self, text):
        """Создание нижней информационной строки"""
        info_frame = tk.Frame(self.root, bg='#002200', height=40)
        info_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        info_frame.pack_propagate(False)

        info_label = tk.Label(info_frame,
                              text=text,
                              font=self.small_font,
                              fg='#00FF00',
                              bg='#002200')
        info_label.pack(pady=8)

        return info_frame

    def create_navigation_buttons(self, buttons_config):
        """Создание панели навигационных кнопок"""
        button_frame = tk.Frame(self.root, bg='black')
        button_frame.pack(fill=tk.X, padx=20, pady=15)

        for text, command in buttons_config:
            btn = tk.Button(button_frame,
                            text=text,
                            font=self.button_font,
                            bg='#003300',
                            fg='white',
                            activebackground='#00AA00',
                            activeforeground='white',
                            relief='raised',
                            borderwidth=4,
                            padx=25,
                            pady=15,
                            command=command)
            btn.pack(side=tk.LEFT, padx=15)

        return button_frame

    def create_day_navigation_buttons(self):
        """Создание кнопок для навигации по дням недели"""
        day_frame = tk.Frame(self.root, bg='black')
        day_frame.pack(fill=tk.X, padx=20, pady=10)
        dict_day = {"ПОНЕДЕЛЬНИК": "ПН", "ВТОРНИК": "ВТ", "СРЕДА": "СР", "ЧЕТВЕРГ": "ЧТ", "ПЯТНИЦА": "ПТ", "СУББОТА": "СБ"}
        for i, day in enumerate(self.days_of_week[:len(self.days_of_week) - 1]):
            day_btn = tk.Button(day_frame,
                                text=dict_day[day],
                                font=self.button_font,
                                bg='#003366',
                                fg='white',
                                activebackground='#0066CC',
                                activeforeground='white',
                                relief='raised',
                                borderwidth=3,
                                padx=15,
                                pady=10,
                                command=lambda idx=i: self.set_day_and_refresh(idx))
            day_btn.pack(side=tk.LEFT, padx=5)

        return day_frame

    def set_day_and_refresh(self, day_index):
        """Установить день и обновить отображение"""
        self.current_day_index = day_index
        self.show_full_schedule()

    def create_group_navigation_buttons(self):
        """Создание кнопок для навигации по группам классов"""
        group_frame = tk.Frame(self.root, bg='black')
        group_frame.pack(fill=tk.X, padx=20, pady=10)

        for i, group in enumerate(self.class_groups):
            group_btn = tk.Button(group_frame,
                                  text=group['name'],
                                  font=self.button_font,
                                  bg='#330066',
                                  fg='white',
                                  activebackground='#6600CC',
                                  activeforeground='white',
                                  relief='raised',
                                  borderwidth=3,
                                  padx=15,
                                  pady=10,
                                  command=lambda idx=i: self.set_group_and_refresh(idx))
            group_btn.pack(side=tk.LEFT, padx=5)

        return group_frame

    def set_group_and_refresh(self, group_index):
        """Установить группу и обновить отображение"""
        self.current_group_index = group_index
        self.show_full_schedule()

    def update_clock(self):
        """Обновление времени"""
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            if hasattr(self, 'clock_label') and self.clock_label.winfo_exists():
                self.clock_label.config(text=current_time)
                # Планируем следующее обновление
                self.clock_job = self.root.after(1000, self.update_clock)
        except Exception as e:
            # Если произошла ошибка (виджет уничтожен), не планируем следующее обновление
            pass

    def get_current_lesson_info(self):
        """Получение информации о текущем или следующем уроке"""
        now = datetime.now()

        # Находим текущий урок или следующую переменную
        current_lesson = None
        next_lesson = None
        is_break = True

        for i, (start_time, end_time) in enumerate(self.lesson_times):
            start_dt = datetime.strptime(start_time, "%H:%M")
            end_dt = datetime.strptime(end_time, "%H:%M")

            # Сравниваем время
            if start_dt.time() <= now.time() <= end_dt.time():
                current_lesson = i  # Текущий урок
                is_break = False
                break
            elif now.time() < start_dt.time():
                next_lesson = i  # Следующий урок
                is_break = True
                break

        # Если время после последнего урока
        if current_lesson is None and next_lesson is None:
            is_break = True

        return current_lesson, next_lesson, is_break


    def show_all_classes_schedule(self):
        self.clear_window()
        self.create_header("✈ ТЕКУЩИЕ УРОКИ - ВСЕ КЛАССЫ ✈")
        self.create_status_bar("Информационная система школьного расписания")

        # Проверка наличия данных
        if not self.rasp_wth_changes:
            self.create_status_bar("Нет данных для отображения (проверьте подключение к серверу)")
            self.create_navigation_buttons([("ВЫХОД", self.root.quit)])
            return

        current_day = self.day_today
        if current_day not in self.rasp_wth_changes:
            self.create_status_bar(f"Нет расписания на {current_day}")
            self.create_navigation_buttons([("ВЫБОР КЛАССА", self.show_class_selection)])
            return

        day_schedule = self.rasp_wth_changes[current_day]

        current_lesson, next_lesson, is_break = self.get_current_lesson_info()
        lesson_to_show = current_lesson if current_lesson is not None else next_lesson

        container = tk.Frame(self.root, bg=self.bg_color)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))

        canvas = tk.Canvas(container, bg=self.bg_color, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        table_frame = tk.Frame(canvas, bg=self.bg_color)
        table_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=table_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        headers = ["КЛАСС", "№ УРОКА", "ВРЕМЯ", "ПРЕДМЕТ", "КАБИНЕТ", "СТАТУС"]
        for i, header in enumerate(headers):
            header_label = tk.Label(table_frame,
                                    text=header,
                                    font=self.header_font,
                                    fg=self.highlight_color,
                                    bg=self.bg_color,
                                    padx=20,
                                    pady=15)
            header_label.grid(row=0, column=i, sticky='ew')

        row_idx = 1
        for class_name in self.all_classes:
            if class_name in day_schedule:
                lessons = day_schedule[class_name]
                if lesson_to_show is not None and lesson_to_show < len(lessons):
                    lesson_data = lessons[lesson_to_show]
                    full_row_data = (
                        class_name,
                        lesson_data[0],   # номер урока
                        lesson_data[1],   # время
                        lesson_data[2],   # предмет
                        lesson_data[4],   # кабинет
                        lesson_data[6]    # статус
                    )

                    is_cancelled = lesson_data[6] == "ОТМЕНЕНО"
                    for col_idx, cell_data in enumerate(full_row_data):
                        if is_cancelled:
                            bg_color = self.cancelled_bg
                            fg_color = '#FFFFFF' if col_idx == 5 else ('#00FFFF' if col_idx in [0, 2] else self.cancelled_fg)
                        else:
                            bg_color = self.bg_color
                            if col_idx == 5:
                                fg_color = self.warning_color if cell_data == "ИЗМЕНЕНО" else ('#FF6666' if cell_data == "ОТМЕНЕНО" else '#00FF00')
                            elif col_idx in [0, 2]:
                                fg_color = self.text_color
                            else:
                                fg_color = '#FFFFFF'

                        cell_label = tk.Label(table_frame,
                                            text=cell_data,
                                            font=self.data_font,
                                            fg=fg_color,
                                            bg=bg_color,
                                            padx=20,
                                            pady=12)
                        cell_label.grid(row=row_idx, column=col_idx, sticky='ew')
                    row_idx += 1

        status_text = ""
        if current_lesson is not None:
            start_time, end_time = self.lesson_times[current_lesson]
            status_text = f"Сейчас идёт урок ({start_time}-{end_time})"
        elif next_lesson is not None:
            start_time, end_time = self.lesson_times[next_lesson]
            status_text = f"Сейчас перемена, следующий урок в {start_time}"
        else:
            status_text = "Учебный день завершён"

        self.create_footer(f"Статус: {status_text} | Всего классов: {len(self.all_classes)} | День: {current_day}")

        buttons = [
            ("ОБНОВИТЬ", self.refresh_all_classes),
            ("ВСЕ РАСПИСАНИЕ", self.show_full_schedule),
            ("ВЫБРАТЬ КЛАСС", self.show_class_selection),
            ("ВЫХОД", self.root.quit)
        ]
        self.create_navigation_buttons(buttons)

        for i in range(len(headers)):
            table_frame.columnconfigure(i, weight=1)


    def show_class_schedule(self, class_name):
        """Показать расписание для конкретного класса"""
        self.clear_window()
        self.current_class = class_name

        # Создаем заголовок
        self.create_header(f"✈ РАСПИСАНИЕ КЛАССА {class_name} ✈")

        if not self.rasp_wth_changes or self.day_today not in self.rasp_wth_changes:
            self.create_status_bar("Нет данных для отображения")
            self.create_navigation_buttons([("НАЗАД", self.show_all_classes_schedule)])
            return
        rasp = self.rasp_wth_changes[self.day_today]

        # Создаем информационную строку
        self.create_status_bar(f"Расписание класса {class_name} на текущий день")

        # Основная таблица
        table_frame = tk.Frame(self.root, bg=self.bg_color)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))

        # Заголовки таблицы
        headers = ["№ УРОКА", "ВРЕМЯ", "ПРЕДМЕТ", "КЛАСС", "КАБИНЕТ", "СТАТУС"]

        for i, header in enumerate(headers):
            header_label = tk.Label(table_frame,
                                    text=header,
                                    font=self.header_font,
                                    fg=self.highlight_color,
                                    bg=self.bg_color,
                                    padx=20,
                                    pady=15)
            header_label.grid(row=0, column=i, sticky='ew')
        # Фильтруем уроки в зависимости от режима
        rasp = self.rasp_wth_changes[self.day_today]
        schedule_to_show = []
        if class_name in rasp.keys():
            schedule_to_show = rasp[class_name]

            if not self.show_all_lessons:
                current_time = datetime.now().time()
                schedule_to_show = []
                for lesson in rasp[class_name]:
                    lesson_time_str = lesson[1]
                    if lesson_time_str:
                        try:
                            lesson_time = datetime.strptime(lesson_time_str, "%H:%M").time()
                            if lesson_time >= current_time:
                                schedule_to_show.append(lesson)
                        except:
                            schedule_to_show.append(lesson)

            # Отображаем уроки
            for row_idx, row_data in enumerate(schedule_to_show, 1):
                is_cancelled = row_data[6] == "ОТМЕНЕНО"

                # Пропускаем колонку с учителем (индекс 5)
                display_data = (row_data[0], row_data[1], row_data[2], row_data[3], row_data[4], row_data[6])

                for col_idx, cell_data in enumerate(display_data):
                    if is_cancelled:
                        bg_color = self.cancelled_bg
                        if col_idx == 5:  # Статус
                            fg_color = '#FFFFFF'
                        elif col_idx in [0, 1]:  # № урока и время
                            fg_color = '#00FFFF'
                        else:
                            fg_color = self.cancelled_fg
                    else:
                        bg_color = self.bg_color
                        if col_idx == 5:  # Статус
                            if cell_data == "ИЗМЕНЕНО":
                                fg_color = self.warning_color
                            elif cell_data == "ОТМЕНЕНО":
                                fg_color = '#FF6666'
                            else:
                                fg_color = '#00FF00'
                        elif col_idx in [0, 1]:  # № урока и время
                            fg_color = self.text_color
                        else:
                            fg_color = '#FFFFFF'

                    cell_label = tk.Label(table_frame,
                                          text=cell_data,
                                          font=self.data_font,
                                          fg=fg_color,
                                          bg=bg_color,
                                          padx=20,
                                          pady=12)
                    cell_label.grid(row=row_idx, column=col_idx, sticky='ew')

        # Информационная строка
        mode_text = "ВСЕ УРОКИ" if self.show_all_lessons else "ТОЛЬКО БУДУЩИЕ"
        self.create_footer(f"Класс: {class_name} | Режим: {mode_text} | Уроков: {len(schedule_to_show)}")

        # Кнопки навигации
        toggle_text = "ТОЛЬКО БУДУЩИЕ" if self.show_all_lessons else "ВСЕ УРОКИ"
        buttons = [
            ("ОБНОВИТЬ", self.refresh_class_schedule),
            (toggle_text, self.toggle_lesson_mode),
            ("ВСЕ РАСПИСАНИЕ", self.show_full_schedule),
            ("ВЫБРАТЬ КЛАСС", self.show_class_selection),
            ("К ОБЩЕМУ РАСПИСАНИЮ", self.show_all_classes_schedule)
        ]
        self.create_navigation_buttons(buttons)

        # Настраиваем вес колонок
        for i in range(len(headers)):
            table_frame.columnconfigure(i, weight=1)


    def show_class_selection(self):
        """Окно выбора класса с крупными элементами и параллелями в 2 колонки"""
        self.clear_window()

        self.create_header("✈ ВЫБОР КЛАССА ✈")
        self.create_status_bar("Выберите параллель, затем класс для просмотра расписания")

        # Основной контейнер (использует pack)
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))

        # ---- Левая панель (параллели) ----
        # Фиксированная ширина для комфортного размещения двух колонок
        left_panel = tk.Frame(main_frame, bg=self.bg_color, width=650)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)  # чтобы ширина не сжималась

        tk.Label(left_panel,
                text="ПАРАЛЛЕЛИ",
                font=self.header_font,
                fg=self.highlight_color,
                bg=self.bg_color).pack(pady=15)

        # Canvas для прокрутки левой панели
        left_canvas = tk.Canvas(left_panel, bg=self.bg_color, highlightthickness=0)
        # left_scrollbar = tk.Scrollbar(left_panel, orient="vertical", command=left_canvas.yview)
        self.left_buttons_frame = tk.Frame(left_canvas, bg=self.bg_color)

        self.left_buttons_frame.bind(
            "<Configure>",
            lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        )
        left_canvas.create_window((0, 0), window=self.left_buttons_frame, anchor="nw")
        # left_canvas.configure(yscrollcommand=left_scrollbar.set)

        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ---- Правая панель (классы) ----
        right_panel = tk.Frame(main_frame, bg=self.bg_color)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.right_title = tk.Label(right_panel,
                                    text="ВЫБЕРИТЕ ПАРАЛЛЕЛЬ",
                                    font=self.header_font,
                                    fg=self.text_color,
                                    bg=self.bg_color)
        self.right_title.pack(pady=15)

        # Canvas для прокрутки правой панели
        right_canvas = tk.Canvas(right_panel, bg=self.bg_color, highlightthickness=0)
        # right_scrollbar = tk.Scrollbar(right_panel, orient="vertical", command=right_canvas.yview)
        self.right_classes_frame = tk.Frame(right_canvas, bg=self.bg_color)

        self.right_classes_frame.bind(
            "<Configure>",
            lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all"))
        )
        right_canvas.create_window((0, 0), window=self.right_classes_frame, anchor="nw")
        # right_canvas.configure(yscrollcommand=right_scrollbar.set)

        right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # right_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ---- Создаём кнопки параллелей в 2 колонки ----
        self.choice_font = font.Font(family="Courier", size=22, weight="bold")

        row, col = 0, 0
        for group in self.class_groups:
            btn = tk.Button(self.left_buttons_frame,
                            text=group['name'],
                            font=self.choice_font,
                            bg='#003366',
                            fg='white',
                            activebackground='#0066CC',
                            activeforeground='white',
                            relief='raised',
                            borderwidth=3,
                            padx=10,
                            pady=12,
                            command=lambda g=group: self.on_grade_selected(g))
            btn.grid(row=row, column=col, padx=8, pady=8, sticky='ew')
            col += 1
            if col >= 2:
                col = 0
                row += 1

        # Растягиваем колонки левой панели
        for i in range(2):
            self.left_buttons_frame.grid_columnconfigure(i, weight=1)
        for i in range(row + 1):
            self.left_buttons_frame.grid_rowconfigure(i, weight=1)

        # Показываем первую параллель по умолчанию
        if self.class_groups:
            self.on_grade_selected(self.class_groups[0])

        self.create_footer(f"Всего доступных классов: {len(self.all_classes)}")

        buttons = [
            ("ВСЕ РАСПИСАНИЕ", self.show_full_schedule),
            ("К ОБЩЕМУ РАСПИСАНИЮ", self.show_all_classes_schedule),
        ]
        self.create_navigation_buttons(buttons)


    def on_grade_selected(self, group):
        """Обновляет правую панель: классы выбранной параллели в 4 колонки"""
        self.right_title.config(text=f"{group['name']}")

        # Очищаем старые кнопки классов
        for widget in self.right_classes_frame.winfo_children():
            widget.destroy()

        # Размещаем классы в 4 колонки
        cols = 5
        row, col = 0, 0
        for class_name in group['classes']:
            btn = tk.Button(self.right_classes_frame,
                            text=class_name,
                            font=self.choice_font,
                            bg='#003366',
                            fg='white',
                            activebackground='#0066CC',
                            activeforeground='white',
                            relief='raised',
                            borderwidth=3,
                            padx=20,
                            pady=18,
                            command=lambda c=class_name: self.show_class_schedule(c))
            btn.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')
            col += 1
            if col >= cols:
                col = 0
                row += 1

        # Настраиваем веса для растяжения
        for i in range(cols):
            self.right_classes_frame.grid_columnconfigure(i, weight=1)
        for i in range(row + 1):
            self.right_classes_frame.grid_rowconfigure(i, weight=1)

        # Подсвечиваем выбранную параллель
        for child in self.left_buttons_frame.winfo_children():
            if isinstance(child, tk.Button):
                if child['text'] == group['name']:
                    child.config(bg='#0066CC')
                else:
                    child.config(bg='#003366')


    def show_full_schedule(self):
        """Показать полное расписание для всех классов"""
        self.clear_window()

        # Проверяем, что есть группы для отображения
        if not self.class_groups:
            self.create_status_bar("Нет данных для отображения")
            self.create_navigation_buttons([("НАЗАД", self.show_all_classes_schedule)])
            return

        # Проверяем индекс текущей группы
        if self.current_group_index >= len(self.class_groups):
            self.current_group_index = 0

        # Проверка наличия данных
        if not self.rasp_wth_changes:
            self.create_status_bar("Нет данных для отображения")
            self.create_navigation_buttons([("ВЫХОД", self.root.quit)])
            return

        # Создаем заголовок
        current_group = self.class_groups[self.current_group_index]
        current_day = self.days_of_week[self.current_day_index]

        # Проверяем, есть ли расписание на этот день
        if current_day not in self.rasp_wth_changes:
            self.create_status_bar(f"Нет расписания на {current_day}")
            self.create_navigation_buttons([("НАЗАД", self.show_all_classes_schedule)])
            return

        day_schedule = self.rasp_wth_changes[current_day]

        self.create_header(f"✈ РАСПИСАНИЕ - {current_day} ✈")
        self.create_status_bar(f"{current_day} | {current_group['name']}")

        # Кнопки навигации по дням
        self.create_day_navigation_buttons()

        # Кнопки навигации по группам классов
        self.create_group_navigation_buttons()

        # Основная таблица
        table_frame = tk.Frame(self.root, bg=self.bg_color)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))

        # Заголовки таблицы
        max_lessons = 0
        for class_name in current_group['classes']:
            if class_name in day_schedule:
                max_lessons = max(max_lessons, len(day_schedule[class_name]))

        if max_lessons == 0:
            self.create_status_bar("Нет уроков для отображения")
            self.create_navigation_buttons([("НАЗАД", self.show_all_classes_schedule)])
            return

        headers = ["КЛАСС"] + [f"УРОК {i}" for i in range(1, max_lessons + 1)]

        for i, header in enumerate(headers):
            header_label = tk.Label(table_frame,
                                    text=header,
                                    font=self.header_font,
                                    fg=self.highlight_color,
                                    bg=self.bg_color,
                                    padx=15,
                                    pady=12,
                                    borderwidth=2,
                                    relief="solid")
            header_label.grid(row=0, column=i, sticky='nsew')

        row_idx = 1
        for class_name in current_group['classes']:
            if class_name in day_schedule:
                row_data = [class_name]
                rasp_cur_class = day_schedule[class_name]

                for lesson_num in range(1, max_lessons + 1):
                    if (lesson_num - 1) < len(rasp_cur_class):
                        lesson_info = f"{rasp_cur_class[lesson_num-1][2]}\n{rasp_cur_class[lesson_num-1][4]}"
                    else:
                        lesson_info = ""
                    row_data.append(lesson_info)

                # Отображаем строку
                for col_idx, cell_data in enumerate(row_data):
                    bg_color = self.bg_color if row_idx % 2 == 0 else '#001144'
                    if col_idx == 0:
                        bg_color = '#002255'
                        fg_color = self.text_color
                    else:
                        fg_color = '#FFFFFF'

                    cell_label = tk.Label(table_frame,
                                        text=cell_data,
                                        font=self.data_font,
                                        fg=fg_color,
                                        bg=bg_color,
                                        padx=15,
                                        pady=10,
                                        borderwidth=1,
                                        relief="solid",
                                        justify="center")
                    cell_label.grid(row=row_idx, column=col_idx, sticky='nsew')
                row_idx += 1

        # Информационная строка
        group_info = f"{self.current_group_index + 1}/{len(self.class_groups)}"
        day_info = f"{self.current_day_index + 1}/{len(self.days_of_week)}"
        self.create_footer(
            f"День: {current_day} | Группа: {current_group['name']} | Страница дня: {day_info} | Страница группы: {group_info}")

        # Кнопки навигации
        buttons = [
            ("ОБЩЕЕ РАСПИСАНИЕ", self.show_all_classes_schedule),
            ("ВЫБРАТЬ КЛАСС", self.show_class_selection),
            ("ВЫХОД", self.root.quit)
        ]
        self.create_navigation_buttons(buttons)

        # Настраиваем вес колонок
        for i in range(len(headers)):
            table_frame.columnconfigure(i, weight=1)

        for i in range(row_idx):
            table_frame.rowconfigure(i, weight=1)

    def prev_group(self):
        """Перейти к предыдущей группе классов"""
        if self.current_group_index > 0:
            self.current_group_index -= 1
            self.show_full_schedule()

    def next_group(self):
        """Перейти к следующей группе классов"""
        if self.current_group_index < len(self.class_groups) - 1:
            self.current_group_index += 1
            self.show_full_schedule()

    def refresh_all_classes(self):
        print("Обновление общего расписания...")
        new_data = download_fromServer.fetch_schedule()
        if new_data is not None:
            self.data = new_data
            download_fromServer.save_schedule_to_cache(new_data)
            self.rasp_wth_changes = self.make_rasp_wth_changes()
            self.all_classes = sorted(self.data["fromExcel"]["sp_classes"], 
                                    key=lambda x: (int(x.split('-')[0]), int(x.split('-')[1])))
            self.class_groups = self.create_class_groups()
        else:
            print("Сервер недоступен, данные не обновлены")
        self.show_all_classes_schedule()
        
    def refresh_class_schedule(self):
        """Обновить расписание для текущего класса"""
        print(f"Обновление расписания для класса {self.current_class}...")
        if self.current_class:
            self.show_class_schedule(self.current_class)

    def toggle_lesson_mode(self):
        """Переключить режим отображения уроков"""
        self.show_all_lessons = not self.show_all_lessons
        if self.current_class:
            self.show_class_schedule(self.current_class)


if __name__ == "__main__":
    app = App()
