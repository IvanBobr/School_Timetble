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

        self.debug_time = None
        self._last_lesson_index = None
        self._last_next_index = None
        self._current_screen = 'main'

        # === ПАЛИТРА ===
        self.bg_color        = '#0A0E1A'
        self.bg_panel        = '#131826'
        self.bg_header       = '#0F1626'
        self.bg_row_even     = '#0A0E1A'
        self.bg_row_odd      = '#0F1626'
        self.bg_row_first_col = '#182238'
        self.bg_row_first_col_hover = '#243049'
        self.separator_color = '#1E2A3F'

        self.text_color      = '#E8EDF5'
        self.text_dim        = '#7A8BA3'
        self.accent_amber    = '#FFB627'
        self.accent_amber_bright = '#FFC94D'
        self.accent_cyan     = '#4FC3F7'
        self.accent_cyan_bright = '#6EE7FF'

        self.highlight_color = self.accent_amber
        self.warning_color   = '#FF9F1C'
        self.cancelled_bg    = '#2A1418'
        self.cancelled_fg    = '#EF4444'

        self.status_ok       = '#4ADE80'
        self.status_warn     = '#FF9F1C'
        self.status_cancel   = '#EF4444'

        self.btn_bg          = '#1A2233'
        self.btn_hover       = '#243049'
        self.btn_disabled_bg = '#151A24'
        self.btn_disabled_fg = '#3E4A5C'

        # === ШРИФТЫ ===
        FONT = "Segoe UI"
        MONO = "Consolas"

        self.title_font  = font.Font(family=FONT, size=34, weight="bold")
        self.header_font = font.Font(family=FONT, size=22, weight="bold")
        self.data_font   = font.Font(family=FONT, size=20)
        self.data_mono   = font.Font(family=MONO, size=20, weight="bold")
        self.small_font  = font.Font(family=FONT, size=14)
        self.button_font = font.Font(family=FONT, size=15, weight="bold")

        # Пагинация
        self.current_classes_page = 0
        self.classes_per_page = 7
        self.auto_flip_job = None
        self.auto_flip_interval = 15000

        # Анимация flip
        self.flip_jobs = []
        self.is_animating = False
        self.row_height_px = 88

        # Ссылки для перерисовки
        self.table_rows = []
        self.rows_container = None
        self.footer_label = None
        self.status_banner_label = None
        self._parallel_card = None
        self.page_info = {"current": 1, "total": 1, "classes_count": 0, "day": ""}
        self.current_page_data = []

        # Время уроков
        self.lesson_times = [
            ("08:30", "09:15"),
            ("09:30", "10:15"),
            ("10:35", "11:20"),
            ("11:40", "12:25"),
            ("12:45", "13:30"),
            ("13:50", "14:35"),
            ("14:55", "15:40"),
            ("15:50", "16:35")
        ]

        self.days_of_week = ["ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА", "СУББОТА", "ВОСКРЕСЕНЬЕ"]
        weekday_index = self.get_time_now().weekday()
        self.day_today = self.days_of_week[weekday_index % 6]

        self._last_lesson_index, self._last_next_index, _ = self.get_current_lesson_info()

        self.data = download_fromServer.fetch_schedule()

        if self.data is not None:
            download_fromServer.save_schedule_to_cache(self.data)
        else:
            print("Server unavailable, trying to load cached data...")
            self.data = download_fromServer.load_schedule_from_cache()
            if self.data is None:
                self.data = {
                    "fromExcel": {"sp_classes": [], "sp_rooms": [], "sp_subjects": [], "schedule": {}},
                    "fromWord": {"replace": [], "skip": [], "day": ""}
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
        self.idle_timer_id = None
        self.is_main_screen = False

        self.setup_window()
        self.setup_idle_timer()
        self.show_all_classes_schedule()
        self.root.mainloop()

    # ---------- БАЗОВЫЕ МЕТОДЫ ----------
    def get_time_now(self):
        if self.debug_time:
            return self.debug_time
        return datetime.now()

    def start_auto_flip(self):
        self.stop_auto_flip()
        self.auto_flip_job = self.root.after(self.auto_flip_interval, self.next_classes_page)

    def stop_auto_flip(self):
        if self.auto_flip_job:
            self.root.after_cancel(self.auto_flip_job)
            self.auto_flip_job = None

    def _row_bg(self, index):
        return self.bg_row_even if index % 2 == 0 else self.bg_row_odd

    # ---------- КЛИКАБЕЛЬНАЯ ЯЧЕЙКА КЛАССА ----------
    def _make_class_cell(self, parent, class_name, bg_color, fg_color, font_):
        lbl = tk.Label(parent, text=class_name, font=font_,
                       fg=fg_color, bg=bg_color,
                       anchor="center", justify="center",
                       cursor='hand2')

        def _click(_e, c=class_name):
            self.show_class_schedule(c)
        def _enter(_e, l=lbl):
            l.configure(bg=self.bg_row_first_col_hover)
        def _leave(_e, l=lbl, b=bg_color):
            l.configure(bg=b)

        lbl.bind('<Button-1>', _click)
        lbl.bind('<Enter>', _enter)
        lbl.bind('<Leave>', _leave)
        return lbl

    # ---------- СТАНДАРТНАЯ ТРОЙКА НАВИГАЦИИ ----------
    def _get_nav_trio(self, active_screen):
        return [
            ("ТЕКУЩИЕ УРОКИ",
             self.show_all_classes_schedule,
             {'active': active_screen == 'main'}),
            ("ВСЁ РАСПИСАНИЕ",
             self.show_full_schedule,
             {'active': active_screen == 'full'}),
            ("ВЫБРАТЬ КЛАСС",
             self.show_class_selection,
             {'active': active_screen == 'selection'}),
        ]

    # ---------- FLIP-АНИМАЦИЯ ----------
    def _prepare_cells(self, row_data, default_bg=None):
        if default_bg is None:
            default_bg = self.bg_color
        class_name, number, time_, subject, room, status, is_cancelled = row_data
        cells = (class_name, number, time_, subject, room, status)
        result = []
        for col_idx, cell_data in enumerate(cells):
            if is_cancelled:
                bg = self.cancelled_bg
                if col_idx == 5:
                    fg = self.cancelled_fg
                elif col_idx in (0, 2):
                    fg = self.accent_cyan_bright
                else:
                    fg = self.text_dim
            else:
                bg = default_bg
                if col_idx == 5:
                    if cell_data == "ИЗМЕНЕНО":
                        fg = self.status_warn
                    elif cell_data == "ОТМЕНЕНО":
                        fg = self.status_cancel
                    else:
                        fg = self.status_ok
                elif col_idx == 0:
                    fg = self.accent_cyan_bright
                elif col_idx == 2:
                    fg = self.accent_amber
                elif col_idx == 1:
                    fg = self.accent_amber_bright
                else:
                    fg = self.text_color
            result.append((cell_data, bg, fg))
        return result

    def _create_row_frame(self, parent, row_data, index):
        row_bg = self._row_bg(index)
        row_frame = tk.Frame(parent, bg=row_bg)
        row_frame.place(x=0, y=index * self.row_height_px,
                        relwidth=1.0, height=self.row_height_px)
        row_frame.pack_propagate(False)

        row_frame.grid_rowconfigure(0, weight=1)
        for i in range(6):
            row_frame.grid_columnconfigure(i, weight=1, uniform="cols")

        for i, (text, bg, fg) in enumerate(self._prepare_cells(row_data, row_bg)):
            lbl_font = self.data_mono if i in (1, 2, 4) else self.data_font
            if i == 0:
                lbl = self._make_class_cell(row_frame, text, bg, fg, lbl_font)
            else:
                lbl = tk.Label(row_frame, text=text, font=lbl_font,
                               fg=fg, bg=bg, padx=10, pady=12,
                               anchor="center", justify="center")
            lbl.grid(row=0, column=i, sticky="nsew")

        sep = tk.Frame(row_frame, bg=self.separator_color, height=1)
        sep.place(relx=0, rely=1.0, anchor='sw', relwidth=1.0)
        sep.lift()
        return row_frame

    def _replace_row_content(self, row_frame, row_data, index):
        for w in row_frame.winfo_children():
            w.destroy()
        row_bg = self._row_bg(index)
        row_frame.configure(bg=row_bg)
        row_frame.grid_rowconfigure(0, weight=1)
        for i in range(6):
            row_frame.grid_columnconfigure(i, weight=1, uniform="cols")
        for i, (text, bg, fg) in enumerate(self._prepare_cells(row_data, row_bg)):
            lbl_font = self.data_mono if i in (1, 2, 4) else self.data_font
            if i == 0:
                lbl = self._make_class_cell(row_frame, text, bg, fg, lbl_font)
            else:
                lbl = tk.Label(row_frame, text=text, font=lbl_font,
                               fg=fg, bg=bg, padx=10, pady=12,
                               anchor="center", justify="center")
            lbl.grid(row=0, column=i, sticky="nsew")
        sep = tk.Frame(row_frame, bg=self.separator_color, height=1)
        sep.place(relx=0, rely=1.0, anchor='sw', relwidth=1.0)
        sep.lift()

    def _cancel_flip_jobs(self):
        for job in self.flip_jobs:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass
        self.flip_jobs = []

    def _flip_single_row(self, index, new_row_data, on_done=None):
        if index >= len(self.table_rows):
            if on_done:
                on_done()
            return
        row_frame = self.table_rows[index]
        if not row_frame.winfo_exists():
            if on_done:
                on_done()
            return

        base_y = index * self.row_height_px
        base_h = self.row_height_px
        mid_h = 3
        half_duration = 110
        steps = 8
        step_ms = max(8, half_duration // steps)

        def first_half(step=0):
            if not row_frame.winfo_exists():
                if on_done:
                    on_done()
                return
            if step > steps:
                self._replace_row_content(row_frame, new_row_data, index)
                second_half(0)
                return
            progress = step / steps
            eased = 1 - (1 - progress) ** 2
            cur_h = base_h - (base_h - mid_h) * eased
            cur_y = base_y + (base_h - cur_h) / 2
            try:
                row_frame.place_configure(y=cur_y, height=cur_h)
            except Exception:
                pass
            job = self.root.after(step_ms, lambda: first_half(step + 1))
            self.flip_jobs.append(job)

        def second_half(step=0):
            if not row_frame.winfo_exists():
                if on_done:
                    on_done()
                return
            if step > steps:
                try:
                    row_frame.place_configure(y=base_y, height=base_h)
                except Exception:
                    pass
                if on_done:
                    on_done()
                return
            progress = step / steps
            eased = progress ** 2
            cur_h = mid_h + (base_h - mid_h) * eased
            cur_y = base_y + (base_h - cur_h) / 2
            try:
                row_frame.place_configure(y=cur_y, height=cur_h)
            except Exception:
                pass
            job = self.root.after(step_ms, lambda: second_half(step + 1))
            self.flip_jobs.append(job)

        first_half(0)

    def _collapse_row(self, index):
        if index >= len(self.table_rows):
            return
        row_frame = self.table_rows[index]
        if not row_frame.winfo_exists():
            return

        base_y = index * self.row_height_px
        base_h = self.row_height_px
        steps = 10
        step_ms = 25

        def step(i=0):
            if not row_frame.winfo_exists():
                return
            if i > steps:
                try:
                    row_frame.destroy()
                except Exception:
                    pass
                return
            progress = i / steps
            eased = 1 - (1 - progress) ** 2
            cur_h = base_h * (1 - eased)
            cur_y = base_y + (base_h - cur_h) / 2
            try:
                row_frame.place_configure(y=cur_y, height=cur_h)
            except Exception:
                pass
            job = self.root.after(step_ms, lambda: step(i + 1))
            self.flip_jobs.append(job)

        step(0)

    def _appear_row(self, index, new_row_data):
        row_bg = self._row_bg(index)
        if index >= len(self.table_rows):
            row_frame = tk.Frame(self.rows_container, bg=row_bg)
            row_frame.place(x=0, y=index * self.row_height_px, relwidth=1.0, height=0)
            row_frame.pack_propagate(False)
            self.table_rows.append(row_frame)
        else:
            row_frame = self.table_rows[index]
            row_frame.configure(bg=row_bg)

        for w in row_frame.winfo_children():
            w.destroy()
        row_frame.grid_rowconfigure(0, weight=1)
        for i in range(6):
            row_frame.grid_columnconfigure(i, weight=1, uniform="cols")
        for i, (text, bg, fg) in enumerate(self._prepare_cells(new_row_data, row_bg)):
            lbl_font = self.data_mono if i in (1, 2, 4) else self.data_font
            if i == 0:
                lbl = self._make_class_cell(row_frame, text, bg, fg, lbl_font)
            else:
                lbl = tk.Label(row_frame, text=text, font=lbl_font,
                               fg=fg, bg=bg, padx=10, pady=12,
                               anchor="center", justify="center")
            lbl.grid(row=0, column=i, sticky="nsew")
        sep = tk.Frame(row_frame, bg=self.separator_color, height=1)
        sep.place(relx=0, rely=1.0, anchor='sw', relwidth=1.0)
        sep.lift()

        base_y = index * self.row_height_px
        target_h = self.row_height_px
        steps = 8
        step_ms = 18

        def step(i=0):
            if not row_frame.winfo_exists():
                return
            if i > steps:
                try:
                    row_frame.place_configure(y=base_y, height=target_h)
                except Exception:
                    pass
                return
            progress = i / steps
            eased = progress ** 2
            cur_h = target_h * eased
            cur_y = base_y + (target_h - cur_h) / 2
            try:
                row_frame.place_configure(y=cur_y, height=cur_h)
            except Exception:
                pass
            job = self.root.after(step_ms, lambda: step(i + 1))
            self.flip_jobs.append(job)

        step(0)

    def _animate_page_change(self, new_rows_data):
        if self.is_animating:
            return
        self.is_animating = True
        self._cancel_flip_jobs()

        old_count = len(self.table_rows)
        new_count = len(new_rows_data)

        delay = 0
        delay_step = 45
        common = min(old_count, new_count)

        for i in range(common):
            self.root.after(delay, lambda idx=i, data=new_rows_data[i]: self._flip_single_row(idx, data))
            delay += delay_step

        for i in range(old_count, new_count):
            self.root.after(delay, lambda idx=i, data=new_rows_data[i]: self._appear_row(idx, data))
            delay += delay_step

        for i in range(new_count, old_count):
            self.root.after(delay, lambda idx=i: self._collapse_row(idx))
            delay += delay_step

        self.current_page_data = new_rows_data
        total_ms = delay + 350
        self.root.after(total_ms, self._on_flip_finished)

    def _on_flip_finished(self):
        self.is_animating = False
        self.table_rows = [r for r in self.table_rows if r.winfo_exists()]
        for i, r in enumerate(self.table_rows):
            try:
                r.place_configure(y=i * self.row_height_px, height=self.row_height_px, relwidth=1.0, x=0)
            except Exception:
                pass
        self._update_footer()
        self.start_auto_flip()

    def _update_footer(self):
        if not self.footer_label or not self.footer_label.winfo_exists():
            return
        pi = self.page_info
        status_text = pi.get("status_text", "")
        self.footer_label.config(
            text=f"Статус: {status_text}  •  Страница: {pi['current']}/{pi['total']}  "
                 f"•  Классов с уроком: {pi['classes_count']}  •  День: {pi['day']}  "
                 f"•  Кликните на класс, чтобы открыть его расписание"
        )

    def _get_page_rows_data(self, day_schedule, lesson_to_show):
        classes_with_lesson = self.get_classes_with_lesson(day_schedule, lesson_to_show)
        total_page = max(1, (len(classes_with_lesson) + self.classes_per_page - 1) // self.classes_per_page)
        if self.current_classes_page >= total_page:
            self.current_classes_page = 0

        start_index = self.current_classes_page * self.classes_per_page
        end_index = start_index + self.classes_per_page
        page_classes = classes_with_lesson[start_index:end_index]

        rows = []
        for class_name in page_classes:
            if class_name in day_schedule:
                lessons = day_schedule[class_name]
                if lesson_to_show is not None and lesson_to_show < len(lessons):
                    lesson_data = lessons[lesson_to_show]
                    rows.append((
                        class_name,
                        lesson_data[0],
                        lesson_data[1],
                        lesson_data[2],
                        lesson_data[4],
                        lesson_data[6],
                        lesson_data[6] == "ОТМЕНЕНО"
                    ))
        return rows, classes_with_lesson, total_page

    # ---------- ПАГИНАЦИЯ ----------
    def _go_to_page(self, delta):
        if self.is_animating:
            return
        current_lesson, next_lesson, _ = self.get_current_lesson_info()
        lesson_to_show = current_lesson if current_lesson is not None else next_lesson
        day_schedule = self.rasp_wth_changes.get(self.day_today, {})
        classes_with_lesson = self.get_classes_with_lesson(day_schedule, lesson_to_show)

        total = max(1, (len(classes_with_lesson) + self.classes_per_page - 1) // self.classes_per_page)
        self.current_classes_page = (self.current_classes_page + delta) % total

        rows, cls, tp = self._get_page_rows_data(day_schedule, lesson_to_show)

        status_text = self._get_status_text()
        self.page_info = {
            "current": self.current_classes_page + 1,
            "total": tp,
            "classes_count": len(cls),
            "day": self.day_today,
            "status_text": status_text
        }

        self._animate_page_change(rows)

    def next_classes_page(self):
        if not self.is_main_screen:
            return
        self._go_to_page(+1)

    def prev_classes_page(self):
        if not self.is_main_screen:
            return
        self._go_to_page(-1)

    def next_classes_page_manual(self):
        if not self.is_main_screen:
            return
        self._go_to_page(+1)

    # ---------- ЛОГИКА ----------
    def create_class_groups(self):
        if not self.all_classes:
            return [{'name': '5-е классы', 'classes': []}]
        groups = {}
        for class_name in self.all_classes:
            match = re.match(r'^(\d+)', class_name)
            if match:
                grade = match.group(1)
                if grade not in groups:
                    groups[grade] = []
                groups[grade].append(class_name)
        sorted_groups = []
        for grade in sorted(groups.keys(), key=int):
            sorted_groups.append({
                'name': f'{grade}-е классы',
                'classes': sorted(groups[grade])
            })
        if not sorted_groups:
            sorted_groups.append({'name': 'Все классы', 'classes': self.all_classes})
        return sorted_groups

    def parse_day_month(self, date_str):
        if not date_str or " " not in date_str:
            return None
        month_map = {
            'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
            'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
            'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
        }
        day_str, month_str = date_str.split()
        day = int(day_str)
        month = month_map[month_str.lower()]
        year = self.get_time_now().date().year
        return date(year, month, day)

    def make_rasp_wth_changes(self):
        if (not self.data or "fromExcel" not in self.data or
            "schedule" not in self.data["fromExcel"] or "fromWord" not in self.data):
            return {}
        data_return = self.data["fromExcel"]["schedule"]
        day_str = self.data["fromWord"].get("day", "")
        if not day_str or " " not in day_str:
            return data_return
        date_changes = self.parse_day_month(day_str)
        if date_changes is None:
            return data_return
        today = self.get_time_now().date()
        print(f"Date from changes: {date_changes}, today: {today}")
        if date_changes == today:
            data_replace = self.data["fromWord"]["replace"]
            data_skip = self.data["fromWord"]["skip"]
            print("Applying changes...")
            for change in data_replace:
                class_torepl = change[3]
                num_torepl = change[0]
                if (self.day_today in data_return and class_torepl in data_return[self.day_today]):
                    if num_torepl - 1 < len(data_return[self.day_today][class_torepl]):
                        data_return[self.day_today][class_torepl][num_torepl - 1] = change
                    else:
                        data_return[self.day_today][class_torepl].append(change)
            for change in data_skip:
                class_torepl = change[0]
                num_torepl = change[1]
                if (self.day_today in data_return and class_torepl in data_return[self.day_today] and
                    num_torepl - 1 < len(data_return[self.day_today][class_torepl])):
                    data_return[self.day_today][class_torepl][num_torepl - 1][2] = '-'
                    data_return[self.day_today][class_torepl][num_torepl - 1][4] = '-'
                    data_return[self.day_today][class_torepl][num_torepl - 1][5] = '-'
                    data_return[self.day_today][class_torepl][num_torepl - 1][6] = 'ОТМЕНЕНО'
        return data_return

    def open_debug_dialog(self):
        from tkinter import simpledialog
        default = self.debug_time.strftime("%Y-%m-%d %H:%M") if self.debug_time else datetime.now().strftime("%Y-%m-%d %H:%M")
        answer = simpledialog.askstring(
            "Debug: установить дату и время",
            "Введите дату и время в формате:\nYYYY-MM-DD HH:MM\n\nОставьте пустым для возврата к реальному времени.",
            initialvalue=default
        )
        if answer is None:
            return
        answer = answer.strip()
        if answer == "":
            self.debug_time = None
            print("Debug: возврат к реальному времени")
        else:
            try:
                self.debug_time = datetime.strptime(answer, "%Y-%m-%d %H:%M")
                print(f"Debug: время установлено на {self.debug_time}")
            except ValueError:
                from tkinter import messagebox
                messagebox.showerror("Ошибка", "Неверный формат. Используйте YYYY-MM-DD HH:MM")
                return
        weekday_index = self.get_time_now().weekday()
        if weekday_index == 6:
            from tkinter import messagebox
            messagebox.showinfo("Выходной", "Воскресенье - выходной день в школе")
            self.day_today = self.days_of_week[0]
        else:
            self.day_today = self.days_of_week[weekday_index % 6]
        self.current_classes_page = 0
        self.rasp_wth_changes = self.make_rasp_wth_changes()
        self.show_all_classes_schedule()

    def get_classes_with_lesson(self, day_schedule, lesson_idx):
        if lesson_idx is None:
            return []
        result = []
        for cls in self.all_classes:
            if cls in day_schedule:
                lessons = day_schedule[cls]
                if lesson_idx < len(lessons):
                    result.append(cls)
        return result

    def setup_window(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = int(screen_width * 0.95)
        window_height = int(screen_height * 0.95)
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.resizable(True, True)
        self.root.bind('<F11>', lambda e: self.root.attributes('-fullscreen',
                                                               not self.root.attributes('-fullscreen')))
        self.root.bind('<Escape>', lambda e: self.root.attributes('-fullscreen', False))
        self.root.bind('<Control-Shift-D>', lambda e: self.open_debug_dialog())
        self.root.bind('<Control-Shift-d>', lambda e: self.open_debug_dialog())
        self.root.bind('<F12>', lambda e: self.open_debug_dialog())

    def clear_window(self):
        self.stop_auto_flip()
        self._cancel_flip_jobs()
        self.is_animating = False
        self.root.unbind_all("<MouseWheel>")
        self.root.unbind_all("<Button-4>")
        self.root.unbind_all("<Button-5>")
        if hasattr(self, 'clock_job') and self.clock_job:
            self.root.after_cancel(self.clock_job)
            self.clock_job = None
        for widget in self.root.winfo_children():
            widget.destroy()
        self.table_rows = []
        self.rows_container = None
        self.footer_label = None
        self.status_banner_label = None
        self._parallel_card = None

    # ---------- КНОПКА-ЧИП ----------
    def _make_chip_button(self, parent, text, command, active=False, font_=None, disabled=False):
        if font_ is None:
            font_ = self.button_font

        if disabled:
            btn = tk.Button(
                parent, text=text, font=font_,
                bg=self.btn_disabled_bg, fg=self.btn_disabled_fg,
                activebackground=self.btn_disabled_bg, activeforeground=self.btn_disabled_fg,
                relief='flat', borderwidth=0, padx=18, pady=10,
                cursor='arrow', command=lambda: None, highlightthickness=0
            )
            return btn

        if active:
            bg, fg, hover = self.accent_amber, self.bg_color, '#FFD166'
        else:
            bg, fg, hover = self.btn_bg, self.accent_amber, self.btn_hover

        btn = tk.Button(
            parent, text=text, font=font_,
            bg=bg, fg=fg,
            activebackground=hover, activeforeground=fg,
            relief='flat', borderwidth=0, padx=18, pady=10,
            cursor='hand2', command=command, highlightthickness=0
        )
        btn.bind('<Enter>', lambda e, b=btn, h=hover: b.configure(bg=h))
        btn.bind('<Leave>', lambda e, b=btn, bg_=bg: b.configure(bg=bg_))
        return btn

    # ---------- ОБНОВЛЕНИЕ ДАННЫХ ----------
    def _fetch_and_apply(self):
        print("Обновление данных с сервера...")
        new_data = download_fromServer.fetch_schedule()
        if new_data is not None:
            self.data = new_data
            download_fromServer.save_schedule_to_cache(new_data)
            self.rasp_wth_changes = self.make_rasp_wth_changes()
            self.all_classes = sorted(self.data["fromExcel"]["sp_classes"],
                                      key=lambda x: (int(x.split('-')[0]), int(x.split('-')[1])))
            self.class_groups = self.create_class_groups()
            return True
        print("Сервер недоступен, данные не обновлены")
        return False

    def refresh_current(self):
        self._fetch_and_apply()
        screen = getattr(self, '_current_screen', 'main')
        if screen == 'main':
            self.show_all_classes_schedule()
        elif screen == 'full':
            self.show_full_schedule()
        elif screen == 'selection':
            self.show_class_selection()
        elif screen == 'class':
            if self.current_class:
                self.show_class_schedule(self.current_class)

    # ---------- ШАПКА / ПАНЕЛИ / КНОПКИ ----------
    def create_header(self, title):
        header_frame = tk.Frame(self.root, bg=self.bg_header)
        header_frame.pack(fill=tk.X)

        inner = tk.Frame(header_frame, bg=self.bg_header)
        inner.pack(fill=tk.X, padx=30, pady=(16, 12))

        tk.Label(inner, text=title, font=self.title_font,
                 fg=self.accent_amber, bg=self.bg_header).pack(side=tk.LEFT)

        clock_color = self.status_cancel if self.debug_time else self.accent_amber
        self.clock_label = tk.Label(inner,
                                    font=font.Font(family="Consolas", size=34, weight="bold"),
                                    fg=clock_color, bg=self.bg_header)
        self.clock_label.pack(side=tk.RIGHT)

        tk.Frame(header_frame, bg=self.accent_amber, height=2).pack(fill=tk.X, side=tk.BOTTOM)

        self.update_clock()
        return header_frame

    def create_status_bar(self, text=None):
        info_frame = tk.Frame(self.root, bg=self.bg_panel)
        info_frame.pack(fill=tk.X)

        if text is None:
            self.status_banner_label = tk.Label(
                info_frame, text="",
                font=font.Font(family="Segoe UI", size=22, weight="bold"),
                fg=self.text_dim, bg=self.bg_panel
            )
            self.status_banner_label.pack(pady=12)
        else:
            self.status_banner_label = tk.Label(
                info_frame, text=text, font=self.data_font,
                fg=self.text_dim, bg=self.bg_panel
            )
            self.status_banner_label.pack(pady=10)

        tk.Frame(info_frame, bg=self.separator_color, height=1).pack(fill=tk.X, side=tk.BOTTOM)
        return info_frame

    def _update_status_banner(self):
        if not self.is_main_screen:
            return
        if not self.status_banner_label or not self.status_banner_label.winfo_exists():
            return
        current_lesson, next_lesson, _ = self.get_current_lesson_info()
        if current_lesson is not None:
            start_time, end_time = self.lesson_times[current_lesson]
            text = f"●  ИДЁТ УРОК №{current_lesson + 1}  •  {start_time} — {end_time}"
            color = self.status_ok
        elif next_lesson is not None:
            start_time, _ = self.lesson_times[next_lesson]
            text = f"●  ПЕРЕМЕНА  •  следующий урок в {start_time}"
            color = self.accent_amber
        else:
            text = "●  УЧЕБНЫЙ ДЕНЬ ЗАВЕРШЁН"
            color = self.text_dim
        self.status_banner_label.config(text=text, fg=color)

    def create_footer(self, text):
        info_frame = tk.Frame(self.root, bg=self.bg_panel)
        info_frame.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Frame(info_frame, bg=self.separator_color, height=1).pack(fill=tk.X, side=tk.TOP)
        self.footer_label = tk.Label(info_frame, text=text, font=self.small_font,
                                     fg=self.text_dim, bg=self.bg_panel)
        self.footer_label.pack(pady=8)
        return info_frame

    def create_navigation_buttons(self, buttons_config):
        button_frame = tk.Frame(self.root, bg=self.bg_color)
        button_frame.pack(fill=tk.X, padx=30, pady=14)

        left_items = []
        right_items = []

        for item in buttons_config:
            if len(item) == 2:
                text, command = item
                opts = {}
            else:
                text, command, opts = item
            if opts.get('side') == 'right':
                right_items.append((text, command, opts))
            else:
                left_items.append((text, command, opts))

        for text, command, opts in left_items:
            if text == "SEP":
                sep = tk.Frame(button_frame, bg=self.separator_color, width=1, height=36)
                sep.pack(side=tk.LEFT, padx=14)
                sep.pack_propagate(False)
                continue
            btn = self._make_chip_button(
                button_frame, text, command,
                active=opts.get('active', False),
                disabled=opts.get('disabled', False),
            )
            btn.pack(side=tk.LEFT, padx=6)

        for text, command, opts in reversed(right_items):
            btn = self._make_chip_button(
                button_frame, text, command,
                active=opts.get('active', False),
                disabled=opts.get('disabled', False),
            )
            btn.pack(side=tk.RIGHT, padx=6)

        return button_frame

    def create_day_navigation_buttons(self):
        day_frame = tk.Frame(self.root, bg=self.bg_color)
        day_frame.pack(fill=tk.X, padx=30, pady=(0, 6))
        dict_day = {"ПОНЕДЕЛЬНИК": "ПН", "ВТОРНИК": "ВТ", "СРЕДА": "СР",
                    "ЧЕТВЕРГ": "ЧТ", "ПЯТНИЦА": "ПТ", "СУББОТА": "СБ"}
        for i, day in enumerate(self.days_of_week[:len(self.days_of_week) - 1]):
            active = (i == self.current_day_index)
            btn = self._make_chip_button(
                day_frame, dict_day[day],
                command=lambda idx=i: self.set_day_and_refresh(idx),
                active=active
            )
            btn.pack(side=tk.LEFT, padx=4)
        return day_frame

    def set_day_and_refresh(self, day_index):
        self.current_day_index = day_index
        self.show_full_schedule()

    def create_group_navigation_buttons(self):
        group_frame = tk.Frame(self.root, bg=self.bg_color)
        group_frame.pack(fill=tk.X, padx=30, pady=(0, 12))
        for i, group in enumerate(self.class_groups):
            active = (i == self.current_group_index)
            btn = self._make_chip_button(
                group_frame, group['name'],
                command=lambda idx=i: self.set_group_and_refresh(idx),
                active=active
            )
            btn.pack(side=tk.LEFT, padx=4)
        return group_frame

    def set_group_and_refresh(self, group_index):
        self.current_group_index = group_index
        self.show_full_schedule()

    def update_clock(self):
        try:
            current_time = self.get_time_now().strftime("%H:%M:%S")
            if hasattr(self, 'clock_label') and self.clock_label.winfo_exists():
                self.clock_label.config(text=current_time)
                new_current, new_next, _ = self.get_current_lesson_info()
                self._update_status_banner()
                if self._last_lesson_index is None:
                    self._last_lesson_index = new_current
                    self._last_next_index = new_next
                elif new_current != self._last_lesson_index or new_next != self._last_next_index:
                    self._last_lesson_index = new_current
                    self._last_next_index = new_next
                    self.current_classes_page = 0
                    self.show_all_classes_schedule()
                    return
                self.clock_job = self.root.after(1000, self.update_clock)
        except Exception as e:
            print(f"[Clock Error] {e}")

    def get_current_lesson_info(self):
        now = self.get_time_now()
        current_lesson = None
        next_lesson = None
        is_break = True
        for i, (start_time, end_time) in enumerate(self.lesson_times):
            start_dt = datetime.strptime(start_time, "%H:%M")
            end_dt = datetime.strptime(end_time, "%H:%M")
            if start_dt.time() <= now.time() <= end_dt.time():
                current_lesson = i
                is_break = False
                break
            elif now.time() < start_dt.time():
                next_lesson = i
                is_break = True
                break
        if current_lesson is None and next_lesson is None:
            is_break = True
        return current_lesson, next_lesson, is_break

    def _get_status_text(self):
        current_lesson, next_lesson, _ = self.get_current_lesson_info()
        if current_lesson is not None:
            start_time, end_time = self.lesson_times[current_lesson]
            return f"Сейчас идёт урок ({start_time}-{end_time})"
        elif next_lesson is not None:
            start_time, end_time = self.lesson_times[next_lesson]
            return f"Сейчас перемена, следующий урок в {start_time}"
        return "Учебный день завершён"

    # ---------- ГЛАВНЫЙ ЭКРАН ----------
    def show_all_classes_schedule(self):
        self.is_main_screen = True
        self._current_screen = 'main'
        self.reset_idle_timer()
        self.clear_window()
        self.create_header("✈  ТЕКУЩИЕ УРОКИ — ВСЕ КЛАССЫ  ✈")
        self.create_status_bar()
        self._update_status_banner()

        if not self.rasp_wth_changes:
            self.create_status_bar("Нет данных для отображения (проверьте подключение к серверу)")
            self.create_navigation_buttons(
                self._get_nav_trio('main') + [
                    ("ВЫХОД", self.root.quit, {'side': 'right'}),
                ]
            )
            return

        current_day = self.day_today
        if current_day not in self.rasp_wth_changes:
            self.create_status_bar(f"Нет расписания на {current_day}")
            self.create_navigation_buttons(
                self._get_nav_trio('main') + [
                    ("ВЫХОД", self.root.quit, {'side': 'right'}),
                ]
            )
            return

        day_schedule = self.rasp_wth_changes[current_day]
        current_lesson, next_lesson, _ = self.get_current_lesson_info()
        lesson_to_show = current_lesson if current_lesson is not None else next_lesson

        container = tk.Frame(self.root, bg=self.bg_color)
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0, 12))

        canvas = tk.Canvas(container, bg=self.bg_color, highlightthickness=0)
        table_frame = tk.Frame(canvas, bg=self.bg_color)

        table_frame.bind("<Configure>",
                         lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        table_window = canvas.create_window((0, 0), window=table_frame, anchor="nw")

        def _stretch_table(event):
            canvas.itemconfig(table_window, width=event.width)
        canvas.bind("<Configure>", _stretch_table)

        canvas.pack(fill="both", expand=True)

        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        headers = ["КЛАСС", "№ УРОКА", "ВРЕМЯ", "ПРЕДМЕТ", "КАБИНЕТ", "СТАТУС"]
        header_frame = tk.Frame(table_frame, bg=self.bg_color)
        header_frame.pack(fill=tk.X)

        for i in range(len(headers)):
            header_frame.grid_columnconfigure(i, weight=1, uniform="cols")

        for i, h in enumerate(headers):
            tk.Label(header_frame, text=h, font=self.header_font,
                     fg=self.accent_amber, bg=self.bg_color,
                     padx=10, pady=16,
                     anchor="center", justify="center").grid(
                row=0, column=i, sticky="nsew")

        tk.Frame(table_frame, bg=self.accent_amber, height=2).pack(fill=tk.X)

        self.rows_container = tk.Frame(table_frame, bg=self.bg_color)
        self.rows_container.pack(fill=tk.BOTH, expand=True)

        rows, classes_with_lesson, total_page = self._get_page_rows_data(day_schedule, lesson_to_show)
        self.rows_container.configure(height=len(rows) * self.row_height_px)
        self.rows_container.pack_propagate(False)

        self.table_rows = []
        for i, row_data in enumerate(rows):
            self.table_rows.append(self._create_row_frame(self.rows_container, row_data, i))
        self.current_page_data = rows

        status_text = self._get_status_text()
        self.page_info = {
            "current": self.current_classes_page + 1,
            "total": total_page,
            "classes_count": len(classes_with_lesson),
            "day": current_day,
            "status_text": status_text
        }

        self.create_footer(
            f"Статус: {status_text}  •  Страница: {self.current_classes_page+1}/{total_page}  "
            f"•  Классов с уроком: {len(classes_with_lesson)}  •  День: {current_day}  "
            f"•  Кликните на класс, чтобы открыть его расписание"
        )

        pages_disabled = total_page <= 1
        buttons = [
            ("◀  СТРАНИЦА", self.prev_classes_page, {'disabled': pages_disabled}),
            ("СТРАНИЦА  ▶", self.next_classes_page_manual, {'disabled': pages_disabled}),
            ("SEP", None),
            ("ОБНОВИТЬ", self.refresh_current),
            ("SEP", None),
        ]
        buttons += self._get_nav_trio('main')
        buttons.append(("ВЫХОД", self.root.quit, {'side': 'right'}))
        self.create_navigation_buttons(buttons)

        self.start_auto_flip()

    # ---------- РАСПИСАНИЕ КЛАССА ----------
    def show_class_schedule(self, class_name):
        self.is_main_screen = False
        self._current_screen = 'class'
        self.clear_window()
        self.current_class = class_name
        self.create_header(f"✈  РАСПИСАНИЕ КЛАССА {class_name}  ✈")

        if not self.rasp_wth_changes or self.day_today not in self.rasp_wth_changes:
            self.create_status_bar("Нет данных для отображения")
            buttons = [
                ("ОБНОВИТЬ", self.refresh_current),
                ("SEP", None),
            ]
            buttons += self._get_nav_trio('class')
            buttons.append(("ВЫХОД", self.root.quit, {'side': 'right'}))
            self.create_navigation_buttons(buttons)
            return
        rasp = self.rasp_wth_changes[self.day_today]
        self.create_status_bar(f"Расписание класса {class_name} на текущий день")

        table_frame = tk.Frame(self.root, bg=self.bg_color)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0, 15))

        headers = ["№ УРОКА", "ВРЕМЯ", "ПРЕДМЕТ", "КЛАСС", "КАБИНЕТ", "СТАТУС"]
        for i, h in enumerate(headers):
            tk.Label(table_frame, text=h, font=self.header_font,
                     fg=self.accent_amber, bg=self.bg_color, padx=20, pady=16,
                     anchor="center").grid(row=0, column=i, sticky='nsew')

        schedule_to_show = []
        if class_name in rasp.keys():
            schedule_to_show = rasp[class_name]
            if not self.show_all_lessons:
                current_time = self.get_time_now().time()
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

            for row_idx, row_data in enumerate(schedule_to_show, 1):
                is_cancelled = row_data[6] == "ОТМЕНЕНО"
                display_data = (row_data[0], row_data[1], row_data[2], row_data[3], row_data[4], row_data[6])
                row_bg = self.bg_row_even if row_idx % 2 == 1 else self.bg_row_odd

                for col_idx, cell_data in enumerate(display_data):
                    if is_cancelled:
                        bg_color = self.cancelled_bg
                        if col_idx == 5:
                            fg_color = self.cancelled_fg
                        elif col_idx in (0, 1):
                            fg_color = self.accent_cyan_bright
                        else:
                            fg_color = self.text_dim
                    else:
                        bg_color = row_bg
                        if col_idx == 5:
                            if cell_data == "ИЗМЕНЕНО":
                                fg_color = self.status_warn
                            elif cell_data == "ОТМЕНЕНО":
                                fg_color = self.status_cancel
                            else:
                                fg_color = self.status_ok
                        elif col_idx == 0:
                            fg_color = self.accent_amber_bright
                        elif col_idx == 1:
                            fg_color = self.accent_amber
                        elif col_idx == 3:
                            fg_color = self.accent_cyan_bright
                        elif col_idx == 4:
                            fg_color = self.text_color
                        else:
                            fg_color = self.text_color

                    cell = tk.Frame(table_frame, bg=bg_color, height=64)
                    cell.grid(row=row_idx, column=col_idx, sticky='nsew')
                    cell.grid_propagate(False)
                    cell.grid_rowconfigure(0, weight=1)
                    cell.grid_columnconfigure(0, weight=1)

                    cell_font = self.data_mono if col_idx in (0, 1, 4) else self.data_font
                    tk.Label(cell, text=cell_data, font=cell_font, fg=fg_color,
                             bg=bg_color, anchor="center", justify="center").grid(
                        row=0, column=0, sticky='nsew', padx=15, pady=4)

                sep = tk.Frame(table_frame, bg=self.separator_color, height=1)
                sep.grid(row=row_idx, column=0, columnspan=len(headers), sticky='sew')

        self.reset_idle_timer()
        mode_text = "ВСЕ УРОКИ" if self.show_all_lessons else "ТОЛЬКО БУДУЩИЕ"
        self.create_footer(f"Класс: {class_name}  •  Режим: {mode_text}  •  Уроков: {len(schedule_to_show)}")

        toggle_text = "ТОЛЬКО БУДУЩИЕ" if self.show_all_lessons else "ВСЕ УРОКИ"
        buttons = [
            ("ОБНОВИТЬ", self.refresh_current),
            (toggle_text, self.toggle_lesson_mode),
            ("SEP", None),
        ]
        buttons += self._get_nav_trio('class')
        buttons.append(("ВЫХОД", self.root.quit, {'side': 'right'}))
        self.create_navigation_buttons(buttons)

        for i in range(len(headers)):
            table_frame.columnconfigure(i, weight=1, uniform="cls")

    # ---------- ВЫБОР КЛАССА ----------
    def show_class_selection(self):
        self.is_main_screen = False
        self._current_screen = 'selection'
        self.clear_window()
        self.create_header("✈  ВЫБОР КЛАССА  ✈")
        self.create_status_bar("Выберите параллель, затем класс для просмотра расписания")

        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0, 15))

        # --- Левая панель: параллели ---
        left_panel = tk.Frame(main_frame, bg=self.bg_panel, width=340)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        left_panel.pack_propagate(False)

        tk.Label(left_panel, text="ПАРАЛЛЕЛИ",
                 font=font.Font(family="Segoe UI", size=14, weight="bold"),
                 fg=self.text_dim, bg=self.bg_panel).pack(pady=(20, 12), anchor="w", padx=24)

        self.left_buttons_frame = tk.Frame(left_panel, bg=self.bg_panel)
        self.left_buttons_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        # --- Вертикальный разделитель ---
        tk.Frame(main_frame, bg=self.separator_color, width=1).pack(side=tk.LEFT, fill=tk.Y)

        # --- Правая панель ---
        self.right_panel = tk.Frame(main_frame, bg=self.bg_color)
        self.right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.right_title = tk.Label(self.right_panel, text="",
                                    font=font.Font(family="Segoe UI", size=24, weight="bold"),
                                    fg=self.accent_amber, bg=self.bg_color,
                                    anchor="w")
        self.right_title.pack(pady=(20, 16), padx=30, anchor="w")

        self.right_classes_frame = tk.Frame(self.right_panel, bg=self.bg_color)
        self.right_classes_frame.pack(fill=tk.X, padx=30)

        self.choice_font = font.Font(family="Segoe UI", size=18, weight="bold")
        self.parallel_font = font.Font(family="Segoe UI", size=17, weight="bold")

        if self.class_groups:
            self.on_grade_selected(self.class_groups[0])

        self.create_footer(f"Всего доступных классов: {len(self.all_classes)}")
        buttons = [
            ("ОБНОВИТЬ", self.refresh_current),
            ("SEP", None),
        ]
        buttons += self._get_nav_trio('selection')
        buttons.append(("ВЫХОД", self.root.quit, {'side': 'right'}))
        self.create_navigation_buttons(buttons)
        self.reset_idle_timer()

    def on_grade_selected(self, group):
        self.right_title.config(text=f"{group['name']}")

        # --- Левая колонка: параллели в один столбец ---
        for child in self.left_buttons_frame.winfo_children():
            child.destroy()

        for g in self.class_groups:
            active = (g['name'] == group['name'])
            btn = self._make_chip_button(
                self.left_buttons_frame, g['name'],
                command=lambda gg=g: self.on_grade_selected(gg),
                active=active, font_=self.parallel_font
            )
            btn.pack(fill=tk.X, pady=4, ipady=4)

        # --- Правая колонка: классы ---
        for widget in self.right_classes_frame.winfo_children():
            widget.destroy()

        cols = 5
        row, col = 0, 0
        for class_name in group['classes']:
            btn = self._make_chip_button(
                self.right_classes_frame, class_name,
                command=lambda c=class_name: self.show_class_schedule(c),
                font_=self.choice_font
            )
            btn.grid(row=row, column=col, padx=6, pady=6, sticky='nsew', ipadx=14, ipady=10)
            col += 1
            if col >= cols:
                col = 0
                row += 1
        for i in range(cols):
            self.right_classes_frame.grid_columnconfigure(i, weight=1, uniform="cls")

        # --- Карточка "СЕЙЧАС В ПАРАЛЛЕЛИ" ---
        self._render_parallel_current_card(group)

    def _render_parallel_current_card(self, group):
        """Карточка с текущим уроком каждого класса параллели."""
        if self._parallel_card and self._parallel_card.winfo_exists():
            self._parallel_card.destroy()

        card = tk.Frame(self.right_panel, bg=self.bg_panel)
        card.pack(fill=tk.BOTH, expand=True, padx=30, pady=(24, 20))
        self._parallel_card = card

        # --- Заголовок ---
        tk.Label(card, text="СЕЙЧАС В ПАРАЛЛЕЛИ",
                 font=font.Font(family="Segoe UI", size=13, weight="bold"),
                 fg=self.text_dim, bg=self.bg_panel).pack(anchor="w", padx=20, pady=(16, 10))

        # --- Строка статуса ---
        current_lesson, next_lesson, _ = self.get_current_lesson_info()
        if current_lesson is not None:
            start, end = self.lesson_times[current_lesson]
            status_text = f"●  Идёт урок №{current_lesson + 1}  •  {start} — {end}"
            status_color = self.status_ok
        elif next_lesson is not None:
            start, _ = self.lesson_times[next_lesson]
            status_text = f"●  Перемена  •  следующий урок в {start}"
            status_color = self.accent_amber
        else:
            status_text = "●  Учебный день завершён"
            status_color = self.text_dim

        tk.Label(card, text=status_text,
                 font=font.Font(family="Segoe UI", size=18, weight="bold"),
                 fg=status_color, bg=self.bg_panel).pack(anchor="w", padx=20, pady=(0, 12))

        # --- Список классов и их текущих уроков ---
        day_schedule = self.rasp_wth_changes.get(self.day_today, {})

        list_frame = tk.Frame(card, bg=self.bg_panel)
        list_frame.pack(fill=tk.X, padx=20, pady=(0, 16))

        if current_lesson is None:
            tk.Label(list_frame,
                     text="Сейчас уроков нет — можно посмотреть всё расписание параллели.",
                     font=self.data_font, fg=self.text_dim, bg=self.bg_panel).pack(anchor="w")
        else:
            for class_name in group['classes']:
                row = tk.Frame(list_frame, bg=self.bg_panel)
                row.pack(fill=tk.X, pady=3)

                tk.Label(row, text=class_name, font=self.data_mono,
                         fg=self.accent_cyan_bright, bg=self.bg_panel,
                         width=6, anchor="w").pack(side=tk.LEFT)

                if class_name in day_schedule and current_lesson < len(day_schedule[class_name]):
                    lesson = day_schedule[class_name][current_lesson]
                    subject = lesson[2]
                    room = lesson[4]
                    status = lesson[6]

                    if status == "ОТМЕНЕНО":
                        subj_color = self.cancelled_fg
                    elif status == "ИЗМЕНЕНО":
                        subj_color = self.status_warn
                    else:
                        subj_color = self.text_color

                    tk.Label(row, text=subject, font=self.data_font,
                             fg=subj_color, bg=self.bg_panel,
                             anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 0))

                    tk.Label(row, text=f"каб. {room}", font=self.data_mono,
                             fg=self.text_dim, bg=self.bg_panel,
                             anchor="e").pack(side=tk.RIGHT)
                else:
                    tk.Label(row, text="—  нет урока  —", font=self.data_font,
                             fg=self.text_dim, bg=self.bg_panel,
                             anchor="w").pack(side=tk.LEFT, padx=(12, 0))

        # --- Кнопка-шорткат ---
        shortcut_row = tk.Frame(card, bg=self.bg_panel)
        shortcut_row.pack(fill=tk.X, padx=20, pady=(4, 16))

        self._make_chip_button(
            shortcut_row,
            f"-> Общее расписание для {group['name'].lower().replace('е', '-x').replace('классы', 'классов')}",
            command=lambda g=group: self._open_full_for_group(g),
            font_=self.button_font
        ).pack(side=tk.LEFT)

    def _open_full_for_group(self, group):
        """Прыжок в 'Всё расписание' с уже выбранной параллелью."""
        try:
            self.current_group_index = self.class_groups.index(group)
        except ValueError:
            self.current_group_index = 0
        self.show_full_schedule()

    # ---------- ВСЁ РАСПИСАНИЕ ----------
    def show_full_schedule(self):
        self.is_main_screen = False
        self._current_screen = 'full'
        self.clear_window()

        if not self.class_groups:
            self.create_status_bar("Нет данных для отображения")
            buttons = self._get_nav_trio('full') + [
                ("ВЫХОД", self.root.quit, {'side': 'right'}),
            ]
            self.create_navigation_buttons(buttons)
            return

        if self.current_group_index >= len(self.class_groups):
            self.current_group_index = 0

        if not self.rasp_wth_changes:
            self.create_status_bar("Нет данных для отображения")
            buttons = self._get_nav_trio('full') + [
                ("ВЫХОД", self.root.quit, {'side': 'right'}),
            ]
            self.create_navigation_buttons(buttons)
            return

        current_group = self.class_groups[self.current_group_index]
        current_day = self.days_of_week[self.current_day_index]

        if current_day not in self.rasp_wth_changes:
            self.create_status_bar(f"Нет расписания на {current_day}")
            buttons = self._get_nav_trio('full') + [
                ("ВЫХОД", self.root.quit, {'side': 'right'}),
            ]
            self.create_navigation_buttons(buttons)
            return

        day_schedule = self.rasp_wth_changes[current_day]
        self.create_header(f"✈  РАСПИСАНИЕ — {current_day}  ✈")
        self.create_status_bar(f"{current_day}  •  {current_group['name']}")
        self.create_day_navigation_buttons()
        self.create_group_navigation_buttons()

        max_lessons = 0
        for class_name in current_group['classes']:
            if class_name in day_schedule:
                max_lessons = max(max_lessons, len(day_schedule[class_name]))

        if max_lessons == 0:
            self.create_status_bar("Нет уроков для отображения")
            buttons = self._get_nav_trio('full') + [
                ("ВЫХОД", self.root.quit, {'side': 'right'}),
            ]
            self.create_navigation_buttons(buttons)
            return

        container = tk.Frame(self.root, bg=self.bg_color)
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0, 12))

        canvas = tk.Canvas(container, bg=self.bg_color, highlightthickness=0)
        table_frame = tk.Frame(canvas, bg=self.bg_color)
        table_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        tw = canvas.create_window((0, 0), window=table_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(tw, width=e.width))
        canvas.pack(fill="both", expand=True)

        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        headers = ["КЛАСС"] + [f"УРОК {i}" for i in range(1, max_lessons + 1)]

        for i, h in enumerate(headers):
            tk.Label(table_frame, text=h, font=self.header_font, fg=self.accent_amber,
                     bg=self.bg_color, padx=15, pady=16,
                     anchor="center").grid(row=0, column=i, sticky='nsew')

        ROW_HEIGHT = 95
        row_idx = 1
        for class_name in current_group['classes']:
            if class_name not in day_schedule:
                continue
            rasp_cur_class = day_schedule[class_name]
            row_data = [class_name]
            for lesson_num in range(1, max_lessons + 1):
                if (lesson_num - 1) < len(rasp_cur_class):
                    lesson_info = f"{rasp_cur_class[lesson_num-1][2]}\n{rasp_cur_class[lesson_num-1][4]}"
                else:
                    lesson_info = ""
                row_data.append(lesson_info)

            row_bg = self.bg_row_even if (row_idx % 2 == 1) else self.bg_row_odd

            for col_idx, cell_data in enumerate(row_data):
                if col_idx == 0:
                    bg_color = self.bg_row_first_col
                    fg_color = self.accent_cyan_bright
                else:
                    bg_color = row_bg
                    fg_color = self.text_color

                cell = tk.Frame(table_frame, bg=bg_color, height=ROW_HEIGHT)
                cell.grid(row=row_idx, column=col_idx, sticky='nsew')
                cell.grid_propagate(False)
                cell.grid_rowconfigure(0, weight=1)
                cell.grid_columnconfigure(0, weight=1)

                if col_idx == 0:
                    lbl = self._make_class_cell(cell, cell_data, bg_color, fg_color, self.data_font)
                    lbl.grid(row=0, column=0, sticky='nsew', padx=15, pady=6)
                else:
                    tk.Label(cell, text=cell_data, font=self.data_font, fg=fg_color,
                             bg=bg_color, anchor="center", justify="center").grid(
                        row=0, column=0, sticky='nsew', padx=15, pady=6)

            sep = tk.Frame(table_frame, bg=self.separator_color, height=1)
            sep.grid(row=row_idx, column=0, columnspan=len(headers), sticky='sew')

            row_idx += 1

        table_frame.columnconfigure(0, weight=0, minsize=220)
        for i in range(1, len(headers)):
            table_frame.columnconfigure(i, weight=1, uniform="full")

        group_info = f"{self.current_group_index + 1}/{len(self.class_groups)}"
        day_info = f"{self.current_day_index + 1}/{len(self.days_of_week)}"
        self.create_footer(f"День: {current_day}  •  Группа: {current_group['name']}  "
                           f"•  Страница дня: {day_info}  •  Страница группы: {group_info}  "
                           f"•  Кликните на класс, чтобы открыть его расписание")

        buttons = [
            ("ОБНОВИТЬ", self.refresh_current),
            ("SEP", None),
        ]
        buttons += self._get_nav_trio('full')
        buttons.append(("ВЫХОД", self.root.quit, {'side': 'right'}))
        self.create_navigation_buttons(buttons)

        self.reset_idle_timer()

    def prev_group(self):
        if self.current_group_index > 0:
            self.current_group_index -= 1
            self.show_full_schedule()

    def next_group(self):
        if self.current_group_index < len(self.class_groups) - 1:
            self.current_group_index += 1
            self.show_full_schedule()

    # ---------- ОБНОВЛЕНИЕ ----------
    def refresh_all_classes(self):
        self._fetch_and_apply()
        self.show_all_classes_schedule()

    def refresh_class_schedule(self):
        self._fetch_and_apply()
        if self.current_class:
            self.show_class_schedule(self.current_class)

    def toggle_lesson_mode(self):
        self.show_all_lessons = not self.show_all_lessons
        if self.current_class:
            self.show_class_schedule(self.current_class)

    def setup_idle_timer(self):
        self.root.bind_all('<Key>', self.reset_idle_timer)
        self.root.bind_all('<Button>', self.reset_idle_timer)
        self.root.bind_all('<Motion>', self.reset_idle_timer)
        self.root.bind_all('<Enter>', self.reset_idle_timer)
        self.root.bind_all('<FocusIn>', self.reset_idle_timer)
        self.reset_idle_timer()

    def reset_idle_timer(self, event=None):
        if self.idle_timer_id:
            self.root.after_cancel(self.idle_timer_id)
            self.idle_timer_id = None
        self.idle_timer_id = self.root.after(300000, self.on_idle_timeout)

    def on_idle_timeout(self):
        self.idle_timer_id = None
        if not self.is_main_screen:
            self.show_all_classes_schedule()


if __name__ == "__main__":
    app = App()