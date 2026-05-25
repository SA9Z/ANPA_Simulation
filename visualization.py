import pygame
import math
from utils import angle_to_vector, distance

class Visualizer:
    """Отрисовка симуляции"""
    
    def __init__(self, screen, config):
        self.screen = screen
        self.config = config
        
        # Цвета
        self.COLORS = {
            'background': (30, 40, 50),
            'grid': (60, 70, 80),
            'ship': (50, 200, 50),
            'auv': (0, 150, 255),
            'auv_heading': (100, 200, 255),
            'obstacle': (150, 50, 50),
            'obstacle_fill': (150, 50, 50, 100),
            'zone': (255, 100, 100, 60),
            'trajectory': (100, 200, 100),
            'waypoint': (50, 255, 50),
            'waypoint_line': (50, 150, 50),
            'sensor_cone': (100, 100, 200, 80),
            'text': (255, 255, 255),
            'warning': (255, 100, 100),
            'success': (100, 255, 100)
        }
        
        # Камера
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0
    
    def world_to_screen(self, x, y):
        """Преобразование мировых координат в экранные"""
        screen_x = (x - self.camera_x) * self.zoom + self.screen.get_width() // 2
        screen_y = (y - self.camera_y) * self.zoom + self.screen.get_height() // 2
        return int(screen_x), int(screen_y)
    
    def screen_to_world(self, screen_x, screen_y):
        """Преобразование экранных координат в мировые"""
        world_x = (screen_x - self.screen.get_width() // 2) / self.zoom + self.camera_x
        world_y = (screen_y - self.screen.get_height() // 2) / self.zoom + self.camera_y
        return world_x, world_y
    
    def draw_grid(self, cell_size, width, height):
        """Отрисовка сетки"""
        screen_w = self.screen.get_width()
        screen_h = self.screen.get_height()
        
        # Определение границ видимой области
        left = self.camera_x - screen_w / (2 * self.zoom)
        right = self.camera_x + screen_w / (2 * self.zoom)
        top = self.camera_y - screen_h / (2 * self.zoom)
        bottom = self.camera_y + screen_h / (2 * self.zoom)
        
        # Вертикальные линии
        x = math.floor(left / cell_size) * cell_size
        while x <= right:
            start = self.world_to_screen(x, top)
            end = self.world_to_screen(x, bottom)
            pygame.draw.line(self.screen, self.COLORS['grid'], start, end, 1)
            x += cell_size
        
        # Горизонтальные линии
        y = math.floor(top / cell_size) * cell_size
        while y <= bottom:
            start = self.world_to_screen(left, y)
            end = self.world_to_screen(right, y)
            pygame.draw.line(self.screen, self.COLORS['grid'], start, end, 1)
            y += cell_size
    
    def draw_cell_outline(self, cell_x, cell_y, cell_size):
        """Отрисовка границы клетки"""
        x1 = cell_x
        y1 = cell_y
        x2 = cell_x + cell_size
        y2 = cell_y + cell_size
        
        p1 = self.world_to_screen(x1, y1)
        p2 = self.world_to_screen(x2, y2)
        
        pygame.draw.rect(self.screen, self.COLORS['grid'], (p1[0], p1[1], p2[0]-p1[0], p2[1]-p1[1]), 2)
    
    def draw_auv(self, position, heading, sensor_range, sensor_angle, mode_color):
        """Отрисовка АНПА с полупрозрачным сектором гидролокатора"""
        x, y = self.world_to_screen(position[0], position[1])
        
        # Треугольник АНПА (оставляем как есть)
        length = 15
        width = 10
        
        heading_rad = math.radians(heading)
        cos_h = math.cos(heading_rad)
        sin_h = math.sin(heading_rad)
        
        # Три точки треугольника
        nose = (x + length * cos_h, y + length * sin_h)
        left = (x - width * sin_h - length * 0.3 * cos_h,
                y + width * cos_h - length * 0.3 * sin_h)
        right = (x + width * sin_h - length * 0.3 * cos_h,
                y - width * cos_h - length * 0.3 * sin_h)
        
        pygame.draw.polygon(self.screen, self.COLORS['auv'], [nose, left, right])
        pygame.draw.polygon(self.screen, self.COLORS['auv_heading'], [nose, left, right], 2)
        
        # Сектор гидролокатора — ПОЛУПРОЗРАЧНЫЙ
        if sensor_range > 0:
            half_angle_rad = math.radians(sensor_angle / 2)
            
            # Начало сектора
            start_angle = math.radians(heading - sensor_angle / 2)
            end_angle = math.radians(heading + sensor_angle / 2)
            
            # Преобразование радиуса в экранные координаты
            end_range = sensor_range * self.zoom
            end_range = min(end_range, 300)  # Ограничение для отрисовки
            
            points = [(x, y)]
            for angle in range(int(start_angle * 180 / math.pi), 
                            int(end_angle * 180 / math.pi) + 5, 5):
                rad = math.radians(angle)
                px = x + end_range * math.cos(rad)
                py = y + end_range * math.sin(rad)
                points.append((px, py))
            
            if len(points) > 2:
                # СОЗДАЁМ ПОВЕРХНОСТЬ С ПРОЗРАЧНОСТЬЮ
                # Находим bounding box для сектора
                all_x = [p[0] for p in points]
                all_y = [p[1] for p in points]
                min_x, max_x = min(all_x), max(all_x)
                min_y, max_y = min(all_y), max(all_y)
                
                # Создаём временную поверхность
                surf_width = int(max_x - min_x) + 10
                surf_height = int(max_y - min_y) + 10
                
                if surf_width > 0 and surf_height > 0:
                    temp_surf = pygame.Surface((surf_width, surf_height), pygame.SRCALPHA)
                    
                    # Смещаем точки для отрисовки на временной поверхности
                    offset_x, offset_y = min_x, min_y
                    shifted_points = [(p[0] - offset_x, p[1] - offset_y) for p in points]
                    
                    # Рисуем залитый сектор с ПРОЗРАЧНОСТЬЮ (альфа-канал 80)
                    pygame.draw.polygon(temp_surf, (100, 100, 200, 80), shifted_points)
                    
                    # Рисуем контур сектора
                    pygame.draw.polygon(temp_surf, (150, 150, 220, 200), shifted_points, 2)
                    
                    # Блендинг с основным экраном
                    self.screen.blit(temp_surf, (offset_x, offset_y))

    def draw_obstacle(self, obstacle, show_zone=True):
        """Отрисовка препятствия и зоны безопасности"""
        pos = obstacle.position
        x, y = self.world_to_screen(pos[0], pos[1])
        
        # Выбор цвета в зависимости от типа
        if obstacle.is_moving:
            fill_color = (200, 200, 50)  # Жёлтый
            border_color = (255, 255, 100)
        else:
            fill_color = self.COLORS['obstacle']  # (150, 50, 50) красный/коричневый
            border_color = (200, 100, 100)

        # Физическое тело
        if obstacle.shape == 'circle':
            radius = max(3, min(obstacle.radius * self.zoom, 100))
            pygame.draw.circle(self.screen, fill_color, (x, y), radius)
            pygame.draw.circle(self.screen, border_color, (x, y), radius, 2)
        else:
            w = obstacle.width * self.zoom
            h = obstacle.height * self.zoom
            rect = pygame.Rect(x - w/2, y - h/2, w, h)
            pygame.draw.rect(self.screen, fill_color, rect)
            pygame.draw.rect(self.screen, border_color, rect, 2)

        # Зона безопасности
        if show_zone:
            zone = obstacle.get_active_zone()
            if zone.type == 'circle':
                radius = zone.radius * self.zoom
                radius = max(3, min(radius, 200))
                surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (255, 100, 100, 60), (radius, radius), radius)
                self.screen.blit(surf, (x - radius, y - radius))
            else:
                # Эллипс
                rx = zone.a * self.zoom
                ry = zone.b * self.zoom
                rx = max(3, min(rx, 200))
                ry = max(3, min(ry, 200))
                
                # Поворот эллипса
                angle = math.degrees(math.atan2(zone.e1[1], zone.e1[0]))
                
                surf = pygame.Surface((rx*2, ry*2), pygame.SRCALPHA)
                pygame.draw.ellipse(surf, (255, 100, 100, 60), (0, 0, rx*2, ry*2))
                
                # Поворот и отрисовка
                rotated = pygame.transform.rotate(surf, -angle)
                self.screen.blit(rotated, (x - rotated.get_width()/2, y - rotated.get_height()/2))
        
    def draw_trajectory(self, trajectory, max_points=None):
        """Отрисовка траектории движения (полностью, без обрезания)"""
        if len(trajectory) < 2:
            return
        
        # Если max_points=None, рисуем все точки
        if max_points is None:
            points_to_draw = trajectory
        else:
            points_to_draw = trajectory[-max_points:]
        
        points = []
        for point in points_to_draw:
            # Поддержка как [x,y], так и [x,y,time]
            if len(point) >= 2:
                screen_point = self.world_to_screen(point[0], point[1])
                points.append(screen_point)
        
        if len(points) > 1:
            pygame.draw.lines(self.screen, self.COLORS['trajectory'], False, points, 2)
            
    def draw_waypoints(self, mission):
        """Отрисовка точек маршрута 'меандр'"""
        if not mission or not mission.waypoints:
            return
        
        waypoints = mission.waypoints
        current_idx = mission.current_waypoint_index
        
        # Линии между точками
        screen_points = []
        for wp in waypoints:
            screen_points.append(self.world_to_screen(wp[0], wp[1]))
        
        if len(screen_points) > 1:
            pygame.draw.lines(self.screen, self.COLORS['waypoint_line'], False, screen_points, 2)
        
        # Отрисовка точек
        for i, wp in enumerate(waypoints):
            x, y = self.world_to_screen(wp[0], wp[1])
            color = self.COLORS['waypoint'] if i >= current_idx else (100, 100, 100)
            pygame.draw.circle(self.screen, color, (x, y), 5)
            pygame.draw.circle(self.screen, (255, 255, 255), (x, y), 5, 1)
    
    def draw_ship(self, position):
        """Отрисовка судна в центре"""
        x, y = self.world_to_screen(position[0], position[1])
        
        # Корпус
        pygame.draw.circle(self.screen, self.COLORS['ship'], (x, y), 12)
        pygame.draw.circle(self.screen, (255, 255, 255), (x, y), 12, 2)
        
        # Якорный крест
        pygame.draw.line(self.screen, (255, 255, 255), (x - 8, y), (x + 8, y), 2)
        pygame.draw.line(self.screen, (255, 255, 255), (x, y - 8), (x, y + 8), 2)
    
    def draw_info_panel(self, simulation, auv_pos, ship_pos):
        """Отрисовка информационной панели"""
        font = pygame.font.Font(None, 24)
        font_small = pygame.font.Font(None, 18)
        
        # Фон панели
        panel_rect = pygame.Rect(10, 10, 280, 200)
        pygame.draw.rect(self.screen, (0, 0, 0, 180), panel_rect)
        pygame.draw.rect(self.screen, (100, 100, 100), panel_rect, 2)
        
        y_offset = 15
        
        # Режим
        mode = simulation.controller.mode
        mode_color = simulation.get_mode_color()
        mode_text = font.render(f"Режим: {mode}", True, mode_color)
        self.screen.blit(mode_text, (20, y_offset))
        y_offset += 25
        
        # Время
        time_text = font.render(f"Время: {simulation.sim_time:.1f} с", True, self.COLORS['text'])
        self.screen.blit(time_text, (20, y_offset))
        y_offset += 25
        
        # Расстояние до ближайшего препятствия
        d_min = simulation.get_distance_to_closest_obstacle()
        d_color = self.COLORS['warning'] if d_min < 30 else self.COLORS['text']
        dist_text = font.render(f"До препятствия: {d_min:.1f} м", True, d_color)
        self.screen.blit(dist_text, (20, y_offset))
        y_offset += 25
        
        # Видимость цели
        if simulation.mission:
            target = simulation.mission.get_current_waypoint()
            if target:
                visible = simulation.is_goal_visible(target)
                vis_text = font.render(f"Видимость цели: {'Да' if visible else 'Нет'}", 
                                        True, self.COLORS['text'])
                self.screen.blit(vis_text, (20, y_offset))
                y_offset += 25
        
        # Прогресс миссии
        if simulation.mission:
            completed, total = simulation.mission.get_progress()
            progress = (completed / total * 100) if total > 0 else 0
            prog_text = font.render(f"Миссия: {completed}/{total} ({progress:.0f}%)", 
                                     True, self.COLORS['text'])
            self.screen.blit(prog_text, (20, y_offset))
            y_offset += 25
        
        # Энергия
        energy_bar_width = 200
        energy_percent = simulation.energy / 1000
        energy_rect = pygame.Rect(20, y_offset, energy_bar_width * energy_percent, 12)
        pygame.draw.rect(self.screen, (100, 100, 100), (20, y_offset, energy_bar_width, 12), 2)
        pygame.draw.rect(self.screen, (50, 200, 50), energy_rect)
        y_offset += 20
        
        # Статус
        if simulation.collision_occurred:
            status_text = font.render("СТОЛКНОВЕНИЕ! Нажмите R для сброса", True, self.COLORS['warning'])
            self.screen.blit(status_text, (20, y_offset))
        elif simulation.mission_success:
            status_text = font.render("МИССИЯ ВЫПОЛНЕНА!", True, self.COLORS['success'])
            self.screen.blit(status_text, (20, y_offset))
    
    def draw_map_screen(self, grid_cols, grid_rows, cell_size, ship_pos, obstacles, selected_cell=None):
        """Отрисовка экрана выбора зоны (карты)"""
        screen_w = self.screen.get_width()
        screen_h = self.screen.get_height()
        
        # Фон
        self.screen.fill(self.COLORS['background'])
        
        # Заголовок
        font_big = pygame.font.Font(None, 36)
        title = font_big.render("ВЫБОР ЗОНЫ ОБСЛЕДОВАНИЯ", True, self.COLORS['text'])
        title_rect = title.get_rect(center=(screen_w // 2, 30))
        self.screen.blit(title, title_rect)
        
        # Расчёт смещения для центрирования сетки
        total_width = grid_cols * cell_size
        total_height = grid_rows * cell_size
        offset_x = (screen_w - total_width) // 2
        offset_y = (screen_h - total_height) // 2
        
        # Отрисовка сетки и препятствий
        for row in range(grid_rows):
            for col in range(grid_cols):
                cell_x = offset_x + col * cell_size
                cell_y = offset_y + row * cell_size
                
                # Цвет клетки
                if selected_cell == (col, row):
                    cell_color = (80, 100, 120)
                else:
                    cell_color = (50, 60, 70)
                
                pygame.draw.rect(self.screen, cell_color, (cell_x, cell_y, cell_size, cell_size))
                pygame.draw.rect(self.screen, self.COLORS['grid'], (cell_x, cell_y, cell_size, cell_size), 2)
                
                # Отображение препятствий в клетке
                for obs in obstacles:
                    # Преобразование мировых координат в экранные для карты
                    obs_map_x = offset_x + (obs.position[0] // cell_size) * cell_size + (obs.position[0] % cell_size) / (cell_size) * cell_size
                    obs_map_y = offset_y + (obs.position[1] // cell_size) * cell_size + (obs.position[1] % cell_size) / (cell_size) * cell_size
                    
                    # Упрощённая проверка принадлежности клетке
                    if col * cell_size <= obs.position[0] < (col+1) * cell_size and \
                       row * cell_size <= obs.position[1] < (row+1) * cell_size:
                        pygame.draw.circle(self.screen, self.COLORS['obstacle'], 
                                         (int(obs_map_x), int(obs_map_y)), max(3, obs.radius // 2))
        
        # Отображение судна
        ship_map_x = offset_x + ship_pos[0]
        ship_map_y = offset_y + ship_pos[1]
        pygame.draw.circle(self.screen, self.COLORS['ship'], (int(ship_map_x), int(ship_map_y)), 10)
        pygame.draw.circle(self.screen, (255, 255, 255), (int(ship_map_x), int(ship_map_y)), 10, 2)
        
        # Инструкция
        font_small = pygame.font.Font(None, 20)
        inst = font_small.render("Нажмите на клетку для выбора зоны | ESC для выхода", True, self.COLORS['text'])
        inst_rect = inst.get_rect(center=(screen_w // 2, screen_h - 20))
        self.screen.blit(inst, inst_rect)
    
    def center_camera_on_auv(self, auv_pos):
        """Центрирование камеры на АНПА"""
        self.camera_x = auv_pos[0]
        self.camera_y = auv_pos[1]