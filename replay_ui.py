import pygame

class ReplayUI:
    """UI-компоненты для режима воспроизведения"""
    
    def __init__(self, screen, config):
        self.screen = screen
        self.config = config
        self.font = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)
        self.font_big = pygame.font.Font(None, 32)
        
        # Панель управления
        self.panel_height = 120
        self.panel_rect = pygame.Rect(0, config.WORLD_HEIGHT - self.panel_height, 
                                       config.WORLD_WIDTH, self.panel_height)
        
        # Ползунок
        self.slider_rect = pygame.Rect(50, config.WORLD_HEIGHT - 80, 
                                        config.WORLD_WIDTH - 100, 10)
        self.slider_handle_radius = 8
        self.dragging_slider = False
        
        # Кнопки
        self.buttons = {}
        self._create_buttons()
        
    def _create_buttons(self):
        """Создание кнопок управления"""
        w, h = 80, 30
        
        # Кнопка Play/Pause
        self.buttons['play_pause'] = {
            'rect': pygame.Rect(20, self.config.WORLD_HEIGHT - 70, w, h),
            'label': 'Пауза'
        }
        
        # Кнопка Stop
        self.buttons['stop'] = {
            'rect': pygame.Rect(110, self.config.WORLD_HEIGHT - 70, w, h),
            'label': 'Стоп'
        }
        
        # Кнопка Speed -1
        self.buttons['speed_down'] = {
            'rect': pygame.Rect(200, self.config.WORLD_HEIGHT - 70, 40, h),
            'label': '0.5x'
        }
        
        # Кнопка Speed +1
        self.buttons['speed_up'] = {
            'rect': pygame.Rect(250, self.config.WORLD_HEIGHT - 70, 40, h),
            'label': '2x'
        }
        
        # Кнопка Reset Speed
        self.buttons['speed_reset'] = {
            'rect': pygame.Rect(300, self.config.WORLD_HEIGHT - 70, 40, h),
            'label': '1x'
        }
        
        # Кнопка выхода из режима воспроизведения
        self.buttons['exit'] = {
            'rect': pygame.Rect(self.config.WORLD_WIDTH - 150, self.config.WORLD_HEIGHT - 70, 130, h),
            'label': 'Выйти (ESC)'
        }
    
    def handle_event(self, event, replay_controller):
        """Обработка событий UI"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            
            # Проверка нажатия на ползунок
            if self.slider_rect.collidepoint(mouse_pos):
                self.dragging_slider = True
                self._update_slider_position(mouse_pos, replay_controller)
                return True
            
            # Проверка нажатия на кнопки
            for btn_id, btn in self.buttons.items():
                if btn['rect'].collidepoint(mouse_pos):
                    self._handle_button(btn_id, replay_controller)
                    return True
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if self.dragging_slider:
                self.dragging_slider = False
                return True
        
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_slider:
                self._update_slider_position(event.pos, replay_controller)
                return True
        
        return False
    
    def _update_slider_position(self, mouse_pos, replay_controller):
        """Обновление позиции ползунка"""
        relative_x = max(0, min(mouse_pos[0] - self.slider_rect.x, self.slider_rect.width))
        progress = relative_x / self.slider_rect.width
        new_time = progress * replay_controller.total_duration
        replay_controller.set_time(new_time)
    
    def _handle_button(self, btn_id, replay_controller):
        """Обработка нажатия кнопок"""
        if btn_id == 'play_pause':
            replay_controller.is_playing = not replay_controller.is_playing
            self.buttons['play_pause']['label'] = 'Пауза' if replay_controller.is_playing else '▶ Пуск'
        
        elif btn_id == 'stop':
            replay_controller.set_time(0)
            replay_controller.is_playing = False
            self.buttons['play_pause']['label'] = 'Пуск'
        
        elif btn_id == 'speed_down':
            replay_controller.speed = max(0.1, replay_controller.speed / 2)
        
        elif btn_id == 'speed_up':
            replay_controller.speed = min(4.0, replay_controller.speed * 2)
        
        elif btn_id == 'speed_reset':
            replay_controller.speed = 1.0
        
        elif btn_id == 'exit':
            return False
        
        # Обновление текста кнопки скорости
        self.buttons['speed_down']['label'] = f'{replay_controller.speed/2:.1f}x' if replay_controller.speed/2 >= 0.1 else '0.1x'
        self.buttons['speed_up']['label'] = f'{replay_controller.speed*2:.1f}x' if replay_controller.speed*2 <= 4 else '4x'
    
    def draw(self, replay_controller):
        """Отрисовка UI воспроизведения"""
        # Фон панели
        pygame.draw.rect(self.screen, (0, 0, 0, 200), self.panel_rect)
        pygame.draw.rect(self.screen, (80, 80, 100), self.panel_rect, 2)
        
        # Информация о времени
        time_text = self.font.render(
            f"Время: {replay_controller.current_time:.1f} / {replay_controller.total_duration:.1f} с", 
            True, (255, 255, 255)
        )
        self.screen.blit(time_text, (20, self.config.WORLD_HEIGHT - 110))
        
        # Скорость воспроизведения
        speed_text = self.font.render(f"Скорость: {replay_controller.speed:.1f}x", True, (255, 255, 255))
        self.screen.blit(speed_text, (200, self.config.WORLD_HEIGHT - 110))
        
        # Режим
        mode = replay_controller.get_mode_at_time()
        mode_color = replay_controller.get_mode_color()
        mode_text = self.font.render(f"Режим: {mode}", True, mode_color)
        self.screen.blit(mode_text, (400, self.config.WORLD_HEIGHT - 110))
        
        # Прогресс миссии
        success = replay_controller.mission_data.get('success', False)
        progress_text = self.font.render(
            f"Миссия: {'УСПЕХ' if success else 'ПРОВАЛ'}", 
            True, (100, 255, 100) if success else (255, 100, 100)
        )
        self.screen.blit(progress_text, (600, self.config.WORLD_HEIGHT - 110))
        
        # Ползунок
        pygame.draw.rect(self.screen, (100, 100, 100), self.slider_rect)
        
        # Заполнение ползунка
        progress = replay_controller.get_progress()
        filled_width = int(self.slider_rect.width * progress)
        if filled_width > 0:
            filled_rect = pygame.Rect(self.slider_rect.x, self.slider_rect.y, 
                                       filled_width, self.slider_rect.height)
            pygame.draw.rect(self.screen, (0, 150, 255), filled_rect)
        
        # Ручка ползунка
        handle_x = self.slider_rect.x + filled_width
        handle_rect = pygame.Rect(handle_x - self.slider_handle_radius, 
                                   self.slider_rect.y - 5,
                                   self.slider_handle_radius * 2, 
                                   self.slider_rect.height + 10)
        pygame.draw.rect(self.screen, (255, 255, 255), handle_rect)
        pygame.draw.rect(self.screen, (0, 150, 255), handle_rect, 2)
        
        # Кнопки
        for btn_id, btn in self.buttons.items():
            # Фон кнопки
            pygame.draw.rect(self.screen, (50, 50, 70), btn['rect'])
            pygame.draw.rect(self.screen, (100, 100, 150), btn['rect'], 2)
            
            # Текст кнопки
            text = self.font_small.render(btn['label'], True, (255, 255, 255))
            text_rect = text.get_rect(center=btn['rect'].center)
            self.screen.blit(text, text_rect)
        
        # Отображение событий
        events = replay_controller.get_events_at_time(0.5)
        if events:
            event_y = self.config.WORLD_HEIGHT - 45
            for event in events[:2]:  # Показываем не более 2 событий
                event_text = self.font_small.render(
                    f"Событие: {event['type']}", 
                    True, (255, 200, 100)
                )
                self.screen.blit(event_text, (20, event_y))
                event_y += 18
    
    def draw_info_panel(self, replay_controller, auv_pos, ship_pos):
        """Отрисовка информационной панели (над UI воспроизведения)"""
        # Фон панели (смещён вверх, чтобы не перекрывать UI)
        panel_rect = pygame.Rect(10, 10, 260, 120)
        pygame.draw.rect(self.screen, (0, 0, 0, 180), panel_rect)
        pygame.draw.rect(self.screen, (100, 100, 100), panel_rect, 2)
        
        y_offset = 15
        
        # Режим (дублируется, но для удобства)
        mode = replay_controller.get_mode_at_time()
        mode_color = replay_controller.get_mode_color()
        mode_text = self.font.render(f"Режим: {mode}", True, mode_color)
        self.screen.blit(mode_text, (20, y_offset))
        y_offset += 25
        
        # Телеметрия
        telemetry = replay_controller.get_telemetry_at_time()
        dist_text = self.font.render(f"До преп.: {telemetry['d_min']:.1f} м", True, (255, 255, 255))
        self.screen.blit(dist_text, (20, y_offset))
        y_offset += 22
        
        tti_text = self.font.render(f"TTI: {telemetry['tti']:.1f} с", True, (255, 255, 255))
        self.screen.blit(tti_text, (20, y_offset))
        y_offset += 22
        
        energy_text = self.font.render(f"Энергия: {1000 - telemetry['energy_consumed']:.0f} / 1000", 
                                        True, (255, 255, 255))
        self.screen.blit(energy_text, (20, y_offset))

    