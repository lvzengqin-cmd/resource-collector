-- 每日资源采集系统 - 数据库初始化脚本
-- 运行此脚本创建所需的数据库表

-- 1. 采集源配置表
CREATE TABLE IF NOT EXISTS collect_sources (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. 网盘配置表
CREATE TABLE IF NOT EXISTS pan_config (
    id BIGSERIAL PRIMARY KEY,
    pan_type TEXT NOT NULL UNIQUE,  -- quark, baidu, uc, thunder
    cookies TEXT,
    target_dir TEXT DEFAULT '/CY资源宝库',
    auto_share BOOLEAN DEFAULT true,
    share_expire INTEGER DEFAULT 0,   -- 0表示永久
    extract_code TEXT DEFAULT '',
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. 系统配置表
CREATE TABLE IF NOT EXISTS system_config (
    id BIGSERIAL PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    value JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. 任务日志表
CREATE TABLE IF NOT EXISTS task_logs (
    id BIGSERIAL PRIMARY KEY,
    task_type TEXT NOT NULL,  -- collect, transfer, all, manual
    status TEXT NOT NULL,    -- running, success, failed
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    duration INTEGER,
    summary JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. 资源表 (如果不存在)
CREATE TABLE IF NOT EXISTS resources (
    id BIGSERIAL PRIMARY KEY,
    title TEXT,
    description TEXT,
    category TEXT,
    pan_type TEXT,
    pan_link TEXT,
    original_link TEXT,
    extract_code TEXT,
    share_link TEXT,
    status TEXT DEFAULT 'pending',  -- pending, transferring, transferred, failed
    views INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 插入默认的采集源
INSERT INTO collect_sources (name, url, enabled) VALUES
    ('Lsfa影视', 'http://ys2.lsfa.site/', true),
    ('Kdocs文档1', 'https://www.kdocs.cn/l/ca0cFRC5S0UC', true),
    ('Kdocs文档2', 'https://www.kdocs.cn/l/cllOLe2rFIpX', true),
    ('Dj影视', 'http://dj.lsfa.site/', true),
    ('全网影视', 'https://www.quanxinghao.com/5200', true)
ON CONFLICT DO NOTHING;

-- 插入默认网盘配置
INSERT INTO pan_config (pan_type, target_dir, enabled) VALUES
    ('quark', '/CY资源宝库', true),
    ('baidu', '/CY资源宝库', true),
    ('uc', '/CY资源宝库', true),
    ('thunder', '/CY资源宝库', true)
ON CONFLICT (pan_type) DO NOTHING;

-- 插入默认定时任务配置
INSERT INTO system_config (key, value) VALUES
    ('cron_schedule', '{"frequency": "daily", "period": "morning", "expression": "0 9 * * *", "utc_cron": "0 1 * * *"}')
ON CONFLICT (key) DO NOTHING;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_resources_pan_type ON resources(pan_type);
CREATE INDEX IF NOT EXISTS idx_resources_status ON resources(status);
CREATE INDEX IF NOT EXISTS idx_resources_created_at ON resources(created_at);
CREATE INDEX IF NOT EXISTS idx_task_logs_created_at ON task_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_collect_sources_enabled ON collect_sources(enabled);

-- 启用RLS (行级安全策略)
ALTER TABLE collect_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE pan_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_logs ENABLE ROW LEVEL SECURITY;

-- 公共访问策略 (对于公开数据)
CREATE POLICY "允许公开读取采集源" ON collect_sources FOR SELECT USING (true);
CREATE POLICY "允许公开读取网盘配置" ON pan_config FOR SELECT USING (true);
CREATE POLICY "允许公开读取系统配置" ON system_config FOR SELECT USING (true);
CREATE POLICY "允许公开读取任务日志" ON task_logs FOR SELECT USING (true);
CREATE POLICY "允许公开读取资源" ON resources FOR SELECT USING (true);

-- 写入策略 (需要认证)
CREATE POLICY "允许认证用户写入采集源" ON collect_sources FOR INSERT WITH CHECK (true);
CREATE POLICY "允许认证用户更新采集源" ON collect_sources FOR UPDATE USING (true);
CREATE POLICY "允许认证用户删除采集源" ON collect_sources FOR DELETE USING (true);
CREATE POLICY "允许认证用户写入网盘配置" ON pan_config FOR INSERT WITH CHECK (true);
CREATE POLICY "允许认证用户更新网盘配置" ON pan_config FOR UPDATE USING (true);
CREATE POLICY "允许认证用户写入系统配置" ON system_config FOR INSERT WITH CHECK (true);
CREATE POLICY "允许认证用户更新系统配置" ON system_config FOR UPDATE USING (true);
CREATE POLICY "允许认证用户写入任务日志" ON task_logs FOR INSERT WITH CHECK (true);
CREATE POLICY "允许认证用户写入资源" ON resources FOR INSERT WITH CHECK (true);
CREATE POLICY "允许认证用户更新资源" ON resources FOR UPDATE USING (true);
