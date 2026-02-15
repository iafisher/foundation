[working-directory: 'python']
publish-to-pypi:
  poetry publish --build

[working-directory: 'python']
test:
  python3 -m unittest discover -s iafisher_foundation -t .
