-- 模版标签两级结构：大标签 + 小标签
-- 执行前请备份 template_tags 表

ALTER TABLE template_tags
  ADD COLUMN parent_id INT NULL AFTER name,
  ADD COLUMN sort_order INT NOT NULL DEFAULT 0 AFTER parent_id,
  ADD COLUMN parent_key INT AS (IFNULL(parent_id, 0)) STORED AFTER sort_order,
  ADD INDEX idx_template_tags_parent_id (parent_id);

ALTER TABLE template_tags
  DROP INDEX uq_template_tags_name;

CREATE UNIQUE INDEX uq_template_tags_parent_key_name ON template_tags (parent_key, name);

ALTER TABLE template_tags
  ADD CONSTRAINT fk_template_tags_parent
    FOREIGN KEY (parent_id) REFERENCES template_tags (id)
    ON DELETE CASCADE;
