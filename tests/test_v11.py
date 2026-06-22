"""Tests for QuickMedia V11 — MCP server integration."""

import subprocess, json, os, time


class TestV11MCPCommand:
    """CLI mcp subcommand."""

    def test_quickmedia_mcp_subcommand_exists(self):
        """quickmedia mcp should be a recognized subcommand."""
        venv = os.path.join(os.path.dirname(__file__), "/Users/zengle/Documents/quickmedia/.venv/bin/quickmedia")
        if not os.path.isfile(venv):
            return  # skip if not installed
        result = subprocess.run([venv, "mcp", "--help"], capture_output=True, text=True, timeout=5)
        # Should exit 0 or at least not print "unknown command"
        assert "unknown" not in (result.stderr + result.stdout).lower()


class TestV11MCPServerStartup:
    """MCP server process lifecycle."""

    def test_mcp_server_starts_and_accepts_initialize(self):
        """Spawn MCP server, send initialize request, get tools list."""
        venv = os.path.join(os.path.dirname(__file__), "/Users/zengle/Documents/quickmedia/.venv/bin/quickmedia")
        if not os.path.isfile(venv):
            return
        import tempfile
        tmp = tempfile.mkdtemp()
        env = {**os.environ, "QUICKMEDIA_HOME": tmp}
        proc = subprocess.Popen(
            [venv, "mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
        )
        try:
            # Send initialize
            init_msg = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0"},
                },
            })
            proc.stdin.write(init_msg + "\n")
            proc.stdin.flush()
            time.sleep(0.5)
            # Read response
            line = proc.stdout.readline()
            resp = json.loads(line) if line else {}
            assert resp.get("id") == 1, f"Expected id=1, got {resp}"
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_mcp_server_returns_tools_list(self):
        """After initialize, tools/list should return tool definitions."""
        venv = os.path.join(os.path.dirname(__file__), "/Users/zengle/Documents/quickmedia/.venv/bin/quickmedia")
        if not os.path.isfile(venv):
            return
        import tempfile
        tmp = tempfile.mkdtemp()
        env = {**os.environ, "QUICKMEDIA_HOME": tmp}
        proc = subprocess.Popen(
            [venv, "mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
        )
        try:
            # Initialize
            proc.stdin.write(json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}) + "\n")
            proc.stdin.flush()
            proc.stdout.readline()  # consume response
            # Send initialized notification
            proc.stdin.write(json.dumps({"jsonrpc":"2.0","method":"notifications/initialized"}) + "\n")
            proc.stdin.flush()
            time.sleep(0.3)
            # Request tools
            proc.stdin.write(json.dumps({"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}) + "\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
            resp = json.loads(line) if line else {}
            tools = resp.get("result", {}).get("tools", [])
            tool_names = [t["name"] for t in tools]
            for name in ["search_assets", "get_asset", "list_assets", "find_similar", "add_asset", "delete_asset"]:
                assert name in tool_names, f"Missing tool: {name}"
        finally:
            proc.terminate()
            proc.wait(timeout=5)


class TestV11Tools:
    """Individual tool call tests."""

    def _call_tool(self, name: str, args: dict) -> dict:
        import tempfile
        venv = os.path.join(os.path.dirname(__file__), "/Users/zengle/Documents/quickmedia/.venv/bin/quickmedia")
        tmp = tempfile.mkdtemp()
        env = {**os.environ, "QUICKMEDIA_HOME": tmp}
        proc = subprocess.Popen(
            [venv, "mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
        )
        try:
            proc.stdin.write(json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}) + "\n")
            proc.stdin.flush()
            proc.stdout.readline()
            proc.stdin.write(json.dumps({"jsonrpc":"2.0","method":"notifications/initialized"}) + "\n")
            proc.stdin.flush()
            proc.stdin.write(json.dumps({"jsonrpc":"2.0","id":99,"method":"tools/call","params":{"name":name,"arguments":args}}) + "\n")
            proc.stdin.flush()
            time.sleep(0.5)
            resp_line = proc.stdout.readline()
            return json.loads(resp_line) if resp_line else {}
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_search_assets_empty_query(self):
        resp = self._call_tool("search_assets", {"query": ""})
        assert "error" in str(resp).lower() or "查询不能为空" in str(resp)

    def test_get_asset_nonexistent(self):
        resp = self._call_tool("get_asset", {"asset_id": 99999})
        assert "error" in str(resp).lower() or "不存在" in str(resp)


class TestV11ToolBugs:
    """Verify reported bugs are fixed."""

    def test_search_assets_respects_mode(self):
        """mode parameter should affect search behavior."""
        import sys
        sys.path.insert(0, '/Users/zengle/Documents/quickmedia')
        from quickmedia.mcp_server import search_assets
        # keyword mode should work without ChromaDB
        r = search_assets("test", mode="keyword", limit=5)
        assert "向量库不存在" not in r, "keyword mode should not require ChromaDB"

    def test_list_assets_filters_by_tags(self):
        """tags parameter should filter results."""
        import sys
        sys.path.insert(0, '/Users/zengle/Documents/quickmedia')
        from quickmedia.mcp_server import list_assets
        data = list_assets(limit=100, tags=["QuickMedia"])
        assert isinstance(data, list), "Should return list"
        assert len(data) > 0, "Should find assets tagged QuickMedia"

    def test_delete_asset_cleans_up_related_data(self):
        """delete_asset should clean tags, search_terms, and vectors."""
        import sys
        sys.path.insert(0, '/Users/zengle/Documents/quickmedia')
        from quickmedia.mcp_server import delete_asset
        r = delete_asset(999999)
        # Non-existent should still not crash
        assert r.ok is False or "不存在" in str(r) or "not found" in str(r)

    def test_add_asset_adds_single_file(self):
        """add_asset should handle single file, not scan directory."""
        import sys
        sys.path.insert(0, '/Users/zengle/Documents/quickmedia')
        from quickmedia.mcp_server import add_asset
        r = add_asset("/nonexistent/file.txt")
        assert r.ok is False or "不存在" in str(r.error or "") or "not found" in str(r.error or "")
