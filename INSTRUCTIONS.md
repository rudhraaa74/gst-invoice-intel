# Repository Structure Instructions

This document outlines the strict rules for organizing files and directories within this repository. Please adhere to these guidelines to maintain a clean and manageable project structure.

## Directory Structure Rules

1.  **`/notebooks`**: 
    *   **Strict Rule**: ALL Jupyter notebooks (`.ipynb` files) must be placed in this directory. Do not place notebooks in the root directory or any other folders.

2.  **`/scripts`**: 
    *   **Strict Rule**: ALL standalone Python scripts (`.py` files), shell scripts (`.sh` files), and other executable scripts used for processing, training, or automation must be placed in this directory.

3.  **`/data`**:
    *   **Strict Rule**: This directory is reserved strictly for datasets. No code or notebooks should be placed here.
    *   **`/data/raw`**: Place all unmodified, raw data files here exactly as they are received or downloaded. **Do not modify these files.**
    *   **`/data/clean`**: Place all processed, cleaned, and transformed data files here. These are the outputs of your data processing scripts.

By following these rules, we ensure reproducibility and clarity across the project.
