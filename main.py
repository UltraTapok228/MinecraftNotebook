import os
import io
import sys
import pygame
from docx import Document
from docx.shared import Pt

def resource_path(relative_path):
    """ Получает абсолютный путь к ресурсам, работает для dev-режима и для PyInstaller """
    try:
        # PyInstaller создает временную папку _MEIPASS
        base_path = sys.getenv('_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# Инициализация Pygame и удержания клавиш
pygame.init()
pygame.key.set_repeat(400, 35)

# Настройки оригинального спрайта
SPRITE_W = 146
SPRITE_H = 180

SCALE = 3 
PAGE_W = SPRITE_W * SCALE
PAGE_H = SPRITE_H * SCALE

# Окно увеличено по высоте для нижней кнопки
WINDOW_WIDTH = (PAGE_W * 2) + 60  
WINDOW_HEIGHT = PAGE_H + 110
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Minecraft Notebook - Full Version")

pygame.scrap.init() 

# Цвета
TEXT_COLOR = (44, 34, 16)      
BACKGROUND_COLOR = (30, 30, 30)
SELECTION_COLOR = (173, 216, 230, 150) 
CURSOR_COLOR = (0, 180, 0)  # Зеленый курсор

# --- ИНИЦИАЛИЗАЦИЯ ШРИФТА ---
try:
    # 1. Загружаем основной шрифт для текста книги (размер 15)
    with open(resource_path("minecraft.ttf"), "rb") as f:
        font_data_main = io.BytesIO(f.read())
    font = pygame.font.Font(font_data_main, 16)
    
    # 2. Создаем ПОЛНОСТЬЮ ОТДЕЛЬНЫЙ поток памяти для шрифта кнопок (размер 11)
    with open(resource_path("minecraft.ttf"), "rb") as f:
        font_data_btn = io.BytesIO(f.read())
    page_num_font = pygame.font.Font(font_data_btn, 16)  
    
except Exception as e:
    print(f"Ошибка загрузки шрифта: {e}. Используется стандартный системный шрифт.")
    font = pygame.font.SysFont("Courier New", 15, bold=True)
    page_num_font = pygame.font.SysFont("Courier New", 13, bold=True)

# --- ЗАГРУЗКА И СБОРКА ИНТЕРФЕЙСА ---
orig_page_img = pygame.image.load(resource_path("img/book.png")).convert_alpha()
orig_page_img = pygame.transform.scale(orig_page_img, (SPRITE_W, SPRITE_H))

left_page_img = pygame.transform.scale(orig_page_img, (PAGE_W, PAGE_H))
right_page_img = pygame.transform.flip(left_page_img, True, False) 

BTN_FORWARD = pygame.image.load(resource_path("img/page_forward_highlighted.png")).convert_alpha()
BTN_BACKWARD = pygame.image.load(resource_path("img/page_backward_highlighted.png")).convert_alpha()
BTN_FORWARD = pygame.transform.scale(BTN_FORWARD, (BTN_FORWARD.get_width() * 2, BTN_FORWARD.get_height() * 2))
BTN_BACKWARD = pygame.transform.scale(BTN_BACKWARD, (BTN_BACKWARD.get_width() * 2, BTN_BACKWARD.get_height() * 2))

left_rect = left_page_img.get_rect(topleft=(30, 30))
right_rect = right_page_img.get_rect(topleft=(left_rect.right, 30))

PADDING_X = 25 * SCALE
PADDING_Y = 22 * SCALE
TEXT_AREA_WIDTH = PAGE_W - (PADDING_X * 2) + 15
MAX_LINES_PER_PAGE = 12
LINE_SPACING = 24

btn_back_rect = BTN_BACKWARD.get_rect(left=left_rect.left + 30, bottom=left_rect.bottom - 20)
btn_forward_rect = BTN_FORWARD.get_rect(right=right_rect.right - 30, bottom=right_rect.bottom - 20)

# Загрузка ресурсов экрана подписания
SIGN_BG_IMG = pygame.image.load(resource_path("img/book_edit.png")).convert_alpha() 
SIGN_BG_IMG = pygame.transform.scale(SIGN_BG_IMG, (146 * SCALE, 180 * SCALE))
SIGN_BG_IMG.set_colorkey([0, 255, 0])

BTN_NORMAL = pygame.image.load(resource_path("img/button.png")).convert_alpha()     
BTN_HOVER = pygame.image.load(resource_path("img/button_highlighted.png")).convert_alpha()       

btn_w, btn_h = BTN_NORMAL.get_width() * SCALE, BTN_NORMAL.get_height() * SCALE
BTN_NORMAL = pygame.transform.scale(BTN_NORMAL, (btn_w, btn_h))
BTN_HOVER = pygame.transform.scale(BTN_HOVER, (btn_w, btn_h))

btn_main_rect = BTN_NORMAL.get_rect(centerx=WINDOW_WIDTH // 2, top=left_rect.bottom + 15)

sign_bg_rect = SIGN_BG_IMG.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 30))
title_input_rect = pygame.Rect(sign_bg_rect.left + 30 * SCALE, sign_bg_rect.top + 43 * SCALE, 88 * SCALE, 10 * SCALE)
author_input_rect = pygame.Rect(sign_bg_rect.left + 37 * SCALE, sign_bg_rect.top + 57 * SCALE, 52 * SCALE, 10 * SCALE)

btn_save_rect = BTN_NORMAL.get_rect(centerx=sign_bg_rect.centerx, top=sign_bg_rect.bottom + 15)

# Состояния
app_state = "EDIT"  
active_field = "TITLE" 
book_title = ""
book_author = ""

# --- ЛОГИКА ТЕКСТА ---
raw_text = ""
pages = []
current_spread_idx = 0  
is_all_selected = False

# Таймер мигания курсора
cursor_visible = True
CURSOR_BLINK_EVENT = pygame.USEREVENT + 1
pygame.time.set_timer(CURSOR_BLINK_EVENT, 500)

def paginate_text(text, font, max_width, max_lines):
    if not text:
        return [[""]]
        
    # Сначала разбиваем текст на абзацы по нажатиям Enter (\n)
    paragraphs = text.split('\n')
    all_pages = []
    current_page_lines = []

    for paragraph in paragraphs:
        # Если абзац пустой (игрок нажал Enter на пустой строке), добавляем пустую строку
        if not paragraph:
            current_page_lines.append("")
            if len(current_page_lines) >= max_lines:
                all_pages.append(current_page_lines)
                current_page_lines = []
            continue

        words = paragraph.split(' ')
        current_line = ""

        for word in words:
            test_line = current_line + " " + word if current_line else word
            width, _ = font.size(test_line)

            if width <= max_width:
                current_line = test_line
            else:
                current_page_lines.append(current_line)
                current_line = word
                if len(current_page_lines) >= max_lines:
                    all_pages.append(current_page_lines)
                    current_page_lines = []

        if current_line:
            current_page_lines.append(current_line)
            if len(current_page_lines) >= max_lines:
                all_pages.append(current_page_lines)
                current_page_lines = []

    if current_page_lines:
        all_pages.append(current_page_lines)

    # Гарантируем четное число страниц для книжного разворота
    if len(all_pages) % 2 != 0:
        all_pages.append([])
    return all_pages if all_pages else [[""], []]


def trigger_save_dialog():
    """Открывает проводник Windows и экспортирует файл в формат Word, сохраняя автора в свойства документа"""
    import tkinter as tk
    from tkinter import filedialog
    
    root = tk.Tk()
    root.withdraw()
    
    file_path = filedialog.asksaveasfilename(
        initialfile=f"{book_title if book_title else 'minecraft_book'}.docx",
        defaultextension=".docx",
        filetypes=[("Word Document", "*.docx")]
    )
    
    if file_path:
        doc = Document()
        style = doc.styles['Normal']
        style.font.name = 'Times New Roman'
        style.font.size = Pt(16)
        
        # ЗАПИСЬ В СВОЙСТВА ФАЙЛА (Метаданные)
        core_properties = doc.core_properties
        core_properties.title = book_title if book_title else "Без названия"
        core_properties.author = book_author if book_author else "Неизвестен"
        
        # Фильтруем пустые технические страницы разворотов с конца книги перед сохранением
        clean_pages = [p for p in pages if any(line.strip() for line in p)]
        if not clean_pages:
            clean_pages = [[""]]

        # Экспортируем страницы книги (теперь первая страница сразу содержит текст блокнота)
        for idx, page_lines in enumerate(clean_pages):
            doc.add_paragraph("\n".join(page_lines))
            if idx < len(clean_pages) - 1:
                doc.add_page_break()
                
        doc.save(file_path)
        return True
    return False


pages = paginate_text(raw_text, font, TEXT_AREA_WIDTH, MAX_LINES_PER_PAGE)
# --- ИГРОВОЙ ЦИКЛ ---
clock = pygame.time.Clock()

while True:
    screen.fill(BACKGROUND_COLOR)
    mouse_pos = pygame.mouse.get_pos()  

    if app_state == "EDIT":
        # 1. ОТРИСОВКА ОБЫЧНОГО БЛОКНОТА
        screen.blit(left_page_img, left_rect)
        screen.blit(right_page_img, right_rect)

        left_page_no = current_spread_idx
        right_page_no = current_spread_idx + 1
        
        # Исправленный подсчет страниц: исключаем пустые технические листы с конца книги
        # НАДЕЖНЫЙ ПОДСЧЕТ СТРАНИЦ: убираем пустые развороты с конца книги
        actual_total_pages = len(pages)
        while actual_total_pages > 2:
            # Проверяем, пуста ли последняя пара страниц (разворот)
            if not pages[actual_total_pages - 1] and not pages[actual_total_pages - 2]:
                actual_total_pages -= 2
            else:
                break
        
        # Если мы пролистали дальше, чем посчитано (например, пишем на новом листе)
        if right_page_no + 1 > actual_total_pages:
            actual_total_pages = right_page_no + 1


        selection_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        
        last_page_with_text = len(pages) - 1
        while last_page_with_text > 0 and not pages[last_page_with_text]:
            last_page_with_text -= 1

        # Отрисовка текста: Левая страница
        if left_page_no < len(pages):
            for i, line_text in enumerate(pages[left_page_no]):
                x = left_rect.left + PADDING_X
                y = left_rect.top + PADDING_Y + i * LINE_SPACING
                if is_all_selected and line_text:
                    text_w, text_h = font.size(line_text)
                    pygame.draw.rect(selection_surface, SELECTION_COLOR, (x, y, text_w, text_h))
                text_surf = font.render(line_text, True, TEXT_COLOR)
                screen.blit(text_surf, (x, y))
                
                if left_page_no == last_page_with_text and i == len(pages[left_page_no]) - 1 and cursor_visible and not is_all_selected:
                    text_w, _ = font.size(line_text)
                    pygame.draw.rect(screen, CURSOR_COLOR, (x + text_w + 2, y + 2, 3, 16))

        # Отрисовка текста: Правая страница
        if right_page_no < len(pages):
            for i, line_text in enumerate(pages[right_page_no]):
                x = right_rect.left + PADDING_X - 10
                y = right_rect.top + PADDING_Y + i * LINE_SPACING
                if is_all_selected and line_text:
                    text_w, text_h = font.size(line_text)
                    pygame.draw.rect(selection_surface, SELECTION_COLOR, (x, y, text_w, text_h))
                text_surf = font.render(line_text, True, TEXT_COLOR)
                screen.blit(text_surf, (x, y))
                
                if right_page_no == last_page_with_text and i == len(pages[right_page_no]) - 1 and cursor_visible and not is_all_selected:
                    text_w, _ = font.size(line_text)
                    pygame.draw.rect(screen, CURSOR_COLOR, (x + text_w + 2, y + 2, 3, 16))

        if not raw_text and cursor_visible:
            pygame.draw.rect(screen, CURSOR_COLOR, (left_rect.left + PADDING_X, left_rect.top + PADDING_Y + 2, 3, 16))

        screen.blit(selection_surface, (0, 0))

        # Нумерация страниц (Исправленная логика)
        num_y_position = left_rect.bottom - 42
        left_num_str = f"{left_page_no + 1} из {actual_total_pages}"
        left_num_surf = page_num_font.render(left_num_str, True, TEXT_COLOR)
        screen.blit(left_num_surf, (left_rect.left + (PAGE_W // 2) - (left_num_surf.get_width() // 2), num_y_position))

        right_num_str = f"{right_page_no + 1} из {actual_total_pages}"
        right_num_surf = page_num_font.render(right_num_str, True, TEXT_COLOR)
        screen.blit(right_num_surf, (right_rect.left + (PAGE_W // 2) - (right_num_surf.get_width() // 2), num_y_position))

        if current_spread_idx > 0:
            screen.blit(BTN_BACKWARD, btn_back_rect)
        screen.blit(BTN_FORWARD, btn_forward_rect)

        # Кнопка под книгой
        if btn_main_rect.collidepoint(mouse_pos):
            screen.blit(BTN_HOVER, btn_main_rect)
        else:
            screen.blit(BTN_NORMAL, btn_main_rect)

        btn_text = page_num_font.render("Перейти к подписанию", True, (0, 0, 0))
        screen.blit(btn_text, btn_text.get_rect(center=btn_main_rect.center))

    elif app_state == "SIGN":
        # 2. ОТРИСОВКА ЭКРАНА ПОДПИСАНИЯ КНИГИ
        screen.blit(SIGN_BG_IMG, sign_bg_rect)

        title_surf = font.render(book_title + ("_" if active_field == "TITLE" and cursor_visible else ""), True, TEXT_COLOR)
        screen.blit(title_surf, (title_input_rect.left + 5, title_input_rect.top + 5))

        author_surf = font.render(book_author + ("_" if active_field == "AUTHOR" and cursor_visible else ""), True, TEXT_COLOR)
        screen.blit(author_surf, (author_input_rect.left + 5, author_input_rect.top + 5))

        if btn_save_rect.collidepoint(mouse_pos):
            screen.blit(BTN_HOVER, btn_save_rect)
        else:
            screen.blit(BTN_NORMAL, btn_save_rect)

        save_text_surf = page_num_font.render("Подписать и Сохранить", True, (0, 0, 0))
        screen.blit(save_text_surf, save_text_surf.get_rect(center=btn_save_rect.center))

    # --- ОБРАБОТКА СОБЫТИЙ ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        elif event.type == CURSOR_BLINK_EVENT:
            cursor_visible = not cursor_visible

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  
                if app_state == "EDIT":
                    if current_spread_idx > 0 and btn_back_rect.collidepoint(event.pos):
                        current_spread_idx -= 2
                        is_all_selected = False
                    elif btn_forward_rect.collidepoint(event.pos):
                        if current_spread_idx >= len(pages) - 2:
                            raw_text += " "
                            pages = paginate_text(raw_text, font, TEXT_AREA_WIDTH, MAX_LINES_PER_PAGE)
                        current_spread_idx += 2
                        is_all_selected = False
                    elif btn_main_rect.collidepoint(event.pos):
                        app_state = "SIGN"

                elif app_state == "SIGN":
                    if title_input_rect.collidepoint(event.pos):
                        active_field = "TITLE"
                    elif author_input_rect.collidepoint(event.pos):
                        active_field = "AUTHOR"
                    elif btn_save_rect.collidepoint(event.pos):
                        if trigger_save_dialog():
                            app_state = "EDIT"

        elif event.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()
            ctrl_pressed = mods & pygame.KMOD_CTRL

            if app_state == "EDIT":
                # Обработка комбинаций клавиш
                if ctrl_pressed and event.key == pygame.K_s:
                    app_state = "SIGN"
                    continue
                elif ctrl_pressed and event.key == pygame.K_a:
                    is_all_selected = True
                    continue 
                elif ctrl_pressed and event.key == pygame.K_c:
                    if is_all_selected and raw_text:
                        pygame.scrap.put(pygame.SCRAP_TEXT, raw_text.encode('utf-8'))
                    continue
                elif ctrl_pressed and event.key == pygame.K_x:
                    if is_all_selected and raw_text:
                        pygame.scrap.put(pygame.SCRAP_TEXT, raw_text.encode('utf-8'))
                        raw_text = ""
                        is_all_selected = False
                        pages = paginate_text(raw_text, font, TEXT_AREA_WIDTH, MAX_LINES_PER_PAGE)
                        current_spread_idx = 0
                    continue
                elif ctrl_pressed and event.key == pygame.K_v:
                    raw_clipboard = pygame.scrap.get(pygame.SCRAP_TEXT)
                    if raw_clipboard:
                        try:
                            # Убираем только нулевые байты \x00, сохраняя переносы строк \n
                            clipboard_text = raw_clipboard.decode('utf-8').replace('\x00', '')
                            if is_all_selected:
                                raw_text = clipboard_text
                                is_all_selected = False
                            else:
                                raw_text += clipboard_text
                        except Exception:
                            pass
                    pages = paginate_text(raw_text, font, TEXT_AREA_WIDTH, MAX_LINES_PER_PAGE)
                    continue


                # Пропускаем системные нажатия Ctrl, чтобы они не стирали текст
                if event.key in (pygame.K_LCTRL, pygame.K_RCTRL):
                    continue

                # Очистка выделенного контента перед вводом
                if is_all_selected:
                    if event.key == pygame.K_BACKSPACE or (event.unicode.isprintable() and not ctrl_pressed):
                        raw_text = ""
                        is_all_selected = False
                        if event.key == pygame.K_BACKSPACE:
                            pages = paginate_text(raw_text, font, TEXT_AREA_WIDTH, MAX_LINES_PER_PAGE)
                            current_spread_idx = 0
                            continue

                # Обычный ввод символов
                if event.key == pygame.K_BACKSPACE:
                    raw_text = raw_text[:-1]
                elif event.key == pygame.K_RETURN:
                    raw_text += "\n"  
                else:
                    if event.unicode.isprintable() and not ctrl_pressed:
                        raw_text += event.unicode
                
                pages = paginate_text(raw_text, font, TEXT_AREA_WIDTH, MAX_LINES_PER_PAGE)
                last_page = len(pages) - 1
                if current_spread_idx < (last_page // 2) * 2:
                    current_spread_idx = (last_page // 2) * 2

            elif app_state == "SIGN":
                if event.key == pygame.K_ESCAPE:
                    app_state = "EDIT"
                elif event.key == pygame.K_TAB:
                                        active_field = "AUTHOR" if active_field == "TITLE" else "TITLE"
                elif event.key == pygame.K_BACKSPACE:
                    if active_field == "TITLE":
                        book_title = book_title[:-1]
                    else:
                        book_author = book_author[:-1]
                elif event.key == pygame.K_RETURN:
                    if trigger_save_dialog():
                        app_state = "EDIT"
                else:
                    if event.unicode.isprintable():
                        if active_field == "TITLE" and len(book_title) < 15:
                            book_title += event.unicode
                        elif active_field == "AUTHOR" and len(book_author) < 12:
                            book_author += event.unicode

    pygame.display.flip()
    clock.tick(30)
