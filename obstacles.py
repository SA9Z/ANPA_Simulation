import random
import math
from zones import CircularZone, EllipticalZone
from utils import normalize, norm, distance

class Obstacle:
    """Класс препятствия"""
    
    def __init__(self, position, radius, auv_length, k=1.8, velocity=None, shape='circle'):
        self.position = list(position)
        self.initial_position = list(position)  # СОХРАНЯЕМ НАЧАЛЬНУЮ ПОЗИЦИЮ
        self.radius = radius
        self.velocity = velocity if velocity is not None else [0.0, 0.0]
        self.shape = shape
        self.width = radius * 2 if shape == 'rectangle' else None
        self.height = radius * 1.5 if shape == 'rectangle' else None
        
        # Зона безопасности
        self.R_safe = radius + k * auv_length
        self.zone = CircularZone(position, self.R_safe)
        self.use_ellipse = False
        self.ellipse_zone = None
        
        # Для движущихся препятствий
        self.is_moving = norm(velocity) > 0.01 if velocity else False
    
    def reset_to_initial(self):
        """Сброс препятствия в начальное положение"""
        self.position = self.initial_position.copy()
        self._update_zone(12)  # v_cruise по умолчанию
        
    def update(self, dt, v_cruise):
        """Обновление позиции движущегося препятствия"""
        if self.is_moving:
            self.position[0] += self.velocity[0] * dt
            self.position[1] += self.velocity[1] * dt
            self._update_zone(v_cruise)
    
    def _update_zone(self, v_cruise):
        """Обновление зоны безопасности (круг или эллипс)"""
        v_res_norm = norm(self.velocity)
        
        if v_res_norm > 0.1 and self.use_ellipse:
            # Деформация в эллипс
            v_rel = v_res_norm / v_cruise
            
            a_ellipse = self.R_safe * (1 + v_rel)
            b_ellipse = self.R_safe * math.sqrt(1 + v_rel)
            
            # Направление скорости
            if v_res_norm > 0:
                e1 = normalize(self.velocity)
            else:
                e1 = [1.0, 0.0]
            e2 = [-e1[1], e1[0]]
            
            # Смещение центра
            center_ellipse = [
                self.position[0] + e1[0] * (self.R_safe * v_rel),
                self.position[1] + e1[1] * (self.R_safe * v_rel)
            ]
            
            self.ellipse_zone = EllipticalZone(center_ellipse, a_ellipse, b_ellipse, e1, e2)
            self.zone = self.ellipse_zone
        else:
            # Круговая зона
            self.zone = CircularZone(self.position, self.R_safe)
    
    def enable_ellipse(self, v_cruise):
        """Включение эллиптической модели"""
        self.use_ellipse = True
        self._update_zone(v_cruise)
    
    def disable_ellipse(self):
        """Отключение эллиптической модели"""
        self.use_ellipse = False
        self.zone = CircularZone(self.position, self.R_safe)
    
    def get_distance_to_boundary(self, auv_pos):
        """Расстояние от АНПА до границы зоны безопасности"""
        return self.zone.distance_to_boundary(auv_pos)
    
    def check_collision(self, auv_pos):
        """Проверка столкновения с физическим телом препятствия"""
        return distance(auv_pos, self.position) < self.radius
    
    def get_active_zone(self):
        """Получение активной зоны безопасности"""
        return self.zone
    
    @staticmethod
    def generate_random(cell_x, cell_y, cell_size, auv_length, k, min_radius=10, max_radius=25):
        """Генерация случайного препятствия в клетке"""
        # Случайная позиция внутри клетки (с отступом от краёв)
        margin = 15
        x = cell_x + margin + random.uniform(0, cell_size - 2*margin)
        y = cell_y + margin + random.uniform(0, cell_size - 2*margin)
        
        radius = random.uniform(min_radius, max_radius)
        
        # Случайная форма
        shape = random.choice(['circle', 'rectangle'])
        
        # Случайная скорость (15% препятствий движутся)
        velocity = None
        if random.random() < 0.15:
            speed = random.uniform(2, 8)
            angle = random.uniform(0, 360)
            vx = speed * math.cos(math.radians(angle))
            vy = speed * math.sin(math.radians(angle))
            velocity = [vx, vy]
        
        return Obstacle([x, y], radius, auv_length, k, velocity, shape)