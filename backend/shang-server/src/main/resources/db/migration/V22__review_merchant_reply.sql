-- ============================================================
-- V22: 评价商家回复
-- 依据 docs/01-requirements/PRD-V2.1-评价商家回复.md
-- ============================================================

ALTER TABLE commerce.review
    ADD COLUMN IF NOT EXISTS merchant_reply TEXT,
    ADD COLUMN IF NOT EXISTS replied_at TIMESTAMPTZ;

COMMENT ON COLUMN commerce.review.merchant_reply IS '商家回复内容；NULL 表示未回复';
COMMENT ON COLUMN commerce.review.replied_at IS '最近一次商家回复时间；NULL 表示未回复';
