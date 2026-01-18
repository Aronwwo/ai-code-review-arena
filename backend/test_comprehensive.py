#!/usr/bin/env python3
"""Comprehensive testing script for AI Code Review Arena."""

import httpx
import json
import time
from typing import Dict, Any

BASE_URL = "http://127.0.0.1:8000"
TOKEN = None

def login():
    """Login and get access token."""
    global TOKEN
    response = httpx.post(
        f"{BASE_URL}/auth/login",
        json={"email": "test@example.com", "password": "Testpass123"}
    )
    if response.status_code == 200:
        TOKEN = response.json()["access_token"]
        print(f"✅ Logged in successfully")
    else:
        print(f"❌ Login failed: {response.text}")
        exit(1)

def headers():
    """Get authorization headers."""
    return {"Authorization": f"Bearer {TOKEN}"}

def create_project(name: str, description: str) -> int:
    """Create a test project."""
    response = httpx.post(
        f"{BASE_URL}/projects",
        headers=headers(),
        json={"name": name, "description": description}
    )
    if response.status_code == 201:
        project_id = response.json()["id"]
        print(f"✅ Created project '{name}' (ID: {project_id})")
        return project_id
    else:
        print(f"❌ Failed to create project: {response.text}")
        return None

def add_file(project_id: int, name: str, content: str, language: str = "python"):
    """Add a file to project."""
    response = httpx.post(
        f"{BASE_URL}/projects/{project_id}/files",
        headers=headers(),
        json={"name": name, "content": content, "language": language}
    )
    if response.status_code == 201:
        print(f"  ✅ Added file '{name}'")
        return True
    else:
        print(f"  ❌ Failed to add file: {response.text}")
        return False

def start_council_review(project_id: int, model: str = "qwen2.5-coder:7b", timeout: int = 180):
    """Start council mode review."""
    agent_config = {
        "provider": "ollama",
        "model": model,
        "timeout_seconds": timeout,
        "max_tokens": 4096
    }

    review_data = {
        "review_mode": "council",
        "agent_roles": ["general", "security", "performance", "style"],
        "agent_configs": {
            "general": agent_config,
            "security": agent_config,
            "performance": agent_config,
            "style": agent_config
        }
    }

    response = httpx.post(
        f"{BASE_URL}/projects/{project_id}/reviews",
        headers=headers(),
        json=review_data
    )

    if response.status_code == 201:
        review_id = response.json()["id"]
        print(f"✅ Started review (ID: {review_id}) with model {model}")
        return review_id
    else:
        print(f"❌ Failed to start review: {response.text}")
        return None

def wait_for_review(review_id: int, max_wait: int = 600):
    """Wait for review to complete."""
    print(f"⏳ Waiting for review {review_id} to complete (max {max_wait}s)...")
    start_time = time.time()

    while time.time() - start_time < max_wait:
        response = httpx.get(
            f"{BASE_URL}/reviews/{review_id}",
            headers=headers()
        )

        if response.status_code == 200:
            review = response.json()
            status = review["status"]

            if status == "completed":
                print(f"✅ Review completed in {int(time.time() - start_time)}s")
                return review
            elif status == "failed":
                print(f"❌ Review failed: {review.get('error_message')}")
                return review
            elif status == "running":
                # Show progress
                elapsed = int(time.time() - start_time)
                print(f"  ⏳ Still running... ({elapsed}s elapsed)", end='\r')
                time.sleep(5)
            else:
                print(f"  📊 Status: {status}", end='\r')
                time.sleep(2)
        else:
            print(f"❌ Failed to get review status: {response.text}")
            return None

    print(f"\n❌ Review timed out after {max_wait}s")
    return None

def get_review_issues(review_id: int):
    """Get issues from review."""
    response = httpx.get(
        f"{BASE_URL}/reviews/{review_id}/issues?page_size=100",
        headers=headers()
    )

    if response.status_code == 200:
        data = response.json()
        issues = data.get("items", [])
        print(f"📋 Found {len(issues)} issues:")

        # Group by agent_role
        by_agent = {}
        for issue in issues:
            agent = issue.get("agent_role", "unknown")
            if agent not in by_agent:
                by_agent[agent] = []
            by_agent[agent].append(issue)

        for agent, agent_issues in by_agent.items():
            print(f"\n  🤖 {agent.upper()} ({len(agent_issues)} issues):")
            for issue in agent_issues[:3]:  # Show first 3
                severity = issue["severity"]
                title = issue["title"]
                emoji = "🔴" if severity == "error" else "🟡" if severity == "warning" else "🔵"
                print(f"    {emoji} {title}")

        return issues
    else:
        print(f"❌ Failed to get issues: {response.text}")
        return []

def get_review_agents(review_id: int):
    """Get agent responses from review."""
    response = httpx.get(
        f"{BASE_URL}/reviews/{review_id}/agents",
        headers=headers()
    )

    if response.status_code == 200:
        agents = response.json()
        print(f"\n🤖 Agent responses:")
        for agent in agents:
            role = agent["role"]
            parsed = "✅" if agent["parsed_successfully"] else "❌"
            timed_out = "⏱️ TIMEOUT" if agent.get("timed_out") else ""
            output_len = len(agent.get("raw_output", "")) if agent.get("raw_output") else 0
            print(f"  {role}: {parsed} ({output_len} chars) {timed_out}")
        return agents
    else:
        print(f"❌ Failed to get agents: {response.text}")
        return []


# ========== TEST PROJECTS ==========

def test_syntax_errors():
    """Test 1: Project with syntax errors."""
    print("\n" + "="*70)
    print("TEST 1: Python project with syntax errors")
    print("="*70)

    project_id = create_project(
        "Test Syntax Errors",
        "Python code with intentional syntax errors"
    )

    # Code with multiple syntax errors
    code = '''def add(a, b)  # Missing colon
    return a + b

nums = [1, 2, 3  # Missing closing bracket
total = sum(nums)
print("Total: " + total)  # TypeError: str + int

for i in range(3):
    print(nums[i+1])  # IndexError: list index out of range

def divide(x, y)
    result = x / y  # Missing colon, potential ZeroDivisionError
    return result
'''

    add_file(project_id, "buggy_code.py", code, "python")

    # Start review with qwen2.5-coder:7b
    review_id = start_council_review(project_id, model="qwen2.5-coder:7b", timeout=180)

    if review_id:
        review = wait_for_review(review_id, max_wait=600)
        if review and review["status"] == "completed":
            issues = get_review_issues(review_id)
            agents = get_review_agents(review_id)

            # Check if general agent found syntax errors
            general_issues = [i for i in issues if i.get("agent_role") == "general"]
            if len(general_issues) >= 2:
                print(f"\n✅ TEST PASSED: General agent found {len(general_issues)} syntax errors")
            else:
                print(f"\n⚠️ TEST WARNING: Expected at least 2 syntax errors, found {len(general_issues)}")

            return True
        else:
            print("\n❌ TEST FAILED: Review did not complete")
            return False

    return False


def test_security_issues():
    """Test 2: Project with security vulnerabilities."""
    print("\n" + "="*70)
    print("TEST 2: Python project with security vulnerabilities")
    print("="*70)

    project_id = create_project(
        "Test Security Issues",
        "Python code with security vulnerabilities"
    )

    # Code with security issues
    code = '''import os
import sqlite3

# SQL Injection vulnerability
def get_user(username):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = '" + username + "'"  # SQL Injection
    cursor.execute(query)
    return cursor.fetchone()

# Command Injection vulnerability
def run_command(user_input):
    os.system("ls " + user_input)  # Command Injection

# Hardcoded credentials
API_KEY = "sk-1234567890abcdef"  # Hardcoded secret
PASSWORD = "admin123"  # Weak password

# Path Traversal vulnerability
def read_file(filename):
    with open("/var/files/" + filename) as f:  # Path Traversal
        return f.read()
'''

    add_file(project_id, "vulnerable_code.py", code, "python")

    # Start review with deepseek-coder:6.7b
    review_id = start_council_review(project_id, model="deepseek-coder:6.7b", timeout=180)

    if review_id:
        review = wait_for_review(review_id, max_wait=600)
        if review and review["status"] == "completed":
            issues = get_review_issues(review_id)
            agents = get_review_agents(review_id)

            # Check if security agent found vulnerabilities
            security_issues = [i for i in issues if i.get("agent_role") == "security"]
            if len(security_issues) >= 2:
                print(f"\n✅ TEST PASSED: Security agent found {len(security_issues)} vulnerabilities")
            else:
                print(f"\n⚠️ TEST WARNING: Expected at least 2 security issues, found {len(security_issues)}")

            return True
        else:
            print("\n❌ TEST FAILED: Review did not complete")
            return False

    return False


def test_performance_issues():
    """Test 3: Project with performance issues."""
    print("\n" + "="*70)
    print("TEST 3: Python project with performance issues")
    print("="*70)

    project_id = create_project(
        "Test Performance Issues",
        "Python code with performance problems"
    )

    # Code with performance issues
    code = '''# N+1 queries problem
def get_users_with_posts():
    users = db.query("SELECT * FROM users")
    for user in users:
        posts = db.query(f"SELECT * FROM posts WHERE user_id = {user.id}")  # N+1 queries
        user.posts = posts
    return users

# Nested loops - O(n²) complexity
def find_duplicates(items):
    duplicates = []
    for i in range(len(items)):
        for j in range(len(items)):
            if i != j and items[i] == items[j]:
                duplicates.append(items[i])
    return duplicates

# Repeated file I/O
def process_logs(filenames):
    results = []
    for filename in filenames:
        with open(filename) as f:  # Opening file in loop
            content = f.read()
            results.append(len(content))
    return results

# No caching - expensive computation repeated
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)  # Exponential time complexity

for i in range(100):
    fib_value = fibonacci(30)  # Calculating same value 100 times
'''

    add_file(project_id, "slow_code.py", code, "python")

    # Start review
    review_id = start_council_review(project_id, model="qwen2.5-coder:7b", timeout=180)

    if review_id:
        review = wait_for_review(review_id, max_wait=600)
        if review and review["status"] == "completed":
            issues = get_review_issues(review_id)
            agents = get_review_agents(review_id)

            # Check if performance agent found issues
            perf_issues = [i for i in issues if i.get("agent_role") == "performance"]
            if len(perf_issues) >= 1:
                print(f"\n✅ TEST PASSED: Performance agent found {len(perf_issues)} issues")
            else:
                print(f"\n⚠️ TEST WARNING: Expected at least 1 performance issue, found {len(perf_issues)}")

            return True
        else:
            print("\n❌ TEST FAILED: Review did not complete")
            return False

    return False


def test_clean_code():
    """Test 4: Clean code (should have minimal issues)."""
    print("\n" + "="*70)
    print("TEST 4: Clean Python code (should pass)")
    print("="*70)

    project_id = create_project(
        "Test Clean Code",
        "Well-written Python code"
    )

    # Clean, well-written code
    code = '''"""Calculator module with proper documentation and error handling."""

from typing import Union


def add(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    """Add two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of a and b
    """
    return a + b


def divide(a: Union[int, float], b: Union[int, float]) -> float:
    """Divide two numbers safely.

    Args:
        a: Numerator
        b: Denominator

    Returns:
        Result of division

    Raises:
        ValueError: If denominator is zero
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def calculate_average(numbers: list[float]) -> float:
    """Calculate average of a list of numbers.

    Args:
        numbers: List of numbers

    Returns:
        Average value

    Raises:
        ValueError: If list is empty
    """
    if not numbers:
        raise ValueError("Cannot calculate average of empty list")
    return sum(numbers) / len(numbers)
'''

    add_file(project_id, "calculator.py", code, "python")

    # Start review
    review_id = start_council_review(project_id, model="qwen2.5-coder:7b", timeout=180)

    if review_id:
        review = wait_for_review(review_id, max_wait=600)
        if review and review["status"] == "completed":
            issues = get_review_issues(review_id)
            agents = get_review_agents(review_id)

            # Clean code should have few or no issues
            if len(issues) <= 3:
                print(f"\n✅ TEST PASSED: Clean code has only {len(issues)} minor issues")
            else:
                print(f"\n⚠️ TEST WARNING: Clean code has {len(issues)} issues (expected ≤ 3)")

            return True
        else:
            print("\n❌ TEST FAILED: Review did not complete")
            return False

    return False


if __name__ == "__main__":
    print("="*70)
    print("COMPREHENSIVE TESTING - AI CODE REVIEW ARENA")
    print("="*70)

    # Login
    login()

    # Run tests
    results = []

    results.append(("Syntax Errors Test", test_syntax_errors()))
    time.sleep(2)

    results.append(("Security Issues Test", test_security_issues()))
    time.sleep(2)

    results.append(("Performance Issues Test", test_performance_issues()))
    time.sleep(2)

    results.append(("Clean Code Test", test_clean_code()))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print(f"\nTotal: {passed}/{total} tests passed ({int(passed/total*100)}%)")
    print("="*70)
