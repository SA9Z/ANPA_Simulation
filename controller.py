import math
from utils import normalize, clamp, cross2d, dot, distance, vector_to_angle, angle_to_vector

class NavigationController:
    """Ядро алгоритма локальной навигации с событийно-временной логикой"""
    
    MODE_NORMAL = "NORMAL"
    MODE_ATTENTION = "ATTENTION"
    MODE_AVOID = "AVOID"
    MODE_RETURN = "RETURN"
    
    def __init__(self, config):
        self.config = config
        
        # Параметры навигации
        self.k = config.K
        self.d_detect = config.D_DETECT
        self.t_max = config.T_MAX
        self.f_normal = config.F_NORMAL
        self.f_att = config.F_ATT
        self.attention_samples = config.ATTENTION_SAMPLES
        self.r_slid = config.R_SLID_FACTOR * config.D_DETECT
        self.v_cruise = config.V_CRUISE
        
        # Состояние
        self.mode = self.MODE_NORMAL
        self.active_obstacle = None
        self.sigma = 1  # 1 = левый обход, -1 = правый
        self.use_ellipse = False
        
        # Временные метки для событий
        self.t_detect = 0
        self.attention_counter = 0
        
        # Журнал событий
        self.events = []
        
        # Для возврата на маршрут
        self.return_target = None
    
    def reset(self):
        """Сброс состояния контроллера"""
        self.mode = self.MODE_NORMAL
        self.active_obstacle = None
        self.sigma = 1
        self.use_ellipse = False
        self.t_detect = 0
        self.attention_counter = 0
        self.events = []
        self.return_target = None
    
    def select_active_obstacle(self, auv_pos, obstacles):
        """Выбор активного препятствия (ближайшее к аппарату)"""
        if not obstacles:
            return None
        
        min_d = float('inf')
        active = None
        
        for obs in obstacles:
            zone = obs.get_active_zone()
            d = zone.distance_to_boundary(auv_pos)
            
            if d < min_d:
                min_d = d
                active = obs
        
        return active
    
    def check_visibility(self, auv_pos, goal_pos, zone):
        """Проверка прямой видимости цели"""
        # Проверка пересечения отрезка [auv_pos, goal_pos] с зоной безопасности
        return not zone.intersects_segment(auv_pos, goal_pos)
    
    def choose_side(self, auv_pos, goal_pos, obstacle):
        """Выбор стороны обхода"""
        obs_pos = obstacle.position
        zone = obstacle.get_active_zone()
        
        # Ось симметрии: направление от препятствия к цели
        e_og = normalize([goal_pos[0] - obs_pos[0], goal_pos[1] - obs_pos[1]])
        
        # Радиальный вектор от препятствия к аппарату
        e_ov = normalize([auv_pos[0] - obs_pos[0], auv_pos[1] - obs_pos[1]])
        
        # Определение стороны по знаку псевдоскалярного произведения
        sigma = 1 if cross2d(e_og, e_ov) >= 0 else -1
        
        return sigma
    
    def get_tangent_vector(self, auv_pos, obstacle, sigma):
        """Получение касательного вектора к зоне безопасности"""
        zone = obstacle.get_active_zone()
        return zone.get_tangent_vector(auv_pos, sigma)
    
    def compute_desired_direction(self, auv_pos, goal_pos, obstacles):
        """Формирование желаемого направления G(t)"""
        # Выбор активного препятствия
        self.active_obstacle = self.select_active_obstacle(auv_pos, obstacles)
        
        # Без препятствий - движение к цели
        if self.active_obstacle is None:
            return normalize([goal_pos[0] - auv_pos[0], goal_pos[1] - auv_pos[1]])
        
        obs = self.active_obstacle
        zone = obs.get_active_zone()
        
        # Расстояние до центра препятствия
        dist_to_center = distance(auv_pos, obs.position)
        
        # Проверка нахождения внутри зоны безопасности
        inside_zone = zone.contains_point(auv_pos)
        d = zone.distance_to_boundary(auv_pos)
        
        # Приоритет 1: Аварийное отталкивание (внутри зоны)
        if inside_zone or d < 0:
            G_rep = zone.get_repulsion_vector(auv_pos)
            return G_rep
        
        # Проверка видимости цели
        visible = self.check_visibility(auv_pos, goal_pos, zone)
        
        # Приоритет 2: Прямая видимость
        if visible:
            G_goal = normalize([goal_pos[0] - auv_pos[0], goal_pos[1] - auv_pos[1]])
            return G_goal
        
        # Приоритет 3: Обход препятствия (цель экранирована)
        # Выбор стороны обхода
        if self.mode == self.MODE_ATTENTION:
            # В режиме ATTENTION определяем сторону
            self.sigma = self.choose_side(auv_pos, goal_pos, obs)
        
        G_tan = self.get_tangent_vector(auv_pos, obs, self.sigma)
        G_rep = zone.get_repulsion_vector(auv_pos)
        
        # Расчёт коэффициента смеси для плавного перехода
        dist_to_boundary = zone.distance_to_boundary(auv_pos)
        
        if dist_to_boundary >= self.r_slid:
            # Чистая касательная
            return G_tan
        elif dist_to_boundary > 0:
            # Переходная полоса
            alpha = clamp(dist_to_boundary / (self.r_slid - 0), 0, 1)
            mixed = [
                alpha * G_tan[0] + (1 - alpha) * G_rep[0],
                alpha * G_tan[1] + (1 - alpha) * G_rep[1]
            ]
            return normalize(mixed)
        else:
            # Отталкивание
            return G_rep
    
    def update(self, auv_pos, auv_heading, goal_pos, obstacles, dt, current_time):
        """Обновление состояния контроллера и обработка событий"""
        # Выбор активного препятствия
        active = self.select_active_obstacle(auv_pos, obstacles)
        
        # Обработка событий в зависимости от режима
        if self.mode == self.MODE_NORMAL:
            # Проверка события ObjectDetected
            if active is not None:
                zone = active.get_active_zone()
                d = zone.distance_to_boundary(auv_pos)
                
                if d < self.d_detect:
                    self.mode = self.MODE_ATTENTION
                    self.t_detect = current_time
                    self.attention_counter = 0
                    self.active_obstacle = active
                    
                    self._add_event("ObjectDetected", current_time, {
                        "id": id(active),
                        "d": d,
                        "pos": list(active.position)
                    })
        
        elif self.mode == self.MODE_ATTENTION:
            # Накопление измерений для классификации
            self.attention_counter += 1
            
            # Проверка временного лимита
            if current_time - self.t_detect > self.t_max:
                self.mode = self.MODE_RETURN
                self._add_event("TimeLimit", current_time, {"t_max": self.t_max})
                return self.compute_desired_direction(auv_pos, goal_pos, obstacles)
            
            # Достаточно измерений для классификации
            if self.attention_counter >= self.attention_samples and active is not None:
                # Классификация: использование эллипса для движущихся препятствий
                if active.is_moving:
                    self.use_ellipse = True
                    active.enable_ellipse(self.v_cruise)
                else:
                    self.use_ellipse = False
                
                # Выбор стороны обхода
                if active is not None:
                    self.sigma = self.choose_side(auv_pos, goal_pos, active)
                
                self.mode = self.MODE_AVOID
                self._add_event("Classified", current_time, {
                    "sigma": self.sigma,
                    "use_ellipse": self.use_ellipse,
                    "is_moving": active.is_moving if active else False
                })
        
        elif self.mode == self.MODE_AVOID:
            # Проверка временного лимита
            if current_time - self.t_detect > self.t_max:
                self.mode = self.MODE_RETURN
                self._add_event("TimeLimit", current_time, {"t_max": self.t_max})
                return self.compute_desired_direction(auv_pos, goal_pos, obstacles)
            
            # Проверка события ObstaclePassed
            if active is None:
                # Препятствие больше не обнаружено
                self.mode = self.MODE_RETURN
                self._add_event("ObstaclePassed", current_time, {"id": 0, "d": 999})
                self.return_target = goal_pos
            else:
                zone = active.get_active_zone()
                d = zone.distance_to_boundary(auv_pos)
                
                # Дополнительная проверка: цель видна И мы достаточно далеко от препятствия
                visible = self.check_visibility(auv_pos, goal_pos, zone)
                
                if d >= self.d_detect and visible:
                    self.mode = self.MODE_RETURN
                    self._add_event("ObstaclePassed", current_time, {
                        "id": id(active),
                        "d": d
                    })
                    self.return_target = goal_pos
        
        elif self.mode == self.MODE_RETURN:
            # Возврат на маршрут - движение к цели
            # Проверка достижения цели (будет обработана в simulation)
            pass
        
        # Вычисление желаемого направления
        return self.compute_desired_direction(auv_pos, goal_pos, obstacles)
    
    def _add_event(self, event_type, time, params):
        """Добавление события в журнал"""
        self.events.append({
            "type": event_type,
            "t": time,
            "params": params
        })
    
    def get_events(self):
        """Получение списка событий"""
        return self.events
    
    def get_current_frequency(self):
        """Получение текущей частоты управления"""
        if self.mode in [self.MODE_ATTENTION, self.MODE_AVOID]:
            return self.f_att
        return self.f_normal