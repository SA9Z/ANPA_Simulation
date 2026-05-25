import math
import numpy as np

def norm(v):
    """Евклидова норма вектора"""
    return math.sqrt(v[0]**2 + v[1]**2)

def normalize(v):
    """Нормализация вектора"""
    n = norm(v)
    if n < 1e-6:
        return [1.0, 0.0]
    return [v[0]/n, v[1]/n]

def clamp(value, min_val, max_val):
    """Ограничение значения"""
    return max(min_val, min(value, max_val))

def cross2d(a, b):
    """Псевдоскалярное произведение (2D)"""
    return a[0]*b[1] - a[1]*b[0]

def dot(a, b):
    """Скалярное произведение"""
    return a[0]*b[0] + a[1]*b[1]

def distance(p1, p2):
    """Расстояние между двумя точками"""
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

def angle_to_vector(angle_deg):
    """Преобразование угла в градусах в вектор направления"""
    rad = math.radians(angle_deg)
    return [math.cos(rad), math.sin(rad)]

def vector_to_angle(v):
    """Преобразование вектора в угол в градусах"""
    return math.degrees(math.atan2(v[1], v[0]))

def rotate_point(point, center, angle_deg):
    """Поворот точки вокруг центра"""
    rad = math.radians(angle_deg)
    dx = point[0] - center[0]
    dy = point[1] - center[1]
    x = dx * math.cos(rad) - dy * math.sin(rad) + center[0]
    y = dx * math.sin(rad) + dy * math.cos(rad) + center[1]
    return [x, y]

def point_in_polygon(point, polygon):
    """Проверка принадлежности точки полигону (лучевой метод)"""
    x, y = point
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i+1)%n]
        if ((y1 > y) != (y2 > y)) and (x < (x2-x1)*(y-y1)/(y2-y1)+x1):
            inside = not inside
    return inside

def circle_intersects_segment(circle_center, radius, seg_start, seg_end):
    """Проверка пересечения отрезка с кругом"""
    ax, ay = seg_start
    bx, by = seg_end
    cx, cy = circle_center
    
    dx = bx - ax
    dy = by - ay
    
    if dx == 0 and dy == 0:
        return distance([ax, ay], [cx, cy]) <= radius
    
    t = ((cx - ax)*dx + (cy - ay)*dy) / (dx*dx + dy*dy)
    t = clamp(t, 0, 1)
    
    closest_x = ax + t*dx
    closest_y = ay + t*dy
    
    return distance([closest_x, closest_y], [cx, cy]) <= radius

def line_intersects_ellipse(ellipse, p1, p2):
    """Проверка пересечения отрезка с эллипсом"""
    # Преобразование в систему координат эллипса
    dx1 = p1[0] - ellipse.center[0]
    dy1 = p1[1] - ellipse.center[1]
    dx2 = p2[0] - ellipse.center[0]
    dy2 = p2[1] - ellipse.center[1]
    
    # Поворот в систему координат эллипса
    px1 = dx1 * ellipse.e1[0] + dy1 * ellipse.e1[1]
    py1 = dx1 * ellipse.e2[0] + dy1 * ellipse.e2[1]
    px2 = dx2 * ellipse.e1[0] + dy2 * ellipse.e1[1]
    py2 = dx2 * ellipse.e2[0] + dy2 * ellipse.e2[1]
    
    # Параметрическое уравнение отрезка
    def f(t):
        x = px1 + t*(px2 - px1)
        y = py1 + t*(py2 - py1)
        return (x**2 / ellipse.a**2) + (y**2 / ellipse.b**2) - 1
    
    # Проверка на концах
    if f(0) <= 0 or f(1) <= 0:
        return True
    
    # Поиск корней квадратного уравнения
    dx = px2 - px1
    dy = py2 - py1
    A = dx**2 / ellipse.a**2 + dy**2 / ellipse.b**2
    B = 2*(px1*dx / ellipse.a**2 + py1*dy / ellipse.b**2)
    C = px1**2 / ellipse.a**2 + py1**2 / ellipse.b**2 - 1
    
    D = B**2 - 4*A*C
    if D < 0:
        return False
    
    t1 = (-B - math.sqrt(D)) / (2*A)
    t2 = (-B + math.sqrt(D)) / (2*A)
    
    return (0 <= t1 <= 1) or (0 <= t2 <= 1)