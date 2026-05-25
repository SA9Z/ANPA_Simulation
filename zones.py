import math
from utils import dot, norm, normalize, distance, circle_intersects_segment, line_intersects_ellipse

class CircularZone:
    """Круговая зона безопасности"""
    
    def __init__(self, center, radius):
        self.center = list(center)
        self.radius = radius
        self.type = 'circle'
    
    def contains_point(self, point):
        """Проверка принадлежности точки зоне"""
        return distance(point, self.center) <= self.radius
    
    def intersects_segment(self, p1, p2):
        """Проверка пересечения отрезка с зоной"""
        return circle_intersects_segment(self.center, self.radius, p1, p2)
    
    def distance_to_boundary(self, point):
        """Расстояние от точки до границы зоны (отрицательное внутри)"""
        return distance(point, self.center) - self.radius
    
    def get_repulsion_vector(self, point):
        """Вектор отталкивания от центра зоны"""
        d = distance(point, self.center)
        if d < 1e-6:
            return [1.0, 0.0]
        return normalize([point[0] - self.center[0], point[1] - self.center[1]])
    
    def get_tangent_vector(self, point, sigma, goal=None):
        """Получение касательного вектора к зоне"""
        dx = point[0] - self.center[0]
        dy = point[1] - self.center[1]
        
        # Нормаль от центра к точке
        normal = normalize([dx, dy])
        
        # Касательная (перпендикуляр к нормали)
        if sigma == 1:  # левая касательная (против часовой стрелки)
            tangent = [-normal[1], normal[0]]
        else:  # правая касательная (по часовой стрелке)
            tangent = [normal[1], -normal[0]]
        
        return tangent
    
    def draw(self, screen, to_screen, color, alpha=128):
        """Отрисовка зоны (реализуется в visualization)"""
        pass


class EllipticalZone:
    """Эллиптическая зона безопасности (для движущихся препятствий)"""
    
    def __init__(self, center, a, b, e1, e2):
        self.center = list(center)
        self.a = a  # большая полуось
        self.b = b  # малая полуось
        self.e1 = list(e1)  # единичный вектор большой оси
        self.e2 = list(e2)  # единичный вектор малой оси
        self.type = 'ellipse'
    
    def _to_local(self, point):
        """Преобразование в локальную систему координат эллипса"""
        dx = point[0] - self.center[0]
        dy = point[1] - self.center[1]
        x = dx * self.e1[0] + dy * self.e1[1]
        y = dx * self.e2[0] + dy * self.e2[1]
        return x, y
    
    def contains_point(self, point):
        """Проверка принадлежности точки зоне"""
        x, y = self._to_local(point)
        return (x**2 / self.a**2) + (y**2 / self.b**2) <= 1
    
    def intersects_segment(self, p1, p2):
        """Проверка пересечения отрезка с зоной"""
        return line_intersects_ellipse(self, p1, p2)
    
    def distance_to_boundary(self, point):
        """Приближённое расстояние до границы эллипса"""
        if self.contains_point(point):
            return -1.0
        # Упрощённая оценка
        x, y = self._to_local(point)
        return math.sqrt(x**2 + y**2) - self.a
    
    def get_repulsion_vector(self, point):
        """Вектор отталкивания от эллипса (градиент)"""
        x, y = self._to_local(point)
        
        # Градиент в локальной системе
        if abs(x) < 1e-6 and abs(y) < 1e-6:
            gx, gy = 1.0, 0.0
        else:
            gx = 2*x / self.a**2
            gy = 2*y / self.b**2
        
        # Нормализация и преобразование в мировую систему
        norm_g = math.sqrt(gx**2 + gy**2)
        if norm_g < 1e-6:
            return normalize([point[0] - self.center[0], point[1] - self.center[1]])
        
        gx /= norm_g
        gy /= norm_g
        
        # Преобразование в мировые координаты
        world_gx = gx * self.e1[0] + gy * self.e2[0]
        world_gy = gx * self.e1[1] + gy * self.e2[1]
        
        return normalize([world_gx, world_gy])
    
    def get_tangent_vector(self, point, sigma, goal=None):
        """Получение касательного вектора к эллипсу"""
        x, y = self._to_local(point)
        
        # Нормаль к эллипсу в локальной системе
        nx = 2*x / self.a**2
        ny = 2*y / self.b**2
        norm_n = math.sqrt(nx**2 + ny**2)
        
        if norm_n < 1e-6:
            return normalize([-self.e2[0], -self.e2[1]])
        
        nx /= norm_n
        ny /= norm_n
        
        # Касательная (перпендикуляр к нормали)
        if sigma == 1:  # левая касательная
            tx = -ny
            ty = nx
        else:  # правая касательная
            tx = ny
            ty = -nx
        
        # Преобразование в мировые координаты
        world_tx = tx * self.e1[0] + ty * self.e2[0]
        world_ty = tx * self.e1[1] + ty * self.e2[1]
        
        return normalize([world_tx, world_ty])
    
    def draw(self, screen, to_screen, color, alpha=128):
        """Отрисовка зоны (реализуется в visualization)"""
        pass