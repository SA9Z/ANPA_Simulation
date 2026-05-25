import json
import os
import sys

class Config:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _get_resource_path(self, relative_path):
        """Получить путь к файлу, работающий как в разработке, так и в exe"""
        try:
            # PyInstaller создает временную папку и сохраняет путь в _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        
        return os.path.join(base_path, relative_path)
    
    def _load_config(self):
        config_path = self._get_resource_path('config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
    
    def get(self, key, default=None):
        keys = key.split('.')
        value = self.data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value
    
    @property
    def WORLD_WIDTH(self): return self.get('world.width')
    @property
    def WORLD_HEIGHT(self): return self.get('world.height')
    @property
    def CELL_SIZE(self): return self.get('world.cell_size')
    @property
    def GRID_COLS(self): return self.get('world.grid_cols')
    @property
    def GRID_ROWS(self): return self.get('world.grid_rows')
    
    @property
    def AUV_LENGTH(self): return self.get('auv.length')
    @property
    def MAX_SPEED(self): return self.get('auv.max_speed')
    @property
    def TURN_RATE(self): return self.get('auv.turn_rate')
    @property
    def SENSOR_RANGE(self): return self.get('auv.sensor_range')
    @property
    def SENSOR_ANGLE(self): return self.get('auv.sensor_angle')
    
    @property
    def K(self): return self.get('navigation.k')
    @property
    def D_DETECT(self): return self.get('navigation.d_detect')
    @property
    def T_MAX(self): return self.get('navigation.t_max')
    @property
    def F_NORMAL(self): return self.get('navigation.f_normal')
    @property
    def F_ATT(self): return self.get('navigation.f_att')
    @property
    def ATTENTION_SAMPLES(self): return self.get('navigation.attention_samples')
    @property
    def R_SLID_FACTOR(self): return self.get('navigation.r_slid_factor')
    @property
    def V_CRUISE(self): return self.get('navigation.v_cruise')
    
    @property
    def MEANDER_STEP_X(self): return self.get('mission.meander_step_x')
    @property
    def MEANDER_STEP_Y(self): return self.get('mission.meander_step_y')
    @property
    def ZONE_WIDTH(self): return self.get('mission.zone_width')
    @property
    def ZONE_HEIGHT(self): return self.get('mission.zone_height')


    @property
    def FULLSCREEN(self): return self.get('window.fullscreen', False)

config = Config()