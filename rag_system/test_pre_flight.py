# preflight_experiment_with_extractor.py - MCQ mode, extract answers directly

import json
import time
import requests
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
import random

# ============================================
# Configuration
# ============================================
RAG_API_URL = "http://localhost:8000/api/query"

# Local dataset path
LOCAL_DATASET_PATH = "/root/autodl-tmp/data/datasets/pre-flight/pre-flight-06.jsonl"

# Experiment configuration
OUTPUT_DIR = "/root/autodl-tmp/data/datasets/pre-flight/experiment_results"

# ============================================
# 🎯 Test mode configuration
# ============================================
TEST_MODE = "sample"

SAMPLE_CONFIG = {
    "international airport ground operations": 30,
    "ICAO rules and regulations": 20,
    "FAA rules and regulations": 15,
    "aviation trivia": -1,
    "complex ground scenarios": -1
}

# ============================================
# Category definitions
# ============================================
CATEGORY_RANGES = {
    "international airport ground operations": (0, 151),
    "ICAO rules and regulations": (152, 236),
    "FAA rules and regulations": (237, 287),
    "aviation trivia": (288, 295),
    "complex ground scenarios": (296, 299)
}

CATEGORY_NAMES = {
    "international airport ground operations": "Ground Operations",
    "ICAO rules and regulations": "ICAO",
    "FAA rules and regulations": "FAA",
    "aviation trivia": "Trivia",
    "complex ground scenarios": "Complex Scenarios"
}

def get_category_display(category: str) -> str:
    return CATEGORY_NAMES.get(category, category)

def get_category_by_index(idx: int) -> str:
    for category, (start, end) in CATEGORY_RANGES.items():
        if start <= idx <= end:
            return category
    return "unknown"

# ============================================

def load_local_dataset(filepath: str) -> List[Dict]:
    print(f"📥 Loading local dataset: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"❌ File does not exist: {filepath}")
        return None
    
    dataset = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if line:
                try:
                    item = json.loads(line)
                    item['_index'] = idx
                    item['_category'] = get_category_by_index(idx)
                    dataset.append(item)
                except json.JSONDecodeError:
                    continue
    
    print(f"✅ Loaded successfully, {len(dataset)} questions total")
    
    print("\n📊 Full dataset category distribution:")
    cat_counter = Counter([item['_category'] for item in dataset])
    for cat, count in cat_counter.items():
        display_name = get_category_display(cat)
        print(f"   {display_name}: {count} questions")
    
    return dataset

def sample_dataset(dataset: List[Dict], sample_config: Dict) -> List[Dict]:
    if not sample_config:
        return dataset
    
    categorized = defaultdict(list)
    for item in dataset:
        cat = item['_category']
        categorized[cat].append(item)
    
    sampled = []
    sampling_info = []
    
    for cat, items in categorized.items():
        total = len(items)
        sample_size = sample_config.get(cat, -1)
        
        if sample_size == -1 or sample_size >= total:
            sampled.extend(items)
            sampling_info.append(f"   {get_category_display(cat)}: {total}/{total} (all)")
        else:
            sampled_items = random.sample(items, sample_size)
            sampled.extend(sampled_items)
            sampling_info.append(f"   {get_category_display(cat)}: {sample_size}/{total} (sampled)")
    
    random.shuffle(sampled)
    
    print("\n📊 Sampling statistics:")
    for info in sampling_info:
        print(info)
    print(f"\n   Total: {len(sampled)} questions")
    
    return sampled

def format_question(item: Dict) -> str:
    question = item.get("input", item.get("question", ""))
    options = item.get("choices", item.get("options", []))
    choices = [f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)]
    return f"{question}\n\nOptions:\n" + "\n".join(choices)

def query_rag_system(question: str, timeout: int = 60) -> Dict[str, Any]:
    payload = {
        "query": question,
        "aircraft_type": "general",
        "context": {"source": "pre-flight-benchmark"}
    }
    
    try:
        response = requests.post(RAG_API_URL, json=payload, timeout=timeout)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}
    except requests.exceptions.Timeout:
        return {"error": "Request timeout"}
    except requests.exceptions.ConnectionError:
        return {"error": "Connection error"}
    except Exception as e:
        return {"error": str(e)}

# ============================================
# 🔧 Simplified extraction: directly match "Answer: X"
# ============================================

def extract_answer_direct(response: Dict) -> str:
    """
    Robustly extract the answer from the framework response.
    Supports multiple formats:
    - "C"
    - "**C**"
    - "**C. Chapter 5**"
    - "Answer: C"
    - "Correct Option: C"
    - "C. Chapter 5"
    - "The answer is C"
    - "Option C is correct"
    """
    final_response = response.get("final_response", "")
    
    if "error" in response:
        return "NO_MATCH"
    
    # First extract the first line (the answer is usually on the first line)
    lines = final_response.strip().split('\n')
    first_line = lines[0].strip() if lines else ""
    
    # Method 1: find the first occurrence of an option letter (A-E), supporting various formats
    # Match patterns: standalone letter, bold, with dot, with parentheses, etc.
    patterns = [
        # Exactly match a single letter (including bold)
        r'\*\*?([A-E])\*\*?\.?\s*',           # **C** or **C.**
        r'^([A-E])\s*[\.\)]',                 # C. or C)
        r'\b([A-E])\b\s*[\.\)]',              # C. after a word boundary
        r'([A-E])\s*[\.\)]\s*[A-Za-z]',       # C. Chapter
        r'\*\*([A-E])\.\s*[A-Za-z]',          # **C. Chapter**
        r'\*\*([A-E])\*\*',                   # **C**
        r'^([A-E])$',                         # a single line with C
        r'[Aa]nswer\s*:\s*([A-E])',          # Answer: C
        r'[Cc]orrect\s*[Oo]ption\s*:\s*([A-E])',  # Correct Option: C
        r'[Tt]he\s*correct\s*answer\s*is\s*([A-E])',  # The correct answer is C
        r'[Tt]he\s*answer\s*is\s*([A-E])',    # The answer is C
        r'[Oo]ption\s*([A-E])\s*is\s*correct', # Option C is correct
    ]
    
    # First search the entire response (not limited to the first line)
    for pattern in patterns:
        match = re.search(pattern, final_response, re.IGNORECASE | re.MULTILINE)
        if match:
            letter = match.group(1).upper()
            if letter in ['A', 'B', 'C', 'D', 'E']:
                return letter
    
    # Method 2: find option letters at the start of a line
    for line in lines:
        line = line.strip()
        # Remove Markdown markers
        cleaned = re.sub(r'\*\*', '', line)
        cleaned = re.sub(r'__', '', cleaned)
        cleaned = re.sub(r'#+\s*', '', cleaned)
        cleaned = cleaned.strip()
        
        # Check if it starts with an option letter
        if len(cleaned) >= 1 and cleaned[0].upper() in ['A', 'B', 'C', 'D', 'E']:
            return cleaned[0].upper()
        
        # Check "X." or "X)" format
        match = re.match(r'^\s*([A-E])\s*[\.\)]', cleaned)
        if match:
            return match.group(1).upper()
    
    # Method 3: find option letters appearing anywhere (last resort)
    for letter in ['A', 'B', 'C', 'D', 'E']:
        # Look for \bC\b or **C**
        if re.search(rf'\b{letter}\b', final_response) or re.search(rf'\*\*{letter}\*\*', final_response):
            # Make sure it is not a substring like "ABC" or "CD"
            if not re.search(rf'[A-Z]{letter}[A-Z]', final_response):
                return letter
    
    # If all methods fail
    return "NO_MATCH"

def run_experiment(dataset, output_file: str = None):
    """Run the experiment - extract answers directly, no second LLM extraction needed"""
    
    total = len(dataset)
    
    print("\n" + "="*80)
    print("🚀 Starting Pre-Flight experiment (direct answer extraction)")
    print("="*80)
    print(f"Test count: {total}")
    print(f"Output file: {output_file}")
    print("="*80)
    
    results = []
    correct = 0
    total_questions = 0
    category_stats = defaultdict(lambda: {"correct": 0, "total": 0, "ids": []})
    agent_combination_stats = defaultdict(lambda: {"correct": 0, "total": 0})
    all_times = []
    errors = []
    no_match_count = 0
    
    experiment_start = time.time()
    
    for i, item in enumerate(dataset):
        total_questions += 1
        
        question_text = item.get("input", item.get("question", ""))
        options = item.get("choices", item.get("options", []))
        question = format_question(item)
        correct_answer = item.get("target", item.get("answer", "")).upper()
        category = item.get('_category', 'unknown')
        category_display = get_category_display(category)
        item_id = item.get("id", f"item_{i+1:04d}")
        question_short = question_text[:150]
        
        print(f"\n📝 [{i+1}/{total}] ID: {item_id}")
        print(f"   Category: {category_display}")
        print(f"   Question: {question_short}...")
        print(f"   Correct answer: {correct_answer}")
        
        query_start = time.time()
        response = query_rag_system(question)
        query_time = time.time() - query_start
        all_times.append(query_time)
        rag_response = response.get("final_response", "")
        
        # ========== Extract answer directly ==========
        model_answer = extract_answer_direct(response)
        
        if model_answer == "NO_MATCH":
            no_match_count += 1
        
        selected_agents = response.get("selected_agents", [])
        agents_str = "+".join(sorted(selected_agents)) if selected_agents else "none"
        
        is_correct = (model_answer == correct_answer)
        
        if is_correct:
            correct += 1
            category_stats[category]["correct"] += 1
            agent_combination_stats[agents_str]["correct"] += 1
        category_stats[category]["total"] += 1
        category_stats[category]["ids"].append(item_id)
        agent_combination_stats[agents_str]["total"] += 1
        
        if not is_correct:
            error_entry = {
                "id": item_id,
                "category": category,
                "category_display": category_display,
                "correct": correct_answer,
                "model": model_answer,
                "agents": selected_agents,
                "agents_str": agents_str,
                "question": question_text[:200],
                "response": rag_response[:500]
            }
            errors.append(error_entry)
        
        result = {
            "id": item_id,
            "category": category,
            "category_display": category_display,
            "question": question_text,
            "correct_answer": correct_answer,
            "model_answer": model_answer,
            "is_correct": is_correct,
            "response_time": query_time,
            "selected_agents": selected_agents,
            "agents_str": agents_str,
            "router_intent": response.get("router_decision", {}).get("intent", "N/A"),
            "extraction_method": "direct"
        }
        results.append(result)
        
        status = "✅" if is_correct else "❌"
        print(f"{status} Model: {model_answer} | Correct: {correct_answer} | Agent: {agents_str} | Time: {query_time:.2f}s")
        print(f"   Response preview: {rag_response[:80]}...")
        
        time.sleep(0.3)
    
    total_time = time.time() - experiment_start
    accuracy = correct / total_questions * 100 if total_questions > 0 else 0
    avg_time = sum(all_times) / len(all_times) if all_times else 0
    
    # Generate report
    report_lines = []
    report_lines.append("="*80)
    report_lines.append("✈️  Pre-Flight experiment report (direct answer extraction)")
    report_lines.append("="*80)
    report_lines.append(f"Experiment time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Test mode: {TEST_MODE.upper()}")
    report_lines.append(f"Test questions: {total_questions}")
    report_lines.append(f"Extraction method: direct regex extraction (Answer: X)")
    report_lines.append(f"NO_MATCH: {no_match_count} questions")
    report_lines.append("="*80)
    report_lines.append("")
    
    # Detailed results per question
    report_lines.append("[Per-Question Detailed Results]")
    report_lines.append("-"*80)
    for i, r in enumerate(results, 1):
        status = "✅ PASS" if r["is_correct"] else "❌ FAIL"
        report_lines.append(f"\n{i:04d}. [{status}] ID: {r['id']}")
        report_lines.append(f"   Category: {r['category_display']}")
        report_lines.append(f"   Question: {r['question']}")
        report_lines.append(f"   Correct answer: {r['correct_answer']}")
        report_lines.append(f"   Model answer: {r['model_answer']}")
        report_lines.append(f"   Agents used: {r['agents_str']}")
        report_lines.append(f"   Time: {r['response_time']:.2f}s")
    
    report_lines.append("")
    report_lines.append("="*80)
    
    # Statistics summary
    report_lines.append("[Statistics Summary]")
    report_lines.append("-"*80)
    report_lines.append(f"Total questions: {total_questions}")
    report_lines.append(f"Correct count: {correct}")
    report_lines.append(f"Error count: {total_questions - correct}")
    report_lines.append(f"Accuracy: {accuracy:.2f}%")
    report_lines.append(f"Total time: {total_time:.2f}s")
    report_lines.append(f"Average response time: {avg_time:.2f}s")
    report_lines.append(f"NO_MATCH: {no_match_count} questions")
    report_lines.append("")
    
    # Statistics by category
    report_lines.append("[Statistics by Category]")
    report_lines.append("-"*80)
    for cat, stats in sorted(category_stats.items()):
        if stats["total"] > 0:
            cat_acc = stats["correct"] / stats["total"] * 100
            display_name = get_category_display(cat)
            report_lines.append(f"  {display_name:30s}: {stats['correct']:3d}/{stats['total']:3d} ({cat_acc:5.1f}%)")
    report_lines.append("")
    
    # Agent combination statistics
    report_lines.append("[Agent Combination Statistics]")
    report_lines.append("-"*80)
    for agents, stats in sorted(agent_combination_stats.items(), key=lambda x: -x[1]["total"]):
        if stats["total"] > 0:
            acc = stats["correct"] / stats["total"] * 100
            report_lines.append(f"  {agents:40s}: {stats['correct']:3d}/{stats['total']:3d} ({acc:5.1f}%)")
    report_lines.append("")
    
    # Usage frequency of each Agent
    report_lines.append("[Usage Frequency of Each Agent]")
    report_lines.append("-"*80)
    agent_freq = defaultdict(int)
    for r in results:
        for agent in r["selected_agents"]:
            agent_freq[agent] += 1
    for agent, count in sorted(agent_freq.items(), key=lambda x: -x[1]):
        pct = count / total_questions * 100 if total_questions > 0 else 0
        report_lines.append(f"  {agent:25s}: {count:3d} times ({pct:5.1f}%)")
    report_lines.append("")
    
    # List of incorrect questions
    report_lines.append("[Incorrect Questions List]")
    report_lines.append("-"*80)
    if errors:
        report_lines.append(f"{len(errors)} incorrect questions total:")
        for e in errors:
            report_lines.append(f"  ❌ {e['id']} [{e['category_display']}]: model={e['model']}, correct={e['correct']}, Agent={e['agents_str']}")
            report_lines.append(f"     Question: {e['question']}")
            report_lines.append(f"     Framework response: {e['response'][:200]}...")
    else:
        report_lines.append("  🎉 All correct!")
    
    report_lines.append("")
    report_lines.append("="*80)
    report_lines.append("Experiment complete")
    report_lines.append("="*80)
    
    report = "\n".join(report_lines)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n💾 Report saved to: {output_file}")
    
    if errors:
        error_file = output_file.replace('.txt', '_errors.json') if output_file else None
        if error_file:
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "total_errors": len(errors),
                    "no_match_count": no_match_count,
                    "errors": errors
                }, f, ensure_ascii=False, indent=2)
            print(f"💾 Error cases saved to: {error_file}")
    
    print("\n" + "="*80)
    print("📊 Experiment complete!")
    print("="*80)
    print(f"Accuracy: {accuracy:.2f}% ({correct}/{total_questions})")
    print(f"Total time: {total_time:.2f}s")
    print(f"Average response time: {avg_time:.2f}s")
    print(f"NO_MATCH: {no_match_count} questions")
    print(f"Results saved to: {output_file}")
    print("="*80)
    
    return results, {
        "total": total_questions,
        "correct": correct,
        "accuracy": accuracy,
        "total_time": total_time,
        "avg_time": avg_time,
        "no_match_count": no_match_count
    }

def main():
    print("="*80)
    print("✈️  Pre-Flight experiment tool (direct answer extraction)")
    print("="*80)
    print(f"Experiment time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Test mode: {TEST_MODE.upper()}")
    print("="*80)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_suffix = "full" if TEST_MODE == "full" else "sample"
    output_file = os.path.join(OUTPUT_DIR, f"preflight_experiment_direct_{mode_suffix}_{timestamp}.txt")
    
    print(f"\n🔍 Checking RAG service...")
    try:
        resp = requests.get("http://localhost:8000/", timeout=5)
        if resp.status_code == 200:
            print("✅ RAG service is running normally")
        else:
            print(f"⚠️ RAG service abnormal response: {resp.status_code}")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Unable to connect to the RAG service; please make sure the system is running")
        return
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return
    
    dataset = load_local_dataset(LOCAL_DATASET_PATH)
    if dataset is None:
        return
    
    if TEST_MODE == "sample":
        print(f"\n📊 Sampling configuration:")
        for cat, size in SAMPLE_CONFIG.items():
            display_name = get_category_display(cat)
            if size == -1:
                print(f"   {display_name}: test all")
            else:
                print(f"   {display_name}: sample {size} questions")
        
        test_dataset = sample_dataset(dataset, SAMPLE_CONFIG)
    else:
        test_dataset = dataset
        print(f"\n📊 Full test: {len(test_dataset)} questions")
    
    results, stats = run_experiment(test_dataset, output_file)
    
    print(f"\n✅ Experiment complete! Accuracy: {stats['accuracy']:.2f}%")
    print(f"   Results file: {output_file}")

if __name__ == "__main__":
    random.seed(42)
    main()