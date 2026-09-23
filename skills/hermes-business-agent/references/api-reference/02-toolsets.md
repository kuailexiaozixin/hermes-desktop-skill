# toolsets — 工具集注册与解析

> **模块**: `toolsets.py`
> **来源**: 本机已装 `hermes-agent 0.19.0` 源码（ast 静态解析，未 import）
> **说明**: 工具集（toolset）的注册、解析、校验与创建。

## 模块文档

Toolsets Module

This module provides a flexible system for defining and managing tool aliases/toolsets.
Toolsets allow you to group tools together for specific scenarios and can be composed
from individual tools or other toolsets.

Features:
- Define custom toolsets with specific tools
- Compose toolsets from other toolsets
- Built-in common toolsets for typical use cases
- Easy extension for new toolsets
- Support for dynamic toolset resolution

Usage:
    from toolsets import get_toolset, resolve_toolset, get_all_toolsets
    
    # Get tools for a specific toolset
    tools = get_toolset("research")
    
    # Resolve a toolset to get all tool names (including from composed toolsets)
    all_tools = resolve_toolset("full_stack")

### 模块文档

Toolsets Module

This module provides a flexible system for defining and managing tool aliases/toolsets.
Toolsets allow you to group tools together for specific scenarios and can be composed
from individual tools or other toolsets.

Features:
- Define custom toolsets with specific tools
- Compose toolsets from other toolsets
- Built-in common toolsets for typical use cases
- Easy extension for new toolsets
- Support for dynamic toolset resolution

Usage:
    from toolsets import get_toolset, resolve_toolset, get_all_toolsets
    
    # Get tools for a specific toolset
    tools = get_toolset("research")
    
    # Resolve a toolset to get all tool names (including from composed toolsets)
    all_tools = resolve_toolset("full_stack")

### 顶层函数

#### def `get_toolset(name: str, include_registry: bool = True) -> Optional[Dict[str, Any]]`

Get a toolset definition by name.

Args:
    name (str): Name of the toolset
    include_registry (bool): When True (default), merge in tools that
        plugins/overlays registered into this toolset via the registry.
        When False, return only the static ``TOOLSETS`` definition (the
        composite-authored view). Platform reverse-mapping in
        ``_get_platform_tools`` uses False so that a tool registered into a
        toolset but absent from a platform's static composite does not drop
        the whole toolset from inference. See issue #49622.

Returns:
    Dict: Toolset definition with description, tools, and includes
    None: If toolset not found. With include_registry=False the static
        view only recognizes names literally present in ``TOOLSETS``, so
        registry/MCP-only toolsets AND registry-derived aliases return None
        (they have no static counterpart).

#### def `bundle_non_core_tools(toolset_name: str) -> Set[str]`

Return a ``hermes-*`` bundle's platform-specific tools, excluding core.

Platform bundles are defined as ``_HERMES_CORE_TOOLS + [platform extras]``.
When a bundle name appears in ``disabled_toolsets``, subtracting the whole
bundle would strip core tools (terminal, read_file, …) shared by every
other enabled toolset, emptying the model's tool list (#33924). This
returns only the bundle's non-core delta (its own extras plus those of any
one-level ``includes``), so disabling a bundle removes its platform tools
while leaving core intact.

Bundle nesting is one level deep in practice (only ``hermes-gateway``
includes other bundles, and those leaves don't nest further), so a single
``includes`` pass is sufficient. Unknown/garbage names fall back to the
full resolution minus core — never re-introducing the core wipe.

#### def `resolve_toolset(name: str, visited: Set[str] = None, include_registry: bool = True) -> List[str]`

Recursively resolve a toolset to get all tool names.

This function handles toolset composition by recursively resolving
included toolsets and combining all tools.

Args:
    name (str): Name of the toolset to resolve
    visited (Set[str]): Set of already visited toolsets (for cycle detection)
    include_registry (bool): When True (default), include tools that
        plugins/overlays registered into a toolset. When False, resolve only
        the static ``TOOLSETS`` definition (includes are still resolved, but
        statically). Platform reverse-mapping uses False so a registry-added
        tool cannot drop the whole toolset from inference (see #49622 and
        ``_get_platform_tools``).

Returns:
    List[str]: List of all tool names in the toolset

#### def `resolve_multiple_toolsets(toolset_names: List[str]) -> List[str]`

Resolve multiple toolsets and combine their tools.

Args:
    toolset_names (List[str]): List of toolset names to resolve
    
Returns:
    List[str]: Combined list of all tool names (deduplicated)

#### def `get_all_toolsets() -> Dict[str, Dict[str, Any]]`

Get all available toolsets with their definitions.

Includes both statically-defined toolsets and plugin-registered ones.

Returns:
    Dict: All toolset definitions

#### def `get_toolset_names() -> List[str]`

Get names of all available toolsets (excluding aliases).

Includes plugin-registered toolset names.

Returns:
    List[str]: List of toolset names

#### def `validate_toolset(name: str) -> bool`

Check if a toolset name is valid.

Args:
    name (str): Toolset name to validate
    
Returns:
    bool: True if valid, False otherwise

#### def `create_custom_toolset(name: str, description: str, tools: List[str] = None, includes: List[str] = None) -> None`

Create a custom toolset at runtime.

Args:
    name (str): Name for the new toolset
    description (str): Description of the toolset
    tools (List[str]): Direct tools to include
    includes (List[str]): Other toolsets to include

#### def `get_toolset_info(name: str) -> Dict[str, Any]`

Get detailed information about a toolset including resolved tools.

Args:
    name (str): Toolset name
    
Returns:
    Dict: Detailed toolset information

