import aiofiles
from datetime import datetime
import json
import os
import subprocess
import traceback
from typing import Optional

from mcp.server.fastmcp import FastMCP


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
            file_path = os.path.join(PR_TEMPLATES_DIR, filename)
            # Check that file is a file before opening
            if os.path.isfile(file_path):
                file_details = {"filename": filename, "type": filename.split('.')[0].lower()}
                # Open the file and retrieve its content
                async with aiofiles.open(file_path, 'r') as content:
                    file_details["content"] = await content.read()
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

if __name__ == "__main__":
    print("Starting Pull Request Agent MCP server...")
    mcp.run()