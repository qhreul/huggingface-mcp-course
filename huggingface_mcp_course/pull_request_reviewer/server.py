import aiofiles
from datetime import datetime
import json
from pathlib import Path
import os
import subprocess
import traceback
from typing import Optional

from mcp.server.fastmcp import FastMCP

from huggingface_mcp_course.pull_request_reviewer.webhook_server import EVENTS_FILE
from huggingface_mcp_course.utils import ioutils

# Directory containing Markdown Templates for Pull Requests depending on type of changes
PR_TEMPLATES_DIR = 'huggingface_mcp_course/pull_request_reviewer/templates'

# Initialize the FastMCP server
mcp = FastMCP('pr-agent')


def generate_error_response(message: str, stacktrace:str = None, code: int = 500) -> str:
    """
    Generate an error message to be returned
    :param message: The message describing the error.
    :param stacktrace: The stacktrace associated with the error.
    :param code: The error code
    :return: A JSON object with the information
    """
    error_response = {
        "error": {
            "code": code,
            "message": message,
            "stacktrace": stacktrace
        }
    }
    return json.dumps(error_response)

# ===== Module 1 Tools =====
@mcp.tool()
async def analyze_file_changes(base_branch: str = 'main', include_diff: bool = True,  max_diff_lines: int = 500) -> str:
    """
    Get the full list of diff and changed files in the current git repository
    :param base_branch: Base branch to compare against (default = "main")
    :param include_diff: Include the full diff content (default = True)
    :param max_diff_lines: Maximum number of diff lines to include (default: 500)
    :return: the full list of diff and changed files
    """
    try:
        # TODO Access working directory from roots (i.e. if working_directory is None)
        # Get current directory
        current_working_directory = os.getcwd()

        # Get list of changed files
        files_result = subprocess.run(
            ['git', 'diff', '--name-status', f'{base_branch}...HEAD'],
            capture_output=True,
            text=True,
            check=True,
            cwd=current_working_directory
        )

        # Get diff statistics
        stat_result = subprocess.run(
            ["git", "diff", "--stat", f"{base_branch}...HEAD"],
            capture_output=True,
            text=True,
            cwd=current_working_directory
        )

        # Get the actual diff if requested
        diff_content = ""
        truncated = False
        if include_diff:
            diff_result = subprocess.run(
                ["git", "diff", f"{base_branch}...HEAD"],
                capture_output=True,
                text=True,
                cwd=current_working_directory
            )
            diff_lines = diff_result.stdout.split('\n')
            
            # IMPORTANT: MCP tools have a 25,000 token response limit!
            # Check if we need to truncate
            if len(diff_lines) > max_diff_lines:
                diff_content = '\n'.join(diff_lines[:max_diff_lines])
                diff_content += f"\n\n... Output truncated. Showing {max_diff_lines} of {len(diff_lines)} lines ..."
                diff_content += "\n... Use max_diff_lines parameter to see more ..."
                truncated = True
            else:
                diff_content = diff_result.stdout

        # Get commit messages for context
        commits_result = subprocess.run(
            ["git", "log", "--oneline", f"{base_branch}..HEAD"],
            capture_output=True,
            text=True,
            cwd=current_working_directory
        )

        analysis = {
            "base_branch": base_branch,
            "files_changed": files_result.stdout,
            "statistics": stat_result.stdout,
            "commits": commits_result.stdout,
            "diff": diff_content if include_diff else "Diff not included (set include_diff=true to see full diff)",
            "truncated": truncated,
            "total_diff_lines": len(diff_lines) if include_diff else 0
        }

        return json.dumps(analysis, indent=2)

    except subprocess.CalledProcessError as e:
        return json.dumps({"error": f"Git error: {e.stderr}"})
    except Exception:
        return generate_error_response(f'Error analyzing the changes against the {base_branch} branch',
                                       traceback.format_exc())



@mcp.tool()
async def get_pr_templates() -> str:
    """
    List available Pull Request templates with their content
    :return: list of available Pull Request templates
    """
    try:
        templates = []
        # Iterate through the list of templates
        for filename in os.listdir(PR_TEMPLATES_DIR):
            print(f'Filename: {filename}')
            file_path = os.path.join(PR_TEMPLATES_DIR, filename)
            print(f'File path: {file_path}')
            # Check that file is a file before opening
            if os.path.isfile(file_path):
                file_details = {"filename": filename, "type": filename.split('.')[0].lower()}
                # Retrieve the data from the file
                file_data = await ioutils.read_file(str(file_path))
                file_details["content"] = file_data
                # Add details of the template to the array
                templates.append(file_details)
        return json.dumps(templates, indent=2)

    except Exception:
        return generate_error_response(f'Error retrieving files from folder = "{PR_TEMPLATES_DIR}"',
                                       traceback.format_exc())

@mcp.tool()
async def suggest_pr_template(changes_summary: str, change_type: str) -> str:
    """
    Let a LLM analyze the changes and suggest the most appropriate Pull Request template
    :param changes_summary: Analysis of what the changes do
    :param change_type: Type of change you've identified (e.g. bug, feature, docs, refactor, etc.)
    :return: Suggested Pull Request template
    """
    try:
        # Retrieve details about the available templates
        template_response = await get_pr_templates()
        template_list = json.loads(template_response)
        print(template_list)

        # Determine matching template
        suggested_template = {}
        for template in template_list:
            if template["type"] == change_type:
                suggested_template = template
                break

        # Generate & return the suggested pull request template
        if len(suggested_template) > 0:
            suggestion = {
                "recommended_template": suggested_template,
                "reasoning": f"Based on your analysis: '{changes_summary}', this appears to be a {change_type} change.",
                "template_content": suggested_template["content"],
                "usage_hint": "LLM can help you fill out this template based on the specific changes in your PR."
            }
            return json.dumps(suggestion, indent=2)
        else:
            return generate_error_response(f'Not Pull Request template were found for {change_type}')

    except Exception:
        return generate_error_response('Error while suggesting which Pull Request template to use',
                                       traceback.format_exc())

# ===== Module 2 Tools: GitHub Actions Tools =====
@mcp.tool()
async def get_recent_actions_events(limit: int = 10) -> str:
    """
    Get recent GitHub Actions events received via webhook.
    :param limit:  Maximum number of events to return (default: 10)
    :return: A list of GitHub Actions events
    """
    # Check that the EVENTS_FILE exists and return empty list if not
    if not ioutils.file_exists(EVENTS_FILE):
        return json.dumps([])

    # Open file to access events
    events = ioutils.read_file_json(EVENTS_FILE)

    # Return most recent events
    recent = events[-limit:]
    return json.dumps(recent, indent=2)

@mcp.tool()
async def get_workflow_status(workflow_name: Optional[str] = None) -> str:
    """
    Get the current status of GitHub Actions workflows.
    :param workflow_name: Optional specific workflow name to filter by
    :return: A JSON object with workflow status information
    """
    if not ioutils.file_exists(EVENTS_FILE):
        return generate_error_response("No GitHub Actions events received yet", code=404)

    # Open file to access events
    events = ioutils.read_file_json(EVENTS_FILE)

    # Check whether file contains any events
    if not events:
        return generate_error_response("No GitHub Actions events received yet", code=404)

    # Filter for workflow events
    workflow_events = [
        e for e in events
        if e.get("workflow_run") is not None
    ]

    if workflow_name:
        workflow_events = [
            e for e in workflow_events
            if e["workflow_run"].get("name") == workflow_name
        ]

    # Group by workflow and get latest status
    workflows = {}
    for event in workflow_events:
        run = event["workflow_run"]
        name = run["name"]
        if name not in workflows or run["updated_at"] > workflows[name]["updated_at"]:
            workflows[name] = {
                "name": name,
                "status": run["status"],
                "conclusion": run.get("conclusion"),
                "run_number": run["run_number"],
                "updated_at": run["updated_at"],
                "html_url": run["html_url"]
            }

    return json.dumps(list(workflows.values()), indent=2)

# ===== Module 2: MCP Prompts =====
@mcp.prompt()
async def analyze_ci_results() -> str:
    """
    Analyze recent CI/CD results and provide insights.
    :return: A string with instructions for a LLM to:
        1. Use get_recent_actions_events()
        2. Use get_workflow_status()
        3. Analyze results and provide insights
    """
    return """Please analyze the recent CI/CD results from GitHub Actions:
    1. First, call get_recent_actions_events() to fetch the latest CI/CD events
    2. Then call get_workflow_status() to check current workflow states
    3. Identify any failures or issues that need attention
    4. Provide actionable next steps based on the results

    Format your response as:
    ## CI/CD Status Summary
    - **Overall Health**: [Good/Warning/Critical]
    - **Failed Workflows**: [List any failures with links]
    - **Successful Workflows**: [List recent successes]
    - **Recommendations**: [Specific actions to take]
    - **Trends**: [Any patterns you notice]"""

@mcp.prompt()
async def create_deployment_summary() -> str:
    """
    Generate a deployment summary for team communication.
    :return: A string that guides a LLM to create a deployment summary
    """
    return """Create a deployment summary for team communication:
    1. Check workflow status with get_workflow_status()
    2. Look specifically for deployment-related workflows
    3. Note the deployment outcome, timing, and any issues

    Format as a concise message suitable for Slack:
    🚀 **Deployment Update**
    - **Status**: [✅ Success / ❌ Failed / ⏳ In Progress]
    - **Environment**: [Production/Staging/Dev]
    - **Version/Commit**: [If available from workflow data]
    - **Duration**: [If available]
    - **Key Changes**: [Brief summary if available]
    - **Issues**: [Any problems encountered]
    - **Next Steps**: [Required actions if failed]

    Keep it brief but informative for team awareness."""

@mcp.prompt()
async def generate_pr_status_report() -> str:
    """
    Generate a comprehensive PR status report including CI/CD results.
    :return: A string that guides a LLM to combine code changes with CI/CD status
    """
    return """Generate a comprehensive PR status report:
    1. Use analyze_file_changes() to understand what changed
    2. Use get_workflow_status() to check CI/CD status
    3. Use suggest_template() to recommend the appropriate PR template
    4. Combine all information into a cohesive report
    
    Your report must follow this Markdown format:
    ## 📋 PR Status Report

    ### 📝 Code Changes
    - **Files Modified**: [Count of files by extension, e.g., 5 .py, 2 .yml]
    - **Change Type**: [Infer one: Feature, Bug Fix, Refactor, Chore, Docs, Testing]
    - **Impact Assessment**: [High, Medium, or Low, with a brief justification]
    - **Key Changes**:
        - [Bulleted list summarizing the most important modifications]

    ### 🔄 CI/CD Status
    - **All Checks**: [Provide a single status: ✅ Passing, ❌ Failing, or ⏳ Running]
    - **Test Results**: [Summarize test outcomes, e.g., "152/152 passed" or "148/152 passed, 4 failed". List failed tests if applicable.]
    - **Build Status**: [Summarize build outcome, e.g., "Build successful" or "Build failed on step 'X'."]
    - **Code Quality**: [Report on linting, code coverage, or other quality gates if data is available.]

    ### 📌 Recommendations
    - **PR Template**: [Suggest the most appropriate PR template type (e.g., Feature, Bug Fix) and explain why.]
    - **Next Steps**: [List clear, actionable steps required for this PR to be merged, e.g., "Address failing tests," "Request review from the backend team."]
    - **Reviewers**: [Suggest 2-3 potential reviewers based on the files and code changed.]

    ### ⚠️ Risks & Considerations
    - [Identify any potential deployment risks, performance impacts, or security concerns.]
    - [Explicitly state if there are any breaking changes.]
    - [Mention any important dependencies that are added, removed, or updated.]"""

@mcp.prompt()
async def troubleshoot_workflow_failure() -> str:
    """
    Help troubleshoot a failing GitHub Actions workflow.
    :return: A string that guides Claude through troubleshooting steps
    """
    return """Help troubleshoot failing GitHub Actions workflows:
    1. Use get_recent_actions_events() to find recent failures
    2. Use get_workflow_status() to see which workflows are failing
    3. Analyze the failure patterns and timing
    4. Provide systematic troubleshooting steps

    Structure your response as:

    ## 🔧 Workflow Troubleshooting Guide

    ### ❌ Failed Workflow Details
    - **Workflow Name**: [Name of failing workflow]
    - **Failure Type**: [Test/Build/Deploy/Lint]
    - **First Failed**: [When did it start failing]
    - **Failure Rate**: [Intermittent or consistent]

    ### 🔍 Diagnostic Information
    - **Error Patterns**: [Common error messages or symptoms]
    - **Recent Changes**: [What changed before failures started]
    - **Dependencies**: [External services or resources involved]

    ### 💡 Possible Causes (ordered by likelihood)
    1. **[Most Likely]**: [Description and why]
    2. **[Likely]**: [Description and why]
    3. **[Possible]**: [Description and why]

    ### ✅ Suggested Fixes
    **Immediate Actions:**
    - [ ] [Quick fix to try first]
    - [ ] [Second quick fix]

    **Investigation Steps:**
    - [ ] [How to gather more info]
    - [ ] [Logs or data to check]

    **Long-term Solutions:**
    - [ ] [Preventive measure]
    - [ ] [Process improvement]

    ### 📚 Resources
    - [Relevant documentation links]
    - [Similar issues or solutions]"""


if __name__ == "__main__":
    print("Starting Pull Request Agent MCP server...")
    print("To receive GitHub webhooks, run the webhook server separately:")
    print("  python webhook_server.py")
    mcp.run()