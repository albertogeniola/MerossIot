REM Before continuing, make sure to set username and password with
REM keyring set https://upload.pypi.org/legacy/ your-username
python setup.py sdist
twine upload dist/*