# AI Assistance Log

Document every time you used an AI tool during this project: what you asked, what it gave you, and what you changed before using it.

This is not about proving you worked hard. It is about building the habit of treating AI output as a first draft, not a final answer.

## Tools used

- ChatGPT
- Claude in VS Code

## Log

### Entry 1 Pydantic model and validation debugging

**What I asked:** I asked for help understanding why some Pydantic tests failed and why some valid records were rejected by the pipeline.

**What it gave me:** The AI helped identify that the cleaned category names in the pipeline did not always match the allowed categories in the Pydantic model.

**What I changed:** I corrected the allowed categories and mapping logic so that valid records were accepted and intentionally invalid records were rejected. I reran the tests until they passed.

### Entry 2 Pipeline debugging

**What I asked:** I asked for help debugging pipeline errors during local runs.

**What it gave me:** The AI helped explain the difference between cleaning errors, validation errors, missing environment variables, and expected invalid rows.

**What I changed:** I updated the pipeline so that invalid records were logged and skipped instead of stopping the full run. I verified that the pipeline processed 44 valid rows and skipped 6 intentionally invalid rows.

### Entry 3 Azure Postgres and Blob Storage

**What I asked:** I asked for help with Azure Postgres, Blob Storage, DBeaver connection setup, and environment variable issues.

**What it gave me:** The AI explained how to structure the storage step, how to separate .env, how to avoid committing secrets, and how to verify Postgres tables and Blob Storage outputs.

**What I changed:** I filled in the real environment variables locally, connected to Postgres through DBeaver, verified the created tables, uploaded the input CSV to Blob Storage, and confirmed that cleaned and summary files were visible in Azure Blob Storage.

### Entry 4 Docker troubleshooting

**What I asked:** I asked for help when Docker Desktop was not running, when Docker could not read the .env file, and when the container could not find the input CSV in Blob Storage.

**What it gave me:** The AI helped explain Docker Engine errors, .env syntax problems, and Blob path issues.

**What I changed:** I fixed the .env file by removing export and quotation marks around connection strings. I uploaded the input CSV to the correct Blob path and reran the Docker container until it completed successfully.

### Entry 5 Claude in VS Code

**What I asked:** I used Claude in VS Code to help inspect code structure, understand error messages, and review changes while editing project files.

**What it gave me:** Claude helped point out syntax issues, formatting problems, and places where the code or documentation did not match the project structure.

**What I changed:** I reviewed the suggestions before applying them. I kept only the changes that matched my project and tested the pipeline, tests, Docker run, Postgres output, and Blob Storage output afterward.
