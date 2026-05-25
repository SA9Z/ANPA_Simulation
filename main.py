import pygame
import sys
import random
import math
import json
import os
from datetime import datetime
from tkinter import filedialog, Tk
from plotter import PlotWindow

from config import config
from simulation import Simulation
from obstacles import Obstacle
from visualization import Visualizer
from data_logger import DataLogger
from replay_controller import ReplayController
from replay_ui import ReplayUI

# Инициализация Pygame
pygame.init()

# Настройки окна (только обычное или полноэкранное)
if config.FULLSCREEN:
    screen = pygame.display.set_mode((config.WORLD_WIDTH, config.WORLD_HEIGHT), pygame.FULLSCREEN)
else:
    screen = pygame.display.set_mode((config.WORLD_WIDTH, config.WORLD_HEIGHT))

pygame.display.set_caption("Локальная навигация АНПА с событийно-временной логикой")
clock = pygame.time.Clock()

# Генерация препятствий
def generate_obstacles():
    """Генерация препятствий в каждой клетке (кроме центра)"""
    obstacles = []
    cell_size = config.CELL_SIZE
    grid_cols = config.GRID_COLS
    grid_rows = config.GRID_ROWS
    
    center_col = grid_cols // 2
    center_row = grid_rows // 2
    center_x = center_col * cell_size + cell_size // 2
    center_y = center_row * cell_size + cell_size // 2
    
    for row in range(grid_rows):
        for col in range(grid_cols):
            # Пропускаем центральную клетку (судно)
            if col == center_col and row == center_row:
                continue
            
            # Координаты клетки
            cell_x = col * cell_size
            cell_y = row * cell_size
            
            # Количество препятствий в клетке (1-3)
            num_obstacles = random.randint(1, 3)
            
            for _ in range(num_obstacles):
                obs = Obstacle.generate_random(
                    cell_x, cell_y, cell_size,
                    config.AUV_LENGTH, config.K,
                    min_radius=10, max_radius=25
                )
                obstacles.append(obs)
    
    return obstacles

# Судно в центре
ship_position = [
    (config.GRID_COLS // 2) * config.CELL_SIZE + config.CELL_SIZE // 2,
    (config.GRID_ROWS // 2) * config.CELL_SIZE + config.CELL_SIZE // 2
]

# Генерация препятствий
obstacles = generate_obstacles()

# Инициализация компонентов
simulation = Simulation(config, obstacles, ship_position)
visualizer = Visualizer(screen, config)
logger = DataLogger()

# Режимы работы
MODE_SIMULATION = "SIMULATION"
MODE_REPLAY = "REPLAY"
MODE_MAP = "MAP"

current_mode = MODE_SIMULATION
replay_controller = None
replay_ui = None

# Состояние приложения
running = True
selected_cell = None
mission_start_time = None
last_save_time = None
message = None
message_timer = 0

plot_window = None
show_plots = False

def show_message(msg, duration=3):
    """Отображение сообщения на экране"""
    global message, message_timer
    message = msg
    message_timer = duration

def save_mission():
    """Сохранение текущей миссии"""
    if simulation.mission_active or simulation.mission_success or simulation.mission_collision:
        duration = simulation.sim_time
        filepath = logger.save_mission(simulation, ship_position, duration)
        show_message(f"Миссия сохранена: {filepath}", 3)

def load_mission_from_file():
    """Загрузка миссии из JSON-файла через диалоговое окно"""
    global current_mode, replay_controller, replay_ui, simulation
    
    # Скрываем окно tkinter
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    file_path = filedialog.askopenfilename(
        title="Выберите файл миссии",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        initialdir="missions"
    )
    
    root.destroy()
    
    if file_path:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                mission_data = json.load(f)
            
            replay_controller = ReplayController(mission_data)
            replay_ui = ReplayUI(screen, config)
            current_mode = MODE_REPLAY
            
            # Останавливаем симуляцию
            simulation.is_paused = True
            
            # Показываем информацию о загруженной миссии
            success_str = "успешно" if mission_data.get('success') else "провалена"
            show_message(f"Миссия загружена: {mission_data['mission_id']} ({success_str})", 4)
            
            print(f"[INFO] Загружена миссия: {mission_data['mission_id']}")
            print(f"  - Длительность: {mission_data['duration']:.1f} с")
            print(f"  - Статус: {'Успех' if mission_data['success'] else 'Провал'}")
            print(f"  - Кол-во точек траектории: {len(mission_data['trajectory'])}")
            print(f"  - Кол-во событий: {len(mission_data['events'])}")
            
        except Exception as e:
            show_message(f"Ошибка загрузки: {str(e)}", 3)
            print(f"[ERROR] Ошибка загрузки миссии: {e}")

def exit_replay_mode():
    global current_mode, replay_controller, replay_ui, plot_window, show_plots
    current_mode = MODE_SIMULATION
    replay_controller = None
    replay_ui = None
    plot_window = None  # закрываем графики
    show_plots = False
    simulation.is_paused = False
    show_message("Возврат к режиму симуляции", 2)

# Главный цикл
while running:
    dt = clock.tick(60) / 1000.0  # 60 FPS
    dt = min(dt, 0.033)  # Ограничение максимального dt
    
    # Обработка событий
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if current_mode == MODE_REPLAY and plot_window and plot_window.visible:
                    plot_window = None
                    show_message("Графики закрыты", 1)
                elif current_mode == MODE_REPLAY:
                    exit_replay_mode()
                else:
                    running = False
            
            elif event.key == pygame.K_r:
                if current_mode != MODE_REPLAY:
                    simulation = Simulation(config, obstacles, ship_position)
                    simulation.mission_active = False
                    selected_cell = None
                    current_mode = MODE_SIMULATION
                    show_message("Симуляция сброшена", 2)
            
            elif event.key == pygame.K_SPACE:
                if current_mode == MODE_SIMULATION:
                    simulation.is_paused = not simulation.is_paused
                    status = "Пауза" if simulation.is_paused else "Продолжение"
                    show_message(status, 1)
                elif current_mode == MODE_REPLAY and replay_controller:
                    replay_controller.is_playing = not replay_controller.is_playing
                    if replay_ui:
                        replay_ui.buttons['play_pause']['label'] = '⏸ Пауза' if replay_controller.is_playing else '▶ Пуск'
                    status = "Пауза" if not replay_controller.is_playing else "Воспроизведение"
                    show_message(status, 1)
            
            elif event.key == pygame.K_m and current_mode == MODE_SIMULATION:
                current_mode = MODE_MAP
                show_message("Режим выбора зоны. Нажмите на клетку.", 2)
            
            elif event.key == pygame.K_j or event.key == pygame.K_o:
                # Загрузка миссии по нажатию J или O
                load_mission_from_file()
            
            elif event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                if current_mode == MODE_SIMULATION:
                    save_mission()
            
            elif event.key == pygame.K_UP and current_mode == MODE_REPLAY and replay_controller:
                # Ускорение воспроизведения
                replay_controller.speed = min(4.0, replay_controller.speed * 1.5)
                show_message(f"Скорость: {replay_controller.speed:.1f}x", 1)
            
            elif event.key == pygame.K_DOWN and current_mode == MODE_REPLAY and replay_controller:
                # Замедление воспроизведения
                replay_controller.speed = max(0.1, replay_controller.speed / 1.5)
                show_message(f"Скорость: {replay_controller.speed:.1f}x", 1)
            
            elif event.key == pygame.K_LEFT and current_mode == MODE_REPLAY and replay_controller:
                # Назад на 1 секунду
                replay_controller.set_time(replay_controller.current_time - 1.0)
                show_message(f"Время: {replay_controller.current_time:.1f} с", 1)
            
            elif event.key == pygame.K_RIGHT and current_mode == MODE_REPLAY and replay_controller:
                # Вперёд на 1 секунду
                replay_controller.set_time(replay_controller.current_time + 1.0)
                show_message(f"Время: {replay_controller.current_time:.1f} с", 1)

            elif event.key == pygame.K_q:
                if current_mode == MODE_SIMULATION and not simulation.mission_active:
                    # Перегенерировать препятствия
                    obstacles = generate_obstacles()
                    simulation.obstacles = obstacles
                    show_message("Препятствия перегенерированы", 2)
                elif current_mode == MODE_MAP:
                    # Тоже можно перегенерировать на карте
                    obstacles = generate_obstacles()
                    show_message("Препятствия перегенерированы", 2)
                        
            elif event.key == pygame.K_f:
                # Переключение полноэкранного режима
                if screen.get_flags() & pygame.FULLSCREEN:
                    screen = pygame.display.set_mode((config.WORLD_WIDTH, config.WORLD_HEIGHT))
                else:
                    screen = pygame.display.set_mode((config.WORLD_WIDTH, config.WORLD_HEIGHT), pygame.FULLSCREEN)
                show_message("Полноэкранный режим: " + ("ВКЛ" if screen.get_flags() & pygame.FULLSCREEN else "ВЫКЛ"), 1)
                
            elif event.key == pygame.K_g and current_mode == MODE_REPLAY:
                if plot_window is None:
                    plot_window = PlotWindow(replay_controller.mission_data)
                    show_message("Графики открыты (G - скрыть/показать)", 2)
                else:
                    if plot_window.visible:
                        plot_window.visible = False
                        show_message("Графики скрыты", 1)
                    else:
                        plot_window.visible = True
                        show_message("Графики показаны", 1)
            

                            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if current_mode == MODE_MAP:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                
                cell_size = config.CELL_SIZE
                grid_cols = config.GRID_COLS
                grid_rows = config.GRID_ROWS
                
                total_width = grid_cols * cell_size
                total_height = grid_rows * cell_size
                offset_x = (config.WORLD_WIDTH - total_width) // 2
                offset_y = (config.WORLD_HEIGHT - total_height) // 2
                
                col = (mouse_x - offset_x) // cell_size
                row = (mouse_y - offset_y) // cell_size
                
                if 0 <= col < grid_cols and 0 <= row < grid_rows:
                    center_col = grid_cols // 2
                    center_row = grid_rows // 2
                    
                    if col == center_col and row == center_row:
                        show_message("Нельзя выбрать клетку с судном!", 2)
                    else:
                        selected_cell = (col, row)
                        survey_center_x = col * cell_size + cell_size // 2
                        survey_center_y = row * cell_size + cell_size // 2
                        
                        simulation.start_mission([survey_center_x, survey_center_y])
                        current_mode = MODE_SIMULATION
                        mission_start_time = datetime.now()
                        show_message(f"Миссия начата в зоне ({col}, {row})", 2)
            
            elif current_mode == MODE_REPLAY and replay_ui:
                # Передаём событие в UI воспроизведения
                replay_ui.handle_event(event, replay_controller)
        
        elif event.type == pygame.MOUSEBUTTONUP and current_mode == MODE_REPLAY and replay_ui:
            replay_ui.handle_event(event, replay_controller)
        
        elif event.type == pygame.MOUSEMOTION and current_mode == MODE_REPLAY and replay_ui:
            replay_ui.handle_event(event, replay_controller)

    # Обновление таймера сообщения
    if message_timer > 0:
        message_timer -= dt
        if message_timer <= 0:
            message = None
    
    # Отрисовка в зависимости от режима
    if current_mode == MODE_MAP:
        visualizer.draw_map_screen(
            config.GRID_COLS, config.GRID_ROWS, config.CELL_SIZE,
            ship_position, obstacles, selected_cell
        )
    
    elif current_mode == MODE_REPLAY and replay_controller:
        # Обновление времени воспроизведения
        replay_controller.update(dt)
        
        # Получение текущего состояния
        auv_pos = replay_controller.get_position_at_time()
        auv_heading = replay_controller.get_heading_at_time()
        
        # Центрирование камеры
        visualizer.center_camera_on_auv(auv_pos)
        
        # Очистка экрана
        screen.fill(visualizer.COLORS['background'])
        
        # Отрисовка сетки
        visualizer.draw_grid(config.CELL_SIZE, config.WORLD_WIDTH, config.WORLD_HEIGHT)
        
        # Отрисовка траектории из сохранённых данных
        if config.get('visualization.show_trajectory', True):
            # Преобразуем траекторию в нужный формат
            trajectory_points = []
            for point in replay_controller.trajectory:
                # Если точка содержит время (x, y, t)
                if len(point) >= 2:
                    trajectory_points.append([point[0], point[1]])
            visualizer.draw_trajectory(trajectory_points, max_points=None)
        


        # Отрисовка зон безопасности и препятствий
        show_zones = config.get('visualization.show_zones', True)
        replay_obstacles = replay_controller.get_obstacles_at_time(replay_controller.current_time)
        for obs_data in replay_obstacles:
            # Создаём временный объект для отрисовки
            temp_obs = type('TempObstacle', (), {})()
            temp_obs.position = obs_data['position']
            temp_obs.radius = obs_data['radius']
            temp_obs.shape = obs_data['shape']
            temp_obs.is_moving = obs_data.get('is_moving', False)
            temp_obs.velocity = obs_data.get('velocity', [0, 0])
            
            # ДОБАВЛЯЕМ отсутствующие атрибуты для прямоугольных препятствий
            temp_obs.width = obs_data['radius'] * 2 if obs_data['shape'] == 'rectangle' else None
            temp_obs.height = obs_data['radius'] * 1.5 if obs_data['shape'] == 'rectangle' else None
            
            # Временная зона для отрисовки
            from zones import CircularZone
            temp_obs.get_active_zone = lambda: CircularZone(temp_obs.position, temp_obs.radius * 2)
            
            visualizer.draw_obstacle(temp_obs, show_zones)
        
        # Отрисовка судна
        visualizer.draw_ship(ship_position)
        
        # Отрисовка точек маршрута (если есть в данных)
        survey_zone = replay_controller.mission_data.get('survey_zone', [400, 400])
        # Создаём временную миссию для отображения зоны
        from mission import Mission

        # survey_zone = replay_controller.get_survey_zone()
        # temp_mission = Mission(
        #     survey_zone,
        #     config.ZONE_WIDTH,
        #     config.ZONE_HEIGHT,
        #     config.MEANDER_STEP_X,
        #     config.MEANDER_STEP_Y
        # )
        # visualizer.draw_waypoints(temp_mission)
        
        # Отрисовка АНПА
        show_sensor = config.get('visualization.show_sensor_cone', True)
        sensor_range = config.SENSOR_RANGE if show_sensor else 0
        mode_color = replay_controller.get_mode_color()
        visualizer.draw_auv(auv_pos, auv_heading, 
                           sensor_range, config.SENSOR_ANGLE, mode_color)
        
        # Отрисовка информационной панели (над UI)
        if replay_ui:
            replay_ui.draw_info_panel(replay_controller, auv_pos, ship_position)
        
        # Отрисовка UI воспроизведения
        replay_ui.draw(replay_controller)
        
        if plot_window and plot_window.visible:
            plot_size = plot_window.get_size()
            if plot_size[0] > 0:
                # Позиция: по центру или в углу - выбираем центр для удобства
                plot_x = (config.WORLD_WIDTH - plot_size[0]) // 2
                plot_y = (config.WORLD_HEIGHT - plot_size[1]) // 2
                
                # Рисуем полупрозрачный фон под графиками для лучшей читаемости
                bg_surf = pygame.Surface((plot_size[0] + 4, plot_size[1] + 4), pygame.SRCALPHA)
                bg_surf.fill((0, 0, 0, 180))
                screen.blit(bg_surf, (plot_x - 2, plot_y - 2))
                
                # Рисуем графики
                plot_window.draw(screen, (plot_x, plot_y))
                
                # Рисуем рамку
                pygame.draw.rect(screen, (200, 200, 200), 
                                (plot_x - 2, plot_y - 2, plot_size[0] + 4, plot_size[1] + 4), 2)
                
                # Подсказка для закрытия
                hint_font = pygame.font.Font(None, 18)
                close_hint = hint_font.render("G - скрыть | ESC - закрыть графики", True, (200, 200, 200))
                hint_rect = close_hint.get_rect(center=(plot_x + plot_size[0] // 2, plot_y + plot_size[1] + 15))
                # Фон для подсказки
                pygame.draw.rect(screen, (0, 0, 0, 200), 
                                (hint_rect.x - 5, hint_rect.y - 2, hint_rect.width + 10, hint_rect.height + 4))
                screen.blit(close_hint, hint_rect)

        # Автоматический выход при завершении
        if replay_controller.current_time >= replay_controller.total_duration:
            if replay_controller.is_playing:
                replay_controller.is_playing = False
                show_message("Воспроизведение завершено", 2)
    
    else:  # MODE_SIMULATION
        # Обновление симуляции
        simulation.update(dt)
        
        # Автоматическое сохранение при завершении миссии
        if not simulation.mission_active and (simulation.mission_success or simulation.mission_collision):
            if last_save_time != simulation.mission_success:
                save_mission()
                last_save_time = simulation.mission_success
        
        # Центрирование камеры на АНПА
        visualizer.center_camera_on_auv(simulation.auv_pos)
        
        # Очистка экрана
        screen.fill(visualizer.COLORS['background'])
        
        # Отрисовка сетки
        visualizer.draw_grid(config.CELL_SIZE, config.WORLD_WIDTH, config.WORLD_HEIGHT)
        
        # Отрисовка траектории
        if config.get('visualization.show_trajectory', True):
            visualizer.draw_trajectory(simulation.trajectory, max_points=None)
        
        # Отрисовка зон безопасности и препятствий
        show_zones = config.get('visualization.show_zones', True)
        for obs in obstacles:
            visualizer.draw_obstacle(obs, show_zones)
        
        # Отрисовка судна
        visualizer.draw_ship(ship_position)
        
        # Отрисовка точек маршрута
        if simulation.mission_active:
            visualizer.draw_waypoints(simulation.mission)
        
        # Отрисовка АНПА
        show_sensor = config.get('visualization.show_sensor_cone', True)
        sensor_range = config.SENSOR_RANGE if show_sensor else 0
        mode_color = simulation.get_mode_color()
        visualizer.draw_auv(simulation.auv_pos, simulation.auv_heading, 
                           sensor_range, config.SENSOR_ANGLE, mode_color)
        
        # Отрисовка информационной панели
        visualizer.draw_info_panel(simulation, simulation.auv_pos, ship_position)
        
        # Подсказка о кнопках
        font_small = pygame.font.Font(None, 16)
        hint_text = font_small.render("J/O - загрузить миссию | Q/Й - генерация препятствий | R - сброс | SPACE - пауза | M - карта", 
                                       True, (150, 150, 150))
        screen.blit(hint_text, (10, config.WORLD_HEIGHT - 25))
    
    # Отображение сообщения
    if message:
        font = pygame.font.Font(None, 30)
        msg_surface = font.render(message, True, (255, 255, 255))
        msg_rect = msg_surface.get_rect(center=(config.WORLD_WIDTH // 2, config.WORLD_HEIGHT - 150))
        
        # Фон сообщения
        pygame.draw.rect(screen, (0, 0, 0, 200), 
                        (msg_rect.x - 10, msg_rect.y - 5, msg_rect.width + 20, msg_rect.height + 10))
        pygame.draw.rect(screen, (100, 100, 100), 
                        (msg_rect.x - 10, msg_rect.y - 5, msg_rect.width + 20, msg_rect.height + 10), 2)
        screen.blit(msg_surface, msg_rect)
    
    # Отображение FPS (опционально)
    if False:  # Включить для отладки
        font = pygame.font.Font(None, 18)
        fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, (200, 200, 200))
        screen.blit(fps_text, (config.WORLD_WIDTH - 60, 10))
    
    pygame.display.flip()

pygame.quit()
sys.exit()