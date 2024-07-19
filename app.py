from flask import Flask, render_template, request
import requests
import re
from datetime import datetime, timezone

app = Flask(__name__)

def parse_input(input_string):
    date_regex = r"before (\d{1,2} [A-Za-z]+ \d{4})"
    model_a_regex = r"(\S+) was created on (\d{4}-\d{2}-\d{2})"
    model_b_regex = r"(\S+) is located at index (\d+)"
    model_cd_regex = r"(\S+) was created (\d+) models before (\S+)"

    date_match = re.search(date_regex, input_string)
    model_a_match = re.search(model_a_regex, input_string)
    model_b_match = re.search(model_b_regex, input_string)
    model_cd_match = re.search(model_cd_regex, input_string)

    if not all([date_match, model_a_match, model_b_match, model_cd_match]):
        raise ValueError("Invalid input format. Please check your input string.")

    return {
        "date": date_match.group(1),
        "model_a": {"name": model_a_match.group(1), "date": model_a_match.group(2)},
        "model_b": {"name": model_b_match.group(1), "index": int(model_b_match.group(2))},
        "model_cd": {"name_c": model_cd_match.group(1), "num": int(model_cd_match.group(2)), "name_d": model_cd_match.group(3)}
    }

def calculate_score(parsed_input, models):
    score = 0
    debug_info = []
    sorted_models = sorted(models, key=lambda x: x['created'], reverse=True)

    # 4 points if model_a was created on the specified date
    model_a = next((m for m in sorted_models if m['id'] == parsed_input['model_a']['name']), None)
    if model_a:
        model_a_date = datetime.fromtimestamp(model_a['created'], tz=timezone.utc).strftime('%Y-%m-%d')
        if model_a_date == parsed_input['model_a']['date']:
            score += 4
            debug_info.append(f"4 points awarded: {parsed_input['model_a']['name']} was created on {model_a_date}")
        else:
            debug_info.append(f"0 points: {parsed_input['model_a']['name']} was created on {model_a_date}, not {parsed_input['model_a']['date']}")
    else:
        debug_info.append(f"0 points: {parsed_input['model_a']['name']} not found in the model list")

    # 2 points if model_b is at the specified index
    if parsed_input['model_b']['index'] < len(sorted_models):
        model_at_index = sorted_models[parsed_input['model_b']['index']]['id']
        if model_at_index == parsed_input['model_b']['name']:
            score += 2
            debug_info.append(f"2 points awarded: {parsed_input['model_b']['name']} is at index {parsed_input['model_b']['index']}")
        else:
            debug_info.append(f"0 points: {model_at_index} is at index {parsed_input['model_b']['index']}, not {parsed_input['model_b']['name']}")
    else:
        debug_info.append(f"0 points: Index {parsed_input['model_b']['index']} is out of range")

    # 1 point if model_c was created num_models before model_d
    index_c = next((i for i, m in enumerate(sorted_models) if m['id'] == parsed_input['model_cd']['name_c']), -1)
    index_d = next((i for i, m in enumerate(sorted_models) if m['id'] == parsed_input['model_cd']['name_d']), -1)
    if index_c != -1 and index_d != -1:
        actual_diff = index_c - index_d - 1  # Changed this line as requested
        if actual_diff == parsed_input['model_cd']['num']:
            score += 1
            debug_info.append(f"1 point awarded: {parsed_input['model_cd']['name_c']} was created {actual_diff} models before {parsed_input['model_cd']['name_d']}")
        else:
            debug_info.append(f"0 points: {parsed_input['model_cd']['name_c']} was created {actual_diff} models before {parsed_input['model_cd']['name_d']}, not {parsed_input['model_cd']['num']}")
    else:
        debug_info.append(f"0 points: One or both models not found in the list")

    return score, debug_info

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        input_string = request.form['input']
        api_key = request.form['api_key']

        try:
            parsed_input = parse_input(input_string)
            cutoff_date = datetime.strptime(parsed_input['date'], '%d %B %Y')

            response = requests.get(
                "https://aiproxy.sanand.workers.dev/openai/v1/models",
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}'
                }
            )
            response.raise_for_status()

            data = response.json()
            filtered_models = [
                model for model in data['data']
                if datetime.fromtimestamp(model['created'], tz=timezone.utc) < cutoff_date.replace(tzinfo=timezone.utc)
            ]

            score, debug_info = calculate_score(parsed_input, filtered_models)
            return render_template('index.html', result=f"The correct total of points is: {score}", debug_info=debug_info)

        except requests.RequestException as e:
            return render_template('index.html', error="Failed to fetch models: " + str(e))
        except ValueError as e:
            return render_template('index.html', error=str(e))
        except Exception as e:
            return render_template('index.html', error="An unexpected error occurred: " + str(e))

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)