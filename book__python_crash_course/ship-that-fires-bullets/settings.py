class Settings:
    """A class to store all settings for Alien Invasion."""

    def __init__(self):
        # Screen settings
        self.screen_with = 1200
        self.screen_height = 800
        self.bg_color = (255, 255, 255)
        self.ship_speed = 1.0
        self.ship_limit = 3
        self.alien_speed = 1.0
        self.fleet_drop_speed = 10
        #  1 -> right
        # -1 -> left
        self.fleet_direction = 1

        # Bullet
        self.bullet_speed = 1
        self.bullet_width = 3
        self.bullet_height = 15
        self.bullet_color = (60, 60, 60)
        self.bullet_allowed = 3