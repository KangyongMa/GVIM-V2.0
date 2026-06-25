import os
import sys
import asyncio
import json

# Setup sys.path to include packages/harness
harness_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "packages", "harness"))
if harness_path not in sys.path:
    sys.path.insert(0, harness_path)

from deerflow.config.extensions_config import get_extensions_config
from deerflow.mcp.cache import initialize_mcp_tools, get_cached_mcp_diagnostics
from deerflow.skills.storage import get_or_new_skill_storage
from deerflow.config.app_config import AppConfig

async def test_mcp_and_skills():
    print("================ [1] CONFIGURATION SYSTEM ================")
    config = get_extensions_config()
    print("Configured MCP Servers:")
    for name, server in config.mcp_servers.items():
        print(f"  - {name}: enabled={server.enabled}, type={server.type}, cmd={server.command}")
    
    print("\nConfigured Skills:")
    for name, skill in config.skills.items():
        print(f"  - {name}: enabled={skill.enabled}")
        
    print("\n================ [2] LOADING MCP SERVERS ================")
    # Re-initialize or load cached MCP tools
    try:
        tools = await initialize_mcp_tools()
        print(f"Successfully initialized MCP. Total loaded tools: {len(tools)}")
        for i, tool in enumerate(tools, 1):
            print(f"  {i}. [{tool.name}]: {tool.description[:60]}...")
    except Exception as e:
        print(f"Error loading MCP tools: {e}")
        
    diagnostics = get_cached_mcp_diagnostics()
    print("\nMCP Diagnostics Status:")
    print(json.dumps(diagnostics, indent=2))

    print("\n================ [3] LOADING SKILLS SYSTEM ================")
    try:
        app_config = AppConfig()
        storage = get_or_new_skill_storage(app_config=app_config)
        skills = storage.load_skills(enabled_only=False)
        print(f"Total skills available in workspace: {len(skills)}")
        enabled_skills = [s for s in skills if s.enabled]
        print(f"Total enabled skills: {len(enabled_skills)}")
        for s in enabled_skills:
            print(f"  - [{s.name}]: category={s.category}, desc={s.description[:60]}...")
    except Exception as e:
        print(f"Error loading skills: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_and_skills())
