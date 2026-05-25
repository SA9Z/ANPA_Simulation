import math

class Mission:
    """Класс для управления миссией и маршрутом 'меандр'"""
    
    def __init__(self, survey_center, zone_width, zone_height, step_x, step_y):
        self.survey_center = list(survey_center)
        self.zone_width = zone_width
        self.zone_height = zone_height
        self.step_x = step_x
        self.step_y = step_y
        
        self.waypoints = []
        self.current_waypoint_index = 0
        self.mission_complete = False
        
        self._generate_meander()
    
    def _generate_meander(self):
        """
        Генерация маршрута 'меандр' — 6 точек для полного покрытия квадрата:
        1. левый нижний угол
        2. правый нижний угол
        3. правая середина
        4. левая середина
        5. правый верхний угол
        6. финал (правый верхний угол)
        """
        self.waypoints = []
        
        # Границы выбранного квадрата
        left = self.survey_center[0] - self.zone_width / 2
        right = self.survey_center[0] + self.zone_width / 2
        bottom = self.survey_center[1] - self.zone_height / 2
        top = self.survey_center[1] + self.zone_height / 2
        
        # Середина по вертикали
        middle_y = self.survey_center[1]
        
        # Точка 1: левый нижний угол
        self.waypoints.append([left, bottom])
        
        # Точка 2: правый нижний угол
        self.waypoints.append([right, bottom])
        
        # Точка 3: правая середина (середина правой стороны)
        self.waypoints.append([right, middle_y])
        
        # Точка 4: левая середина (середина левой стороны)
        self.waypoints.append([left, middle_y])
        
        # Точка 5: правый верхний угол
        self.waypoints.append([left, top])
        
        # Точка 6: финал (остаёмся в правом верхнем углу)
        self.waypoints.append([right, top])
        
        print(f"[DEBUG] Сгенерировано {len(self.waypoints)} точек маршрута:")
        for i, wp in enumerate(self.waypoints):
            print(f"  {i+1}: ({wp[0]:.1f}, {wp[1]:.1f})")
    
    def get_current_waypoint(self):
        """Получение текущей целевой точки"""
        if self.current_waypoint_index < len(self.waypoints):
            return self.waypoints[self.current_waypoint_index]
        return None
    
    def advance_to_next_waypoint(self):
        """Переход к следующей точке маршрута"""
        self.current_waypoint_index += 1
        if self.current_waypoint_index >= len(self.waypoints):
            self.mission_complete = True
            return False
        return True
    
    def get_progress(self):
        """Получение прогресса выполнения миссии"""
        total = len(self.waypoints)
        completed = self.current_waypoint_index
        return completed, total
    
    def get_nearest_waypoint_index(self, auv_pos):
        """Получение индекса ближайшей точки маршрута"""
        if not self.waypoints:
            return 0
        
        min_dist = float('inf')
        min_idx = 0
        
        for i, wp in enumerate(self.waypoints):
            dist = math.hypot(wp[0] - auv_pos[0], wp[1] - auv_pos[1])
            if dist < min_dist:
                min_dist = dist
                min_idx = i
        
        return min_idx
    
    def reset_to_nearest_waypoint(self, auv_pos):
        """Сброс к ближайшей точке маршрута (после обхода препятствия)"""
        self.current_waypoint_index = self.get_nearest_waypoint_index(auv_pos)