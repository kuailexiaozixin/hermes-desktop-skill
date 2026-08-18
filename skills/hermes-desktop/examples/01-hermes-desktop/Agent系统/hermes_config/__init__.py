"""hermes_config.py — Hermes Desktop 通用底座的「配置与数据层」

职责（与业务完全解耦，任何桌面应用都可原样复用）：
  1. HERMES_HOME 定位：进程内 Library 模式下 AIAgent 读取 skills / config.yaml /
     memories 的根目录。frozen(EXE) → EXE 同目录 hermes_data；dev → 项目目录 .hermes_data。
  2. config.yaml 读 / 深合并写 / 全量覆盖写（删除键场景）。
  3. VENDOR_PRESETS：36 家厂商的原生 Hermes provider id + base_url + 候选模型，
     数据源为 hermes-llms-full.txt（HARD-GATE），供设置中心「模型」面板下拉。
  4. llm.json 多模型管理：增删改查 + 活动模型 + 采样/推理强度透传。
  5. 技能（skills/<name>/SKILL.md）CRUD + 启停。
  6. MCP servers 增删改查启停。
  7. Cron 定时任务（HERMES_HOME/cron/jobs.json）。
  8. materialize_hermes_env()：把上述环境一次性落地，供 main.py 启动时调用。

设计原则：尽量用原生 Hermes 概念（provider id / config.yaml 结构 / SKILL.md 目录），
非必要不自创；所有写操作都走深合并，绝不抹掉 config.yaml 中其它键。
"""

# 拆包后统一 re-export，保持 `import x as m; m.xxx` 完全兼容

from ._paths import (VENDOR_PRESETS, DEFAULT_VENDOR, DEFAULT_MODEL, DEFAULT_SKILLS_DIR, NO_BUNDLED_MARKER, get_hermes_home, project_root, output_dir, read_config_yaml, update_config_yaml)
from ._env import (get_env_value, set_env_value)
from ._models import (write_model_routes, ensure_default_web_search_backend, get_web_search_status, get_llm_config, save_llm_config, get_models_list, save_models_list, get_active_model_cfg, reasoning_effort_to_config, read_agent_settings, write_agent_settings, get_loop_max_iterations)
from ._skills import (ensure_default_skills, get_disabled_skills_set, set_skill_enabled, list_skills, read_skill, create_skill, update_skill, delete_skill)
from ._mcp import (list_mcp_servers, upsert_mcp_server, remove_mcp_server, set_mcp_enabled, trigger_mcp_discovery)
from ._data import (list_jobs, add_job, update_job, delete_job, set_job_status, materialize_hermes_env, get_soul, save_soul, MEMORY_FILES, list_memory, save_memory, get_system_prompt, save_system_prompt, list_wiki, get_wiki, save_wiki, delete_wiki, CHANNELS, get_channels, save_channel, get_kanban, add_kanban_task)

