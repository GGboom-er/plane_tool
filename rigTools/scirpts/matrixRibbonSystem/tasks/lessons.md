# 经验沉淀 (Lessons)

## Maya MCP & Gemini CLI 集成

- **触发条件**: 需要在 `gemini` CLI 中直接调用 Maya 工具。
- **根因**: CLI 默认不加载特定代理的 MCP 配置。
- **正确方案**: 
  - 确认 Maya MCP Server 位置: `C:\Users\yuweiming\AppData\Roaming\Python\Python311\site-packages\maya_mcp_server`
  - 在 `C:\Users\yuweiming\.gemini\mcp_config.json` 中添加服务器定义。
- **避坑规则**: `gemini` CLI (Node.js 版) 的配置文件位于 `~/.gemini/mcp_config.json`，而非 `AppData`。
