from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import Number
import random
from typing import List, Tuple
from pathlib import Path
from datetime import datetime


def format_value(val: float):
    return f"{val:.5f}".rstrip('0').rstrip('.') if val % 1 else str(int(val))


def apply_operation(op, a, b):
    if op == '+':
        return a + b
    elif op == '-':
        return a - b
    elif op == '*':
        return round(a * b, 5)
    elif op == '/':
        return round(a / b, 5)
    return 0


def get_operations(numbers):
    next_level = []
    operations = []
    for i in range(len(numbers) - 1):
        a, b = numbers[i], numbers[i + 1]
        if b.value == 0:
            op = random.choice(['+', '-', '*'])
        else:
            op = random.choice(['+', '-', '*', '/'])
        val = apply_operation(op, a.value, b.value)
        base = random.randint(2, 10)
        digits = Number.decimal_to_digits(base, abs(int(val)))
        res = Number(base=base, digits=digits, value=val, negative=val < 0)
        next_level.append(res)
        operations.append((op, i, i + 1))
    return next_level, operations


def build_graph_edges(levels, operations_map):
    edges = []
    op_nodes = []
    for lvl, ops in operations_map.items():
        for i, (op, a_idx, b_idx) in enumerate(ops):
            from_a = f"L{lvl-1}_{a_idx}"
            from_b = f"L{lvl-1}_{b_idx}"
            result = f"L{lvl}_{i}"
            op_node = f"OP_{lvl}_{i}"
            op_nodes.append((op_node, op))

            edges.append((from_a, op_node))
            edges.append((from_b, op_node))
            edges.append((op_node, result))
    return edges, op_nodes


def generate_log_filename(user: str, num: int):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{user.replace(' ', '_')}_logs_{num}_{timestamp}.txt"
    return filename


def start_view(request):
    if request.method == 'POST':
        user = request.POST.get('user')
        request.session['user'] = user
        request.session['attempts'] = []
        request.session['attempt_number'] = 1

        levels, operations_map, display_data, correct_answers = generate_data()

        request.session['data'] = {
            'levels': {str(k): [(n.base, n.digits, n.value, n.negative) for n in v] for k, v in levels.items()},
            'operations_map': {str(k): v for k, v in operations_map.items()},
            'display_data': display_data,
        }

        request.session['correct_answers'] = {str(k): v for k, v in correct_answers.items()}

        graph_edges, op_nodes = build_graph_edges(levels, operations_map)
        node_labels = {}
        node_levels = {}

        for lvl, nums in levels.items():
            for i, n in enumerate(nums):
                node_id = f"L{lvl}_{i}"
                node_labels[node_id] = str(n)
                node_levels[node_id] = lvl

        for op_id, op in op_nodes:
            node_labels[op_id] = op
            node_levels[op_id] = int(op_id.split('_')[1])

        request.session['graph_edges'] = graph_edges
        request.session['op_nodes'] = op_nodes
        request.session['node_labels'] = node_labels
        request.session['node_levels'] = node_levels

        return redirect('quiz')

    return render(request, 'tasks/main.html')


def quiz_view(request):
    user = request.session.get('user')
    if not user:
        return redirect('main')

    attempt_number = request.session.get('attempt_number', 1)
    data = request.session.get('data')
    correct_answers = request.session.get('correct_answers')

    levels = {}
    for k, v in data['levels'].items():
        level_values = []
        for base, digits, value, negative in v:
            number = Number(base=base, digits=digits, value=value, negative=negative)
            level_values.append(number)
        levels[int(k)] = level_values

    operations_map = {int(k): v for k, v in data['operations_map'].items()}
    display_data = data['display_data']

    if request.method == 'POST':
        user_answers = {}
        for lvl_ops in display_data:
            lvl = lvl_ops['level']
            user_answers[lvl] = {}
            for row in lvl_ops['rows']:
                key = f"answer_{lvl}_{row['index']}"
                try:
                    user_val = float(request.POST.get(key))
                    user_val = round(user_val, 5)
                except (ValueError, TypeError):
                    user_val = None
                user_answers[lvl][row['index']] = user_val

        log = [f"Прогон №{attempt_number}, пользователь: {user}"]
        log.append("===" * 20)
        log.append(f"Дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log.append("===" * 20)

        log.append("=== Уровень 0 ====")
        for i, n in enumerate(levels[0]):
            log.append(f"y(0,{i}) = {n} = {format_value(n.value)}")

        for lvl in range(1, len(levels)):
            log.append(f"\n=== Уровень {lvl} ===")
            current = levels[lvl - 1]
            operations = get_operations_from_data(operations_map[lvl])
            for i, (op, a_idx, b_idx) in enumerate(operations):
                a = current[a_idx]
                b = current[b_idx]
                res_val = format_value(apply_operation(op, a.value, b.value))
                log.append(
                    f"y({lvl},{i}) = y({lvl - 1},{a_idx}) {op} y({lvl - 1},{b_idx}) = {a.value} {op} {b.value} = {res_val} → {a} {op} {b}"
                )

        log.append("\n=== Проверка ответов ===")
        correct = 0
        for lvl in user_answers:
            for i, (u, c) in enumerate(zip(user_answers[lvl].values(), correct_answers[str(lvl)])):
                if u is None:
                    ok = False
                elif isinstance(c, float):
                    ok = abs(u - c) < 0.0001
                else:
                    ok = u == c
                log.append(f"Ур.{lvl} Оп.{i + 1}: ваш {u} → {'верно' if ok else f'неверно (Правильный ответ: {format_value(c)})'}")
                correct += int(ok)

        score = int(correct >= 1)
        log.append(f"\nИтоговая оценка: {score}")
        log.append("===" * 20)

        attempts = request.session.get('attempts', [])
        attempts.append(score)
        request.session['attempts'] = attempts
        request.session['attempt_number'] = attempt_number + 1
        request.session['log_data'] = '\n'.join(log)

        del request.session['data']
        del request.session['correct_answers']

        return redirect('result')

    return render(request, 'tasks/quiz.html', {
        'display_data': display_data,
        'attempt_number': attempt_number,
        'user': user
    })


def result_view(request):
    attempts = request.session.get('attempts', [])
    best_score = max(attempts) if attempts else 0
    user = request.session.get('user')
    attempt_number = request.session.get('attempt_number', 1)
    log_data = request.session.get('log_data', '')

    graph_edges = request.session.get('graph_edges', [])
    op_nodes = request.session.get('op_nodes', [])
    node_labels = request.session.get('node_labels', {})
    node_levels = request.session.get('node_levels', {})

    if request.method == 'POST':
        comment = request.POST.get('comment', '')
        log_data += f"\nКомментарий: {comment}"
        request.session['log_data'] = log_data

    log_filename = generate_log_filename(user, attempt_number)

    return render(request, 'tasks/result.html', {
        'score': best_score,
        'attempts': attempts,
        'attempt_number': attempt_number,
        'user': user,
        'log_data': log_data,
        'log_filename': log_filename,
        'graph_edges': graph_edges,
        'op_nodes': op_nodes,
        'node_labels': node_labels,
        'node_levels': node_levels,
    })


def generate_data():
    levels = {0: [Number.random() for _ in range(random.randint(3, 5))]}
    operations_map = {}
    correct_answers = {}
    lvl = 1
    current = levels[0]

    while len(current) > 1:
        next_level, ops = get_operations(current)
        levels[lvl] = next_level
        operations_map[lvl] = ops
        correct_answers[lvl] = [round(apply_operation(op, current[a].value, current[b].value), 5) for op, a, b in ops]
        current = next_level
        lvl += 1

    display_data = []
    for lvl, ops in operations_map.items():
        rows = []
        prev_level = levels[lvl - 1]
        for i, (op, a_idx, b_idx) in enumerate(ops):
            rows.append({
                'index': i,
                'a': str(prev_level[a_idx]),
                'b': str(prev_level[b_idx]),
                'op': op
            })
        display_data.append({'level': lvl, 'rows': rows})

    return levels, operations_map, display_data, correct_answers


def get_operations_from_data(operations_data):
    return [(op, a_idx, b_idx) for op, a_idx, b_idx in operations_data]
