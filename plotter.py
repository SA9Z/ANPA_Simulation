# plotter.py
import pygame
import matplotlib
matplotlib.use('Agg')  # Используем backend без GUI
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import io

class PlotWindow:
    """Окно с графиками для анализа миссии"""
    
    def __init__(self, mission_data):
        self.mission_data = mission_data
        self.fig = None
        self.surface = None
        self.visible = True
        self.generate_plots()
    
    def generate_plots(self):
        """Создание графиков на основе данных миссии"""
        telemetry = self.mission_data.get('telemetry', {})
        times = telemetry.get('time', [])
        
        if not times or len(times) < 2:
            return
        
        # Убеждаемся, что все массивы имеют одинаковую длину
        d_min_data = telemetry.get('d_min', [])
        tti_data = telemetry.get('TTI', [])
        energy_data = telemetry.get('energy_consumed', [])
        modes_data = telemetry.get('mode', [])
        
        # Обрезаем или дополняем массивы до длины times
        min_len = len(times)
        d_min_data = d_min_data[:min_len] if len(d_min_data) >= min_len else d_min_data + [999] * (min_len - len(d_min_data))
        tti_data = tti_data[:min_len] if len(tti_data) >= min_len else tti_data + [999] * (min_len - len(tti_data))
        energy_data = energy_data[:min_len] if len(energy_data) >= min_len else energy_data + [0] * (min_len - len(energy_data))
        modes_data = modes_data[:min_len] if len(modes_data) >= min_len else modes_data + ['NORMAL'] * (min_len - len(modes_data))
        
        # Создаём фигуру с одинаковой горизонтальной осью для всех графиков
        fig, axs = plt.subplots(2, 2, figsize=(8, 6))
        fig.suptitle(f"Миссия {self.mission_data.get('mission_id', 'unknown')}", fontsize=10)
        
        # 1. Расстояние до ближайшего препятствия
        axs[0, 0].plot(times, d_min_data, 'r-', linewidth=1)
        axs[0, 0].set_ylabel('м', fontsize=8)
        axs[0, 0].set_title('Дистанция до препятствия', fontsize=9)
        axs[0, 0].set_xlabel('Время, с', fontsize=8)
        axs[0, 0].tick_params(labelsize=7)
        axs[0, 0].grid(True, alpha=0.3)
        # Устанавливаем диапазон оси X от 0 до максимального времени
        axs[0, 0].set_xlim(0, max(times) if times else 1)
        
        # 2. TTI (Time to Impact)
        axs[0, 1].plot(times, tti_data, 'b-', linewidth=1)
        axs[0, 1].set_ylabel('с', fontsize=8)
        axs[0, 1].set_title('TTI (время до столкновения)', fontsize=9)
        axs[0, 1].set_xlabel('Время, с', fontsize=8)
        axs[0, 1].tick_params(labelsize=7)
        axs[0, 1].grid(True, alpha=0.3)
        axs[0, 1].set_xlim(0, max(times) if times else 1)
        
        # 3. Расход энергии
        energy_remaining = [1000 - e for e in energy_data]
        axs[1, 0].plot(times, energy_remaining, 'g-', linewidth=1)
        axs[1, 0].set_ylabel('у.е.', fontsize=8)
        axs[1, 0].set_xlabel('Время, с', fontsize=8)
        axs[1, 0].set_title('Остаток энергии', fontsize=9)
        axs[1, 0].tick_params(labelsize=7)
        axs[1, 0].grid(True, alpha=0.3)
        axs[1, 0].set_xlim(0, max(times) if times else 1)
        
        # 4. Режимы работы
        mode_map = {'NORMAL': 0, 'ATTENTION': 1, 'AVOID': 2, 'RETURN': 3}
        mode_nums = [mode_map.get(m, 0) for m in modes_data]
        axs[1, 1].step(times, mode_nums, 'm-', where='post', linewidth=1)
        axs[1, 1].set_yticks([0, 1, 2, 3])
        axs[1, 1].set_yticklabels(['NORM', 'ATT', 'AVOID', 'RET'], fontsize=7)
        axs[1, 1].set_xlabel('Время, с', fontsize=8)
        axs[1, 1].set_title('Режимы навигации', fontsize=9)
        axs[1, 1].tick_params(labelsize=7)
        axs[1, 1].grid(True, alpha=0.3)
        axs[1, 1].set_xlim(0, max(times) if times else 1)
        
        # Добавляем статистику в правый нижний угол маленьким текстом
        success = self.mission_data.get('success', False)
        duration = self.mission_data.get('duration', 0)
        total_energy = energy_data[-1] if energy_data else 0
        events = self.mission_data.get('events', [])
        
        # Текст статистики с правильным отображением статуса
        status_text = '✓ УСПЕХ' if success else '✗ ПРОВАЛ'
        stats_text = f"Статус: {status_text} | Длит.: {duration:.1f}с | Энергия: {total_energy:.0f} | Событий: {len(events)}"
        
        fig.text(0.5, 0.02, stats_text, ha='center', fontsize=8, 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.1)
        self.fig = fig
        self._convert_to_pygame_surface()
    
    def _convert_to_pygame_surface(self):
        """Конвертация matplotlib Figure в pygame Surface"""
        if self.fig is None:
            return
        
        buf = io.BytesIO()
        self.fig.savefig(buf, format='png', dpi=80, bbox_inches='tight')
        buf.seek(0)
        
        self.surface = pygame.image.load(buf)
        plt.close(self.fig)
    
    def draw(self, screen, pos=(0, 0)):
        """Отрисовка окна с графиками"""
        if self.surface and self.visible:
            screen.blit(self.surface, pos)
    
    def get_size(self):
        if self.surface:
            return self.surface.get_size()
        return (0, 0)
    
    def toggle(self):
        self.visible = not self.visible
    
    def close(self):
        if self.fig:
            plt.close(self.fig)
        self.fig = None
        self.surface = None