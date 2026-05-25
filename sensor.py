import math
import random
from utils import distance, angle_to_vector, dot, normalize

class Sonar:
    """Гидролокатор АНПА"""
    
    def __init__(self, range_max, angle_deg, noise_std=2.0):
        self.range_max = range_max
        self.angle_deg = angle_deg  # полный угол сектора
        self.half_angle = angle_deg / 2
        self.noise_std = noise_std  # стандартное отклонение шума
    
    def detect_obstacles(self, auv_pos, auv_heading_deg, obstacles):
        """Обнаружение препятствий в секторе обзора"""
        detected = []
        
        # Направление курса
        heading_vec = angle_to_vector(auv_heading_deg)
        
        for obs in obstacles:
            # Вектор от АНПА к препятствию
            to_obs = [obs.position[0] - auv_pos[0], obs.position[1] - auv_pos[1]]
            dist = distance(auv_pos, obs.position)
            
            # Проверка дальности
            if dist > self.range_max:
                continue
            
            # Проверка угла
            if dist > 0.01:
                obs_angle = math.degrees(math.atan2(to_obs[1], to_obs[0]))
                heading_vec_angle = auv_heading_deg
                
                # Разница углов
                angle_diff = abs(obs_angle - heading_vec_angle)
                angle_diff = min(angle_diff, 360 - angle_diff)
                
                if angle_diff <= self.half_angle:
                    # Добавляем шум к измерению
                    noisy_dist = dist + random.gauss(0, self.noise_std)
                    noisy_dist = max(0.1, noisy_dist)
                    
                    detected.append({
                        'obstacle': obs,
                        'distance': noisy_dist,
                        'angle': obs_angle,
                        'true_distance': dist
                    })
        
        return detected
    
    def get_closest_detected(self, auv_pos, auv_heading_deg, obstacles):
        """Получение ближайшего обнаруженного препятствия"""
        detected = self.detect_obstacles(auv_pos, auv_heading_deg, obstacles)
        
        if not detected:
            return None
        
        return min(detected, key=lambda x: x['distance'])