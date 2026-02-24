CREATE TABLE IF NOT EXISTS system_settings (
  id INT PRIMARY KEY DEFAULT 1,
  app_name VARCHAR(120) NOT NULL DEFAULT 'Dashboard Saúde',
  default_language VARCHAR(10) NOT NULL DEFAULT 'pt-BR',
  timezone VARCHAR(64) NOT NULL DEFAULT 'America/Sao_Paulo',
  enable_notifications TINYINT(1) NOT NULL DEFAULT 1,
  enable_audit_log TINYINT(1) NOT NULL DEFAULT 1,
  data_refresh_minutes INT NOT NULL DEFAULT 15,
  maps_default_zoom INT NOT NULL DEFAULT 6,

  updated_by_user_id INT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT chk_single_row CHECK (id = 1),
  CONSTRAINT fk_settings_user FOREIGN KEY (updated_by_user_id) REFERENCES user(id)
) ENGINE=InnoDB;

INSERT IGNORE INTO system_settings (id) VALUES (1);
----------------
CREATE TABLE IF NOT EXISTS user_profile (
  user_id INT PRIMARY KEY,
  phone VARCHAR(30) NULL,
  location VARCHAR(120) NULL,
  about TEXT NULL,
  avatar_url VARCHAR(255) NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_profile_user FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
) ENGINE=InnoDB;