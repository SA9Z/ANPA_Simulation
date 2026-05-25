import json
import os
from datetime import datetime

class DataLogger:
    """Сохранение и загрузка данных миссий"""
    
    def __init__(self, save_dir="missions"):
        self.save_dir = save_dir
        self._ensure_dir()
    
    def _ensure_dir(self):
        """Создание директории для сохранения миссий"""
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            
    def save_mission(self, simulation, survey_center, duration):
        """Сохранение миссии в JSON"""
        mission_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamp = datetime.now().isoformat()
        
        # Сбор данных
        trajectory_data = []
        for point in simulation.trajectory:
            trajectory_data.append([point[0], point[1], point[2]])
        
        events = simulation.controller.get_events()
        
        # Прогресс миссии
        completed, total = 0, 0
        if simulation.mission:
            completed, total = simulation.mission.get_progress()
        
        # Сохранение ВСЕХ препятствий (статических и динамических)
        all_obstacles = []
        for obs in simulation.obstacles:
            obs_data = {
                'id': id(obs),
                'type': 'dynamic' if obs.is_moving else 'static',
                'radius': obs.radius,
                'shape': obs.shape,
                'is_moving': obs.is_moving
            }
            if obs.is_moving:
                # Сохраняем НАЧАЛЬНУЮ позицию и скорость
                # Для движущихся препятствий нужно сохранить initial_position
                if hasattr(obs, 'initial_position'):
                    obs_data['initial_position'] = obs.initial_position.copy()
                else:
                    # Если initial_position не сохранён, используем текущую позицию
                    # и вычитаем перемещение за время миссии
                    obs_data['initial_position'] = [
                        obs.position[0] - obs.velocity[0] * duration,
                        obs.position[1] - obs.velocity[1] * duration
                    ]
                obs_data['velocity'] = obs.velocity.copy()
            else:
                obs_data['position'] = obs.position.copy()
            all_obstacles.append(obs_data)
        
        mission_data = {
            "mission_id": mission_id,
            "timestamp": timestamp,
            "survey_zone": [survey_center[0], survey_center[1]],
            "duration": duration,
            "success": simulation.mission_success,
            "collision": simulation.mission_collision,
            "route_completed": completed,
            "route_total": total,
            "trajectory": trajectory_data,
            "events": events,
            "telemetry": simulation.telemetry,
            "obstacles": all_obstacles
        }
        
        filename = f"mission_{mission_id}.json"
        filepath = os.path.join(self.save_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(mission_data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def load_mission(self, filepath):
        """Загрузка данных миссии из JSON"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_missions(self):
        """Получение списка сохранённых миссий"""
        self._ensure_dir()
        missions = []
        
        for filename in os.listdir(self.save_dir):
            if filename.startswith("mission_") and filename.endswith(".json"):
                filepath = os.path.join(self.save_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    missions.append({
                        "id": data["mission_id"],
                        "timestamp": data["timestamp"],
                        "success": data["success"],
                        "duration": data["duration"],
                        "filepath": filepath
                    })
        
        return sorted(missions, key=lambda x: x["timestamp"], reverse=True)