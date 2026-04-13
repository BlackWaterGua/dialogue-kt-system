import os
import configparser
import time
import json
import pandas as pd
from openai import OpenAI
from rich import print as rprint
from rich.tree import Tree
from rich.console import Console
from pathlib import Path
config = configparser.ConfigParser()
config.read('./config.ini')
client_openai = OpenAI(
    organization = config['openai']['organization'],
    api_key = config['openai']['api_key']
)

BASE_DIR = Path(__file__).resolve().parents[1]

course_id = "bbd868bf59e7471a986d5e50b6d011f1"
mindmap_path = BASE_DIR / "data" / course_id / "mindmap.jsonl"
mindmap_data = []
with open(mindmap_path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            mindmap_data.append(json.loads(line))

file_name = "別用愛了，用冰發電吧！——可燃冰的發現、應用及油氣能源的未來.pdf"

for item in mindmap_data:
    if item['file_name'] == file_name:
        mindmap_data_filtered = item

def traverse_mindmap(node, level=0):
    # print("  " * level + "- " + node['topic'])
    if 'children' in node and node['children']:
        for child in node['children']:
            traverse_mindmap(child, level + 1)

def extract_knowledge_points(node, knowledge_dict=None):
    if knowledge_dict is None:
        knowledge_dict = {}
    
    # 如果節點有 id 和 knowledge_points，則加入字典
    if 'id' in node and 'knowledge_points' in node:
        knowledge_dict[node['id']] = node['knowledge_points']
    
    # 遞迴處理子節點
    if 'children' in node and node['children']:
        for child in node['children']:
            extract_knowledge_points(child, knowledge_dict)
    
    return knowledge_dict

def remove_knowledge_points(node):
    # 建立新的節點字典,不包含 knowledge_points
    new_node = {k: v for k, v in node.items() if k != 'knowledge_points'}
    
    # 如果有子節點,遞迴處理
    if 'children' in node and node['children']:
        new_node['children'] = []
        for child in node['children']:
            new_node['children'].append(remove_knowledge_points(child))
    
    return new_node

def add_node(mindmap, parent_id, new_node):
    if mindmap['id'] == parent_id:
        if 'children' not in mindmap:
            mindmap['children'] = []
        mindmap['children'].append(new_node)
        return {
            'success': True,
            'message': '節點新增成功'
        }
    if 'children' in mindmap:
        for child in mindmap['children']:
            result = add_node(child, parent_id, new_node)
            if result.get('success'):
                return result
    return {
        'success': False,
        'message': '找不到目標父節點'
    }

def edit_node(mindmap, node_id, new_topic):
    if mindmap['id'] == node_id:
        mindmap['topic'] = new_topic
        return {
            'success': True,
            'message': '節點編輯成功'
        }
    if 'children' in mindmap and mindmap['children']:
        for child in mindmap['children']:
            result = edit_node(child, node_id, new_topic)
            if result.get('success'):
                return result
    return {
        'success': False, 
        'message': '找不到目標節點'
    }

def move_node(mindmap, node_id, new_parent_id):
    # 找到要移動的節點和其父節點
    node_to_move = None
    parent_node = None
    
    def find_node(current_node, parent=None):
        nonlocal node_to_move, parent_node
        if current_node['id'] == node_id:
            node_to_move = current_node
            parent_node = parent
            return True
        if 'children' in current_node:
            for child in current_node['children']:
                if find_node(child, current_node):
                    return True
        return False
    
    # 搜尋要移動的節點
    find_node(mindmap)
    if not node_to_move:
        return False
        
    # 從原父節點中移除該節點
    if parent_node:
        parent_node['children'].remove(node_to_move)
    
    # 將節點加入新的父節點底下
    def add_to_new_parent(current_node):
        if current_node['id'] == new_parent_id:
            if 'children' not in current_node:
                current_node['children'] = []
            current_node['children'].append(node_to_move)
            return True
        if 'children' in current_node:
            for child in current_node['children']:
                if add_to_new_parent(child):
                    return True
        return False
    
    success = add_to_new_parent(mindmap)
    return {
        'success': success,
        'message': '節點移動成功' if success else '找不到目標父節點'
    }

def delete_node(mindmap, node_id):
    if mindmap['id'] == node_id:
        return {
            'success': True,
            'message': '節點刪除成功',
            'should_delete': True
        }
    
    if 'children' in mindmap and mindmap['children']:
        for i, child in enumerate(mindmap['children']):
            result = delete_node(child, node_id)
            if result.get('success'):
                if result.get('should_delete'):
                    mindmap['children'].pop(i)
                return {
                    'success': True,
                    'message': '節點刪除成功'
                }
    
    return {
        'success': False,
        'message': '找不到目標節點'
    }

def save_mindmap(mindmap_data, file_name):
    """保存心智圖到檔案"""
    try:
        # 更新心智圖資料
        for item in mindmap_data:
            if item['file_name'] == file_name:
                item['mindmap'] = mindmap
                break
        
        # 寫入檔案
        with open(mindmap_path, 'w', encoding='utf-8') as f:
            for item in mindmap_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        return True
    except Exception as e:
        print(f"保存心智圖時發生錯誤：{str(e)}")
        return False

def update_assistant_instructions(mindmap):
    """更新 assistant 的系統提示，反映最新的心智圖狀態"""
    try:
        # 檢查是否已包含心智圖結構的說明
        if "你現在正在協助教師編輯以下心智圖。其結構如下（以 JSON 呈現）：" in assistant.instructions:
            # 替換舊的心智圖結構說明
            updated_instructions = assistant.instructions.replace(
                assistant.instructions[assistant.instructions.find("你現在正在協助教師編輯以下心智圖。其結構如下（以 JSON 呈現）："):],
                f"你現在正在協助教師編輯以下心智圖。其結構如下（以 JSON 呈現）：{mindmap}"
            )
        else:
            # 如果沒有，則新增心智圖結構說明
            updated_instructions = assistant.instructions + f"\n你現在正在協助教師編輯以下心智圖。其結構如下（以 JSON 呈現）：{mindmap}"

        # 更新 Assistant
        updated_assistant = client_openai.beta.assistants.update(
            assistant_id=assistant.id,
            instructions=updated_instructions,
            tools=tools,
            model="gpt-4o-mini"
        )
        return updated_assistant
    except Exception as e:
        print(f"更新系統提示時發生錯誤：{str(e)}")
        return None

def print_mindmap(mindmap):
    """使用 rich 套件美化輸出心智圖"""
    console = Console()
    
    # 創建根節點，包含 ID 和主題
    tree = Tree(f"[bold blue]ID: {mindmap['id']} | 主題: {mindmap['topic']}[/bold blue]")
    
    def add_children(node, tree_node):
        if 'children' in node and node['children']:
            for child in node['children']:
                # 為每個子節點創建一個包含 ID 和主題的節點
                child_node = tree_node.add(f"[green]ID: {child['id']} | 主題: {child['topic']}[/green]")
                # 遞迴處理子節點的子節點
                add_children(child, child_node)
    
    add_children(mindmap, tree)
    console.print(tree)

mindmap_without_knowledge = remove_knowledge_points(mindmap_data_filtered["mindmap"])
# traverse_mindmap(mindmap_data_filtered["mindmap"])

# Define function
tools = [
    {
        "type": "file_search"
    },
    {
        "type": "function",
        "function": {
            "name": "add_node",
            "description": "在心智圖中添加新節點",
            "parameters": {
                "type": "object",
                "properties": {
                    "parent_id": {
                        "type": "string",
                        "description": "父節點的 ID"
                    },
                    "new_node": {
                        "type": "object",
                        "description": "新節點的資訊，必須提供 id 和 topic",
                        "properties": {
                            "id": {
                            "type": "string",
                            "description": "新節點的唯一識別 ID"
                            },
                            "topic": {
                                "type": "string",
                                "description": "新節點的標題或主題"
                            }
                        },
                        "required": ["id", "topic"]
                    }
                },
                "required": ["parent_id", "new_node"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_node",
            "description": "編輯心智圖中的節點",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "要編輯的節點 ID"
                    },
                    "new_topic": {
                        "type": "string",
                        "description": "新的節點主題"
                    }
                },
                "required": ["node_id", "new_topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_node",
            "description": "移動心智圖中的節點到新的父節點下",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "要移動的節點 ID"
                    },
                    "new_parent_id": {
                        "type": "string",
                        "description": "新的父節點 ID"
                    }
                },
                "required": ["node_id", "new_parent_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_node",
            "description": "從心智圖中刪除節點",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "要刪除的節點 ID"
                    }
                },
                "required": ["node_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "undo_last_action",
            "description": "撤銷最後一個心智圖操作",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]
# tools = []

# Append mindmap data to the assistant
mindmap = remove_knowledge_points(mindmap_data_filtered["mindmap"])
# # Retrieve Assistant
assistant = client_openai.beta.assistants.retrieve("asst_3WYZPOXUldz8hng2Yo0mZocp")

# 檢查是否已包含心智圖結構的說明
if "你現在正在協助教師編輯以下心智圖。其結構如下（以 JSON 呈現）：" in assistant.instructions:
    # 替換舊的心智圖結構說明
    updated_instructions = assistant.instructions.replace(
        assistant.instructions[assistant.instructions.find("你現在正在協助教師編輯以下心智圖。其結構如下（以 JSON 呈現）："):],
        f"你現在正在協助教師編輯以下心智圖。其結構如下（以 JSON 呈現）：：{mindmap}"
    )
else:
    # 如果沒有，則新增心智圖結構說明
    updated_instructions = assistant.instructions + f"\n你現在正在協助教師編輯以下心智圖。其結構如下（以 JSON 呈現）：{mindmap}"

# Update Assistant for function calling
assistant = client_openai.beta.assistants.update(
  assistant_id="asst_3WYZPOXUldz8hng2Yo0mZocp",
  instructions=updated_instructions,
  tools=tools,
  model="gpt-4o-mini"
)

knowledge_points_dict = extract_knowledge_points(mindmap_data_filtered["mindmap"])
# 建立聊天執行緒
thread = client_openai.beta.threads.create()

user_input = f"[系統訊息] 請參考 system prompt 中的心智圖開始對話"

# 在檔案開頭添加操作歷史記錄
action_history = []

def undo_last_action():
    """撤銷最後一個操作"""
    global mindmap
    if action_history:
        mindmap = action_history.pop()
        return {
            'success': True,
            'message': '成功撤銷上一個操作'
        }
    return {
        'success': False,
        'message': '沒有可撤銷的操作'
    }

def chat_loop():
    global mindmap  # 宣告使用全域變數
    global assistant
    global user_input
    
    while True:
        # 新增使用者訊息
        message = client_openai.beta.threads.messages.create(
            thread_id=thread.id,
            role="user", 
            content=user_input
        )
        
        # 建立並執行對話
        run = client_openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )
        
        # 輪詢執行結果
        while True:
            run_status = client_openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run_status.status == "completed":
                break
            elif run_status.status == "requires_action":
                tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []
                
                for tool_call in tool_calls:
                    if tool_call.function.name in ["add_node", "edit_node", "move_node", "delete_node"]:
                        # 在執行操作前保存當前狀態
                        action_history.append(mindmap)
                        
                        # 執行心智圖操作
                        function_args = json.loads(tool_call.function.arguments)
                        if tool_call.function.name == "add_node":
                            result = add_node(mindmap, function_args["parent_id"], function_args["new_node"])
                        elif tool_call.function.name == "edit_node":
                            result = edit_node(mindmap, function_args["node_id"], function_args["new_topic"])
                        elif tool_call.function.name == "move_node":
                            result = move_node(mindmap, function_args["node_id"], function_args["new_parent_id"])
                        elif tool_call.function.name == "delete_node":
                            result = delete_node(mindmap, function_args["node_id"])
                        
                        # 更新系統提示
                        if result.get('success'):
                            updated_assistant = update_assistant_instructions(mindmap)
                            if updated_assistant:
                                assistant = updated_assistant
                        
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": json.dumps(result, ensure_ascii=False)
                        })
                    elif tool_call.function.name == "undo_last_action":
                        result = undo_last_action()
                        if result.get('success'):
                            updated_assistant = update_assistant_instructions(mindmap)
                            if updated_assistant:
                                assistant = updated_assistant
                        
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": json.dumps(result, ensure_ascii=False)
                        })

                # 提交 function calling 的結果
                run = client_openai.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread.id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
            else:
                time.sleep(1)

        # 取得並顯示助理的回應
        messages = client_openai.beta.threads.messages.list(thread_id=thread.id)
        print("助理:", messages.data[0].content[0].text.value)
        print("--------------------------------")

        # 取得使用者輸入
        user_input = input("請輸入訊息 (輸入'exit'結束對話): ")
        print("--------------------------------")
        
        # 檢查是否要結束對話
        if user_input.lower() == 'exit':
            print("結束對話")
            break
        if user_input.lower() == 'check':
            print_mindmap(mindmap)
            print("--------------------------------")
            user_input = input("請繼續輸入訊息: ")
            if user_input.lower() == 'exit':
                print("結束對話")
                break
            print("--------------------------------")

# 開始對話
chat_loop()