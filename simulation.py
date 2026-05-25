import math
import time
import random
from utils import normalize, distance, vector_to_angle, angle_to_vector
from controller import NavigationController
from mission import Mission

class Simulation:
    """Управление симуляцией движения АНПА"""
    
    def __init__(self, config, obstacles, ship_position):
        self.config = config
        self.obstacles = obstacles
        self.ship_position = list(ship_position)
        
        # Параметры АНПА
        self.auv_length = config.AUV_LENGTH
        self.max_speed = config.MAX_SPEED
        self.turn_rate = config.TURN_RATE  # град/сек
        
        # Состояние АНПА
        self.auv_pos = list(ship_position)
        self.auv_heading = 0.0  # градусы
        self.auv_speed = 0.0
        self.trajectory = []  # список точек [x, y, time]
        
        # Контроллер
        self.controller = NavigationController(config)
        
        # Миссия
        self.mission = None
        self.mission_active = False
        self.mission_success = False
        self.mission_collision = False
        
        # Время
        self.sim_time = 0.0
        self.last_update_time = None
        self.is_running = True
        self.is_paused = False
        
        # Телеметрия
        self.telemetry = {
            'time': [],
            'mode': [],
            'd_min': [],
            'TTI': [],
            'energy_consumed': []
        }
        
        # Энергия
        self.energy = 1000.0  # условных единиц
        self.energy_consumption_rate = 0.5  # ед/сек при движении
        
        # Флаг столкновения
        self.collision_occurred = False
    
    def start_mission(self, survey_center):
        """Начало миссии в заданной зоне"""
        self.mission = Mission(
            survey_center,
            self.config.ZONE_WIDTH,
            self.config.ZONE_HEIGHT,
            self.config.MEANDER_STEP_X,
            self.config.MEANDER_STEP_Y
        )
        self.mission_active = True
        self.mission_success = False
        self.mission_collision = False
        self.collision_occurred = False
        
        # Сброс состояния АНПА
        self.auv_pos = list(self.ship_position)
        self.trajectory = [[self.auv_pos[0], self.auv_pos[1], 0.0]]
        self.controller.reset()
        self.sim_time = 0.0
        self.energy = 1000.0
        
        # Очистка телеметрии
        self.telemetry = {
            'time': [],
            'mode': [],
            'd_min': [],
            'TTI': [],
            'energy_consumed': []
        }
    
    def update(self, dt):
        """Обновление состояния симуляции"""
        if self.is_paused or not self.is_running:
            return
        
        if not self.mission_active:
            return
        
        # Обновление времени
        self.sim_time += dt
        self.energy -= self.energy_consumption_rate * dt * (self.auv_speed / self.max_speed)
        
        if self.energy <= 0:
            self.mission_active = False
            self.mission_success = False
            return
        
        # Обновление позиций движущихся препятствий
        for obs in self.obstacles:
            if obs.is_moving:
                obs.update(dt, self.config.V_CRUISE)
        
        # Получение текущей целевой точки
        if self.mission.mission_complete:
            self.mission_active = False
            self.mission_success = True
            return
        
        target = self.mission.get_current_waypoint()
        
        # В режиме RETURN используем сохранённую цель
        if self.controller.mode == self.controller.MODE_RETURN:
            if self.controller.return_target is not None:
                target = self.controller.return_target
            else:
                # Возврат на ближайшую точку маршрута
                target = self.mission.get_current_waypoint()
                if target is None:
                    # Если нет активной точки — завершаем миссию
                    self.mission_active = False
                    self.mission_success = True
                    return
        
        if target is None:
            return
        
        # Обновление контроллера
        desired_dir = self.controller.update(
            self.auv_pos, self.auv_heading, target, self.obstacles, dt, self.sim_time
        )
        
        # Вычисление желаемого курса
        desired_heading = vector_to_angle(desired_dir)
        
        # Поворот к желаемому курсу
        heading_diff = desired_heading - self.auv_heading
        heading_diff = ((heading_diff + 180) % 360) - 180
        
        max_turn = self.turn_rate * dt
        if abs(heading_diff) > max_turn:
            heading_diff = max_turn if heading_diff > 0 else -max_turn
        
        self.auv_heading += heading_diff
        self.auv_heading %= 360
        
        # Движение вперёд
        speed = self.max_speed
        self.auv_speed = speed
        
        move_vec = angle_to_vector(self.auv_heading)
        self.auv_pos[0] += move_vec[0] * speed * dt
        self.auv_pos[1] += move_vec[1] * speed * dt
        
        # Запись траектории
        self.trajectory.append([self.auv_pos[0], self.auv_pos[1], self.sim_time])
        
        # Проверка столкновений
        for obs in self.obstacles:
            if obs.check_collision(self.auv_pos):
                self.mission_active = False
                self.mission_success = False
                self.mission_collision = True
                self.collision_occurred = True
                return
        
        # Проверка достижения целевой точки
        dist_to_target = distance(self.auv_pos, target)
        if dist_to_target < 15:  # порог достижения
            if self.controller.mode != self.controller.MODE_RETURN:
                self.mission.advance_to_next_waypoint()
            else:
                # В режиме RETURN - возвращаемся на маршрут
                self.controller.mode = self.controller.MODE_NORMAL
                self.mission.reset_to_nearest_waypoint(self.auv_pos)
                self.controller.return_target = None
        
        # Сбор телеметрии (с пониженной частотой)
        if len(self.telemetry['time']) < 1 or self.sim_time - self.telemetry['time'][-1] >= 1.0:
            self.telemetry['time'].append(self.sim_time)
            self.telemetry['mode'].append(self.controller.mode)
            
            # Минимальное расстояние до препятствий
            d_min = float('inf')
            for obs in self.obstacles:
                d = distance(self.auv_pos, obs.position) - obs.radius
                d_min = min(d_min, d)
            self.telemetry['d_min'].append(d_min if d_min != float('inf') else 999)
            
            # TTI (Time to Impact)
            if self.controller.active_obstacle:
                zone = self.controller.active_obstacle.get_active_zone()
                d_obst = max(0, zone.distance_to_boundary(self.auv_pos))
                v_res = 10  # упрощённо
                tti = d_obst / v_res if v_res > 0 else 999
                self.telemetry['TTI'].append(tti)
            else:
                self.telemetry['TTI'].append(999)
            
            self.telemetry['energy_consumed'].append(1000 - self.energy)
    
    def get_mode_color(self):
        """Получение цвета для текущего режима"""
        mode_colors = {
            "NORMAL": (0, 255, 0),
            "ATTENTION": (255, 255, 0),
            "AVOID": (255, 0, 0),
            "RETURN": (0, 255, 255)
        }
        return mode_colors.get(self.controller.mode, (255, 255, 255))
    
    def get_distance_to_closest_obstacle(self):
        """Расстояние до ближайшего препятствия"""
        min_dist = float('inf')
        for obs in self.obstacles:
            d = distance(self.auv_pos, obs.position) - obs.radius
            min_dist = min(min_dist, d)
        return min_dist if min_dist != float('inf') else 999
    
    def is_goal_visible(self, goal_pos):
        """Проверка видимости цели"""
        if self.controller.active_obstacle is None:
            return True
        
        zone = self.controller.active_obstacle.get_active_zone()
        return self.controller.check_visibility(self.auv_pos, goal_pos, zone)