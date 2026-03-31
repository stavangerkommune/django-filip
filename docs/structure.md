# Project Structure
This documentation explains how Django apps in the project are organized, and the intended use of various modules (.py files).

## helpers.py
Used for internal helper functions that are small, reusable, and do not represent business logic.

Examples: data formatting, conversion, small validation functions.

- Not intended as a public interface to other apps
- Keep functions simple and focused
- Avoid letting this grow into a "dump" file

## services.py
External API's at the moment, for use in quick scripts that don't need a whole Django installation.

## Other Files
- models.py: Database models and related methods
- utils.py: Avoid utils.py. Use helpers.py or services.py instead