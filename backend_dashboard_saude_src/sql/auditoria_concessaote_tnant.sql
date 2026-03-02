CREATE TABLE user_tenant_audit (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    tenant_id BIGINT NOT NULL,
    action ENUM('GRANTED','REVOKED') NOT NULL,
    performed_by INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);