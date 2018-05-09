unit:
	pytest -v

coverage:
	pytest --cov=smashctl --cov-report=html --cov-report=term-missing
