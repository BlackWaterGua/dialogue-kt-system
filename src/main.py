from openai import OpenAI, AsyncOpenAI
import configparser
import requests
import json
import pandas as pd
import re
from io import StringIO
import networkx as nx
import matplotlib.pyplot as plt
from prompt import PROMPTS
from datetime import datetime
import os

# 讀取設定檔
config = configparser.ConfigParser()
config.read('./config.ini')

# 初始化 OpenAI 客戶端
client_openai = OpenAI( 
    organization = config['openai']['organization'],
    api_key = config['openai']['api_key']
)

def openai_complete(prompt, model="gpt-4o-mini", system_prompt=None, history_messages=[], temperature=0.1, json_mode=False):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})
    response = client_openai.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        response_format={"type": "json_object"} if json_mode else None
    )
    content = response.choices[0].message.content
    return content

def LightRAG_retrieve_nodes(query="", mode="hybrid", only_need_context=True, top_k=15, course_id=""):
    url = "http://localhost:9621/query"
    headers = {
        "Content-Type": "application/json"
    }
    
    # 將 course_id 作為查詢參數
    params = {
        "course_id": course_id
    }
    
    payload = {
        "query": query,
        "mode": mode,
        "only_need_context": only_need_context,
        "top_k": top_k
    }
    
    try:
        response = requests.post(url, headers=headers, params=params, json=payload)
        response.raise_for_status()  # 檢查是否有錯誤狀態碼
        result = "\n" +  response.json()["response"].replace('\t', '')
        sections = ["Entities", "Relationships", "Sources"]
        LightRAG_result_tables = {}
        for section in sections:
            match = re.search(rf"\n-----{section}-----\n```csv\n(.*?)\n```", result, re.DOTALL)
            df = pd.read_csv(StringIO(match.group(1)), sep=r"<\|\|>", engine="python")
            LightRAG_result_tables[section] = df
        return LightRAG_result_tables

    except requests.exceptions.RequestException as e:
        print(f"API 呼叫發生錯誤: {e}")
        return None

def KC_extract(data_table):
    #取出所有知識點的資料
    json_list = []
    for _, row in data_table.iterrows():
        entity_json = {
            'KC_name': row['entity'],
            'KC_description': row['description']
        }
        json_list.append(entity_json)
    return json_list

def dialogue_extract(dialogue):
    #提取對話中的 role 和 content
    dialogue_list = []
    for utter in dialogue:
        dialogue_item = {
            "role": utter["role"],
            "content": utter["content"]
        }
        # 如果存在 "time" 鍵，則添加到對話項目中
        if "time" in utter:
            dialogue_item["time"] = utter["time"]
        dialogue_list.append(dialogue_item)
    return dialogue_list

def annotate_knowledge_points(dialogue, course_id=""):
    # 標註知識點
    anno_prompt = PROMPTS["ANNO_KC_PROMPT"]

    Dialogue = dialogue_extract(dialogue)
    tmp_data = LightRAG_retrieve_nodes(query=json.dumps(Dialogue), course_id=course_id)["Entities"]
    if not tmp_data.empty:
        KC_information = KC_extract(tmp_data)
    else:
        KC_information = None

    if not KC_information:
        return [], []
    # 知識點判斷
    context_base = dict(
        examples=PROMPTS["ANNO_KC_EXAMPLE"],
        dialogue=json.dumps(dialogue),
        knowledge_points=json.dumps(KC_information)
    )
    prompt = anno_prompt.format(**context_base)
    anno_nodes = eval(openai_complete(prompt=prompt))
    
    return anno_nodes, KC_information

def get_users_data(course_id=""):
    # 建立課程資料夾（如果不存在）
    course_dir = f"data/{course_id}" if course_id else "data"
    os.makedirs(course_dir, exist_ok=True)
    
    # 讀取 user_status.jsonl 檔案
    users_data = []
    file_path = os.path.join(course_dir, "user_status.jsonl")
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                users_data.append(json.loads(line))
    return users_data

def get_or_create_user(user_id, course_id="", user_name=None):
    users_data = get_users_data(course_id)
    # 找到使用者資料或建立新使用者
    user_info = next((user for user in users_data if user.get("user_id") == user_id), None)
    if not user_info:
        # print(f"建立新使用者...ID: {user_id}")
        user_info = {
            "user_id": user_id,
            "user_KC_status": [],
            "last_tracing_time": None
        }
        if user_name:
            user_info["user_name"] = user_name
            
        users_data.append(user_info)
        
        # 建立課程資料夾（如果不存在）
        course_dir = f"data/{course_id}" if course_id else "data"
        os.makedirs(course_dir, exist_ok=True)
        
        # 將新增的使用者資料寫入對應的 .jsonl 檔案
        try:
            file_path = os.path.join(course_dir, "user_status.jsonl")
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(user_info, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"Error saving user data: {e}")
    
    return user_info

def get_user_kc_status(user_info, anno_nodes_info):
    # 取出 user_info 中已存在的知識點狀態
    user_KC_status = []
    for node in anno_nodes_info:
        existing_kc = next((kc for kc in user_info["user_KC_status"] if kc["KC_name"] == node["KC_name"]), None)
        if existing_kc:
            temp_KC_status = existing_kc
            temp_KC_status["KC_description"] = node["KC_description"]
            user_KC_status.append(temp_KC_status)
        else:
            temp_KC_status = {
                "KC_name": node['KC_name'],
                "KC_description": node["KC_description"],
                "mastery_score": 0,
                "mastery_history": []
            }
            user_KC_status.append(temp_KC_status)
    return user_KC_status

def update_user_kc_status(user_info, user_mastery_result, time, course_id=""):
    # 更新 user_KC_status
    for kc_result in user_mastery_result:
        # 找到對應的知識點
        kc = next((k for k in user_info["user_KC_status"] if k["KC_name"] == kc_result["KC_name"]), None)
        if kc:
            # 如果知識點已存在,更新分數和歷史記錄
            kc["mastery_score"] = kc_result["mastery_score"]
            kc["mastery_history"].extend(kc_result["mastery_history"])
        else:
            # 如果是新知識點則加入
            user_info["user_KC_status"].append(kc_result)
    
    # 更新特定使用者的資料到 user_status.jsonl
    try:
        # 建立課程資料夾（如果不存在）
        course_dir = f"data/{course_id}" if course_id else "data"
        os.makedirs(course_dir, exist_ok=True)
        
        # 讀取現有的使用者資料
        file_path = os.path.join(course_dir, "user_status.jsonl")
        existing_users = []
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    existing_users.append(json.loads(line))
        
        # 更新特定使用者的資料
        updated = False
        with open(file_path, 'w', encoding='utf-8') as f:
            for existing_user in existing_users:
                if existing_user['user_id'] == user_info['user_id']:
                    user_info["last_tracing_time"] = time
                    f.write(json.dumps(user_info, ensure_ascii=False) + '\n')
                    updated = True
                else:
                    user_info["last_tracing_time"] = time
                    f.write(json.dumps(existing_user, ensure_ascii=False) + '\n')
        # if updated:
        #     print(f"更新使用者資料成功: {user_info['user_id']}")
    except Exception as e:
        print(f"更新使用者資料時發生錯誤: {e}")
    return user_info

def store_trace_history(user_info, user_mastery_result, dialogue, time, course_id="", conversation_id=None):
    # 儲存學習歷程
    temp_data = {
        'user_id': user_info['user_id'],
        'user_name': user_info['user_name'],
        'user_KC_status': user_info['user_KC_status'],
        'user_mastery_result': user_mastery_result,
        'dialogue': dialogue,
        'conversation_id': conversation_id,
        'tracing_time': time
    }
    
    # 建立課程資料夾（如果不存在）
    course_dir = f"data/{course_id}" if course_id else "data"
    os.makedirs(course_dir, exist_ok=True)
    
    file_path = os.path.join(course_dir, "user_trace_history.jsonl")
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(temp_data, ensure_ascii=False) + '\n')

def annotate_mastery(user_id, anno_nodes, KC_information, dialogue, time, course_id="", user_name=None, conversation_id=None, update_user_status=False, store_trace_result=False, real_time=False):
    anno_kc = [item for item in KC_information if item["KC_name"] in anno_nodes]
    # 抓取學生資料
    user_info = get_or_create_user(user_id, course_id, user_name)
    user_KC_status = get_user_kc_status(user_info, anno_kc)

    if real_time:
        # 將對話分成已追蹤和未追蹤部分
        tracked_dialogue = dialogue[:-2]
        untracked_dialogue = dialogue[-2:]

        # 建立格式化字串
        formatted_lines = ["["]
        formatted_lines.append("  // ----(Dialogue already tracked)----")
        for msg in tracked_dialogue:
            formatted_lines.append("  " + json.dumps(msg, ensure_ascii=False, indent=2).replace("\n", "\n  ") + ",")
        formatted_lines.append("  // ----(Dialogue already tracked)----")
        formatted_lines.append("  // ----(Dialogue not yet tracked)----")
        for msg in untracked_dialogue:
            formatted_lines.append("  " + json.dumps(msg, ensure_ascii=False, indent=2).replace("\n", "\n  ") + ",")
        formatted_lines.append("  // ----(Dialogue not yet tracked)----")
        formatted_lines.append("]")

        formatted_dialogue = "\n".join(formatted_lines)
        # print("real_time dialogue:\n", formatted_dialogue)

        context_base = dict(
            language="繁體中文",
            examples=PROMPTS["ANNO_MASTERY_REAL_TIME_EXAMPLE"],
            user_KC_status=json.dumps(user_KC_status, ensure_ascii=False),
            dialogue=json.dumps(formatted_dialogue, ensure_ascii=False)
        )
        anno_score = PROMPTS["ANNO_MASTERY_REAL_TIME_PROMPT"]
    else:
        context_base = dict(
            language="繁體中文",
            examples=PROMPTS["ANNO_MASTERY_EXAMPLE"],
            user_KC_status=json.dumps(user_KC_status, ensure_ascii=False),
            dialogue=json.dumps(dialogue, ensure_ascii=False)
        )
        anno_score = PROMPTS["ANNO_MASTERY_PROMPT"]

    prompt = anno_score.format(**context_base)
    response = openai_complete(prompt=prompt)
    try:
        user_mastery_result = json.loads(response)
    except json.JSONDecodeError:
        print("無法解析 OpenAI 的回應為 JSON，原始回應：")
        print(response)
        return None
        
    # print("user_mastery_result:\n", json.dumps(user_mastery_result, ensure_ascii=False, indent=2))
    
    if update_user_status:
        user_info = update_user_kc_status(user_info, user_mastery_result, time, course_id)
    if store_trace_result:
        store_trace_history(user_info, user_mastery_result, dialogue, time, course_id, conversation_id)
    return user_mastery_result

def get_trace_status(user_id, course_id="", print_status=False):
    target_user = []
    try:
        # 建立課程資料夾（如果不存在）
        course_dir = f"data/{course_id}" if course_id else "data"
        os.makedirs(course_dir, exist_ok=True)
        
        file_path = os.path.join(course_dir, "user_status.jsonl")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                user_data = [json.loads(line) for line in f]
                # 找到特定使用者
                target_user = next((user for user in user_data if user['user_id'] == user_id), None)
                
                if print_status:
                    if target_user:
                        print(f"\n使用者ID: {target_user['user_id']}")
                        print(f"使用者名稱: {target_user['user_name']}")
                        print("知識點狀態:")
                        for kc in target_user['user_KC_status']:
                            print(f"\n  知識點: {kc['KC_name']}")
                            print(f"  掌握程度: {kc['mastery_score']}")
                            print("  學習歷程:")
                            for history in kc['mastery_history']:
                                print(f"    {history}")
                    else:
                        print(f"找不到使用者ID {user_id}")
        return target_user
    except Exception as e:
        print(f"讀取使用者資料時發生錯誤: {e}")

def retrieve_node_relations(kc_id, course_id=""):
    url = "http://localhost:9621/graph/node/neighbors"
    params = {
        "course_id": course_id,
        "node_id": kc_id
    }
    response = requests.get(url, params=params)
    return response.json()

def plot_knowledge_graph(user_id, course_id=""):
    target_user = get_trace_status(user_id, course_id)
    # 建立圖形
    G = nx.DiGraph()
    for node in target_user['user_KC_status']:
        G.add_node(node["KC_name"], score=node["mastery_score"])
    user_kc_list = [node_id['KC_name'] for node_id in target_user['user_KC_status']]
    # 取得所有知識點之間的關係
    edges = []
    for kc in user_kc_list:
        relations = retrieve_node_relations(kc)
        # 檢查每個關係的目標節點是否在使用者的知識點列表中
        for relation in relations:
            target_node = relation[1]
            if target_node in user_kc_list:
                edges.append((kc, target_node))
    G.add_edges_from(edges)

    # 計算節點顏色（以分數映射顏色）
    def score_to_color(score):
        # 0:紅、1:綠（RGB 線性插值）
        r = int((1 - score) * 255)
        g = int(score * 255)
        b = 80
        return (r/255, g/255, b/255)

    node_colors = [score_to_color(G.nodes[n]["score"]) for n in G.nodes]
    node_labels = {n: f'{n}\n{G.nodes[n]["score"]:.2f}' for n in G.nodes}

    # 畫圖
    plt.figure(figsize=(10, 6))
    plt.rcParams['font.family'] = 'Microsoft JhengHei'  # 或改為 'SimHei'、'Taipei Sans TC Beta'
    plt.rcParams['axes.unicode_minus'] = False  # 避免負號顯示為方框
    pos = nx.shell_layout(G)
    nx.draw(G, pos, with_labels=True, labels=node_labels,
            node_color=node_colors, edge_color='gray',
            node_size=1500, font_size=10, font_weight='bold')
    plt.title("學生知識點掌握圖譜", fontsize=14)
    plt.show()

def plot_knowledge_mastery_boxplot(course_id="", kc_names=None, end_date=None, min_samples=3, target_user_id=None):
    """
    繪製知識點掌握程度的箱型圖
    
    Args:
        course_id (str): 課程 ID
        kc_names (list): 要顯示的知識點名稱列表，如果為 None 則顯示所有知識點
        end_date (datetime): 結束日期，預設為 2024/6/1
        min_samples (int): 最少需要的樣本數，少於此數量的知識點將被過濾掉
        target_user_id (str): 要特別標示的學生 ID，如果為 None 則不標示任何學生
    """
    if end_date is None:
        end_date = datetime(2024, 6, 1)
    
    # 獲取所有學生的資料
    users_data = get_users_data(course_id)
    
    # 收集所有知識點的分數
    kc_scores = {}
    target_user_scores = {}  # 儲存目標學生的分數
    target_user_name = None  # 儲存目標學生的名稱
    
    # 讀取學習歷程資料以獲取時間資訊
    trace_data = {}
    trace_file = os.path.join(f"data/{course_id}" if course_id else "data", "user_trace_history.jsonl")
    if os.path.exists(trace_file):
        with open(trace_file, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                user_name = data['user_name']
                user_id = next((user['user_id'] for user in users_data if user.get('user_name') == user_name), None)
                time = datetime.strptime(data['time'], '%Y/%m/%d %H:%M:%S')
                if time <= end_date:
                    trace_data[user_name] = data['user_KC_status']
                    # 如果是目標學生，記錄其分數
                    if target_user_id and user_id == target_user_id:
                        target_user_name = user_name
                        for kc in data['user_KC_status']:
                            kc_name = kc['KC_name']
                            if kc_names is None or kc_name in kc_names:
                                target_user_scores[kc_name] = kc['mastery_score']
    
    for user in users_data:
        user_name = user.get('user_name')
        if user_name not in trace_data:
            continue
            
        for kc in trace_data[user_name]:
            kc_name = kc['KC_name']
            # 如果指定了知識點列表，只收集指定的知識點
            if kc_names is None or kc_name in kc_names:
                if kc_name not in kc_scores:
                    kc_scores[kc_name] = []
                kc_scores[kc_name].append(kc['mastery_score'])
    
    if not kc_scores:
        print("沒有找到任何知識點資料")
        return
        
    # 過濾掉樣本數太少的知識點
    filtered_kc_scores = {k: v for k, v in kc_scores.items() if len(v) >= min_samples}
    
    if not filtered_kc_scores:
        print(f"沒有知識點的樣本數達到最小要求({min_samples}個)")
        return
    
    # 準備繪圖資料
    kc_names = list(filtered_kc_scores.keys())
    scores = [filtered_kc_scores[name] for name in kc_names]
    
    # 設定中文字體
    plt.rcParams['font.family'] = 'Microsoft JhengHei'
    plt.rcParams['axes.unicode_minus'] = False
    
    # 建立圖表
    plt.figure(figsize=(12, 6))
    boxplot = plt.boxplot(scores, labels=kc_names)
    
    # 如果有指定目標學生，在圖上標示其分數
    if target_user_id and target_user_scores:
        for i, kc_name in enumerate(kc_names):
            if kc_name in target_user_scores:
                score = target_user_scores[kc_name]
                plt.plot(i+1, score, 'ro', markersize=8, label='目標學生' if i == 0 else "")
    
    # 設定標題和軸標籤
    title = f'知識點掌握程度分布 (至 {end_date.strftime("%Y/%m/%d")}, 最少{min_samples}筆資料)'
    if target_user_id and target_user_name:
        title += f'\n紅點表示學生 {target_user_name} (ID: {target_user_id}) 的分數'
    plt.title(title, fontsize=14)
    plt.xlabel('知識點名稱', fontsize=12)
    plt.ylabel('掌握程度分數', fontsize=12)
    
    # 如果有標示目標學生，添加圖例
    if target_user_id and target_user_scores:
        plt.legend()
    
    # 旋轉 x 軸標籤以避免重疊
    plt.xticks(rotation=45, ha='right')
    
    # 調整布局
    plt.tight_layout()
    
    # 顯示圖表
    plt.show()
    
    # 輸出統計資訊
    print(f"\n知識點統計資訊 (至 {end_date.strftime('%Y/%m/%d')})：")
    # 先輸出有足夠樣本的知識點
    print("\n符合最少樣本數要求的知識點：")
    for kc_name in kc_names:
        scores = filtered_kc_scores[kc_name]
        print(f"\n{kc_name}:")
        print(f"  平均分數: {sum(scores)/len(scores):.2f}")
        print(f"  中位數: {sorted(scores)[len(scores)//2]:.2f}")
        print(f"  最高分: {max(scores):.2f}")
        print(f"  最低分: {min(scores):.2f}")
        print(f"  樣本數: {len(scores)}")
        if target_user_id and kc_name in target_user_scores:
            print(f"  目標學生分數: {target_user_scores[kc_name]:.2f}")
    
    # 輸出被過濾掉的知識點資訊
    filtered_out = set(kc_scores.keys()) - set(filtered_kc_scores.keys())
    if filtered_out:
        print(f"\n樣本數不足的知識點（少於{min_samples}筆）：")
        for kc_name in filtered_out:
            print(f"{kc_name}: {len(kc_scores[kc_name])}筆資料")
