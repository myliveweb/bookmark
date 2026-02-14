import sys
import json
import os
import httpx

def get_chat_history_xml(file_path, limit=10):
    if not os.path.exists(file_path):
        return ""

    data = ''
    clean_list = []
    n = 0
    try:

        with open(file_path, "r", encoding='utf-8') as f:
            data = f.read()

        xml_output = "<chat_history>\n"

        if data:
            data_list = data.split('------ ')
            if len(data_list) > 0:
                for item in data_list:
                    if item == '':
                        continue
                    item_list = item.split(' ------')
                    clean_list.append(item_list[1].strip())

                if len(clean_list) > 0:
                    for item in clean_list[-limit:]:
                        print(item)
                        split_user_list = item.split('USER:')
                        split_assistant_list = split_user_list[1].split('MODEL:')
                        user_text = split_assistant_list[0].strip()
                        assistant_text = split_assistant_list[1].strip()
                        if user_text:
                            xml_output += f'  <turn role="user">{user_text}</turn>\n'
                        if assistant_text and assistant_text != "[no response text]":
                            xml_output += f'  <turn role="assistant">{assistant_text}</turn>\n'

        xml_output += "</chat_history>"
        return xml_output, len(clean_list)
    except Exception as e:
        return f"<!-- Error loading history: {e} -->", 0

def get_chat_summary(summary_file):
    if not os.path.exists(summary_file):
        return ""

    data = ''
    error_file = ".gemini/hooks/history/error.log"
    summary_text = ''

    try:
        with open(summary_file, "r", encoding='utf-8') as f:
            data = f.read()

        if data:
            item_list = data.split(' ------')
            summary_text = item_list[1].strip()

        return summary_text
    except Exception as e:
        with open(error_file, "a+") as f:
            f.write(f"<!-- Error loading summary: {e} -->\n\n")
        return f"<!-- Error loading summary: {e} -->"

def regenerate_summary(last_turn, regenerate_num):
    url = f"http://127.0.0.1:8000/api/regenerate_summary"
    try:
        resp = httpx.post(url, json={"last_turn": last_turn, "regenerate_num": regenerate_num}, timeout=10)
        data = resp.json()
        # print(f"resp! {resp}")
        # print(f"data! {data}")
        return {"status_code": resp.status_code, "ok": resp.is_success, "response": data}
    except Exception as exc:
        return {"error": str(exc)}

def main():
    last_turn = 10
    regenerate_num = 60
    # 1. Читаем ввод от CLI
    # try:
    #     input_data = json.loads(sys.stdin.read())
    # except:
    #     return

    # current_prompt = input_data.get("prompt", "")
    current_prompt = "Привет Джин!"

    history_file = ".gemini/hooks/history/last.md"
    summary_file = ".gemini/hooks/history/summary.md"

    # 2. Собираем историю
    history_xml, num_turn = get_chat_history_xml(history_file, limit=last_turn)
    summary_text = get_chat_summary(summary_file)
    if num_turn > regenerate_num:
        regenerate_summary(last_turn, regenerate_num)

    augmented_summary = ''
    if summary_text:
        augmented_summary = f"""
[CONVERSATION SUMMARY]
{summary_text}
"""

    # 3. Формируем финальный «пирог» контекста
    # Мы ставим Summary самым первым, затем историю, затем текущий вопрос
    augmented_prompt = f"""{augmented_summary}
[CHAT HISTORY]
{history_xml}

[CURRENT USER REQUEST]
{current_prompt}
"""

    # 4. Возвращаем результат в CLI
    # Помни про статус 'success' для версии 0.27.0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "BeforeAgent",
            "additionalContext": augmented_prompt
        }
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()

# # Возвращаем пустой успех, чтобы не ломать работу
# print(json.dumps({"status": "ok"}))