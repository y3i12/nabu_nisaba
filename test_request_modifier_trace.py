#!/usr/bin/env python3
"""
Table test for RequestModifier - trace why tool_result_state isn't populating
"""

import json
from src.nisaba.wrapper.request_modifier import RequestModifier, RMPState

def test_tool_result_tracking():
    """
    Test with a realistic message structure containing tool results
    """
    
    print("=" * 80)
    print("TABLE TEST: Tool Result Tracking")
    print("=" * 80)
    
    # Realistic message structure with tool result
    test_body = {
        'model': 'claude-3',
        'messages': [
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'text',
                        'text': 'Hello'
                    }
                ]
            },
            {
                'role': 'assistant',
                'content': [
                    {
                        'type': 'text',
                        'text': 'Let me help'
                    },
                    {
                        'type': 'tool_use',
                        'id': 'toolu_123',
                        'name': 'read_file'
                    }
                ]
            },
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'tool_result',
                        'tool_use_id': 'toolu_ABC',
                        'content': {
                            'type': 'text',
                            'text': 'File contents here'
                        }
                    }
                ]
            }
        ],
        'metadata': {
            'user_id': 'test_session_trace123'
        }
    }
    
    print("\n📋 INPUT STRUCTURE:")
    print(f"Messages: {len(test_body['messages'])}")
    print(f"Message 0: role={test_body['messages'][0]['role']}, content blocks={len(test_body['messages'][0]['content'])}")
    print(f"Message 1: role={test_body['messages'][1]['role']}, content blocks={len(test_body['messages'][1]['content'])}")
    print(f"Message 2: role={test_body['messages'][2]['role']}, content blocks={len(test_body['messages'][2]['content'])}")
    print(f"  - Message 2 content[0] has type: {test_body['messages'][2]['content'][0]['type']}")
    print(f"  - Message 2 content[0] has tool_use_id: {test_body['messages'][2]['content'][0]['tool_use_id']}")
    
    print("\n🔍 EXPECTED FLOW:")
    print("1. body (dict) -> messages (list)")
    print("2. messages[0] (dict) -> role='user' -> _message_block_count() fires")
    print("3. messages[0] -> content (list) -> content[0] (dict)")
    print("4. content[0] -> type='text' -> _content_block_count() fires")
    print("5. ... repeat for messages[1] ...")
    print("6. messages[2] -> role='user' -> _message_block_count() fires")
    print("7. messages[2] -> content[0] -> type='tool_result' -> _content_block_count() fires")
    print("8. messages[2] -> content[0] -> tool_use_id='toolu_ABC' -> _tool_use_id_state() fires ⭐")
    print("9. messages[2] -> content[0] -> content (nested) -> text -> _process_tool_result() fires ⭐")
    
    print("\n" + "=" * 80)
    print("EXECUTING...")
    print("=" * 80)
    
    modifier = RequestModifier(cache_path='.nisaba/test_cache/')
    result = modifier.process_request(test_body)
    
    print("\n📊 RESULTS:")
    print(f"Block offset: {modifier.state.last_block_offset}")
    print(f"Tool states tracked: {len(modifier.state.tool_result_state)}")
    
    if modifier.state.tool_result_state:
        print("\n✅ SUCCESS - Tool states captured:")
        for tool_id, state in modifier.state.tool_result_state.items():
            print(f"  Tool ID: {tool_id}")
            print(f"    Block offset: {state['block_offset']}")
            print(f"    Status: {state['tool_result_status']}")
            print(f"    Window: {state['window_state']}")
    else:
        print("\n❌ FAILURE - No tool states captured")
        print("\nDEBUG: Check modifier rules structure")
        print("\nModifier rules for messages:")
        print(json.dumps(modifier.modifier_rules['messages'], indent=2, default=str))
    
    print("\n" + "=" * 80)
    print("CHECKING LOGS...")
    print("=" * 80)
    
    import subprocess
    result = subprocess.run(
        ['tail', '-100', '.nisaba/logs/proxy.log'],
        capture_output=True,
        text=True
    )
    
    lines = result.stdout.split('\n')
    
    # Look for key indicators
    callable_calls = [l for l in lines if 'Calling _' in l]
    tool_use_id_lines = [l for l in lines if 'tool_use_id' in l.lower()]
    
    print(f"\nCallable invocations found: {len(callable_calls)}")
    for line in callable_calls[-5:]:
        print(f"  {line}")
    
    print(f"\nTool use ID references: {len(tool_use_id_lines)}")
    for line in tool_use_id_lines[-3:]:
        print(f"  {line}")

if __name__ == "__main__":
    test_tool_result_tracking()
