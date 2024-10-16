
# AURA (Advanced User Response Agent) Usage Instructions

AURA is a custom Discord bot that handles user queries, processes uploaded files, and manages conversation memory. This guide explains how to interact with AURA using commands that follow the format: `aura, <command>`.

## Table of Contents
1. [General Usage](#general-usage)
2. [Commands](#commands)
    - [List Files](#list-files)
    - [Upload and Review Files](#upload-and-review-files)
    - [Delete Files](#delete-files)
    - [File Questions](#file-questions)

---

## General Usage

To use AURA, simply type commands in your Discord channel in the following format:

```
aura, <command>
```

AURA will respond based on the recognized commands.

---

## Commands

### List Files
- **Usage**: `aura, list files`
- **Description**: AURA will list all the files uploaded to the current guild (server). The bot retrieves the file names from its stored directory and displays them.

### Upload and Review Files
- **Usage**: 
  - Direct Upload: Upload a file to the Discord channel, then type `aura, please review this file`.
  - Reply to File: If a file has already been uploaded in the chat, reply to the file message with the command `aura, please review this file`.
- **Description**: AURA will review and process the uploaded file, whether it's uploaded directly or if you're replying to a previously uploaded file in the chat.

### Delete Files
- **Usage**: `aura, delete the <file-name> file`
- **Description**: AURA will delete the specified file from the guild's directory. If the file is not found, AURA will notify the user.

### File Questions
- **Usage**: `aura, question about the <file-name> file. <your-question>`
- **Description**: Ask AURA a question about a specific file. The bot will retrieve the file and attempt to answer the question based on its content.

---

## Customization

You can extend AURA's capabilities by modifying its codebase, such as adding new file handling commands or integrating additional APIs. AURA currently supports file-based interactions and will respond based on the files stored on the server.
