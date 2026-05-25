import pygame
import math
from utils import distance, angle_to_vector

class ReplayController:
    """Контроллер воспроизведения сохранённой миссии"""
    
    MODE_NORMAL = "NORMAL"
    MODE_ATTENTION = "ATTENTION"
    MODE_AVOID = "AVOID"
    MODE_RETURN = "RETURN"
        
    def __init__(self, mission_data):
        self.mission_data = mission_data
        
        # Извлечение данных
        self.trajectory = mission_data.get('trajectory', [])
        self.events = mission_data.get('events', [])
        self.telemetry = mission_data.get('telemetry', {})
        
        # ЗАГРУЗКА ПРЕПЯТСТВИЙ
        self.obstacles_data = mission_data.get('obstacles', [])
        
        # Состояние воспроизведения
        self.current_time = 0.0
        self.total_duration = mission_data.get('duration', 0)
        self.is_playing = True
        self.speed = 1.0
        
        self._build_time_index()

    def get_obstacles_at_time(self, current_time):
        """Получение позиций препятствий в текущий момент времени"""
        obstacles_replay = []
        
        for obs_data in self.obstacles_data:
            if obs_data['type'] == 'static':
                # Статическое препятствие — позиция не меняется
                obs_replay = {
                    'position': obs_data['position'],
                    'radius': obs_data['radius'],
                    'shape': obs_data.get('shape', 'circle'),
                    'is_moving': False
                }
                # Добавляем width/height для прямоугольников
                if obs_replay['shape'] == 'rectangle':
                    obs_replay['width'] = obs_data['radius'] * 2
                    obs_replay['height'] = obs_data['radius'] * 1.5
            else:
                # Динамическое препятствие — интерполяция по времени
                initial_pos = obs_data['initial_position']
                velocity = obs_data['velocity']
                
                # Ограничиваем время длительностью миссии
                t = min(current_time, self.total_duration)
                
                # Позиция = начальная + скорость * время
                pos = [
                    initial_pos[0] + velocity[0] * t,
                    initial_pos[1] + velocity[1] * t
                ]
                obs_replay = {
                    'position': pos,
                    'radius': obs_data['radius'],
                    'shape': obs_data.get('shape', 'circle'),
                    'is_moving': True,
                    'velocity': velocity
                }
                # Добавляем width/height для прямоугольников
                if obs_replay['shape'] == 'rectangle':
                    obs_replay['width'] = obs_data['radius'] * 2
                    obs_replay['height'] = obs_data['radius'] * 1.5
            
            obstacles_replay.append(obs_replay)
        
        return obstacles_replay
        
    def _build_time_index(self):
        """Построение индекса для быстрого поиска по времени"""
        self.trajectory_index = []
        for i, point in enumerate(self.trajectory):
            self.trajectory_index.append({
                'time': point[2],
                'index': i,
                'position': [point[0], point[1]]
            })
        
        self.telemetry_index = []
        times = self.telemetry.get('time', [])
        modes = self.telemetry.get('mode', [])
        d_min = self.telemetry.get('d_min', [])
        tti = self.telemetry.get('TTI', [])
        energy = self.telemetry.get('energy_consumed', [])
        
        for i, t in enumerate(times):
            self.telemetry_index.append({
                'time': t,
                'mode': modes[i] if i < len(modes) else 'NORMAL',
                'd_min': d_min[i] if i < len(d_min) else 999,
                'tti': tti[i] if i < len(tti) else 999,
                'energy_consumed': energy[i] if i < len(energy) else 0
            })
    
    def set_time(self, time_sec):
        """Установка времени воспроизведения"""
        self.current_time = max(0, min(time_sec, self.total_duration))
        
    def get_position_at_time(self):
        """Получение позиции АНПА в текущий момент времени"""
        if not self.trajectory_index:
            return [400, 400]
        
        # Бинарный поиск
        left, right = 0, len(self.trajectory_index) - 1
        result_idx = 0
        
        while left <= right:
            mid = (left + right) // 2
            if self.trajectory_index[mid]['time'] <= self.current_time:
                result_idx = mid
                left = mid + 1
            else:
                right = mid - 1
        
        return self.trajectory_index[result_idx]['position'].copy()
    
    def get_heading_at_time(self):
        """Вычисление курса по траектории"""
        if not self.trajectory_index:
            return 0.0
        
        # Находим текущую и следующую позиции
        current_pos = self.get_position_at_time()
        
        # Ищем следующую позицию
        next_pos = current_pos
        for point in self.trajectory_index:
            if point['time'] > self.current_time:
                next_pos = point['position']
                break
        
        # Вычисляем направление
        dx = next_pos[0] - current_pos[0]
        dy = next_pos[1] - current_pos[1]
        
        if abs(dx) < 0.01 and abs(dy) < 0.01:
            # Если стоим, ищем предыдущую позицию для направления
            prev_pos = current_pos
            for point in reversed(self.trajectory_index):
                if point['time'] < self.current_time:
                    prev_pos = point['position']
                    break
            dx = current_pos[0] - prev_pos[0]
            dy = current_pos[1] - prev_pos[1]
        
        if abs(dx) < 0.01 and abs(dy) < 0.01:
            return 0.0
        
        return math.degrees(math.atan2(dy, dx))
    
    def get_mode_at_time(self):
        """Получение режима в текущий момент времени"""
        if not self.telemetry_index:
            return self.MODE_NORMAL
        
        # Бинарный поиск по времени
        left, right = 0, len(self.telemetry_index) - 1
        result = self.telemetry_index[0]
        
        while left <= right:
            mid = (left + right) // 2
            if self.telemetry_index[mid]['time'] <= self.current_time:
                result = self.telemetry_index[mid]
                left = mid + 1
            else:
                right = mid - 1
        
        return result['mode']
    
    def get_telemetry_at_time(self):
        """Получение телеметрии в текущий момент времени"""
        if not self.telemetry_index:
            return {'d_min': 999, 'tti': 999, 'energy_consumed': 0}
        
        # Бинарный поиск
        left, right = 0, len(self.telemetry_index) - 1
        result = self.telemetry_index[0]
        
        while left <= right:
            mid = (left + right) // 2
            if self.telemetry_index[mid]['time'] <= self.current_time:
                result = self.telemetry_index[mid]
                left = mid + 1
            else:
                right = mid - 1
        
        return {
            'd_min': result.get('d_min', 999),
            'tti': result.get('tti', 999),
            'energy_consumed': result.get('energy_consumed', 0)
        }
    
    def get_events_at_time(self, time_window=1.0):
        """Получение событий в окрестности текущего времени"""
        nearby_events = []
        for event in self.events:
            if abs(event['t'] - self.current_time) < time_window:
                nearby_events.append(event)
        return nearby_events
    
    def update(self, dt):
        """Обновление времени воспроизведения"""
        if self.is_playing:
            self.current_time += dt * self.speed
            if self.current_time >= self.total_duration:
                self.current_time = self.total_duration
                self.is_playing = False
                return True  # Воспроизведение завершено
        return False  # Воспроизведение продолжается
    
    def get_progress(self):
        """Получение прогресса воспроизведения (0-1)"""
        if self.total_duration <= 0:
            return 0
        return self.current_time / self.total_duration
    
    def get_mode_color(self):
        """Получение цвета для текущего режима"""
        mode_colors = {
            "NORMAL": (0, 255, 0),
            "ATTENTION": (255, 255, 0),
            "AVOID": (255, 0, 0),
            "RETURN": (0, 255, 255)
        }
        return mode_colors.get(self.get_mode_at_time(), (255, 255, 255))
    
    # В replay_controller.py добавить метод:
    def get_survey_zone(self):
        return self.mission_data.get('survey_zone', [400, 400])

