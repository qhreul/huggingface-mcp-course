<div>
    <h1>HuggingFace Model Context Protocol Course</h1>
</div>

<p align="center">
    <a href="https://www.python.org/downloads/release/python-31111/">
        <img alt="python" src="https://img.shields.io/badge/python-3.11-blue.svg"/>
    </a>
      <a href="https://python-poetry.org/">
    <img alt="poetry" src="https://img.shields.io/pypi/v/poetry?label=poetry">
  </a>
  <a href="https://github.com/qhreul/huggingface-mcp-course/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-Apache%202.0-green"/>
  </a>
</p>

## Table of Content
- [Description](#description)
- [Getting started](#getting-started)
  - [Requirements](#requirements)
  - [Set up Environment](#set-up-environment)

## Description
The [HuggingFace Model Context Protocol (MCP) Course](https://huggingface.co/learn/mcp-course/), developed in 
collaboration with Anthropic, teaches the theory, design, and practical use of MCP for building AI applications that 
leverage external data and tools.

## Getting started

### Requirements
- Git 
- Python >=3.11, <3.12
- [Poetry](https://python-poetry.org/) >= 2.0

### Set up Environment
1. Configure access to Poetry virtual environment
   ```
   poetry config virtualenvs.in-project true
   ```
2. Install dependencies
   ```
   poetry install
   ```
3. Select Poetry virtual environment as Jupyter kernel
   1. Activate the Poetry virtual environment
   ```
   poetry env activate
   ```