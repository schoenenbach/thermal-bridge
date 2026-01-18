---
description: Wrap up work with README/ROADMAP updates and a gitmoji commit
---

# Wrap Up Commit Workflow

This workflow wraps up the work done during this chat session by updating documentation and creating a well-structured commit.

## Steps

### 1. Update Documentation

1. **Review README.md** - Check if any changes made during this session affect user-facing features, installation, configuration, or usage. If so, update the relevant sections.

2. **Check ROADMAP.md** - If the work completed relates to a roadmap item:
   - Mark the completed item as done (e.g., `[x]` or strikethrough)
   - Update any related progress notes
   - If partially complete, note the current status

### 2. Prepare the Commit

3. **Identify changed files** - Review all files that were modified, created, or deleted during this conversation. This includes:
   - Code changes made by the agent
   - README.md updates (if made)
   - ROADMAP.md updates (if made)

4. **Check git status** - Run `git status` to confirm which files have changes.

5. **Stage only relevant files** - Stage ONLY the files that were modified as part of this chat session using `git add <file1> <file2> ...`. Do NOT stage unrelated changes.

6. **Determine the appropriate gitmoji** - Select ONE gitmoji that best describes the primary change:
   - ✨ `:sparkles:` - New feature
   - 🐛 `:bug:` - Bug fix
   - ♻️ `:recycle:` - Refactor code
   - 📝 `:memo:` - Documentation only
   - 🎨 `:art:` - Improve structure/format
   - ⚡ `:zap:` - Performance improvement
   - 🔧 `:wrench:` - Configuration files
   - ✅ `:white_check_mark:` - Add/update tests
   - 🔥 `:fire:` - Remove code/files
   - 🚀 `:rocket:` - Deploy/release
   - 💄 `:lipstick:` - UI/style changes
   - 🏗️ `:building_construction:` - Architectural changes
   - ➕ `:heavy_plus_sign:` - Add dependency
   - ➖ `:heavy_minus_sign:` - Remove dependency
   - 🔒 `:lock:` - Security fix
   
   Full list: https://gitmoji.dev

7. **Write commit message following Chris Beams' rules**:
   - **Subject line**: Start with gitmoji, then imperative mood summary (max 50 chars after emoji)
   - **Blank line** between subject and body
   - **Body** (if needed): Explain *what* and *why*, not *how*. Wrap at 72 characters. Put most effort on the why of the change. What is the driver of changing something.
   
   Example format:
   ```
   ✨ Add user authentication endpoint
   
   Implement JWT-based authentication for the API. This replaces the
   previous session-based approach to better support mobile clients.
   
   - Add /auth/login and /auth/refresh endpoints
   - Include token expiration handling
   - Update README with auth configuration
   ```

8. **Create the commit** - Run `git commit -m "<subject>" -m "<body>"` or use `git commit` with an editor for multi-line messages.

9. **Verify the commit** - Run `git log -1` to confirm the commit was created correctly.

## Chris Beams' Seven Rules

1. Separate subject from body with a blank line
2. Limit the subject line to 50 characters (excluding gitmoji)
3. Capitalize the subject line
4. Do not end the subject line with a period
5. Use the imperative mood in the subject line ("Add feature" not "Added feature")
6. Wrap the body at 72 characters
7. Use the body to explain *what* and *why* vs. *how*

Reference: https://cbea.ms/git-commit/