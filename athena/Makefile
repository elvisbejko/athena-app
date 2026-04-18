clean:
	find -type d -name __pycache__ -exec rm -rfv {} +

tree:
	tree --dirsfirst

lexicon:
	grep -winr --exclude-dir=.venv "class" . | awk '{print $$2}'
