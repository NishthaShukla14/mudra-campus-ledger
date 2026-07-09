# Mudra Campus Ledger

Mudra Campus Ledger is a lightweight web-based ledger and expense-tracking application for campus groups, student organizations, and small clubs. It provides an easy interface to record incomes and expenses, view balances and transaction history, and generate simple reports for transparent financial record-keeping.

> This README was generated and replaces an earlier draft. Please update any framework-specific commands, environment variables, and badges to match the actual project details.

## Project status

- Languages: HTML (~58%) and Python (~42%)
- Likely stack: HTML front-end with a Python back-end (Django, Flask, or similar). The repository previously referenced Django in its roadmap — adjust below steps if you use a different framework.

## Features

- User authentication and profile/dashboard
- Record transactions (income / expense) with date, category, and notes
- View transaction history and running balance
- Simple analytics and charts (transaction summaries by category / date)
- SQLite-friendly storage for quick setup (replace with PostgreSQL/MySQL in production)

## Quick start (generic Python)

1. Clone the repository

```bash
git clone https://github.com/NishthaShukla14/mudra-campus-ledger.git
cd mudra-campus-ledger
```

2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # macOS / Linux
# or on Windows (PowerShell)
# venv\Scripts\Activate.ps1
```

3. Install dependencies (if provided)

```bash
pip install -r requirements.txt
```

4. Configure environment variables

Create a `.env` file or export these as environment variables. Example:

```env
SECRET_KEY=replace-with-secret
DATABASE_URL=sqlite:///data/mudra_ledger.db
FLASK_ENV=development  # or DJANGO settings as appropriate
```

5. Initialize the database

- If the project is Django:

```bash
python manage.py migrate
python manage.py createsuperuser  # optional
```

- If the project is Flask or another framework, run the provided DB init script (if any) or follow the project-specific instructions.

6. Run the app

- Django example:

```bash
python manage.py runserver
```

- Flask example (if applicable):

```bash
export FLASK_APP=app.py
flask run
```

Open the local URL printed by the server (commonly http://127.0.0.1:8000 or http://127.0.0.1:5000).

## Configuration

- Keep secrets (SECRET_KEY, DB credentials) out of version control.
- Static files and templates should live in `static/` and `templates/` as per your chosen framework.
- Use environment variables or a config file for production settings.

## Suggested data model

- Transaction: id, date, amount, type (income/expense), category, note, created_by
- Category: id, name, description

Adjust the schema to fit your requirements and the chosen web framework's ORM.

## Testing

If tests exist, run them with pytest or the project's test runner:

```bash
pytest
# or for Django
python manage.py test
```

Add unit tests for key logic (balance calculations, import/export, permissions) if not present.

## Contributing

Contributions are welcome. Suggested workflow:

1. Fork the repo and create a branch: `git checkout -b feature/my-change`
2. Implement your change and add tests
3. Commit and push, then open a pull request describing your change

Please keep PRs focused and include screenshots or steps to reproduce when reporting bugs.

## Roadmap / TODO (from previous notes)

- Add/verify user authentication and authorization
- Implement transfer/fee payment flow and ledger updates
- Add CSV import/export and reporting (monthly/quarterly summaries)
- Improve analytics and charting
- Add automated tests and CI pipeline
- Containerize (Docker) and provide deployment instructions

## License

This repository currently has no license file. Add a LICENSE (for example MIT or Apache-2.0) if you want to make the project's license explicit.

## Maintainer

NishthaShukla14

For issues or feature requests, please open an issue in this repository.
