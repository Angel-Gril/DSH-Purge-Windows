"""Bounded, read-only MCP handshake. No sample analysis, no credential logging."""
import argparse
import asyncio
import json
import os
import sys
from datetime import timedelta
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def probe(args):
    params = StdioServerParameters(command=args.command, args=args.args,
                                  cwd=args.cwd, env=dict(os.environ))
    # Server stderr stays on the local console; report contains only tool names.
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=180)) as session:
            await session.initialize()
            listed = await session.list_tools()
            names = [tool.name for tool in listed.tools]
            if not names:
                raise RuntimeError('Server returned no tools')
            called = None
            if args.status_tool:
                if args.status_tool not in names:
                    raise RuntimeError('Expected read-only tool missing: ' + args.status_tool)
                result = await session.call_tool(args.status_tool, {})
                if result.isError:
                    raise RuntimeError('Read-only status tool reported an error')
                called = args.status_tool
            print(json.dumps({'ok': True, 'count': len(names), 'tools': names[:12],
                              'readOnlyCall': called}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cwd', required=True)
    parser.add_argument('--status-tool')
    parser.add_argument('command')
    parser.add_argument('args', nargs=argparse.REMAINDER)
    try:
        asyncio.run(probe(parser.parse_args()))
    except Exception as exc:
        def causes(error):
            nested = getattr(error, 'exceptions', None)
            if nested:
                return [entry for child in nested for entry in causes(child)]
            return [{'type': type(error).__name__, 'message': str(error)[:500]}]
        print(json.dumps({'ok': False, 'errorType': type(exc).__name__, 'causes': causes(exc)}), file=sys.stderr)
        sys.exit(1)
